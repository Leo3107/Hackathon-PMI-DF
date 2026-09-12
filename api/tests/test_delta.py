"""O "por que o score mudou" — `specs/02-motor-de-risco.md` §11.

Compara dois instantes fator a fator, ordenado por impacto absoluto, e prova
que a leitura da tela ("712 → 604, −108 pontos, decompostos assim") é a mesma
aritmética do score, não uma heurística de apresentação.
"""

from __future__ import annotations

import pytest

from models.enums import Tendencia
from scoring import CONFIG_PADRAO, calcular_risco, comparar_avaliacoes
from scoring.delta import (
    SITUACAO_MANTIDO,
    SITUACAO_NOVO,
    SITUACAO_REMOVIDO,
    classificar_tendencia,
    deltas_de_fatores,
    estimar_variacao_90d,
    fatores_da_avaliacao,
)

from fixtures import cliente_excelente, serie_em_deterioracao


def _comparacao_final():
    serie = serie_em_deterioracao()
    return comparar_avaliacoes(calcular_risco(serie[-2]), calcular_risco(serie[-1]))


def test_comparacao_identifica_os_dois_instantes():
    comparacao = _comparacao_final()
    assert comparacao.cliente_id == "cli-deterioracao"
    assert comparacao.data_anterior == "2026-06-14"
    assert comparacao.data_atual == "2026-09-12"
    assert comparacao.delta_score < 0


def test_linhas_ordenadas_por_impacto_absoluto():
    comparacao = _comparacao_final()
    modulos = [abs(linha.delta) for linha in comparacao.fatores]
    assert modulos == sorted(modulos, reverse=True)


def test_maiores_contribuintes_sao_os_eventos_do_periodo():
    """As novas execuções lideram a queda; a dívida ativa também piora."""
    comparacao = _comparacao_final()
    linhas = {linha.fator_id: linha for linha in comparacao.fatores}
    assert comparacao.fatores[0].fator_id == "execucoes_titulo"
    assert linhas["execucoes_titulo"].delta < 0
    assert linhas["divida_ativa"].delta < 0
    #: já vinha crescendo no trimestre anterior: continua pesando, sem novo delta
    assert linhas["divida_ativa_crescente"].impacto_atual < 0


def test_fator_novo_e_fator_removido():
    anterior = calcular_risco(serie_em_deterioracao()[0])
    atual = calcular_risco(serie_em_deterioracao()[-1])
    linhas = {linha.fator_id: linha for linha in comparar_avaliacoes(anterior, atual).fatores}

    #: não havia execução no primeiro snapshot
    assert linhas["execucoes_titulo"].situacao == SITUACAO_NOVO
    assert linhas["execucoes_titulo"].impacto_anterior == 0.0
    assert linhas["execucoes_titulo"].impacto_atual < 0

    #: fator presente nos dois instantes
    assert linhas["pontualidade"].situacao == SITUACAO_MANTIDO


def test_fator_removido_aparece_com_delta_positivo():
    """Quem melhora também é explicado: o fator some e devolve pontos."""
    atual = calcular_risco(cliente_excelente())
    piorado = cliente_excelente().model_copy(deep=True)
    piorado.juridico.protestos_ativos = 2
    anterior = calcular_risco(piorado)

    linhas = {linha.fator_id: linha for linha in comparar_avaliacoes(anterior, atual).fatores}
    assert linhas["protestos"].situacao == SITUACAO_REMOVIDO
    assert linhas["protestos"].impacto_atual == 0.0
    assert linhas["protestos"].delta > 0


def test_delta_fecha_com_a_variacao_do_score():
    comparacao = _comparacao_final()
    soma = sum(linha.delta for linha in comparacao.fatores)
    assert soma == pytest.approx(
        comparacao.delta_score, abs=CONFIG_PADRAO.tolerancia_fechamento
    )
    assert abs(comparacao.diferenca_de_fechamento) < CONFIG_PADRAO.tolerancia_fechamento


def test_comparacao_consigo_mesma_e_toda_nula():
    avaliacao = calcular_risco(cliente_excelente())
    comparacao = comparar_avaliacoes(avaliacao, avaliacao)
    assert comparacao.delta_score == 0.0
    assert all(linha.delta == 0.0 for linha in comparacao.fatores)
    assert all(linha.situacao == SITUACAO_MANTIDO for linha in comparacao.fatores)


def test_deltas_de_listas_vazias():
    assert deltas_de_fatores([], []) == []


# ---------------------------------------------------------------------------
# §11 · Classificação da tendência
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("variacao", "esperada"),
    [
        (120.0, Tendencia.MELHORANDO),
        (25.0, Tendencia.MELHORANDO),
        (24.0, Tendencia.ESTAVEL),
        (0.0, Tendencia.ESTAVEL),
        (-24.0, Tendencia.ESTAVEL),
        (-25.0, Tendencia.DETERIORANDO),
        (-79.0, Tendencia.DETERIORANDO),
        (-80.0, Tendencia.DETERIORACAO_ACELERADA),
        (-300.0, Tendencia.DETERIORACAO_ACELERADA),
    ],
)
def test_classificacao_da_tendencia(variacao, esperada):
    assert classificar_tendencia(variacao) is esperada


def test_variacao_de_90_dias_soma_apenas_os_fatores_da_janela():
    avaliacao = calcular_risco(serie_em_deterioracao()[-1])
    fatores = fatores_da_avaliacao(avaliacao)
    janela = set(CONFIG_PADRAO.fatores_de_janela_90d)
    esperado = sum(f.impacto_global_ajustado for f in fatores if f.id in janela)
    assert estimar_variacao_90d(fatores) == pytest.approx(esperado, abs=1e-4)
    assert avaliacao.tendencia is classificar_tendencia(estimar_variacao_90d(fatores))
