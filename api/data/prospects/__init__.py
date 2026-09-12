"""Agrega os 4 prospects do fluxo de due diligence — `specs/06-dados-simulados.md` §11.

Prospects não têm histórico interno nem série de snapshots: são consultados uma
única vez, na data de referência.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.fatos import FatosDoCliente

from . import beira_rio, nova_alianca, ribeirao_claro, santa_helena_norte

__all__ = ["MODULOS", "PROSPECTS", "FATOS_POR_PROSPECT"]

MODULOS = (nova_alianca, ribeirao_claro, beira_rio, santa_helena_norte)

PROSPECTS: list[Cliente] = [modulo.CLIENTE for modulo in MODULOS]

FATOS_POR_PROSPECT: dict[str, FatosDoCliente] = {
    modulo.CLIENTE.id: modulo.FATOS for modulo in MODULOS
}
