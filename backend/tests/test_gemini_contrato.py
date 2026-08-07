"""Testes do contrato do JSON devolvido pelo Gemini.

A validação existe para o bot nunca executar uma consulta de saldo com período
inventado ("ano") ou ambíguo — nesse caso a resposta é recusada e o usuário
recebe um pedido de reformulação, em vez de um saldo silenciosamente errado.
"""
import pytest
from pydantic import ValidationError

from app.services.gemini import PERIODOS_SALDO, TransacaoExtraida


@pytest.mark.parametrize("periodo", PERIODOS_SALDO)
def test_aceita_os_periodos_do_contrato(periodo: str) -> None:
    extraida = TransacaoExtraida(
        eh_transacao=False, eh_consulta_saldo=True, periodo_consulta=periodo
    )
    assert extraida.periodo_consulta == periodo


@pytest.mark.parametrize("periodo", ["ano", "semestre", "3 meses", "MES", ""])
def test_recusa_periodo_fora_da_lista(periodo: str) -> None:
    with pytest.raises(ValidationError):
        TransacaoExtraida(
            eh_transacao=False, eh_consulta_saldo=True, periodo_consulta=periodo
        )


def test_recusa_consulta_de_saldo_sem_periodo() -> None:
    with pytest.raises(ValidationError, match="periodo_consulta"):
        TransacaoExtraida(eh_transacao=False, eh_consulta_saldo=True)


def test_recusa_lancamento_e_consulta_ao_mesmo_tempo() -> None:
    with pytest.raises(ValidationError, match="ao mesmo tempo"):
        TransacaoExtraida(
            eh_transacao=True,
            tipo="despesa",
            valor=40.0,
            eh_consulta_saldo=True,
            periodo_consulta="mes",
        )


def test_lancamento_simples_continua_valido() -> None:
    extraida = TransacaoExtraida(
        eh_transacao=True, tipo="despesa", valor=42.9, descricao="mercado"
    )
    assert extraida.eh_consulta_saldo is False
    assert extraida.periodo_consulta is None


def test_mensagem_sem_transacao_nem_consulta_continua_valida() -> None:
    extraida = TransacaoExtraida(eh_transacao=False, observacao="não entendi")
    assert extraida.observacao == "não entendi"
