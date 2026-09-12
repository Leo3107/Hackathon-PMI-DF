"""Score final, rating e redistribuição de saturação — §3 e §5 da spec do motor.

A invariante I2 é o contrato com o jurado:

    scoreCalculado = 1000 + Σ impactoGlobalAjustado(fator)

Quando uma dimensão satura no clamp, a igualdade só se mantém se o excedente
for devolvido: os `impactoGlobal` daquela dimensão são reescalados
**proporcionalmente** até que a soma feche de novo. O fator de escala é

    alvo   = peso × (score_com_clamp − 1000)
    atual  = peso × (score_sem_clamp − 1000)   ( = Σ impactoGlobal da dimensão )
    escala = alvo ÷ atual
"""

from __future__ import annotations

from dataclasses import dataclass

from models.avaliacao import FatorCalculado
from models.enums import Rating

from .config import ScoringConfig, resolver_config
from .dimensoes import DimensaoBruta, soma_de_impactos, substituir_fatores
from .util import NEUTRO, arredondar

__all__ = [
    "ResultadoDeScore",
    "fator_de_escala_da_dimensao",
    "impacto_global_ajustado",
    "redistribuir_saturacao",
    "calcular_score",
    "classificar_rating",
    "rotulo_do_rating",
    "rating_mais_severo",
]

#: Escala neutra: nenhuma redistribuição a fazer.
_ESCALA_NEUTRA: float = 1.0


@dataclass(frozen=True)
class ResultadoDeScore:
    score: float
    rating: Rating
    dimensoes: list[DimensaoBruta]
    soma_impactos_ajustados: float


def fator_de_escala_da_dimensao(
    dimensao: DimensaoBruta, config: ScoringConfig | None = None
) -> float:
    """Quanto os impactos da dimensão precisam encolher para a soma fechar."""
    cfg = resolver_config(config)
    if not dimensao.saturou:
        return _ESCALA_NEUTRA
    atual = dimensao.peso * (dimensao.score_bruto - cfg.score_base)
    if atual == NEUTRO:
        return _ESCALA_NEUTRA
    alvo = dimensao.peso * (dimensao.score - cfg.score_base)
    return alvo / atual


def impacto_global_ajustado(
    fator: FatorCalculado,
    dimensao: DimensaoBruta,
    config: ScoringConfig | None = None,
) -> float:
    """`impactoGlobal` do fator após a redistribuição de saturação da dimensão."""
    cfg = resolver_config(config)
    return arredondar(
        fator.impacto_global * fator_de_escala_da_dimensao(dimensao, cfg), cfg.casas_score
    )


def redistribuir_saturacao(
    dimensoes: list[DimensaoBruta], config: ScoringConfig | None = None
) -> list[DimensaoBruta]:
    """Devolve as dimensões com `impactoGlobalAjustado` já reescalado."""
    cfg = resolver_config(config)
    redistribuidas: list[DimensaoBruta] = []
    for dimensao in dimensoes:
        ajustados = [
            fator.model_copy(
                update={"impacto_global_ajustado": impacto_global_ajustado(fator, dimensao, cfg)}
            )
            for fator in dimensao.fatores
        ]
        redistribuidas.append(substituir_fatores(dimensao, ajustados))
    return redistribuidas


def calcular_score(
    dimensoes: list[DimensaoBruta], config: ScoringConfig | None = None
) -> ResultadoDeScore:
    """Média ponderada das dimensões, rating e redistribuição, de uma vez."""
    cfg = resolver_config(config)
    redistribuidas = redistribuir_saturacao(dimensoes, cfg)
    score = arredondar(
        sum(d.score * d.peso for d in redistribuidas) if redistribuidas else cfg.score_base,
        cfg.casas_score,
    )
    soma = sum(
        fator.impacto_global_ajustado for d in redistribuidas for fator in d.fatores
    )
    return ResultadoDeScore(
        score=score,
        rating=classificar_rating(score, cfg),
        dimensoes=redistribuidas,
        soma_impactos_ajustados=arredondar(soma, cfg.casas_score),
    )


def classificar_rating(score: float, config: ScoringConfig | None = None) -> Rating:
    """Faixas da §5, avaliadas do rating mais alto para o mais baixo."""
    cfg = resolver_config(config)
    for piso, rating in cfg.faixas_rating:
        if score >= piso:
            return rating
    return cfg.faixas_rating[-1][1]


def rotulo_do_rating(rating: Rating, config: ScoringConfig | None = None) -> str:
    cfg = resolver_config(config)
    return cfg.rotulos_rating[rating]


def rating_mais_severo(
    candidatos: list[Rating], config: ScoringConfig | None = None
) -> Rating:
    """O pior rating da lista — base da composição de vetos (§8)."""
    cfg = resolver_config(config)
    return max(candidatos, key=lambda rating: cfg.severidade_do_rating[rating])


def soma_de_impactos_brutos(dimensoes: list[DimensaoBruta]) -> float:
    return sum(soma_de_impactos(d.fatores) for d in dimensoes)
