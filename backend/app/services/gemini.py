"""Cascata do Gemini: extrai lançamentos financeiros de áudio ou texto (seção 4.2 do guia).

Tenta primeiro o modelo Flash mais recente e, em caso de falha (indisponibilidade,
quota, modelo removido), cai para o modelo estável configurado em `GEMINI_MODEL_FALLBACK`.
"""
import json
import logging
from functools import lru_cache
from typing import Literal, get_args

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError, model_validator

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

# Períodos aceitos numa consulta de saldo — precisam bater com as chaves de
# `PERIODOS` em app/services/telegram_bot.py. É um Literal (e não uma lista de
# str) para que o valor entre no schema enviado ao Gemini como enum: um "ano"
# ou qualquer outro período inventado é recusado na validação, em vez de virar
# "mes" silenciosamente.
PeriodoSaldo = Literal["dia", "semana", "mes", "3meses"]
PERIODOS_SALDO: tuple[str, ...] = get_args(PeriodoSaldo)

# Resposta ao usuário quando o Gemini responde, mas fora do contrato.
OBSERVACAO_FORA_DO_CONTRATO = (
    "🤔 Não consegui entender essa mensagem. Tente de novo dizendo o valor e o que foi "
    "(ex.: “gastei 40 no mercado”) ou pergunte pelo saldo do dia, da semana, do mês ou "
    "dos últimos 3 meses."
)

PROMPT = f"""Você é o motor de extração de um gestor financeiro pessoal brasileiro.
Analise a mensagem do usuário (áudio ou texto) e devolva UM ÚNICO JSON.

A mensagem pode ser (a) um lançamento financeiro para registrar ou (b) uma pergunta
sobre saldo/gastos/receitas. Nunca as duas coisas ao mesmo tempo.

Regras para LANÇAMENTO (ex.: "gastei 40 no mercado", "recebi 3500 de salário"):
- "eh_transacao": true.
- "tipo": "receita" (dinheiro que entrou) ou "despesa" (dinheiro que saiu).
- "valor": número positivo em reais. Converta por extenso: "quarenta e dois e noventa" -> 42.90.
- "descricao": resumo curto (até 60 caracteres) do que foi pago ou recebido.
- "categoria": escolha exatamente uma entre {", ".join(CATEGORIAS)}.
- "metodo_pagamento": um entre {", ".join(METODOS_PAGAMENTO)}; use null se não for citado.
- Nunca invente valores nem categorias fora da lista.

Regras para CONSULTA DE SALDO (ex.: "quanto gastei hoje?", "qual meu saldo essa semana",
"quanto recebi esse mês", "como estou nos últimos 3 meses"):
- "eh_transacao": false (nunca true junto com "eh_consulta_saldo").
- "eh_consulta_saldo": true.
- "periodo_consulta": obrigatório, exatamente um entre {", ".join(PERIODOS_SALDO)}
  ("dia" = hoje, "semana" = semana atual, "mes" = mês atual, "3meses" = últimos 3 meses).
  Se a mensagem não deixar claro o período, use "mes". Não invente outros períodos:
  para "esse ano" ou qualquer intervalo fora da lista, use "3meses".

Se a mensagem não for nem um lançamento nem uma pergunta de saldo, ou se um lançamento
não tiver o valor claro, devolva "eh_transacao": false, "eh_consulta_saldo": false e
escreva em "observacao" uma frase curta, em português, explicando ao usuário o que ele
deve enviar."""


class TransacaoExtraida(BaseModel):
    """JSON estruturado devolvido pela IA."""

    eh_transacao: bool = Field(description="true somente se houver um lançamento financeiro claro")
    tipo: str | None = Field(default=None, description='"receita" ou "despesa"')
    valor: float | None = Field(default=None, description="Valor positivo em reais")
    descricao: str | None = Field(default=None, description="Resumo curto do lançamento")
    categoria: str | None = None
    metodo_pagamento: str | None = None
    eh_consulta_saldo: bool = Field(
        default=False, description="true se a mensagem for uma pergunta sobre saldo/gastos/receitas"
    )
    periodo_consulta: PeriodoSaldo | None = Field(
        default=None, description='um entre "dia", "semana", "mes", "3meses"'
    )
    observacao: str | None = Field(
        default=None, description="Mensagem ao usuário quando não houver transação nem consulta"
    )

    @model_validator(mode="after")
    def _checar_coerencia(self) -> "TransacaoExtraida":
        """Barra combinações que o resto do fluxo não sabe tratar.

        Sem isto, uma consulta de saldo sem período (ou uma resposta que é
        lançamento e consulta ao mesmo tempo) seguiria adiante e viraria uma
        decisão silenciosa do bot.
        """
        if self.eh_transacao and self.eh_consulta_saldo:
            raise ValueError(
                "resposta não pode ser lançamento e consulta de saldo ao mesmo tempo"
            )
        if self.eh_consulta_saldo and self.periodo_consulta is None:
            raise ValueError("consulta de saldo exige `periodo_consulta`")
        return self


class GeminiIndisponivelError(RuntimeError):
    """Todos os modelos da cascata falharam (rede, quota, modelo removido)."""


class RespostaForaDoContratoError(ValueError):
    """O Gemini respondeu, mas o JSON não obedece ao schema combinado."""


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
    """Aceita tanto o objeto já validado (`parsed`) quanto o JSON cru em `text`.

    Qualquer desvio do schema vira `RespostaForaDoContratoError`, para a cascata
    distinguir "o modelo não respondeu" de "o modelo respondeu bobagem".
    """
    try:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, TransacaoExtraida):
            return parsed
        if isinstance(parsed, dict):
            return TransacaoExtraida.model_validate(parsed)
        if not response.text:
            raise RespostaForaDoContratoError("resposta vazia do Gemini")
        return TransacaoExtraida.model_validate(json.loads(response.text))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise RespostaForaDoContratoError(str(exc)) from exc


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
    houve_resposta_fora_do_contrato = False

    for modelo in modelos:
        try:
            response = await get_client().aio.models.generate_content(
                model=modelo,
                contents=contents,
                config=_config(),
            )
            return _parse(response)
        except RespostaForaDoContratoError as exc:
            # O modelo respondeu — tentar o próximo pode dar um JSON válido.
            houve_resposta_fora_do_contrato = True
            ultimo_erro = exc
            logger.warning("Modelo %s respondeu fora do contrato: %s", modelo, exc)
        except Exception as exc:  # noqa: BLE001 — a cascata existe justamente para absorver
            ultimo_erro = exc
            logger.warning("Modelo %s falhou na cascata do Gemini: %s", modelo, exc)

    if houve_resposta_fora_do_contrato:
        # A IA está de pé, só não produziu um JSON utilizável: dizer "indisponível"
        # seria mentira, e executar um período chutado seria pior ainda.
        logger.error("Nenhum modelo devolveu JSON dentro do contrato: %s", ultimo_erro)
        return TransacaoExtraida(eh_transacao=False, observacao=OBSERVACAO_FORA_DO_CONTRATO)

    raise GeminiIndisponivelError(
        f"Nenhum modelo da cascata respondeu ({', '.join(modelos)})"
    ) from ultimo_erro
