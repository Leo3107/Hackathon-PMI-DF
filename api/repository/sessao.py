"""Estado de sessão que viaja no corpo das requisições — `00-decisoes.md` D3.

Decisões do analista, status de red flag e eventos simulados vivem no
`localStorage` do navegador. Nada é persistido no servidor. O que **altera o
cálculo** é reenviado a cada requisição, e é por isso que as rotas de leitura
da carteira e do cliente são `POST`: elas carregam corpo.

Espelha `EstadoDeSessaoApi` e `EventoSimulado` de `web/types/api.ts`.
"""

from __future__ import annotations

from pydantic import Field

from models.base import ModeloLastro
from models.enums import StatusRedFlag, TipoEventoDeRisco

__all__ = ["EventoSimulado", "EstadoDeSessao", "SESSAO_VAZIA"]


class EventoSimulado(ModeloLastro):
    """Evento injetado pelo controle de demonstração ao vivo (D10)."""

    tipo: TipoEventoDeRisco
    #: ISO datetime da injeção.
    data: str = ""


class EstadoDeSessao(ModeloLastro):
    eventos_simulados: list[EventoSimulado] = Field(default_factory=list)
    #: `redFlagId` → status marcado pelo analista.
    status_red_flags: dict[str, StatusRedFlag] = Field(default_factory=dict)


SESSAO_VAZIA = EstadoDeSessao()
