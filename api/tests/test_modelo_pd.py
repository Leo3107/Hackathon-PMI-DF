"""`scoring.modelo_pd` — o modelo preditivo de PD da Tarefa 1.

Cobre a fórmula (sigmoide sobre intercepto + soma de coeficiente×termo), a
centragem dos termos `log1p_*` de idade e capital, a política "nulo entra como
0", e a integração com `scoring.calcular_risco` via `adaptadores.adaptar`.
"""

from __future__ import annotations

from math import exp, log1p

import pytest
from adaptadores import adaptar
from coleta.models import Features
from scoring import calcular_risco
from scoring.modelo_pd import (
    AVISO,
    COEFICIENTES,
    INTERCEPTO,
    REFERENCIAS_DE_CENTRAGEM,
    avaliar_modelo_pd,
    calcular_pd_12m,
    contribuicoes,
)

DOC = "12345678000190"
DATA_REF = "2026-09-12"


def _features(**kwargs) -> Features:
    return Features(documento=DOC, **kwargs)


def test_aviso_e_o_do_json_e_fala_de_dado_fabricado():
    assert "FABRICADO" in AVISO.upper() or "fabricado" in AVISO.lower()


def test_features_totalmente_vazio_nao_e_so_o_intercepto():
    """Idade e capital ausentes (`0` pela política "nulo entra como 0") ficam
    **abaixo** das referências de centragem — o termo não é zero, é negativo,
    e como os dois coeficientes são negativos isso aumenta a PD: silêncio
    sobre idade/capital não é tratado como "empresa grande e madura"."""
    log_odds_esperado = (
        INTERCEPTO
        + COEFICIENTES["log1p_idade_empresa_meses"]
        * (log1p(0.0) - log1p(REFERENCIAS_DE_CENTRAGEM["idade_empresa_meses"]))
        + COEFICIENTES["log1p_capital_social"]
        * (log1p(0.0) - log1p(REFERENCIAS_DE_CENTRAGEM["capital_social"]))
    )
    pd = calcular_pd_12m(_features())
    assert pd == pytest.approx(1.0 / (1.0 + exp(-log_odds_esperado)))
    # E é maior que a PD "neutra" que só o intercepto daria — o ponto do teste.
    assert pd > 1.0 / (1.0 + exp(-INTERCEPTO))


def test_log1p_de_idade_e_capital_sao_centrados():
    ref_idade = REFERENCIAS_DE_CENTRAGEM["idade_empresa_meses"]
    ref_capital = REFERENCIAS_DE_CENTRAGEM["capital_social"]
    features = _features(idade_empresa_meses=int(ref_idade), capital_social=ref_capital)
    # Na própria referência, o termo centrado é zero — sobra só o intercepto.
    pd = calcular_pd_12m(features)
    esperado = 1.0 / (1.0 + exp(-INTERCEPTO))
    assert pd == pytest.approx(esperado, abs=1e-9)


def test_log1p_divida_ativa_nao_e_centrado():
    valor = 1_200_000.0
    features = _features(divida_ativa_total=valor)
    itens = {c.termo: c for c in contribuicoes(features)}
    termo = itens["log1p_divida_ativa_total"]
    assert termo.contribuicao_log_odds == pytest.approx(
        COEFICIENTES["log1p_divida_ativa_total"] * log1p(valor)
    )


def test_nulo_entra_como_zero_em_todo_termo():
    """Um `Features` vazio dá a mesma PD que um com todos os campos do modelo
    explicitamente zerados/`False` — nulo nunca é tratado como valor especial."""
    vazio = _features()
    explicito = _features(
        divida_ativa_total=0.0,
        flag_situacao_irregular=False,
        n_empresas_do_socio_inaptas=0,
        n_autos_infracao=0,
        flag_embargo_ativo=False,
        idade_empresa_meses=0,
        capital_social=0.0,
        desvio_produtividade_vs_media_5a=0.0,
        anomalia_na_fase_critica=0.0,
        n_protestos_ativos=0,
    )
    assert calcular_pd_12m(vazio) == pytest.approx(calcular_pd_12m(explicito))


def test_mais_divida_ativa_aumenta_a_pd():
    baixa = calcular_pd_12m(_features(divida_ativa_total=10_000.0))
    alta = calcular_pd_12m(_features(divida_ativa_total=5_000_000.0))
    assert alta > baixa


def test_situacao_irregular_aumenta_a_pd():
    regular = calcular_pd_12m(_features(flag_situacao_irregular=False))
    irregular = calcular_pd_12m(_features(flag_situacao_irregular=True))
    assert irregular > regular


def test_idade_maior_reduz_a_pd():
    """Coeficiente negativo: empresa mais velha (acima da referência) reduz PD."""
    jovem = calcular_pd_12m(_features(idade_empresa_meses=12))
    madura = calcular_pd_12m(_features(idade_empresa_meses=480))
    assert madura < jovem


def test_contribuicoes_tem_uma_linha_por_coeficiente_do_json():
    itens = contribuicoes(_features(divida_ativa_total=1.0))
    assert {c.termo for c in itens} == set(COEFICIENTES)
    for item in itens:
        assert item.coeficiente == COEFICIENTES[item.termo]


def test_contribuicoes_reconstroi_a_pd():
    features = _features(
        divida_ativa_total=2_000_000.0,
        flag_situacao_irregular=True,
        n_protestos_ativos=3,
    )
    resultado = avaliar_modelo_pd(features)
    log_odds = INTERCEPTO + sum(c.contribuicao_log_odds for c in resultado.contribuicoes)
    assert resultado.pd12 == pytest.approx(1.0 / (1.0 + exp(-log_odds)))
    assert resultado.aviso == AVISO


# ---------------------------------------------------------------------------
# Integração com o motor — a PD "sai deste modelo" quando `modelo_pd` é passado
# ---------------------------------------------------------------------------


def test_calcular_risco_usa_o_modelo_quando_informado():
    features = _features(divida_ativa_total=3_000_000.0, flag_situacao_irregular=True)
    resultado = adaptar(features, cliente_id="cli-x", data_referencia=DATA_REF)
    avaliacao = calcular_risco(
        resultado.fatos, config=resultado.config, data_referencia=DATA_REF,
        modelo_pd=resultado.modelo_pd,
    )
    assert avaliacao.pd.pd12m == pytest.approx(resultado.modelo_pd.pd12, abs=1e-5)
    assert avaliacao.modelo_pd is not None
    assert avaliacao.modelo_pd.aviso == AVISO
    assert len(avaliacao.modelo_pd.contribuicoes) == len(COEFICIENTES)


def test_pd6_menor_que_pd12_menor_que_pd24_com_modelo():
    features = _features(divida_ativa_total=1_000_000.0, n_protestos_ativos=2)
    resultado = adaptar(features, cliente_id="cli-y", data_referencia=DATA_REF)
    avaliacao = calcular_risco(
        resultado.fatos, config=resultado.config, data_referencia=DATA_REF,
        modelo_pd=resultado.modelo_pd,
    )
    assert avaliacao.pd.pd6m < avaliacao.pd.pd12m < avaliacao.pd.pd24m


def test_sem_modelo_pd_o_campo_fica_none():
    features = _features()
    resultado = adaptar(features, cliente_id="cli-z", data_referencia=DATA_REF)
    avaliacao = calcular_risco(resultado.fatos, config=resultado.config, data_referencia=DATA_REF)
    assert avaliacao.modelo_pd is None
