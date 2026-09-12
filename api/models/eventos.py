"""Série histórica, eventos, alertas, trilha de auditoria e delta de score."""

from __future__ import annotations

from pydantic import Field

from .base import ModeloLastro
from .enums import (
    CodigoRecomendacao,
    DecisaoAnalista,
    DimensaoId,
    FonteId,
    Rating,
    Severidade,
    TipoEventoDeRisco,
)
from .fatos import FatosDoCliente

__all__ = [
    "SnapshotHistorico",
    "EventoDeRisco",
    "Alerta",
    "RegistroAuditoria",
    "DeltaDeFator",
    "ComparacaoDeAvaliacoes",
]


class SnapshotHistorico(ModeloLastro):
    #: ISO date
    data: str
    fatos: FatosDoCliente


class EventoDeRisco(ModeloLastro):
    id: str
    cliente_id: str
    #: ISO date
    data: str
    tipo: TipoEventoDeRisco
    severidade: Severidade
    titulo: str
    descricao: str
    fonte: FonteId
    #: derivado do recálculo do snapshot
    score_apos: float
    delta_score: float
    evidencia_ids: list[str] = Field(default_factory=list)


class Alerta(ModeloLastro):
    id: str
    cliente_id: str
    cliente_nome: str
    #: ISO date
    data: str
    severidade: Severidade
    titulo: str
    descricao: str
    impacto: str
    acao_recomendada: str
    lido: bool = False
    evento_id: str | None = None


class RegistroAuditoria(ModeloLastro):
    id: str
    cliente_id: str
    cliente_nome: str
    analista: str
    #: ISO datetime
    data_hora: str
    score_no_momento: float
    rating_no_momento: Rating
    recomendacao_gerada: CodigoRecomendacao
    decisao_analista: DecisaoAnalista
    justificativa: str
    #: true quando o analista decidiu diferente do recomendado.
    divergiu_da_recomendacao: bool


class DeltaDeFator(ModeloLastro):
    """Uma linha do "por que o score mudou" (`02-motor-de-risco.md` §11).

    Tipo derivado do motor, não previsto na spec 01 — necessário para expor a
    invariante I6 ao frontend.
    """

    fator_id: str
    dimensao: DimensaoId
    rotulo: str
    detalhe: str | None = None
    impacto_anterior: float
    impacto_atual: float
    delta: float
    #: 'novo' quando só existe em t1, 'removido' quando só existe em t0.
    situacao: str


class ComparacaoDeAvaliacoes(ModeloLastro):
    """Resultado de `scoring.delta.comparar_avaliacoes`."""

    cliente_id: str
    data_anterior: str
    data_atual: str
    score_anterior: float
    score_atual: float
    delta_score: float
    #: ordenado por |delta| decrescente
    fatores: list[DeltaDeFator] = Field(default_factory=list)
    #: score_atual − score_anterior − Σ delta. Deve ser 0 (tolerância 0,5). Ver I6.
    diferenca_de_fechamento: float
