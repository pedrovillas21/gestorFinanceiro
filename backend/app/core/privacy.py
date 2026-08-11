"""Políticas de privacidade publicadas e imutáveis do canal Telegram."""

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from types import MappingProxyType


@dataclass(frozen=True)
class PrivacyPolicy:
    version: str
    title: str
    published_at: date
    content: str

    @property
    def content_sha256(self) -> str:
        return sha256(self.content.encode("utf-8")).hexdigest()


_POLICY_2026_08_10 = PrivacyPolicy(
    version="2026-08-10",
    title="Política de Privacidade do canal Telegram",
    published_at=date(2026, 8, 10),
    content=(
        "Ao conectar sua conta ao bot do Gestor Financeiro, tratamos seu "
        "identificador de chat do Telegram, as mensagens e os áudios que você "
        "envia ao bot e os lançamentos financeiros extraídos desse conteúdo.\n\n"
        "Usamos esses dados exclusivamente para vincular o chat à sua conta, "
        "interpretar comandos, registrar transações e responder consultas "
        "financeiras solicitadas por você. Mensagens e áudios podem ser enviados "
        "ao Google Gemini para extração e interpretação. O Telegram também trata "
        "os dados necessários para entregar as mensagens, conforme os próprios "
        "termos e política da plataforma.\n\n"
        "Armazenamos o vínculo com o chat, a versão e o momento deste consentimento "
        "e as transações confirmadas. Pendências de confirmação expiram "
        "automaticamente. Tokens de conexão são temporários e de uso único. Os "
        "dados da conta permanecem até sua exclusão ou pelo período necessário "
        "para cumprir obrigações legais e de segurança.\n\n"
        "Não vendemos seus dados. O acesso é limitado aos serviços necessários "
        "para operar o Gestor Financeiro. Você pode deixar de usar o canal Telegram "
        "e excluir sua conta para remover os dados associados, observadas eventuais "
        "obrigações legais de retenção.\n\n"
        "Ao confirmar esta versão, você declara que leu esta política e autoriza "
        "o tratamento descrito para usar o canal Telegram."
    ),
)

# Uma versão publicada nunca deve ser alterada. Mudanças no texto exigem uma nova
# chave/versionamento para que o consentimento continue identificando o aviso exato.
PRIVACY_POLICIES = MappingProxyType({_POLICY_2026_08_10.version: _POLICY_2026_08_10})


def get_privacy_policy(version: str) -> PrivacyPolicy:
    """Retorna somente políticas efetivamente publicadas."""
    try:
        return PRIVACY_POLICIES[version]
    except KeyError as exc:
        raise KeyError(f"política de privacidade não publicada: {version}") from exc


def has_privacy_policy(version: str) -> bool:
    return version in PRIVACY_POLICIES
