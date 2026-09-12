"""Modelos pydantic v2 do Lastro.

Tradução literal de `specs/01-modelo-de-dados.md`. Campos em `snake_case` no
Python, chaves `camelCase` no JSON — ver `models.base.ModeloLastro`.

    >>> from models import FatosDoCliente
    >>> FatosDoCliente(clienteId="x", dataReferencia="2026-09-12").json_do_contrato()["clienteId"]
    'x'
"""

from __future__ import annotations

from .avaliacao import (
    AVISO_DO_ANALISTA,
    AcaoRecomendada,
    AuditoriaDeFechamento,
    AvaliacaoDeRisco,
    DimensaoAvaliada,
    FatorCalculado,
    ProbabilidadeDeDefault,
    Recomendacao,
    RedFlag,
    RiscoRJ,
    SinalRJ,
    StayPeriod,
    VetoAtivo,
)
from .base import ModeloLastro, para_camel
from .cliente import Cliente
from .enums import (
    CodigoRecomendacao,
    DecisaoAnalista,
    DimensaoId,
    DirecaoFator,
    EfeitoVeto,
    EstadoCliente,
    FonteId,
    NaturezaGarantia,
    OrigemCliente,
    Rating,
    RiscoZarc,
    Severidade,
    SituacaoCar,
    SituacaoRfb,
    StatusParcela,
    StatusRedFlag,
    Tendencia,
    TipoEventoDeRisco,
    TipoEvidencia,
    TipoGarantia,
    TipoOperacao,
    TipoPessoa,
)
from .eventos import (
    Alerta,
    ComparacaoDeAvaliacoes,
    DeltaDeFator,
    EventoDeRisco,
    RegistroAuditoria,
    SnapshotHistorico,
)
from .exposicao import Barter, ExposicaoCalculada, Garantia, Operacao, Parcela
from .fatos import (
    CovenantRompido,
    Evidencia,
    FatosAgro,
    FatosAmbientais,
    FatosCadastrais,
    FatosDoCliente,
    FatosFiscais,
    FatosInternos,
    FatosJuridicos,
    RecuperacaoJudicial,
)
from .tabelas import (
    HAIRCUT_POR_TIPO_GARANTIA,
    NATUREZA_CPR_FINANCEIRA_SEM_REGISTRO,
    NATUREZA_POR_TIPO_GARANTIA,
    natureza_da_garantia,
    valor_atualizado_da_garantia,
)

__all__ = [
    # base
    "ModeloLastro",
    "para_camel",
    # enums
    "Rating",
    "DimensaoId",
    "Tendencia",
    "Severidade",
    "StatusRedFlag",
    "TipoPessoa",
    "TipoOperacao",
    "TipoGarantia",
    "NaturezaGarantia",
    "EstadoCliente",
    "RiscoZarc",
    "FonteId",
    "CodigoRecomendacao",
    "DecisaoAnalista",
    "OrigemCliente",
    "SituacaoRfb",
    "SituacaoCar",
    "StatusParcela",
    "TipoEvidencia",
    "DirecaoFator",
    "EfeitoVeto",
    "TipoEventoDeRisco",
    # cliente
    "Cliente",
    # fatos
    "CovenantRompido",
    "RecuperacaoJudicial",
    "FatosInternos",
    "FatosJuridicos",
    "FatosFiscais",
    "FatosAgro",
    "FatosCadastrais",
    "FatosAmbientais",
    "Evidencia",
    "FatosDoCliente",
    # exposição
    "Parcela",
    "Barter",
    "Operacao",
    "Garantia",
    "ExposicaoCalculada",
    # avaliação
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
    # eventos e histórico
    "SnapshotHistorico",
    "EventoDeRisco",
    "Alerta",
    "RegistroAuditoria",
    "DeltaDeFator",
    "ComparacaoDeAvaliacoes",
    # tabelas canônicas
    "NATUREZA_POR_TIPO_GARANTIA",
    "NATUREZA_CPR_FINANCEIRA_SEM_REGISTRO",
    "HAIRCUT_POR_TIPO_GARANTIA",
    "natureza_da_garantia",
    "valor_atualizado_da_garantia",
]
