"""Invariantes I1 a I6 e determinismo — `specs/02-motor-de-risco.md` §14.

São as seis igualdades que sustentam uma arguição: se qualquer uma quebrar, o
jurado soma os números na tela e o protótipo desmonta.
"""

from __future__ import annotations

import pytest

from models.enums import Tendencia
from scoring import (
    CONFIG_PADRAO,
    calcular_risco,
    calcular_pd,
    comparar_avaliacoes,
    fechou,
    pd12_do_score,
)
from scoring.audit import soma_dos_impactos_ajustados
from scoring.delta import fatores_da_avaliacao

from fixtures import PERFIS, todas_as_series, todos_os_perfis

#: Varredura das invariantes de curva. Passo 1 no domínio inteiro do score.
_PASSO_VARREDURA = 1
_SCORE_MINIMO = 0
_SCORE_MAXIMO = 1000


# ---------------------------------------------------------------------------
# I1 · Os pesos das sete dimensões somam exatamente 1,00
# ---------------------------------------------------------------------------


def test_pesos_somam_um():
    assert sum(CONFIG_PADRAO.pesos_dimensoes.values()) == pytest.approx(1.0, abs=1e-12)


def test_toda_dimensao_do_contrato_tem_peso():
    for nome, fatos in todos_os_perfis():
        avaliacao = calcular_risco(fatos)
        assert len(avaliacao.dimensoes) == len(CONFIG_PADRAO.pesos_dimensoes), nome
        assert sum(d.peso for d in avaliacao.dimensoes) == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# I2 · A soma das contribuições reconstrói o score
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_fechamento_de_soma_nos_perfis(nome):
    avaliacao = calcular_risco(PERFIS[nome]())
    assert fechou(avaliacao.auditoria), avaliacao.auditoria
    reconstruido = CONFIG_PADRAO.score_base + soma_dos_impactos_ajustados(
        fatores_da_avaliacao(avaliacao)
    )
    assert avaliacao.score_calculado == pytest.approx(
        reconstruido, abs=CONFIG_PADRAO.tolerancia_fechamento
    )


def test_fechamento_de_soma_em_todos_os_snapshots():
    for nome, serie in todas_as_series():
        for fatos in serie:
            avaliacao = calcular_risco(fatos)
            assert fechou(avaliacao.auditoria), (nome, fatos.data_referencia)


def test_fechamento_sobrevive_a_saturacao_de_dimensao():
    """Ao menos um perfil satura no clamp — e ainda assim a soma fecha."""
    saturou = False
    for _, fatos in todos_os_perfis():
        avaliacao = calcular_risco(fatos)
        saturou = saturou or any(d.saturou for d in avaliacao.dimensoes)
        assert fechou(avaliacao.auditoria)
    assert saturou, "nenhum perfil exercita a redistribuição de saturação"


# ---------------------------------------------------------------------------
# I3 · PD 12m é estritamente decrescente no score
# ---------------------------------------------------------------------------


def test_pd_monotonica():
    anterior = pd12_do_score(_SCORE_MINIMO)
    for score in range(_SCORE_MINIMO + _PASSO_VARREDURA, _SCORE_MAXIMO + 1, _PASSO_VARREDURA):
        atual = pd12_do_score(score)
        assert atual < anterior, score
        anterior = atual


def test_pd_ancorada_nos_valores_conferidos_da_spec():
    """Tabela da §6, conferida numericamente em 2026-09-12."""
    esperado = {
        1000: 0.0060,
        900: 0.0149,
        800: 0.0363,
        750: 0.0557,
        700: 0.0841,
        650: 0.1237,
        604: 0.1713,
        600: 0.1759,
        500: 0.3100,
        400: 0.4441,
        300: 0.5359,
        150: 0.5967,
    }
    for score, pd in esperado.items():
        assert pd12_do_score(score) == pytest.approx(pd, abs=5e-5), score


# ---------------------------------------------------------------------------
# I4 · PD6 < PD12 < PD24 em toda combinação
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tendencia", list(Tendencia))
def test_ordem_das_pds(tendencia):
    for score in range(_SCORE_MINIMO, _SCORE_MAXIMO + 1, _PASSO_VARREDURA):
        pd = calcular_pd(score, tendencia)
        assert pd.pd6m < pd.pd12m < pd.pd24m, (score, tendencia)


def test_tendencia_pior_eleva_as_pds_de_horizonte():
    """A tendência não move a PD de 12m, só as de 6 e 24 meses."""
    score = 604
    melhorando = calcular_pd(score, Tendencia.MELHORANDO)
    acelerada = calcular_pd(score, Tendencia.DETERIORACAO_ACELERADA)
    assert melhorando.pd12m == acelerada.pd12m
    assert melhorando.pd6m < acelerada.pd6m
    assert melhorando.pd24m < acelerada.pd24m
    #: Tabela conferida da §6 para score 604.
    assert melhorando.pd6m == pytest.approx(0.0767, abs=5e-5)
    assert acelerada.pd24m == pytest.approx(0.3748, abs=5e-5)


# ---------------------------------------------------------------------------
# I5 · Os dois eixos são independentes
# ---------------------------------------------------------------------------

#: Faixas usadas só pelo teste para dizer o que é "moderado" e o que é "alto".
_PD_MODERADA_MAXIMA = 0.20
_PD_ALTA_MINIMA = 0.25
_RJ_ALTA_MINIMA = 0.30
_RJ_BAIXA_MAXIMA = 0.05


def test_eixos_independentes():
    moderado_rj_alto = calcular_risco(PERFIS["pd_moderado_rj_alto"]())
    alto_rj_baixo = calcular_risco(PERFIS["pd_alto_rj_baixo"]())

    assert moderado_rj_alto.pd.pd12m <= _PD_MODERADA_MAXIMA
    assert moderado_rj_alto.risco_rj.probabilidade_12m >= _RJ_ALTA_MINIMA

    assert alto_rj_baixo.pd.pd12m >= _PD_ALTA_MINIMA
    assert alto_rj_baixo.risco_rj.probabilidade_12m <= _RJ_BAIXA_MAXIMA


# ---------------------------------------------------------------------------
# I6 · A soma dos deltas reconstrói a variação do score
# ---------------------------------------------------------------------------


def test_fechamento_de_deltas():
    for nome, serie in todas_as_series():
        avaliacoes = [calcular_risco(fatos) for fatos in serie]
        for anterior, atual in zip(avaliacoes, avaliacoes[1:]):
            comparacao = comparar_avaliacoes(anterior, atual)
            soma = sum(linha.delta for linha in comparacao.fatores)
            assert soma == pytest.approx(
                atual.score_calculado - anterior.score_calculado,
                abs=CONFIG_PADRAO.tolerancia_fechamento,
            ), (nome, comparacao.data_anterior, comparacao.data_atual)
            assert abs(comparacao.diferenca_de_fechamento) < CONFIG_PADRAO.tolerancia_fechamento


def test_serie_em_deterioracao_cai_de_b_para_c():
    serie = [calcular_risco(fatos) for fatos in todas_as_series()[0][1]]
    scores = [a.score_calculado for a in serie]
    assert scores == sorted(scores, reverse=True), scores
    assert serie[0].rating_final.value == "B"
    assert serie[-1].rating_final.value == "C"


# ---------------------------------------------------------------------------
# Determinismo — mesma entrada, saída idêntica
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_determinismo(nome):
    primeira = calcular_risco(PERFIS[nome]())
    segunda = calcular_risco(PERFIS[nome]())
    assert primeira.json_do_contrato() == segunda.json_do_contrato()


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_data_de_referencia_explicita_equivale_a_dos_fatos(nome):
    fatos = PERFIS[nome]()
    implicita = calcular_risco(fatos)
    explicita = calcular_risco(fatos, data_referencia=fatos.data_referencia)
    assert implicita.json_do_contrato() == explicita.json_do_contrato()
