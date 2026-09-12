"""Risco de recuperação judicial — `specs/02-motor-de-risco.md` §7.

RJ é insolvência **coletiva**: quem a dirige é a pluralidade de credores, não o
atraso bilateral com a Krill Tech. Por isso o índice, a elegibilidade legal e a
conversão em probabilidade têm teste próprio, separado do da PD.
"""

from __future__ import annotations

import pytest

from models.enums import TipoPessoa
from scoring import CONFIG_PADRAO, calcular_risco
from scoring.exposicao import calcular_exposicao
from scoring.probabilidades import (
    calcular_rj_index,
    elegibilidade_para_rj,
    probabilidade_de_rj,
)

from fixtures import (
    PERFIS,
    cliente_em_rj_com_stay_period,
    cliente_excelente,
    cliente_pf_nao_elegivel_rj,
)


def test_conversao_de_indice_em_probabilidade():
    """Tabela da §7, conferida numericamente em 2026-09-12."""
    esperado = {
        10: 0.0030,
        20: 0.0090,
        30: 0.0263,
        40: 0.0715,
        45: 0.1114,
        50: 0.1641,
        55: 0.2250,
        60: 0.2859,
        70: 0.3785,
        80: 0.4237,
    }
    for indice, probabilidade in esperado.items():
        assert probabilidade_de_rj(indice) == pytest.approx(probabilidade, abs=5e-5), indice


def test_probabilidade_de_rj_e_crescente_no_indice():
    anterior = probabilidade_de_rj(CONFIG_PADRAO.rj_index_minimo)
    for indice in range(1, int(CONFIG_PADRAO.rj_index_maximo) + 1):
        atual = probabilidade_de_rj(indice)
        assert atual > anterior, indice
        anterior = atual


def test_pluralidade_de_credores_entra_no_indice():
    fatos = PERFIS["pd_moderado_rj_alto"]()
    indice, sinais = calcular_rj_index(fatos, calcular_exposicao(fatos))
    rotulos = [sinal.rotulo for sinal in sinais]
    assert CONFIG_PADRAO.rotulos_sinais_rj["pluralidade_credores"] in rotulos
    assert indice == pytest.approx(sum(sinal.pontos for sinal in sinais))


def test_patrimonio_forte_reduz_o_indice():
    fatos = cliente_excelente()
    _, sinais = calcular_rj_index(fatos, calcular_exposicao(fatos))
    redutores = [s for s in sinais if s.pontos < 0]
    assert redutores, "o redutor de patrimônio não foi aplicado"
    assert redutores[0].pontos == CONFIG_PADRAO.redutor_rj_patrimonio_forte


def test_elegibilidade_pj_e_sempre_verdadeira():
    elegibilidade = elegibilidade_para_rj(cliente_excelente())
    assert elegibilidade.elegivel is True
    assert elegibilidade.motivo is None


def test_pf_sem_atividade_comprovada_nao_e_elegivel_e_o_indice_e_atenuado():
    avaliacao = calcular_risco(cliente_pf_nao_elegivel_rj())
    risco = avaliacao.risco_rj
    assert risco.elegivel is False
    assert risco.motivo_inelegibilidade == CONFIG_PADRAO.motivo_inelegibilidade_rj
    assert risco.rj_index_efetivo == pytest.approx(
        risco.rj_index * CONFIG_PADRAO.fator_atenuacao_rj_inelegivel, abs=1e-3
    )
    #: o índice bruto é alto; o risco de RJ, não — ele migra para execução individual
    assert risco.rj_index > CONFIG_PADRAO.rj_centro
    assert risco.probabilidade_12m < probabilidade_de_rj(risco.rj_index)


def test_pf_com_atividade_comprovada_volta_a_ser_elegivel():
    fatos = cliente_pf_nao_elegivel_rj().model_copy(deep=True)
    fatos.cadastral.anos_atividade_comprovada = 3.0
    fatos.cadastral.possui_inscricao_estadual = True

    elegibilidade = elegibilidade_para_rj(fatos)
    assert elegibilidade.elegivel is True

    avaliacao = calcular_risco(fatos)
    assert avaliacao.risco_rj.rj_index_efetivo == pytest.approx(
        avaliacao.risco_rj.rj_index
    )


def test_tipo_pessoa_ausente_assume_o_padrao_conservador():
    fatos = cliente_pf_nao_elegivel_rj().model_copy(deep=True)
    fatos.cadastral.tipo_pessoa = None
    assert CONFIG_PADRAO.tipo_pessoa_padrao is TipoPessoa.PJ
    assert elegibilidade_para_rj(fatos).elegivel is True


def test_rj_em_curso_deixa_de_ser_probabilidade_e_vira_evento():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    risco = avaliacao.risco_rj
    assert risco.evento_ja_ocorrido is True
    assert risco.probabilidade_12m == CONFIG_PADRAO.probabilidade_rj_evento_ocorrido


def test_pd_e_rj_nao_compartilham_escala():
    """Nenhum perfil força correlação: os dois eixos se movem separadamente."""
    moderado_rj_alto = calcular_risco(PERFIS["pd_moderado_rj_alto"]())
    alto_rj_baixo = calcular_risco(PERFIS["pd_alto_rj_baixo"]())
    assert moderado_rj_alto.pd.pd12m < alto_rj_baixo.pd.pd12m
    assert moderado_rj_alto.risco_rj.probabilidade_12m > alto_rj_baixo.risco_rj.probabilidade_12m
