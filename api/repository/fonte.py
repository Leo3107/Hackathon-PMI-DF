"""Fonte de dados bruta do repositório — `specs/06-dados-simulados.md` §3.

O pacote `data/` é escrito por outro workstream e expõe um agregador com nomes
fixos. Esta camada é o **adaptador**: lê aqueles nomes, tolera ausência e
entrega uma estrutura estável para `repository.memoria`.

Se `data/` ainda não existir no disco, `carregar_fonte()` devolve uma fonte
vazia em vez de explodir na importação — o serviço sobe, `/api/saude` responde
e as telas mostram estado vazio, que é o comportamento pedido por
`03-ux-e-telas.md` §9 (nunca tela branca).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from models.cliente import Cliente
from models.eventos import Alerta, EventoDeRisco, RegistroAuditoria, SnapshotHistorico
from models.fatos import FatosDoCliente

if TYPE_CHECKING:  # só para tipagem — evita exigir `coleta` no runtime deste módulo
    from coleta.models import Features

__all__ = ["FonteDeDados", "carregar_fonte", "so_digitos"]

_log = logging.getLogger(__name__)

#: Nomes públicos esperados em `data/__init__.py` (spec 06 §3).
_NOME_CLIENTES = "CLIENTES"
_NOME_PROSPECTS = "PROSPECTS"
_NOME_FATOS = "FATOS_POR_CLIENTE"
_NOME_SNAPSHOTS = "SNAPSHOTS_POR_CLIENTE"
_NOME_EVENTOS = "EVENTOS_POR_CLIENTE"
_NOME_ALERTAS = "ALERTAS"
_NOME_AUDITORIA = "REGISTROS_AUDITORIA"
#: Acrescentados na Tarefa 2 — dataset real de CNPJs (`data/carregador_csv.py`).
_NOME_FEATURES = "FEATURES_POR_CLIENTE"
_NOME_PERFIS = "PERFIL_POR_CLIENTE"
_NOME_DATA_REFERENCIA = "DATA_REFERENCIA"


def so_digitos(documento: str) -> str:
    """`12.345.678/0001-95` → `12345678000195`. Comparação de documento é por dígito."""
    return "".join(caractere for caractere in documento if caractere.isdigit())


@dataclass(frozen=True)
class FonteDeDados:
    """Dataset simulado já normalizado. Imutável do ponto de vista das rotas."""

    clientes: list[Cliente] = field(default_factory=list)
    prospects: list[Cliente] = field(default_factory=list)
    fatos_por_cliente: dict[str, FatosDoCliente] = field(default_factory=dict)
    snapshots_por_cliente: dict[str, list[SnapshotHistorico]] = field(
        default_factory=dict
    )
    eventos_por_cliente: dict[str, list[EventoDeRisco]] = field(default_factory=dict)
    alertas: list[Alerta] = field(default_factory=list)
    registros_auditoria: list[RegistroAuditoria] = field(default_factory=list)
    #: Tarefa 2 — `Features` brutas por documento, base real de CNPJs. Vazio
    #: para a fonte de teste (perfis à mão de `tests/fixtures.py`): nesse caso
    #: o repositório usa só `fatos_por_cliente`, sem modelo de PD nem
    #: renormalização de cobertura.
    features_por_cliente: dict[str, "Features"] = field(default_factory=dict)
    #: Perfil de risco do CSV mock (`limpo`, `divida_ativa`, ...). Só para a
    #: semeadura de demonstração da carteira (Tarefa 3) — não é fato de risco.
    perfil_por_cliente: dict[str, str] = field(default_factory=dict)
    #: Data de referência do dataset carregado. `""` quando a fonte é o stub de
    #: teste; `routes.comum.data_de_referencia` cai para `date.today()` nesse caso.
    data_referencia: str = ""

    @property
    def vazia(self) -> bool:
        return not self.clientes and not self.prospects

    def todos_os_perfis(self) -> list[Cliente]:
        """Carteira + prospects. A due diligence procura nos dois."""
        return [*self.clientes, *self.prospects]

    def por_id(self, cliente_id: str) -> Cliente | None:
        for cliente in self.todos_os_perfis():
            if cliente.id == cliente_id:
                return cliente
        return None

    def por_documento(self, documento: str) -> Cliente | None:
        """Normaliza a pontuação dos dois lados antes de comparar (spec 06 §3)."""
        alvo = so_digitos(documento)
        if not alvo:
            return None
        for cliente in self.todos_os_perfis():
            if so_digitos(cliente.documento) == alvo:
                return cliente
        return None


def _lista(modulo: Any, nome: str) -> list:
    valor = getattr(modulo, nome, None)
    return list(valor) if valor else []


def _dicionario(modulo: Any, nome: str) -> dict:
    valor = getattr(modulo, nome, None)
    return dict(valor) if valor else {}


def fonte_do_modulo(modulo: Any) -> FonteDeDados:
    """Constrói a fonte a partir de qualquer módulo que respeite os nomes da spec 06.

    Aceita também um stub de teste — é o ponto de injeção usado pela suíte
    enquanto `data/` não existe.
    """
    return FonteDeDados(
        clientes=_lista(modulo, _NOME_CLIENTES),
        prospects=_lista(modulo, _NOME_PROSPECTS),
        fatos_por_cliente=_dicionario(modulo, _NOME_FATOS),
        snapshots_por_cliente=_dicionario(modulo, _NOME_SNAPSHOTS),
        eventos_por_cliente=_dicionario(modulo, _NOME_EVENTOS),
        alertas=_lista(modulo, _NOME_ALERTAS),
        registros_auditoria=_lista(modulo, _NOME_AUDITORIA),
        features_por_cliente=_dicionario(modulo, _NOME_FEATURES),
        perfil_por_cliente=_dicionario(modulo, _NOME_PERFIS),
        data_referencia=str(getattr(modulo, _NOME_DATA_REFERENCIA, "") or ""),
    )


def carregar_fonte() -> FonteDeDados:
    """Importa `data/` sob demanda. Ausência ou defeito degrada para fonte vazia."""
    try:
        import data  # noqa: PLC0415 — importação tardia é deliberada
    except Exception:  # noqa: BLE001 — dataset defeituoso não pode derrubar o motor
        _log.warning(
            "pacote `data` indisponível ou com defeito; o serviço sobe com a "
            "carteira vazia. Ver specs/06-dados-simulados.md §3.",
            exc_info=True,
        )
        return FonteDeDados()
    try:
        return fonte_do_modulo(data)
    except Exception:  # noqa: BLE001 — idem: degrada, não quebra a demonstração
        _log.warning("`data` não expõe os nomes da spec 06 §3.", exc_info=True)
        return FonteDeDados()
