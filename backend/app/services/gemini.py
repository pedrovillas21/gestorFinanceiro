"""Cascata do Gemini: extrai lançamentos financeiros de áudio ou texto (seção 4.2 do guia).

Tenta primeiro o modelo Flash mais recente e, em caso de falha (indisponibilidade,
quota, modelo removido), cai para o modelo estável configurado em `GEMINI_MODEL_FALLBACK`.
"""
import json
import logging
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

CATEGORIAS = [
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Compras",
    "Serviços",
    "Salário",
    "Investimentos",
    "Outros",
]

METODOS_PAGAMENTO = ["pix", "dinheiro", "débito", "crédito", "boleto", "transferência"]

PROMPT = f"""Você é o motor de extração de um gestor financeiro pessoal brasileiro.
Analise a mensagem do usuário (áudio ou texto) e devolva UM ÚNICO JSON com o lançamento descrito.

Regras:
- "tipo": "receita" (dinheiro que entrou) ou "despesa" (dinheiro que saiu).
- "valor": número positivo em reais. Converta por extenso: "quarenta e dois e noventa" -> 42.90.
- "descricao": resumo curto (até 60 caracteres) do que foi pago ou recebido.
- "categoria": escolha exatamente uma entre {", ".join(CATEGORIAS)}.
- "metodo_pagamento": um entre {", ".join(METODOS_PAGAMENTO)}; use null se não for citado.
- Se a mensagem NÃO descrever um lançamento financeiro, ou se o valor não estiver claro,
  devolva "eh_transacao": false e escreva em "observacao" uma frase curta, em português,
  explicando ao usuário o que ele deve enviar.
- Nunca invente valores nem categorias fora da lista."""


class TransacaoExtraida(BaseModel):
    """JSON estruturado devolvido pela IA."""

    eh_transacao: bool = Field(description="true somente se houver um lançamento financeiro claro")
    tipo: str | None = Field(default=None, description='"receita" ou "despesa"')
    valor: float | None = Field(default=None, description="Valor positivo em reais")
    descricao: str | None = Field(default=None, description="Resumo curto do lançamento")
    categoria: str | None = None
    metodo_pagamento: str | None = None
    observacao: str | None = Field(
        default=None, description="Mensagem ao usuário quando não houver transação"
    )


class GeminiIndisponivelError(RuntimeError):
    """Todos os modelos da cascata falharam."""


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Cliente único do google-genai (criado sob demanda para não exigir a chave no import)."""
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=PROMPT,
        response_mime_type="application/json",
        response_schema=TransacaoExtraida,
        temperature=0.1,
    )


def _parse(response) -> TransacaoExtraida:
    """Aceita tanto o objeto já validado (`parsed`) quanto o JSON cru em `text`."""
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, TransacaoExtraida):
        return parsed
    if isinstance(parsed, dict):
        return TransacaoExtraida.model_validate(parsed)
    if not response.text:
        raise ValueError("resposta vazia do Gemini")
    return TransacaoExtraida.model_validate(json.loads(response.text))


async def extrair_transacao(
    *,
    texto: str | None = None,
    audio: bytes | None = None,
    mime_type: str = "audio/ogg",
) -> TransacaoExtraida:
    """Envia texto ou áudio para a cascata do Gemini e devolve o lançamento estruturado."""
    if not texto and not audio:
        raise ValueError("informe `texto` ou `audio`")

    contents: list = []
    if audio:
        contents.append(types.Part.from_bytes(data=audio, mime_type=mime_type))
        contents.append("Transcreva o áudio e extraia o lançamento financeiro descrito nele.")
    if texto:
        contents.append(f"Mensagem do usuário: {texto}")

    modelos = [settings.GEMINI_MODEL_PRIMARY, settings.GEMINI_MODEL_FALLBACK]
    ultimo_erro: Exception | None = None

    for modelo in modelos:
        try:
            response = await get_client().aio.models.generate_content(
                model=modelo,
                contents=contents,
                config=_config(),
            )
            return _parse(response)
        except Exception as exc:  # noqa: BLE001 — a cascata existe justamente para absorver
            ultimo_erro = exc
            logger.warning("Modelo %s falhou na cascata do Gemini: %s", modelo, exc)

    raise GeminiIndisponivelError(
        f"Nenhum modelo da cascata respondeu ({', '.join(modelos)})"
    ) from ultimo_erro
