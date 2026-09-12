"""Motor de risco determinístico do Lastro — `specs/02-motor-de-risco.md`.

    fatos → fatores → dimensões → score → rating → vetos → PD, RJ, ações

Função pura e síncrona: sem I/O, sem relógio, sem aleatoriedade. A data de
referência é sempre parâmetro explícito, o que torna os testes determinísticos
e os snapshots históricos recalculáveis.

    >>> from models import FatosDoCliente
    >>> from scoring import calcular_risco
    >>> avaliacao = calcular_risco(
    ...     FatosDoCliente(clienteId="demo", dataReferencia="2026-09-12")
    ... )
    >>> avaliacao.score_calculado, avaliacao.rating_final.value
    (1000.0, 'A')
"""

from __future__ import annotations

from datetime import date

from models.avaliacao import AvaliacaoDeRisco, DimensaoAvaliada
from models.fatos import FatosDoCliente

from .audit import fatores_das_dimensoes, fechou, verificar_fechamento
from .config import CONFIG_PADRAO, ScoringConfig, resolver_config
from .delta import (
    classificar_tendencia,
    comparar_avaliacoes,
    deltas_de_fatores,
    estimar_variacao_90d,
    fatores_da_avaliacao,
)
from .dimensoes import (
    DimensaoBruta,
    calcular_dimensoes_brutas,
    montar_dimensao_avaliada,
)
from .exposicao import ResumoDeExposicao, calcular_exposicao, normalizar_garantias
from .fatores import calcular_todos_os_fatores
from .probabilidades import calcular_pd, calcular_risco_rj, pd12_do_score
from .recomendacao import escolher_codigo, montar_recomendacao
from .red_flags import derivar_red_flags
from .score import calcular_score, classificar_rating, rating_mais_severo
from .stay_period import calcular_stay_period
from .util import para_data
from .vetos import aplicar_vetos, avaliar_vetos

__all__ = [
    "calcular_risco",
    "CONFIG_PADRAO",
    "ScoringConfig",
    "resolver_config",
    "calcular_exposicao",
    "normalizar_garantias",
    "calcular_todos_os_fatores",
    "calcular_dimensoes_brutas",
    "calcular_score",
    "classificar_rating",
    "rating_mais_severo",
    "avaliar_vetos",
    "aplicar_vetos",
    "calcular_pd",
    "pd12_do_score",
    "calcular_risco_rj",
    "calcular_stay_period",
    "derivar_red_flags",
    "escolher_codigo",
    "montar_recomendacao",
    "classificar_tendencia",
    "estimar_variacao_90d",
    "comparar_avaliacoes",
    "deltas_de_fatores",
    "fatores_da_avaliacao",
    "verificar_fechamento",
    "fechou",
]


def _resolver_data(
    fatos: FatosDoCliente, data_referencia: date | str | None
) -> date:
    """A data vem do parâmetro ou dos próprios fatos — nunca do relógio."""
    if data_referencia is None:
        return para_data(fatos.data_referencia)
    if isinstance(data_referencia, str):
        return para_data(data_referencia)
    return data_referencia


def _dimensao_avaliada(
    bruta: DimensaoBruta, cfg: ScoringConfig
) -> DimensaoAvaliada:
    """Cada dimensão carrega a tendência dos seus próprios eventos de 90 dias."""
    variacao = estimar_variacao_90d(bruta.fatores, cfg)
    return montar_dimensao_avaliada(bruta, classificar_tendencia(variacao, cfg), cfg)


def calcular_risco(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | str | None = None,
) -> AvaliacaoDeRisco:
    """Avaliação completa de um instante de fatos — o contrato da §14."""
    cfg = resolver_config(config)
    data_ref = _resolver_data(fatos, data_referencia)

    resumo: ResumoDeExposicao = calcular_exposicao(fatos, cfg, data_ref)
    fatores_por_dimensao = calcular_todos_os_fatores(fatos, cfg, data_ref, resumo)
    brutas = calcular_dimensoes_brutas(fatores_por_dimensao, cfg)

    resultado = calcular_score(brutas, cfg)
    fatores = fatores_das_dimensoes(resultado.dimensoes)

    variacao_90d = estimar_variacao_90d(fatores, cfg)
    tendencia = classificar_tendencia(variacao_90d, cfg)

    vetos = avaliar_vetos(fatos, resumo, cfg)
    rating_final = aplicar_vetos(resultado.rating, vetos, cfg)

    return AvaliacaoDeRisco(
        cliente_id=fatos.cliente_id,
        data_referencia=data_ref.isoformat(),
        score_calculado=resultado.score,
        rating_calculado=resultado.rating,
        rating_final=rating_final,
        vetos_ativos=vetos,
        dimensoes=[_dimensao_avaliada(bruta, cfg) for bruta in resultado.dimensoes],
        pd=calcular_pd(resultado.score, tendencia, cfg),
        risco_rj=calcular_risco_rj(fatos, resumo, cfg),
        stay_period=calcular_stay_period(fatos, cfg, data_ref),
        exposicao=resumo.calculada,
        tendencia=tendencia,
        red_flags=derivar_red_flags(fatos, fatores, vetos, variacao_90d, cfg),
        recomendacao=montar_recomendacao(
            rating_final, tendencia, vetos, fatos, resumo, cfg
        ),
        evidencias=list(fatos.evidencias),
        auditoria=verificar_fechamento(resultado.score, fatores, cfg),
    )
