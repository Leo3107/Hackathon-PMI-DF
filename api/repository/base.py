"""Interface `RepositorioLastro` — `specs/01-modelo-de-dados.md`, §"Repositório".

A spec descreve a interface em TypeScript, porque nasceu quando o mock vivia no
frontend. Com a revisão de stack (D3) o repositório passou para o Flask; esta
é a mesma interface, método a método, em Python síncrono.

O repositório serve **fatos**, não avaliações. Quem transforma fato em score é
`scoring.calcular_risco`, e só ele. A única exceção declarada é
`obter_eventos`, cujos campos `scoreApos` e `deltaScore` são preenchidos em
runtime pelo recálculo do snapshot correspondente (spec 06 §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.cliente import Cliente
from models.enums import TipoEventoDeRisco
from models.eventos import Alerta, EventoDeRisco, RegistroAuditoria, SnapshotHistorico
from models.fatos import FatosDoCliente

__all__ = ["RepositorioLastro", "ClienteNaoEncontrado"]


class ClienteNaoEncontrado(LookupError):
    """Id ausente do dataset. Vira `CLIENTE_NAO_ENCONTRADO` (404) na camada de rota."""

    def __init__(self, cliente_id: str) -> None:
        super().__init__(cliente_id)
        self.cliente_id = cliente_id


class RepositorioLastro(ABC):
    @abstractmethod
    def listar_clientes(self) -> list[Cliente]: ...

    @abstractmethod
    def obter_cliente(self, cliente_id: str) -> Cliente | None: ...

    @abstractmethod
    def obter_fatos_atuais(self, cliente_id: str) -> FatosDoCliente: ...

    @abstractmethod
    def obter_historico(self, cliente_id: str) -> list[SnapshotHistorico]: ...

    @abstractmethod
    def obter_eventos(self, cliente_id: str) -> list[EventoDeRisco]: ...

    @abstractmethod
    def listar_alertas(self) -> list[Alerta]: ...

    @abstractmethod
    def listar_auditoria(self) -> list[RegistroAuditoria]: ...

    @abstractmethod
    def registrar_decisao(self, dados: dict) -> RegistroAuditoria: ...

    @abstractmethod
    def consultar_documento(self, documento: str) -> Cliente | None: ...

    @abstractmethod
    def simular_evento(
        self, cliente_id: str, tipo: TipoEventoDeRisco
    ) -> FatosDoCliente: ...
