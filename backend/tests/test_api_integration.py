from collections.abc import Generator
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.user import User


def test_auth_transactions_dashboard_and_tenant_isolation() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        privacy_policy = client.get("/api/v1/telegram/privacy-policy")
        assert privacy_policy.status_code == 200
        policy = privacy_policy.json()
        assert policy["version"] == "2026-08-10"
        assert policy["content_sha256"] == sha256(
            policy["content"].encode("utf-8")
        ).hexdigest()
        immutable_policy = client.get(policy["privacy_policy_url"])
        assert immutable_policy.status_code == 200
        assert immutable_policy.json() == policy

        register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "primeiro@example.com",
                "password": "Senha-segura1",
                "full_name": "Primeiro",
            },
        )
        assert register.status_code == 201
        # RegisterRequest já valida complexidade — não há o que migrar aqui.
        assert register.json()["user"]["must_change_password"] is False
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

        telegram_link = client.post(
            "/api/v1/telegram/link",
            headers=headers,
            json={"consent": True, "consent_version": policy["version"]},
        )
        assert telegram_link.status_code == 200
        assert telegram_link.json()["consent_version"] == policy["version"]
        assert (
            telegram_link.json()["privacy_policy_url"]
            == policy["privacy_policy_url"]
        )
        assert telegram_link.json()["deep_link"].startswith("https://t.me/bot_de_teste")

        stale_consent = client.post(
            "/api/v1/telegram/link",
            headers=headers,
            json={"consent": True, "consent_version": "versao-antiga"},
        )
        assert stale_consent.status_code == 409

        created = client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "description": "Mercado",
                "amount": "10.005",
                "category": "Alimentação",
                "type": "expense",
                "occurred_at": "2026-08-07T12:00:00-03:00",
            },
        )
        assert created.status_code == 201
        assert created.json()["amount"] == "10.01"

        listing = client.get("/api/v1/transactions", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        summary = client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["expense"] == "10.01"
        assert summary.json()["balance"] == "-10.01"

        second = client.post(
            "/api/v1/auth/register",
            json={"email": "segundo@example.com", "password": "Senha-segura1"},
        )
        second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
        second_listing = client.get("/api/v1/transactions", headers=second_headers)
        assert second_listing.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_login_migrates_must_change_password_flag_for_legacy_accounts() -> None:
    """Conta anterior à regra de complexidade: o login é o único ponto que ainda
    vê a senha em claro para descobrir se ela precisa trocar (bcrypt não
    devolve a senha original a partir do hash — não dá para varrer isso offline).
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        # Inserida direto no banco, contornando o RegisterRequest — do jeito que
        # uma conta criada antes desta regra (ou por scripts/criar_usuario.py,
        # antes do fix) estaria hoje.
        db = testing_session()
        db.add(
            User(
                email="legado@example.com",
                full_name="Conta antiga",
                hashed_password=hash_password("senhafraca"),
                must_change_password=True,
            )
        )
        db.commit()
        db.close()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "legado@example.com", "password": "senhafraca"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["must_change_password"] is True

        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Bloqueio de verdade, não só um aviso que o front pode ignorar: com a
        # senha pendente, toda rota de dado financeiro devolve 403 — mesmo com
        # um access token válido. Um token roubado não compra acesso.
        blocked = client.get("/api/v1/transactions", headers=headers)
        assert blocked.status_code == 403

        blocked_portfolio = client.get("/api/v1/investments/portfolio", headers=headers)
        assert blocked_portfolio.status_code == 403

        # Mas quem está bloqueado ainda alcança a saída: ver quem é, trocar a
        # senha e sair — nunca fica preso sem jeito de resolver a pendência.
        still_me = client.get("/api/v1/auth/me", headers=headers)
        assert still_me.status_code == 200
        assert still_me.json()["must_change_password"] is True

        change = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "senhafraca", "new_password": "Senha-Nova1!"},
        )
        assert change.status_code == 200
        # A senha nova já passou pela validação de complexidade — a pendência some.
        assert change.json()["user"]["must_change_password"] is False

        new_headers = {"Authorization": f"Bearer {change.json()['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=new_headers)
        assert me.status_code == 200
        assert me.json()["must_change_password"] is False

        # Acesso normal restaurado depois da troca.
        unblocked = client.get("/api/v1/transactions", headers=new_headers)
        assert unblocked.status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_login_does_not_flag_legacy_accounts_whose_password_already_complies() -> None:
    """Senha antiga que por acaso já cumpre a regra nova não pede troca à toa."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        db = testing_session()
        db.add(
            User(
                email="sortudo@example.com",
                hashed_password=hash_password("Senha-Forte1"),
                must_change_password=True,  # como toda linha migrada pela alembic
            )
        )
        db.commit()
        db.close()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "sortudo@example.com", "password": "Senha-Forte1"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["must_change_password"] is False
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_blocked_account_keeps_the_right_to_leave() -> None:
    """`must_change_password=True` barra o resto da API, mas não vira uma cela:
    a pessoa ainda consegue apagar a própria conta sem resolver a pendência
    primeiro (o direito de exclusão não pode depender de política de senha).
    Já editar o nome do perfil (PATCH /me) e listar sessões seguem trancados,
    mesmo não sendo dado financeiro — a exceção é só o que a docstring de
    `require_password_compliant_user` lista.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        db = testing_session()
        db.add(
            User(
                email="preso@example.com",
                hashed_password=hash_password("senhafraca"),
                must_change_password=True,
            )
        )
        db.commit()
        db.close()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "preso@example.com", "password": "senhafraca"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        blocked_rename = client.patch(
            "/api/v1/auth/me", headers=headers, json={"full_name": "Novo Nome"}
        )
        assert blocked_rename.status_code == 403

        blocked_sessions = client.get("/api/v1/auth/sessions", headers=headers)
        assert blocked_sessions.status_code == 403

        deleted = client.delete("/api/v1/auth/me", headers=headers)
        assert deleted.status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
