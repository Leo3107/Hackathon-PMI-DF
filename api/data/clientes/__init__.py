"""Agrega os 18 clientes de carteira — `specs/06-dados-simulados.md` §3.

Cada módulo expõe exatamente três nomes: `CLIENTE`, `FATOS` e `SNAPSHOTS`.
A ordem desta lista é a ordem da tabela consolidada da §5.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.eventos import SnapshotHistorico
from models.fatos import FatosDoCliente

from . import (
    alto_paranaiba,
    barra_do_ipe,
    cerrado_norte,
    chapadao_algodoeira,
    coop_vale_do_ivai,
    dois_irmaos,
    frutivale,
    ipanema_graos,
    joao_camargo,
    maria_nogueira,
    ponta_verde,
    rio_formoso,
    santa_ines,
    santa_vitoria_arroz,
    sao_bento_bioenergia,
    serra_do_urucui,
    tres_barras,
    vale_do_piquiri,
)

__all__ = ["MODULOS", "CLIENTES", "FATOS_POR_CLIENTE", "SNAPSHOTS_POR_CLIENTE"]

#: Na ordem da §5.
MODULOS = (
    santa_ines,
    vale_do_piquiri,
    cerrado_norte,
    rio_formoso,
    barra_do_ipe,
    alto_paranaiba,
    serra_do_urucui,
    sao_bento_bioenergia,
    chapadao_algodoeira,
    ponta_verde,
    joao_camargo,
    tres_barras,
    ipanema_graos,
    frutivale,
    santa_vitoria_arroz,
    dois_irmaos,
    maria_nogueira,
    coop_vale_do_ivai,
)

CLIENTES: list[Cliente] = [modulo.CLIENTE for modulo in MODULOS]

FATOS_POR_CLIENTE: dict[str, FatosDoCliente] = {
    modulo.CLIENTE.id: modulo.FATOS for modulo in MODULOS
}

SNAPSHOTS_POR_CLIENTE: dict[str, list[SnapshotHistorico]] = {
    modulo.CLIENTE.id: modulo.SNAPSHOTS for modulo in MODULOS
}
