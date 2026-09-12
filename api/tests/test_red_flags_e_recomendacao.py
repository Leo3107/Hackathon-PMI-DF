"""Red flags (§13) e recomendação operacional (§12).

A red flag nasce do mesmo fator que moveu o score — nunca de texto escrito à
mão — e a recomendação é escolhida por regra, com ações parametrizadas pelos
números reais do cliente.
"""

from __future__ import annotations

import pytest

from models.avaliacao import AVISO_DO_ANALISTA, VetoAtivo
from models.enums import CodigoRecomendacao, EfeitoVeto, Rating, Severidade, Tendencia
from scoring import CONFIG_PADRAO, calcular_exposicao, calcular_risco, escolher_codigo
from scoring.formatacao import moeda, percentual_de_fracao, plural_dias

from fixtures import (
    PERFIS,
    cliente_critico,
    cliente_em_deterioracao,
    cliente_em_rj_com_stay_period,
    cliente_excelente,
    cliente_inadimplencia_tecnica,
    todos_os_perfis,
)


def _por_id(colecao):
    return {item.id: item for item in colecao}


def _fatores(avaliacao):
    return {f.id: f for d in avaliacao.dimensoes for f in d.fatores}


# ---------------------------------------------------------------------------
# §13 · Red flags derivadas dos mesmos fatores
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_red_flag_nunca_diverge_do_fator_que_a_gerou(nome):
    avaliacao = calcular_risco(PERFIS[nome]())
    fatores = _fatores(avaliacao)
    for flag in avaliacao.red_flags:
        if flag.fator_id is None:
            continue
        assert flag.fator_id in fatores, flag.id
        assert flag.impacto_em_pontos == fatores[flag.fator_id].impacto_global_ajustado


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_red_flags_ordenadas_por_severidade(nome):
    avaliacao = calcular_risco(PERFIS[nome]())
    ordens = [CONFIG_PADRAO.ordem_de_severidade[f.severidade] for f in avaliacao.red_flags]
    assert ordens == sorted(ordens)
    assert len({f.id for f in avaliacao.red_flags}) == len(avaliacao.red_flags)


def test_inadimplencia_tecnica_gera_red_flag_alta_sem_nenhum_atraso():
    """A tese do produto: detectar antes do calote, não depois."""
    fatos = cliente_inadimplencia_tecnica()
    assert fatos.interno.atraso_medio_dias_12m == 0.0
    assert fatos.interno.pior_atraso_dias_12m == 0.0
    assert fatos.interno.pct_titulos_pagos_em_dia_12m == 1.0

    avaliacao = calcular_risco(fatos)
    flags = _por_id(avaliacao.red_flags)
    flag = flags["rf-inadimplencia_tecnica"]
    assert flag.severidade is Severidade.ALTA
    assert flag.impacto_em_pontos < 0
    assert flag.evidencia_ids == ["ev-tec-1"]
    #: nenhum fator de atraso se materializou
    assert "atraso_medio" not in _fatores(avaliacao)
    assert "pior_atraso" not in _fatores(avaliacao)


def test_rj_em_curso_gera_red_flag_critica():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    flags = _por_id(avaliacao.red_flags)
    assert flags["rf-rj_distribuida"].severidade is Severidade.CRITICA
    assert avaliacao.red_flags[0].severidade is Severidade.CRITICA


def test_embargo_sobre_garantia_gera_red_flag_critica_a_partir_do_veto():
    avaliacao = calcular_risco(PERFIS["veto_ambiental"]())
    flags = _por_id(avaliacao.red_flags)
    flag = flags["rf-VETO_EMBARGO_GARANTIA"]
    assert flag.severidade is Severidade.CRITICA
    assert flag.evidencia_ids == ["ev-veto-1"]
    #: o impacto exibido é o do fator ambiental correspondente
    assert flag.impacto_em_pontos == _fatores(avaliacao)["embargo_ibama"].impacto_global_ajustado


def test_queda_acentuada_de_score_vira_red_flag_alta():
    avaliacao = calcular_risco(cliente_critico())
    assert avaliacao.tendencia is Tendencia.DETERIORACAO_ACELERADA
    flags = _por_id(avaliacao.red_flags)
    queda = flags["rf-queda_de_score"]
    assert queda.severidade is Severidade.ALTA
    assert queda.titulo == CONFIG_PADRAO.titulo_red_flag_queda_de_score


def test_cliente_impecavel_so_gera_red_flag_informativa():
    """Rating A não silencia a tela: sobra só o que é informativo."""
    avaliacao = calcular_risco(cliente_excelente())
    assert {flag.severidade for flag in avaliacao.red_flags} <= {Severidade.BAIXA}


# ---------------------------------------------------------------------------
# §12 · Árvore de decisão, avaliada em ordem
# ---------------------------------------------------------------------------


def _resumo(nome):
    return calcular_exposicao(PERFIS[nome]())


def _veto(efeito: EfeitoVeto) -> VetoAtivo:
    return VetoAtivo(id="VETO_FRAUDE", rotulo="Fraude", efeito=efeito, justificativa="teste")


def test_veto_de_forca_d_vence_qualquer_rating():
    resumo = _resumo("excelente")
    codigo = escolher_codigo(
        Rating.A, Tendencia.MELHORANDO, [_veto(EfeitoVeto.FORCA_D)], resumo
    )
    assert codigo is CodigoRecomendacao.SUSPENDER_EXPOSICAO


@pytest.mark.parametrize("tendencia", list(Tendencia))
def test_rating_d_sempre_suspende(tendencia):
    codigo = escolher_codigo(Rating.D, tendencia, [], _resumo("excelente"))
    assert codigo is CodigoRecomendacao.SUSPENDER_EXPOSICAO


def test_rating_c_com_deterioracao_acelerada_suspende_nova_exposicao():
    resumo = _resumo("em_deterioracao")
    assert (
        escolher_codigo(Rating.C, Tendencia.DETERIORACAO_ACELERADA, [], resumo)
        is CodigoRecomendacao.SUSPENDER_NOVA_EXPOSICAO_A_PRAZO
    )
    assert (
        escolher_codigo(Rating.C, Tendencia.DETERIORANDO, [], resumo)
        is CodigoRecomendacao.APROVAR_COM_RESTRICOES
    )


def test_rating_b_com_exposicao_desprotegida_em_rj_exige_restricoes():
    resumo = _resumo("moderado")
    exposicao = resumo.calculada
    fracao = exposicao.exposicao_em_risco_em_rj / exposicao.exposicao_total
    assert fracao > CONFIG_PADRAO.limiar_exposicao_rj_rating_b
    assert (
        escolher_codigo(Rating.B, Tendencia.ESTAVEL, [], resumo)
        is CodigoRecomendacao.APROVAR_COM_RESTRICOES
    )


def test_rating_b_protegido_depende_da_tendencia():
    resumo = _resumo("pd_moderado_rj_alto")
    exposicao = resumo.calculada
    fracao = exposicao.exposicao_em_risco_em_rj / exposicao.exposicao_total
    assert fracao <= CONFIG_PADRAO.limiar_exposicao_rj_rating_b

    assert (
        escolher_codigo(Rating.B, Tendencia.ESTAVEL, [], resumo)
        is CodigoRecomendacao.APROVAR
    )
    assert (
        escolher_codigo(Rating.B, Tendencia.DETERIORANDO, [], resumo)
        is CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO
    )
    assert (
        escolher_codigo(Rating.B, Tendencia.DETERIORACAO_ACELERADA, [], resumo)
        is CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO
    )


def test_rating_a_com_limite_estourado_pede_revisao_de_limite():
    alta_utilizacao = calcular_exposicao(cliente_inadimplencia_tecnica())
    assert (
        alta_utilizacao.calculada.limite_utilizado_pct
        > CONFIG_PADRAO.limiar_utilizacao_revisao_de_limite
    )
    assert (
        escolher_codigo(Rating.A, Tendencia.ESTAVEL, [], alta_utilizacao)
        is CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE
    )
    assert (
        escolher_codigo(Rating.A, Tendencia.ESTAVEL, [], _resumo("excelente"))
        is CodigoRecomendacao.APROVAR
    )


# ---------------------------------------------------------------------------
# §12 · Ações parametrizadas pelos números do cliente
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_toda_recomendacao_traz_acoes_prazo_e_aviso(nome):
    avaliacao = calcular_risco(PERFIS[nome]())
    recomendacao = avaliacao.recomendacao
    assert recomendacao.acoes, nome
    assert recomendacao.aviso == AVISO_DO_ANALISTA
    assert recomendacao.rotulo == CONFIG_PADRAO.rotulos_recomendacao[recomendacao.codigo]
    assert (
        recomendacao.prazo_reavaliacao_dias
        == CONFIG_PADRAO.prazo_reavaliacao_por_rating[avaliacao.rating_final]
    )
    reavaliar = _por_id(recomendacao.acoes)["reavaliar_em"]
    assert plural_dias(recomendacao.prazo_reavaliacao_dias) in reavaliar.rotulo


def test_acoes_carregam_os_numeros_reais_do_cliente():
    fatos = cliente_em_deterioracao()
    avaliacao = calcular_risco(fatos)
    exposicao = avaliacao.exposicao
    acoes = _por_id(avaliacao.recomendacao.acoes)

    reducao = CONFIG_PADRAO.reducao_limite_por_rating_e_tendencia[avaliacao.rating_final][
        avaliacao.tendencia
    ]
    novo_limite = exposicao.limite_aprovado * (1.0 - reducao)
    assert moeda(exposicao.limite_aprovado) in acoes["reduzir_limite"].rotulo
    assert moeda(novo_limite) in acoes["reduzir_limite"].rotulo
    assert percentual_de_fracao(reducao, casas=0) in acoes["reduzir_limite"].rotulo

    assert exposicao.exposicao_em_risco > 0
    assert (
        moeda(exposicao.exposicao_em_risco)
        in acoes["exigir_garantia_adicional"].rotulo
    )

    garantia = calcular_exposicao(fatos).maior_garantia_concursal
    assert garantia is not None
    conversao = acoes["converter_para_extraconcursal"]
    assert moeda(garantia.valor_atualizado) in conversao.rotulo
    assert CONFIG_PADRAO.rotulos_tipo_garantia[garantia.tipo] in conversao.rotulo
    assert moeda(exposicao.exposicao_em_risco_em_rj) in (conversao.detalhe or "")


def test_suspensao_aciona_garantia_extraconcursal_e_analise_especializada():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    acoes = _por_id(avaliacao.recomendacao.acoes)
    assert avaliacao.recomendacao.codigo is CodigoRecomendacao.SUSPENDER_EXPOSICAO
    assert moeda(avaliacao.exposicao.valor_extraconcursal) in acoes["acionar_garantia"].rotulo
    #: o valor concursal é citado como o que NÃO pode ser somado
    assert (
        moeda(avaliacao.exposicao.valor_concursal)
        in (acoes["acionar_garantia"].detalhe or "")
    )
    assert "VETO_RJ" not in acoes["encaminhar_analise_especializada"].rotulo
    detalhe = acoes["encaminhar_analise_especializada"].detalhe or ""
    assert avaliacao.vetos_ativos[0].rotulo in detalhe


def test_acao_sem_numero_para_exibir_nao_e_emitida():
    """Sem garantia concursal relevante, a conversão simplesmente não aparece."""
    avaliacao = calcular_risco(cliente_critico())
    acoes = _por_id(avaliacao.recomendacao.acoes)
    assert avaliacao.exposicao.valor_extraconcursal == 0.0
    assert "acionar_garantia" not in acoes


def test_prioridades_sao_as_da_configuracao():
    prioridades = {
        CONFIG_PADRAO.prioridade_alta,
        CONFIG_PADRAO.prioridade_media,
        CONFIG_PADRAO.prioridade_baixa,
    }
    for nome, fatos in todos_os_perfis():
        for acao in calcular_risco(fatos).recomendacao.acoes:
            assert acao.prioridade in prioridades, (nome, acao.id)
