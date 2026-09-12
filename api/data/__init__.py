"""Dataset real do Lastro — Tarefa 2 (substitui os 18 clientes inventados).

3.000 CNPJs de soja (12 UFs, 6 perfis de risco), lidos de
`data/mock/features_agro_mock.csv` por `data.carregador_csv` e traduzidos por
`adaptadores.features_para_fatos.adaptar` — o mesmo adaptador que a due
diligence de CNPJ avulso já usa para dado público real.

**Nada aqui é carteira.** A carteira (o que `POST /api/carteira` lista) é o
conjunto de documentos com declaração de operação do analista
(`repository.declaracoes.RepositorioDeDeclaracoes`), montada em runtime por
`RepositorioEmMemoria` — não um recorte estático deste módulo. Os 3.000
registros aqui são só o universo consultável (devem aparecer na due diligence
por documento e na ficha do cliente; a lista de carteira, não).

Sem histórico real para 3.000 CNPJs, `SNAPSHOTS_POR_CLIENTE`,
`EVENTOS_POR_CLIENTE`, `ALERTAS` e `REGISTROS_AUDITORIA` saem vazios de
propósito: inventar uma série temporal ou uma trilha de auditoria para uma
base pública seria exatamente o erro que os workstreams 2 e 3 existem para
evitar. `repository.fonte.carregar_fonte` e `RepositorioEmMemoria` já degradam
com graça para essas ausências (nenhuma tela quebra; históricos e alertas
aparecem vazios).

API pública (nomes lidos por `repository.fonte.fonte_do_modulo`):

    >>> from data import PROSPECTS, FATOS_POR_CLIENTE, FEATURES_POR_CLIENTE
    >>> len(PROSPECTS)
    3000
"""

from __future__ import annotations

from models.cliente import Cliente
from models.eventos import Alerta, EventoDeRisco, RegistroAuditoria, SnapshotHistorico
from models.fatos import FatosDoCliente

from .carregador_csv import (
    CAMINHO_CSV,
    DATA_REFERENCIA,
    FATOS_POR_CLIENTE,
    FEATURES_POR_CLIENTE,
    PERFIL_POR_CLIENTE,
    PROSPECTS,
    normalizar_documento,
)

__all__ = [
    "CLIENTES",
    "PROSPECTS",
    "FATOS_POR_CLIENTE",
    "FEATURES_POR_CLIENTE",
    "PERFIL_POR_CLIENTE",
    "SNAPSHOTS_POR_CLIENTE",
    "EVENTOS_POR_CLIENTE",
    "ALERTAS",
    "REGISTROS_AUDITORIA",
    "DATA_REFERENCIA",
    "CAMINHO_CSV",
    "normalizar_documento",
]

#: Nenhum CNPJ nasce em carteira: a carteira é a declaração do analista
#: (Tarefa 3, `repository.declaracoes`). `RepositorioEmMemoria.listar_clientes`
#: filtra `PROSPECTS` pelos documentos declarados em runtime.
CLIENTES: list[Cliente] = []

#: Sem base real para inventar. Ver docstring do módulo.
SNAPSHOTS_POR_CLIENTE: dict[str, list[SnapshotHistorico]] = {}
EVENTOS_POR_CLIENTE: dict[str, list[EventoDeRisco]] = {}
ALERTAS: list[Alerta] = []
REGISTROS_AUDITORIA: list[RegistroAuditoria] = []
