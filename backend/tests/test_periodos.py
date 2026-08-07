"""Testes dos recortes de período usados por `/saldo` e pela consulta via IA.

O que importa aqui é a fronteira: o início do período é calculado no fuso de São
Paulo e devolvido em UTC, que é como as datas ficam gravadas em `transactions`.
"""
from datetime import UTC, datetime

import pytest

from app.services import gemini
from app.services.telegram_bot import (
    PERIODOS,
    TZ,
    _inicio_3_meses,
    _inicio_da_semana,
    _inicio_do_dia,
    _inicio_do_mes,
)


def sp(texto: str) -> datetime:
    """Datetime no fuso de São Paulo a partir de "AAAA-MM-DD HH:MM"."""
    return datetime.fromisoformat(texto).replace(tzinfo=TZ)


def em_sp(momento: datetime) -> datetime:
    """Traz um resultado (sempre em UTC) de volta para o fuso de São Paulo."""
    assert momento.tzinfo is UTC, "o início do período deve sair em UTC"
    return momento.astimezone(TZ)


@pytest.mark.parametrize(
    ("agora", "esperado"),
    [
        # Meio do mês: janela móvel, começa no mesmo dia 3 meses atrás.
        ("2026-08-05 15:30", "2026-05-05 00:00"),
        ("2026-01-15 08:00", "2025-10-15 00:00"),
        # Bordas 29/30/31 caindo em fevereiro: encosta no último dia do mês.
        ("2026-05-29 12:00", "2026-02-28 00:00"),
        ("2026-05-30 12:00", "2026-02-28 00:00"),
        ("2026-05-31 12:00", "2026-02-28 00:00"),
        # Mesmo caso em ano bissexto.
        ("2024-05-31 12:00", "2024-02-29 00:00"),
        # Dia 31 num mês de destino que também tem 31.
        ("2026-03-31 23:59", "2025-12-31 00:00"),
        # Virada de ano.
        ("2026-02-10 06:00", "2025-11-10 00:00"),
    ],
)
def test_inicio_3_meses(agora: str, esperado: str) -> None:
    assert em_sp(_inicio_3_meses(sp(agora))) == sp(esperado)


def test_inicio_3_meses_nao_pula_para_o_primeiro_do_mes() -> None:
    """Regressão: a versão antiga truncava para o dia 1 e encurtava a janela."""
    assert em_sp(_inicio_3_meses(sp("2026-08-05 10:00"))) != sp("2026-06-01 00:00")


def test_inicio_do_dia() -> None:
    assert em_sp(_inicio_do_dia(sp("2026-08-05 15:30"))) == sp("2026-08-05 00:00")


@pytest.mark.parametrize(
    ("agora", "esperado"),
    [
        ("2026-08-05 15:30", "2026-08-03 00:00"),  # quarta -> segunda da mesma semana
        ("2026-08-03 00:10", "2026-08-03 00:00"),  # a própria segunda
        ("2026-08-09 23:00", "2026-08-03 00:00"),  # domingo ainda pertence à semana
        ("2026-08-02 09:00", "2026-07-27 00:00"),  # domingo que cruza o mês
    ],
)
def test_inicio_da_semana(agora: str, esperado: str) -> None:
    assert em_sp(_inicio_da_semana(sp(agora))) == sp(esperado)


def test_inicio_do_mes() -> None:
    assert em_sp(_inicio_do_mes(sp("2026-08-05 15:30"))) == sp("2026-08-01 00:00")


def test_periodos_batem_com_o_contrato_da_ia() -> None:
    """As chaves de `PERIODOS` e os valores aceitos pelo Gemini não podem divergir."""
    assert set(PERIODOS) == set(gemini.PERIODOS_SALDO)


def test_todas_as_funcoes_de_periodo_rodam_sem_argumento() -> None:
    """Em produção `PERIODOS` chama cada função sem passar `agora`."""
    for _titulo, calcular_inicio in PERIODOS.values():
        assert calcular_inicio().tzinfo is UTC
