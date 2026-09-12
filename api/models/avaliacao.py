"""Saída do motor — derivada, nunca persistida. `specs/01-modelo-de-dados.md`."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ModeloLastro
from .enums import (
    CodigoRecomendacao,
    DimensaoId,
    DirecaoFator,
    EfeitoVeto,
    FonteId,
    Rating,
    Severidade,
    StatusRedFlag,
    Tendencia,
)
from .exposicao import ExposicaoCalculada
from .fatos import Evidencia

__all__ = [
    "FatorCalculado",
    "DimensaoAvaliada",
    "ProbabilidadeDeDefault",
    "SinalRJ",
    "RiscoRJ",
    "StayPeriod",
    "VetoAtivo",
    "RedFlag",
    "AcaoRecomendada",
    "Recomendacao",
    "AuditoriaDeFechamento",
    "AvaliacaoDeRisco",
    "AVISO_DO_ANALISTA",
]

#: Texto não dispensável exigido pela §12 da spec do motor.
AVISO_DO_ANALISTA = "Decisão final sujeita à avaliação do analista responsável."


class FatorCalculado(ModeloLastro):
    id: str
    dimensao: DimensaoId
    #: texto pronto para a UI, em pt-BR
    rotulo: str
    #: ex.: 'atraso médio subiu de 3 para 11 dias'
    detalhe: str | None = None
    #: sempre positivo
    pontos: float
    direcao: DirecaoFator
    #: peso(dimensão) × pontos × sinal. Soma de todos reconstrói o score. Ver I2.
    impacto_global: float
    #: após redistribuição de saturação
    impacto_global_ajustado: float
    fonte: FonteId
    evidencia_ids: list[str] = Field(default_factory=list)


class DimensaoAvaliada(ModeloLastro):
    id: DimensaoId
    rotulo: str
    #: 0..1000
    score: float
    #: 0..1
    peso: float
    #: score × peso
    contribuicao: float
    tendencia: Tendencia
    fatores: list[FatorCalculado] = Field(default_factory=list)
    fontes: list[FonteId] = Field(default_factory=list)
    saturou: bool = False


class ProbabilidadeDeDefault(ModeloLastro):
    #: 0..1
    pd6m: float
    pd12m: float
    pd24m: float
    #: texto curto explicando a derivação, exibido em tooltip
    metodo: str


class SinalRJ(ModeloLastro):
    rotulo: str
    pontos: float


class RiscoRJ(ModeloLastro):
    #: 0..1, ou 1 quando o evento já ocorreu.
    probabilidade_12m: float
    evento_ja_ocorrido: bool
    #: 0..100
    rj_index: float
    rj_index_efetivo: float
    elegivel: bool
    motivo_inelegibilidade: str | None = None
    sinais: list[SinalRJ] = Field(default_factory=list)


class StayPeriod(ModeloLastro):
    ativo: bool
    #: ISO date
    data_deferimento: str
    dias_decorridos: int
    dias_restantes: int
    #: o que a Krill Tech NÃO pode fazer
    bloqueios: list[str] = Field(default_factory=list)
    #: o que segue possível (extraconcursal)
    permitido: list[str] = Field(default_factory=list)


class VetoAtivo(ModeloLastro):
    id: str
    rotulo: str
    efeito: EfeitoVeto
    justificativa: str
    evidencia_ids: list[str] = Field(default_factory=list)


class RedFlag(ModeloLastro):
    id: str
    severidade: Severidade
    titulo: str
    descricao: str
    #: ISO date
    data: str
    fonte: FonteId
    #: negativo
    impacto_em_pontos: float
    status: StatusRedFlag = StatusRedFlag.NOVA
    evidencia_ids: list[str] = Field(default_factory=list)
    fator_id: str | None = None


class AcaoRecomendada(ModeloLastro):
    id: str
    #: já parametrizado com os números do cliente
    rotulo: str
    detalhe: str | None = None
    prioridade: Literal[1, 2, 3]


class Recomendacao(ModeloLastro):
    codigo: CodigoRecomendacao
    rotulo: str
    acoes: list[AcaoRecomendada] = Field(default_factory=list)
    prazo_reavaliacao_dias: int
    #: Preenchido pelo LLM em runtime; nunca vem do mock.
    explicacao: str | None = None
    aviso: Literal["Decisão final sujeita à avaliação do analista responsável."] = (
        AVISO_DO_ANALISTA
    )


class AuditoriaDeFechamento(ModeloLastro):
    soma_impactos: float
    score_reconstruido: float
    #: Deve ser 0 (tolerância 0,5). Ver I2.
    diferenca: float


class AvaliacaoDeRisco(ModeloLastro):
    cliente_id: str
    data_referencia: str
    score_calculado: float
    rating_calculado: Rating
    rating_final: Rating
    vetos_ativos: list[VetoAtivo] = Field(default_factory=list)
    dimensoes: list[DimensaoAvaliada] = Field(default_factory=list)
    pd: ProbabilidadeDeDefault
    risco_rj: RiscoRJ = Field(alias="riscoRJ", serialization_alias="riscoRJ")
    stay_period: StayPeriod | None = None
    exposicao: ExposicaoCalculada
    tendencia: Tendencia
    red_flags: list[RedFlag] = Field(default_factory=list)
    recomendacao: Recomendacao
    evidencias: list[Evidencia] = Field(default_factory=list)
    auditoria: AuditoriaDeFechamento
