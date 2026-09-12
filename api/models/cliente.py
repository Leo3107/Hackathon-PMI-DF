"""Identidade do cliente — `specs/01-modelo-de-dados.md`, seção "Identidade do cliente"."""

from __future__ import annotations

from pydantic import Field

from .base import ModeloLastro
from .enums import EstadoCliente, OrigemCliente, TipoPessoa

__all__ = ["Cliente"]


class Cliente(ModeloLastro):
    id: str
    razao_social: str
    nome_fantasia: str | None = None
    #: CPF ou CNPJ formatado, dígito verificador válido, SIMULADO.
    documento: str
    tipo_pessoa: TipoPessoa
    municipio: str
    uf: str
    #: ex.: 'Produtor rural — grãos'
    atividade: str
    cnae_principal: str
    #: ex.: ['Soja', 'Milho safrinha']
    culturas: list[str] = Field(default_factory=list)
    #: ISO date
    inicio_relacionamento: str
    estado: EstadoCliente = EstadoCliente.ATIVO
    #: Distingue o fluxo A (due diligence) do fluxo B (monitoramento).
    origem: OrigemCliente = OrigemCliente.CARTEIRA
