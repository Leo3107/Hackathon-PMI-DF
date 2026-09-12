"""Corpos das requisições da camada de linguagem — `04-camada-llm.md` §2.1.

JSON em camelCase, campos em `snake_case`, como todo o contrato do Lastro
(`models.base.ModeloLastro`). `EstadoDeSessao` é **o mesmo** modelo aceito pelo
endpoint de avaliação do motor: prosa e números têm de falar do mesmo cálculo.

Nota de nomenclatura: a spec chama este módulo `models.py`. O nome real é
`pedidos.py`, para não competir com o pacote `models/` do contrato de dados.
"""

from __future__ import annotations

from models.base import ModeloLastro
from pydantic import Field
from repository import EstadoDeSessao

from .engine import LIMITE_HISTORICO, LIMITE_PERGUNTA, MensagemCopiloto

__all__ = ["PedidoNarrativa", "PedidoCopiloto"]


class PedidoNarrativa(ModeloLastro):
    cliente_id: str = Field(min_length=1)
    sessao: EstadoDeSessao = Field(default_factory=EstadoDeSessao)


class PedidoCopiloto(PedidoNarrativa):
    pergunta: str = Field(min_length=1, max_length=LIMITE_PERGUNTA)
    historico: list[MensagemCopiloto] = Field(
        default_factory=list, max_length=LIMITE_HISTORICO
    )
