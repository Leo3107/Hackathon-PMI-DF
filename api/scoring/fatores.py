"""Featurizers — um por dimensão. `specs/02-motor-de-risco.md` §4.

Cada função recebe `FatosDoCliente` e devolve `list[FatorCalculado]` com os
ids exatos do catálogo da spec. **Fator com `pontos == 0` não é emitido** —
fator zerado não polui a tela nem a soma.

`impactoGlobal = peso(dimensão) × pontos × sinal`. `impactoGlobalAjustado`
nasce igual e só é reescalado em `scoring.score`, quando a dimensão satura.
"""

from __future__ import annotations

from datetime import date

from models.avaliacao import FatorCalculado
from models.enums import DimensaoId, DirecaoFator, SituacaoCar, SituacaoRfb
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .exposicao import ResumoDeExposicao, calcular_exposicao, cobertura_limitada
from .formatacao import moeda, numero, percentual_de_fracao
from .util import NEUTRO, dias_entre, limitar, para_data, para_data_opcional, razao_segura

__all__ = [
    "fatores_comportamentais",
    "fatores_juridicos",
    "fatores_fiscais",
    "fatores_agroclimaticos",
    "fatores_cadastrais",
    "fatores_ambientais",
    "fatores_de_garantias",
    "FEATURIZERS",
    "calcular_todos_os_fatores",
    "anos_de_relacionamento",
]


# ---------------------------------------------------------------------------
# Infraestrutura comum
# ---------------------------------------------------------------------------


def _evidencias_do_fator(fator_id: str, fatos: FatosDoCliente) -> list[str]:
    return [e.id for e in fatos.evidencias if fator_id in e.fatores_relacionados]


def _fator(
    *,
    fator_id: str,
    dimensao: DimensaoId,
    rotulo: str,
    pontos: float,
    direcao: DirecaoFator,
    fatos: FatosDoCliente,
    cfg: ScoringConfig,
    detalhe: str | None = None,
) -> FatorCalculado | None:
    """Monta um fator já com seu impacto global — ou nada, se zerado."""
    if pontos <= NEUTRO:
        return None
    peso = cfg.pesos_dimensoes[dimensao]
    sinal = cfg.sinal_risco if direcao is DirecaoFator.RISCO else cfg.sinal_protecao
    impacto = peso * pontos * sinal
    return FatorCalculado(
        id=fator_id,
        dimensao=dimensao,
        rotulo=rotulo,
        detalhe=detalhe,
        pontos=round(pontos, cfg.casas_pontos),
        direcao=direcao,
        impacto_global=round(impacto, cfg.casas_score),
        impacto_global_ajustado=round(impacto, cfg.casas_score),
        fonte=cfg.fonte_por_fator.get(fator_id, cfg.fonte_padrao_dimensao[dimensao]),
        evidencia_ids=_evidencias_do_fator(fator_id, fatos),
    )


def _compactar(candidatos: list[FatorCalculado | None]) -> list[FatorCalculado]:
    return [fator for fator in candidatos if fator is not None]


def _faixa(valor: float, faixas: tuple[tuple[float, float], ...]) -> float:
    """Primeira faixa cujo limite superior não foi atingido; 0 fora de todas."""
    for limite, pontos in faixas:
        if valor < limite:
            return pontos
    return NEUTRO


def anos_de_relacionamento(fatos: FatosDoCliente, cfg: ScoringConfig, data_ref: date) -> float:
    """Tempo de relacionamento derivado da operação mais antiga do cliente.

    `FatosDoCliente` não carrega `inicioRelacionamento` (ele vive em `Cliente`,
    spec 01) e o motor recebe apenas fatos. A contratação mais antiga é a única
    testemunha do início do relacionamento presente nos próprios fatos.
    """
    datas = [para_data_opcional(op.data_contratacao) for op in fatos.operacoes]
    validas = [d for d in datas if d is not None]
    if not validas:
        return NEUTRO
    return max(NEUTRO, dias_entre(min(validas), data_ref) / cfg.dias_por_ano)


# ---------------------------------------------------------------------------
# D1 · Comportamental
# ---------------------------------------------------------------------------


def fatores_comportamentais(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    interno = fatos.interno
    dim = DimensaoId.COMPORTAMENTAL

    anos = anos_de_relacionamento(fatos, cfg, data_ref)
    delta_atraso = interno.atraso_medio_dias_90d - interno.atraso_medio_dias_12m
    n_covenants = len(interno.covenants_rompidos)

    return _compactar(
        [
            _fator(
                fator_id="atraso_medio",
                dimensao=dim,
                rotulo="Atraso médio de pagamento em 12 meses",
                detalhe=f"Atraso médio de {numero(interno.atraso_medio_dias_12m)} dias",
                pontos=limitar(
                    interno.atraso_medio_dias_12m * cfg.coef_atraso_medio, cfg.teto_atraso_medio
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="pior_atraso",
                dimensao=dim,
                rotulo="Pior atraso registrado em 12 meses",
                detalhe=f"Pior atraso de {numero(interno.pior_atraso_dias_12m)} dias",
                pontos=limitar(
                    interno.pior_atraso_dias_12m * cfg.coef_pior_atraso, cfg.teto_pior_atraso
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="pontualidade",
                dimensao=dim,
                rotulo="Títulos pagos em dia em 12 meses",
                detalhe=(
                    f"{percentual_de_fracao(interno.pct_titulos_pagos_em_dia_12m)} "
                    "dos títulos pagos em dia"
                ),
                pontos=(cfg.pontualidade_plena - interno.pct_titulos_pagos_em_dia_12m)
                * cfg.coef_pontualidade,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="renegociacoes",
                dimensao=dim,
                rotulo="Renegociações nos últimos 12 meses",
                detalhe=f"{numero(interno.renegociacoes_12m)} renegociação(ões) no período",
                pontos=limitar(
                    interno.renegociacoes_12m * cfg.coef_renegociacoes, cfg.teto_renegociacoes
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="inadimplencia_tecnica",
                dimensao=dim,
                rotulo="Inadimplência técnica — covenants contratuais rompidos",
                detalhe=(
                    "; ".join(c.descricao for c in interno.covenants_rompidos)
                    if interno.covenants_rompidos
                    else None
                ),
                pontos=limitar(
                    n_covenants * cfg.coef_inadimplencia_tecnica, cfg.teto_inadimplencia_tecnica
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="tendencia_atraso",
                dimensao=dim,
                rotulo="Deterioração do atraso médio nos últimos 90 dias",
                detalhe=(
                    f"Atraso médio subiu de {numero(interno.atraso_medio_dias_12m)} "
                    f"para {numero(interno.atraso_medio_dias_90d)} dias"
                ),
                pontos=limitar(
                    max(NEUTRO, delta_atraso) * cfg.coef_tendencia_atraso,
                    cfg.teto_tendencia_atraso,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="relacionamento",
                dimensao=dim,
                rotulo="Tempo de relacionamento com a Krill Tech",
                detalhe=f"{numero(anos, casas=1)} anos de histórico interno",
                pontos=limitar(anos * cfg.coef_relacionamento, cfg.teto_relacionamento),
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="historico_limpo",
                dimensao=dim,
                rotulo="Sem atraso relevante em 24 meses",
                detalhe="Nenhum atraso acima de 5 dias no período",
                pontos=cfg.pontos_historico_limpo if interno.sem_atraso_relevante_24m else NEUTRO,
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D2 · Jurídico & processual
# ---------------------------------------------------------------------------


def fatores_juridicos(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
    resumo: ResumoDeExposicao | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    resumo = resumo or calcular_exposicao(fatos, cfg, data_ref)
    juridico = fatos.juridico
    dim = DimensaoId.JURIDICO

    exposicao_total = resumo.calculada.exposicao_total
    razao_execucao = razao_segura(juridico.valor_total_em_execucao, exposicao_total)
    tem_rj = juridico.recuperacao_judicial is not None

    return _compactar(
        [
            _fator(
                fator_id="execucoes_titulo",
                dimensao=dim,
                rotulo="Execuções de título ajuizadas em 12 meses",
                detalhe=f"{numero(juridico.execucoes_titulo_12m)} execução(ões) no período",
                pontos=limitar(
                    juridico.execucoes_titulo_12m * cfg.coef_execucoes_titulo,
                    cfg.teto_execucoes_titulo,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="materialidade_execucao",
                dimensao=dim,
                rotulo="Materialidade do valor em execução",
                detalhe=(
                    f"{moeda(juridico.valor_total_em_execucao)} em execução, "
                    f"{percentual_de_fracao(razao_execucao)} da exposição"
                ),
                pontos=limitar(
                    razao_execucao * cfg.coef_materialidade_execucao,
                    cfg.teto_materialidade_execucao,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="aceleracao_judicial",
                dimensao=dim,
                rotulo="Aceleração judicial nos últimos 90 dias",
                detalhe=(
                    f"{numero(juridico.execucoes_titulo_90d)} execuções distribuídas em 90 dias"
                ),
                pontos=(
                    cfg.pontos_aceleracao_judicial
                    if juridico.execucoes_titulo_90d >= cfg.minimo_execucoes_90d_aceleracao
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="protestos",
                dimensao=dim,
                rotulo="Protestos ativos",
                detalhe=f"{numero(juridico.protestos_ativos)} protesto(s) em aberto",
                pontos=limitar(
                    juridico.protestos_ativos * cfg.coef_protestos, cfg.teto_protestos
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="protesto_recorrente",
                dimensao=dim,
                rotulo="Protestos recorrentes em 12 meses",
                detalhe=f"{numero(juridico.protestos_12m)} protestos nos últimos 12 meses",
                pontos=(
                    cfg.pontos_protesto_recorrente
                    if juridico.protestos_12m >= cfg.minimo_protestos_12m_recorrente
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="pedido_falencia",
                dimensao=dim,
                rotulo="Pedido de falência distribuído contra o cliente",
                pontos=cfg.pontos_pedido_falencia if juridico.pedido_falencia else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="rj_distribuida",
                dimensao=dim,
                rotulo="Recuperação judicial ajuizada ou deferida",
                detalhe=(
                    "Distribuída em "
                    f"{juridico.recuperacao_judicial.data_distribuicao}"
                    if tem_rj
                    else None
                ),
                pontos=cfg.pontos_rj_distribuida if tem_rj else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="trabalhistas",
                dimensao=dim,
                rotulo="Reclamações trabalhistas com trânsito em julgado",
                detalhe=f"{numero(juridico.acoes_trabalhistas_transitadas)} ação(ões) transitada(s)",
                pontos=limitar(
                    juridico.acoes_trabalhistas_transitadas * cfg.coef_trabalhistas,
                    cfg.teto_trabalhistas,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="pluralidade_credores",
                dimensao=dim,
                rotulo="Pluralidade de credores distintos executando",
                detalhe=(
                    f"{numero(juridico.credores_distintos_executando)} credores distintos "
                    "em execução — sinal de crise de liquidez, não de disputa bilateral"
                ),
                pontos=(
                    cfg.pontos_pluralidade_credores
                    if juridico.credores_distintos_executando >= cfg.minimo_credores_distintos
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="sem_litigio",
                dimensao=dim,
                rotulo="Sem litígio em 36 meses",
                pontos=cfg.pontos_sem_litigio if juridico.sem_litigio_36m else NEUTRO,
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D3 · Fiscal & trabalhista
# ---------------------------------------------------------------------------


def fatores_fiscais(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
    resumo: ResumoDeExposicao | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    resumo = resumo or calcular_exposicao(fatos, cfg, data_ref)
    fiscal = fatos.fiscal
    dim = DimensaoId.FISCAL

    razao_divida = razao_segura(fiscal.divida_ativa_pgfn, resumo.calculada.exposicao_total)
    cresceu = fiscal.divida_ativa_pgfn > fiscal.divida_ativa_pgfn_90d_atras

    return _compactar(
        [
            _fator(
                fator_id="divida_ativa",
                dimensao=dim,
                rotulo="Dívida ativa na PGFN",
                detalhe=(
                    f"{moeda(fiscal.divida_ativa_pgfn)} inscritos, "
                    f"{percentual_de_fracao(razao_divida)} da exposição"
                ),
                pontos=limitar(razao_divida * cfg.coef_divida_ativa, cfg.teto_divida_ativa),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="divida_ativa_crescente",
                dimensao=dim,
                rotulo="Dívida ativa em crescimento nos últimos 90 dias",
                detalhe=(
                    f"De {moeda(fiscal.divida_ativa_pgfn_90d_atras)} "
                    f"para {moeda(fiscal.divida_ativa_pgfn)}"
                ),
                pontos=cfg.pontos_divida_ativa_crescente if cresceu else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="cndt_positiva",
                dimensao=dim,
                rotulo="CNDT positiva",
                detalhe=(
                    f"Débito trabalhista de {moeda(fiscal.valor_debito_trabalhista)} "
                    "com trânsito em julgado"
                ),
                pontos=cfg.pontos_cndt_positiva if fiscal.cndt_positiva else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="fgts_irregular",
                dimensao=dim,
                rotulo="CRF-FGTS irregular",
                pontos=cfg.pontos_fgts_irregular if not fiscal.crf_fgts_regular else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="parcelamento_rompido",
                dimensao=dim,
                rotulo="Parcelamento fiscal rompido em 12 meses",
                pontos=(
                    cfg.pontos_parcelamento_rompido
                    if fiscal.parcelamento_rompido_12m
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="certidoes_negativas",
                dimensao=dim,
                rotulo="Todas as certidões negativas e vigentes",
                pontos=(
                    cfg.pontos_certidoes_negativas
                    if fiscal.todas_certidoes_negativas
                    else NEUTRO
                ),
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D4 · Agro & climático
# ---------------------------------------------------------------------------


def _barter_sem_lastro(fatos: FatosDoCliente, cfg: ScoringConfig) -> bool:
    """Barter cuja CPR vinculada não existe ou não está registrada."""
    cprs_registradas = {
        g.id for g in fatos.garantias if g.tipo in cfg.tipos_cpr and g.registrada
    }
    for operacao in fatos.operacoes:
        if operacao.barter is None:
            continue
        vinculo = operacao.barter.cpr_vinculada_id
        if vinculo is None or vinculo not in cprs_registradas:
            return True
    return False


def fatores_agroclimaticos(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    agro = fatos.agro
    dim = DimensaoId.AGROCLIMATICO

    culturas = agro.culturas
    deficit_produtividade = max(NEUTRO, -agro.produtividade_vs_media_regional_pct)
    fracao_irrigada = razao_segura(agro.area_irrigada_ha, agro.area_total_ha)
    tem_protecao_climatica = (
        fracao_irrigada >= cfg.fracao_minima_area_irrigada or agro.seguro_agricola_vigente
    )

    return _compactar(
        [
            _fator(
                fator_id="zarc_risco",
                dimensao=dim,
                rotulo="Risco ZARC da cultura na região",
                detalhe=f"Classificação ZARC: {agro.risco_zarc.value}",
                pontos=cfg.pontos_zarc[agro.risco_zarc],
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="quebra_safra_regional",
                dimensao=dim,
                rotulo="Quebra de safra regional no último ciclo",
                detalhe=(
                    f"Quebra de {numero(agro.quebra_safra_regional_pct, casas=1)}% "
                    f"na safra {agro.safra_referencia}"
                ),
                pontos=limitar(
                    agro.quebra_safra_regional_pct * cfg.coef_quebra_safra, cfg.teto_quebra_safra
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="desvio_precipitacao",
                dimensao=dim,
                rotulo="Desvio da precipitação acumulada vs. normal climatológica",
                detalhe=f"Desvio de {numero(agro.desvio_precipitacao_pct, casas=1)}%",
                pontos=limitar(
                    abs(agro.desvio_precipitacao_pct) * cfg.coef_desvio_precipitacao,
                    cfg.teto_desvio_precipitacao,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="monocultura",
                dimensao=dim,
                rotulo="Cultura única, sem diversificação",
                detalhe=f"Exploração concentrada em {', '.join(culturas)}" if culturas else None,
                pontos=cfg.pontos_monocultura if len(culturas) == 1 else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="produtividade_abaixo",
                dimensao=dim,
                rotulo="Produtividade abaixo da média regional",
                detalhe=f"{numero(deficit_produtividade, casas=1)}% abaixo da média regional",
                pontos=limitar(
                    deficit_produtividade * cfg.coef_produtividade_abaixo,
                    cfg.teto_produtividade_abaixo,
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="barter_sem_lastro",
                dimensao=dim,
                rotulo="Operação barter sem CPR registrada cobrindo-a",
                detalhe="Safra prometida sem lastro formal registrado",
                pontos=(
                    cfg.pontos_barter_sem_lastro if _barter_sem_lastro(fatos, cfg) else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="irrigacao_ou_seguro",
                dimensao=dim,
                rotulo="Irrigação relevante ou seguro agrícola vigente",
                detalhe=(
                    f"{numero(agro.area_irrigada_ha)} ha irrigados de "
                    f"{numero(agro.area_total_ha)} ha"
                    if fracao_irrigada >= cfg.fracao_minima_area_irrigada
                    else "Seguro agrícola vigente para a safra"
                ),
                pontos=cfg.pontos_irrigacao_ou_seguro if tem_protecao_climatica else NEUTRO,
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="diversificacao",
                dimensao=dim,
                rotulo="Diversificação de culturas",
                detalhe=f"{numero(len(culturas))} culturas distintas: {', '.join(culturas)}"
                if culturas
                else None,
                pontos=(
                    cfg.pontos_diversificacao
                    if len(culturas) >= cfg.minimo_culturas_diversificacao
                    else NEUTRO
                ),
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D5 · Cadastral & societário
# ---------------------------------------------------------------------------


def fatores_cadastrais(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
    resumo: ResumoDeExposicao | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    resumo = resumo or calcular_exposicao(fatos, cfg, data_ref)
    cadastral = fatos.cadastral
    dim = DimensaoId.CADASTRAL

    exposicao_total = resumo.calculada.exposicao_total
    razao_capital = razao_segura(cadastral.capital_social, exposicao_total)
    tem_exposicao = exposicao_total > NEUTRO

    return _compactar(
        [
            _fator(
                fator_id="situacao_cadastral",
                dimensao=dim,
                rotulo="Situação cadastral na Receita Federal",
                detalhe=f"Situação {cadastral.situacao_rfb.value}",
                pontos=(
                    cfg.pontos_situacao_cadastral
                    if cadastral.situacao_rfb is not SituacaoRfb.ATIVA
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="tempo_atividade",
                dimensao=dim,
                rotulo="Tempo de atividade",
                detalhe=f"{numero(cadastral.anos_atividade, casas=1)} anos de atividade",
                pontos=_faixa(cadastral.anos_atividade, cfg.faixas_tempo_atividade),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="alteracao_societaria",
                dimensao=dim,
                rotulo="Alteração societária relevante em 180 dias",
                pontos=(
                    cfg.pontos_alteracao_societaria
                    if cadastral.alteracao_societaria_180d
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="saida_socio_majoritario",
                dimensao=dim,
                rotulo="Saída de sócio majoritário em 12 meses",
                pontos=(
                    cfg.pontos_saida_socio_majoritario
                    if cadastral.saida_socio_majoritario_12m
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="capital_vs_exposicao",
                dimensao=dim,
                rotulo="Capital social frente à exposição",
                detalhe=(
                    f"Capital de {moeda(cadastral.capital_social)} para "
                    f"{moeda(exposicao_total)} de exposição"
                ),
                pontos=(
                    _faixa(razao_capital, cfg.faixas_capital_vs_exposicao)
                    if tem_exposicao
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="cnae_incompativel",
                dimensao=dim,
                rotulo="CNAE principal incompatível com a atividade declarada",
                pontos=(
                    cfg.pontos_cnae_incompativel if not cadastral.cnae_compativel else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="qsa_estavel",
                dimensao=dim,
                rotulo="Quadro societário estável há 5 anos ou mais",
                pontos=cfg.pontos_qsa_estavel if cadastral.qsa_estavel_5anos else NEUTRO,
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D6 · Ambiental
# ---------------------------------------------------------------------------


def fatores_ambientais(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    ambiental = fatos.ambiental
    dim = DimensaoId.AMBIENTAL

    return _compactar(
        [
            _fator(
                fator_id="embargo_ibama",
                dimensao=dim,
                rotulo="Embargo do IBAMA vigente sobre imóvel do cliente",
                detalhe=(
                    "Embargo recai sobre bem dado em garantia"
                    if ambiental.embargo_sobre_imovel_em_garantia
                    else None
                ),
                pontos=cfg.pontos_embargo_ibama if ambiental.embargo_ibama_vigente else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="auto_infracao",
                dimensao=dim,
                rotulo="Auto de infração ambiental não quitado",
                pontos=cfg.pontos_auto_infracao if ambiental.auto_infracao_nao_quitado else NEUTRO,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="car_ausente",
                dimensao=dim,
                rotulo="Imóvel sem Cadastro Ambiental Rural",
                pontos=(
                    cfg.pontos_car_ausente
                    if ambiental.situacao_car is SituacaoCar.AUSENTE
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="car_irregular",
                dimensao=dim,
                rotulo="CAR em situação pendente ou irregular",
                detalhe=f"Situação do CAR: {ambiental.situacao_car.value}",
                pontos=(
                    cfg.pontos_car_irregular
                    if ambiental.situacao_car in cfg.situacoes_car_irregulares
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="sobreposicao_app",
                dimensao=dim,
                rotulo="Sobreposição com reserva legal ou APP",
                pontos=(
                    cfg.pontos_sobreposicao_app
                    if ambiental.sobreposicao_app_ou_reserva
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="car_regular",
                dimensao=dim,
                rotulo="CAR ativo e regular",
                pontos=(
                    cfg.pontos_car_regular
                    if ambiental.situacao_car is SituacaoCar.ATIVO_REGULAR
                    else NEUTRO
                ),
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# D7 · Garantias & exposição
# ---------------------------------------------------------------------------


def fatores_de_garantias(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
    resumo: ResumoDeExposicao | None = None,
) -> list[FatorCalculado]:
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    resumo = resumo or calcular_exposicao(fatos, cfg, data_ref)
    exposicao = resumo.calculada
    dim = DimensaoId.GARANTIAS

    cobertura_extra = cobertura_limitada(exposicao.cobertura_extraconcursal, cfg)
    cobertura_total = cobertura_limitada(exposicao.cobertura_total, cfg)
    descoberto_extra = cfg.cobertura_maxima_no_calculo - cobertura_extra
    descoberto_total = cfg.cobertura_maxima_no_calculo - cobertura_total

    pontos_utilizacao = NEUTRO
    if exposicao.limite_utilizado_pct > cfg.limiar_utilizacao_alta:
        pontos_utilizacao += cfg.pontos_utilizacao_alta
    if exposicao.limite_utilizado_pct > cfg.limiar_utilizacao_critica:
        pontos_utilizacao += cfg.pontos_utilizacao_critica
    pontos_utilizacao = limitar(pontos_utilizacao, cfg.teto_utilizacao_limite)

    fracao_vencimento_proximo = razao_segura(exposicao.a_vencer_90d, resumo.total_a_vencer)

    return _compactar(
        [
            _fator(
                fator_id="descoberto_extraconcursal",
                dimensao=dim,
                rotulo="Exposição descoberta de garantia extraconcursal",
                detalhe=(
                    f"{moeda(exposicao.exposicao_em_risco_em_rj)} sem proteção em cenário de RJ "
                    f"({percentual_de_fracao(descoberto_extra)} da exposição)"
                ),
                pontos=descoberto_extra * cfg.coef_descoberto_extraconcursal,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="descoberto_total",
                dimensao=dim,
                rotulo="Exposição descoberta de qualquer garantia",
                detalhe=(
                    f"{moeda(exposicao.exposicao_em_risco)} sem qualquer garantia "
                    f"({percentual_de_fracao(descoberto_total)} da exposição)"
                ),
                pontos=descoberto_total * cfg.coef_descoberto_total,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="utilizacao_limite",
                dimensao=dim,
                rotulo="Utilização do limite aprovado",
                detalhe=(
                    f"{percentual_de_fracao(exposicao.limite_utilizado_pct)} de "
                    f"{moeda(exposicao.limite_aprovado)} utilizados"
                ),
                pontos=pontos_utilizacao,
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="concentracao_patrimonial",
                dimensao=dim,
                rotulo="Exposição acima de 2× o patrimônio declarado",
                detalhe=(
                    f"{moeda(exposicao.exposicao_total)} de exposição contra "
                    f"{moeda(fatos.patrimonio_declarado)} de patrimônio"
                ),
                pontos=(
                    cfg.pontos_concentracao_patrimonial
                    if exposicao.exposicao_total
                    > cfg.multiplo_patrimonio_concentracao * fatos.patrimonio_declarado
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="vencimento_concentrado",
                dimensao=dim,
                rotulo="Vencimentos concentrados em 90 dias",
                detalhe=(
                    f"{percentual_de_fracao(fracao_vencimento_proximo)} do saldo a vencer "
                    f"({moeda(exposicao.a_vencer_90d)}) vence em até 90 dias"
                ),
                pontos=(
                    cfg.pontos_vencimento_concentrado
                    if fracao_vencimento_proximo > cfg.fracao_vencimento_concentrado
                    else NEUTRO
                ),
                direcao=DirecaoFator.RISCO,
                fatos=fatos,
                cfg=cfg,
            ),
            _fator(
                fator_id="sobrecolateral",
                dimensao=dim,
                rotulo="Cobertura extraconcursal integral",
                detalhe=(
                    f"{moeda(exposicao.valor_extraconcursal)} em garantias extraconcursais "
                    f"para {moeda(exposicao.exposicao_total)} de exposição"
                ),
                pontos=(
                    cfg.pontos_sobrecolateral
                    if exposicao.cobertura_extraconcursal >= cfg.cobertura_minima_sobrecolateral
                    else NEUTRO
                ),
                direcao=DirecaoFator.PROTECAO,
                fatos=fatos,
                cfg=cfg,
            ),
        ]
    )


#: Um featurizer por dimensão, na ordem de apresentação.
FEATURIZERS: dict[DimensaoId, object] = {
    DimensaoId.COMPORTAMENTAL: fatores_comportamentais,
    DimensaoId.JURIDICO: fatores_juridicos,
    DimensaoId.FISCAL: fatores_fiscais,
    DimensaoId.AGROCLIMATICO: fatores_agroclimaticos,
    DimensaoId.CADASTRAL: fatores_cadastrais,
    DimensaoId.AMBIENTAL: fatores_ambientais,
    DimensaoId.GARANTIAS: fatores_de_garantias,
}


def calcular_todos_os_fatores(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
    resumo: ResumoDeExposicao | None = None,
) -> dict[DimensaoId, list[FatorCalculado]]:
    """Executa os sete featurizers e devolve os fatores agrupados por dimensão."""
    cfg = resolver_config(config)
    data_ref = data_referencia or para_data(fatos.data_referencia)
    resumo = resumo or calcular_exposicao(fatos, cfg, data_ref)

    return {
        DimensaoId.COMPORTAMENTAL: fatores_comportamentais(fatos, cfg, data_ref),
        DimensaoId.JURIDICO: fatores_juridicos(fatos, cfg, data_ref, resumo),
        DimensaoId.FISCAL: fatores_fiscais(fatos, cfg, data_ref, resumo),
        DimensaoId.AGROCLIMATICO: fatores_agroclimaticos(fatos, cfg, data_ref),
        DimensaoId.CADASTRAL: fatores_cadastrais(fatos, cfg, data_ref, resumo),
        DimensaoId.AMBIENTAL: fatores_ambientais(fatos, cfg, data_ref),
        DimensaoId.GARANTIAS: fatores_de_garantias(fatos, cfg, data_ref, resumo),
    }
