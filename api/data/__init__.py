"""Dataset simulado do Lastro — `specs/06-dados-simulados.md`.

**18 clientes de carteira + 4 prospects**, com seis snapshots históricos cada,
eventos de risco, alertas, evidências e trilha de auditoria. Exposição total da
carteira: **R$ 244.300.000,00**.

Regras do pacote, verificadas por teste (`api/tests/test_dataset.py`):

* nada aqui importa de `scoring` — o dataset descreve **fatos**, não avaliações;
* nada aqui escreve campo derivado (score, rating, PD, red flag, recomendação,
  `natureza` ou `valorAtualizado` de garantia, `scoreApos`, `deltaScore`);
* toda `Evidencia` carrega `simulada = true` (invariante I10).

API pública:

    >>> from data import CLIENTES, FATOS_POR_CLIENTE
    >>> len(CLIENTES)
    18
    >>> FATOS_POR_CLIENTE["cerrado-norte"].data_referencia
    '2026-09-12'
"""

from __future__ import annotations

from models.cliente import Cliente
from models.eventos import Alerta, EventoDeRisco, RegistroAuditoria, SnapshotHistorico
from models.fatos import FatosDoCliente

from ._base import DATA_REFERENCIA, DATAS_SNAPSHOT, normalizar_documento
from .alertas import ALERTAS
from .auditoria import REGISTROS as REGISTROS_AUDITORIA
from .catalogo import (
    CLIENTES,
    FATOS_DE_TODOS_OS_REGISTROS,
    PROSPECTS,
    TODOS_OS_REGISTROS,
    por_documento,
    por_id,
)
from .clientes import FATOS_POR_CLIENTE, SNAPSHOTS_POR_CLIENTE
from .eventos import EVENTOS, EVENTOS_POR_CLIENTE
from .fontes import ROTULOS_FONTE
from .prospects import FATOS_POR_PROSPECT

__all__ = [
    "CLIENTES",
    "PROSPECTS",
    "FATOS_POR_CLIENTE",
    "SNAPSHOTS_POR_CLIENTE",
    "EVENTOS_POR_CLIENTE",
    "ALERTAS",
    "REGISTROS_AUDITORIA",
    "por_documento",
    # auxiliares
    "TODOS_OS_REGISTROS",
    "FATOS_POR_PROSPECT",
    "FATOS_DE_TODOS_OS_REGISTROS",
    "EVENTOS",
    "ROTULOS_FONTE",
    "DATA_REFERENCIA",
    "DATAS_SNAPSHOT",
    "normalizar_documento",
    "por_id",
]

#: Tipagem explícita da API pública, para quem lê o módulo antes do repositório.
CLIENTES: list[Cliente]
PROSPECTS: list[Cliente]
FATOS_POR_CLIENTE: dict[str, FatosDoCliente]
SNAPSHOTS_POR_CLIENTE: dict[str, list[SnapshotHistorico]]
EVENTOS_POR_CLIENTE: dict[str, list[EventoDeRisco]]
ALERTAS: list[Alerta]
REGISTROS_AUDITORIA: list[RegistroAuditoria]
