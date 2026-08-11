from collections.abc import Generator
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app


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
                "password": "senha-segura",
                "full_name": "Primeiro",
            },
        )
        assert register.status_code == 201
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
            json={"email": "segundo@example.com", "password": "senha-segura"},
        )
        second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
        second_listing = client.get("/api/v1/transactions", headers=second_headers)
        assert second_listing.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
