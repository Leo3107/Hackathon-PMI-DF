"""Catálogo de identidades — `specs/06-dados-simulados.md` §3.

Reúne os 18 clientes de carteira e os 4 prospects de due diligence e oferece a
busca por documento, que normaliza a pontuação antes de comparar.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.fatos import FatosDoCliente

from ._base import normalizar_documento
from .clientes import CLIENTES as _CLIENTES_DE_CARTEIRA
from .clientes import FATOS_POR_CLIENTE as _FATOS_DE_CARTEIRA
from .prospects import FATOS_POR_PROSPECT as _FATOS_DE_PROSPECTS
from .prospects import PROSPECTS as _PROSPECTS

__all__ = [
    "CLIENTES",
    "PROSPECTS",
    "TODOS_OS_REGISTROS",
    "FATOS_DE_TODOS_OS_REGISTROS",
    "por_documento",
    "por_id",
]

CLIENTES: list[Cliente] = list(_CLIENTES_DE_CARTEIRA)
PROSPECTS: list[Cliente] = list(_PROSPECTS)

#: Os 22 registros consultáveis pelo fluxo de nova análise.
TODOS_OS_REGISTROS: list[Cliente] = [*CLIENTES, *PROSPECTS]

FATOS_DE_TODOS_OS_REGISTROS: dict[str, FatosDoCliente] = {
    **_FATOS_DE_CARTEIRA,
    **_FATOS_DE_PROSPECTS,
}

_POR_DOCUMENTO: dict[str, Cliente] = {
    normalizar_documento(cliente.documento): cliente for cliente in TODOS_OS_REGISTROS
}
_POR_ID: dict[str, Cliente] = {cliente.id: cliente for cliente in TODOS_OS_REGISTROS}


def por_documento(documento: str) -> Cliente | None:
    """Busca por CPF/CNPJ ignorando pontuação. `None` quando não há correspondência.

    A rota de nova análise responde 404 com `DOCUMENTO_NAO_ENCONTRADO` neste caso
    e **jamais** inventa um cliente (§11).
    """
    return _POR_DOCUMENTO.get(normalizar_documento(documento))


def por_id(cliente_id: str) -> Cliente | None:
    return _POR_ID.get(cliente_id)
