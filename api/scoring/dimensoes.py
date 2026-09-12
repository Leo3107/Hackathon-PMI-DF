"""Agregação de fatores em dimensões — `specs/02-motor-de-risco.md` §3.

    scoreDimensao = clamp( 1000 - Σ penalidades + Σ bonus , 0 , 1000 )
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from models.avaliacao import DimensaoAvaliada, FatorCalculado
from models.enums import DimensaoId, DirecaoFator, FonteId, Tendencia

from .config import ScoringConfig, resolver_config
from .util import NEUTRO, arredondar, clamp

__all__ = [
    "DimensaoBruta",
    "calcular_dimensao_bruta",
    "calcular_dimensoes_brutas",
    "montar_dimensao_avaliada",
]


@dataclass(frozen=True)
class DimensaoBruta:
    """Dimensão antes de virar modelo de saída — guarda o score pré-clamp."""

    id: DimensaoId
    peso: float
    penalidades: float
    bonus: float
    #: 1000 − penalidades + bônus, sem clamp. Denuncia a saturação.
    score_bruto: float
    #: `score_bruto` restrito a [0, 1000].
    score: float
    saturou: bool
    fatores: list[FatorCalculado]


def calcular_dimensao_bruta(
    dimensao: DimensaoId,
    fatores: list[FatorCalculado],
    config: ScoringConfig | None = None,
) -> DimensaoBruta:
    cfg = resolver_config(config)
    penalidades = sum(f.pontos for f in fatores if f.direcao is DirecaoFator.RISCO)
    bonus = sum(f.pontos for f in fatores if f.direcao is DirecaoFator.PROTECAO)
    score_bruto = cfg.score_base - penalidades + bonus
    score = clamp(score_bruto, cfg.score_minimo, cfg.score_maximo)
    return DimensaoBruta(
        id=dimensao,
        peso=cfg.pesos_dimensoes[dimensao],
        penalidades=penalidades,
        bonus=bonus,
        score_bruto=score_bruto,
        score=score,
        saturou=score != score_bruto,
        fatores=list(fatores),
    )


def calcular_dimensoes_brutas(
    fatores_por_dimensao: dict[DimensaoId, list[FatorCalculado]],
    config: ScoringConfig | None = None,
) -> list[DimensaoBruta]:
    cfg = resolver_config(config)
    return [
        calcular_dimensao_bruta(dimensao, fatores_por_dimensao.get(dimensao, []), cfg)
        for dimensao in cfg.pesos_dimensoes
    ]


def _fontes(fatores: list[FatorCalculado]) -> list[FonteId]:
    """Fontes distintas, na ordem de aparição — a UI lista assim."""
    vistas: list[FonteId] = []
    for fator in fatores:
        if fator.fonte not in vistas:
            vistas.append(fator.fonte)
    return vistas


def montar_dimensao_avaliada(
    bruta: DimensaoBruta,
    tendencia: Tendencia,
    config: ScoringConfig | None = None,
) -> DimensaoAvaliada:
    cfg = resolver_config(config)
    return DimensaoAvaliada(
        id=bruta.id,
        rotulo=cfg.rotulos_dimensoes[bruta.id],
        score=arredondar(bruta.score, cfg.casas_score),
        peso=bruta.peso,
        contribuicao=arredondar(bruta.score * bruta.peso, cfg.casas_score),
        tendencia=tendencia,
        fatores=bruta.fatores,
        fontes=_fontes(bruta.fatores),
        saturou=bruta.saturou,
    )


def substituir_fatores(bruta: DimensaoBruta, fatores: list[FatorCalculado]) -> DimensaoBruta:
    """Cópia da dimensão com outra lista de fatores (usada pela redistribuição)."""
    return replace(bruta, fatores=fatores)


def soma_de_impactos(fatores: list[FatorCalculado]) -> float:
    return sum(f.impacto_global for f in fatores) if fatores else NEUTRO
