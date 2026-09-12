"""Fechamento das somas — a invariante I2 exposta como número auditável.

    scoreCalculado = 1000 + Σ impactoGlobalAjustado(fator)

`verificarFechamento` devolve a diferença entre o score exibido e a soma
reconstruída. O contrato é que ela seja 0 (tolerância `TOLERANCIA_FECHAMENTO`)
para todo cliente e todo snapshot — inclusive quando alguma dimensão satura no
clamp e o excedente é redistribuído por `scoring.score`.
"""

from __future__ import annotations

from collections.abc import Iterable

from models.avaliacao import AuditoriaDeFechamento, FatorCalculado

from .config import ScoringConfig, resolver_config
from .dimensoes import DimensaoBruta
from .util import arredondar

__all__ = [
    "soma_dos_impactos_ajustados",
    "fatores_das_dimensoes",
    "verificar_fechamento",
    "fechou",
]


def soma_dos_impactos_ajustados(fatores: Iterable[FatorCalculado]) -> float:
    return sum(fator.impacto_global_ajustado for fator in fatores)


def fatores_das_dimensoes(dimensoes: Iterable[DimensaoBruta]) -> list[FatorCalculado]:
    return [fator for dimensao in dimensoes for fator in dimensao.fatores]


def verificar_fechamento(
    score: float,
    fatores: Iterable[FatorCalculado],
    config: ScoringConfig | None = None,
) -> AuditoriaDeFechamento:
    """Diferença entre o score calculado e o score reconstruído pela soma."""
    cfg = resolver_config(config)
    soma = soma_dos_impactos_ajustados(fatores)
    reconstruido = cfg.score_base + soma
    return AuditoriaDeFechamento(
        soma_impactos=arredondar(soma, cfg.casas_score),
        score_reconstruido=arredondar(reconstruido, cfg.casas_score),
        diferenca=arredondar(score - reconstruido, cfg.casas_score),
    )


def fechou(
    auditoria: AuditoriaDeFechamento, config: ScoringConfig | None = None
) -> bool:
    """A soma fecha dentro da tolerância declarada na configuração."""
    cfg = resolver_config(config)
    return abs(auditoria.diferenca) < cfg.tolerancia_fechamento
