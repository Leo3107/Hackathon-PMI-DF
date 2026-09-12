"""Utilitários compartilhados pelos blueprints.

Três responsabilidades, e só três:

1. **Ler o corpo** com tolerância — corpo vazio é legítimo em `POST` de leitura
   (o frontend nem sempre tem estado de sessão para mandar).
2. **Validar o estado de sessão** (D3) e convertê-lo em `EstadoDeSessao`.
3. **Serializar** modelos pydantic com `model_dump(by_alias=True)`, que é o
   que garante as chaves camelCase do contrato TypeScript.
"""

from __future__ import annotations

from datetime import date
from http import HTTPStatus
from typing import Any, Iterable

from flask import current_app, jsonify, request
from models.base import ModeloLastro
from pydantic import ValidationError
from repository import EstadoDeSessao, RepositorioEmMemoria

from .erros import CodigoErro, ErroApi

__all__ = [
    "repositorio",
    "corpo_da_requisicao",
    "sessao_da_requisicao",
    "serializar",
    "resposta",
    "lista_serializada",
    "serializar_agregado",
    "data_de_referencia",
]

#: Chave do repositório nas extensões da app (evita variável global de módulo).
CHAVE_REPOSITORIO = "lastro.repositorio"


def repositorio() -> RepositorioEmMemoria:
    return current_app.extensions[CHAVE_REPOSITORIO]


def corpo_da_requisicao() -> dict[str, Any]:
    """Corpo JSON como dicionário. Ausente ou vazio → `{}`; malformado → 400."""
    if not request.data:
        return {}
    corpo = request.get_json(silent=True)
    if corpo is None:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "O corpo da requisição não é JSON válido.",
        )
    if not isinstance(corpo, dict):
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "O corpo da requisição deve ser um objeto JSON.",
        )
    return corpo


def sessao_da_requisicao() -> EstadoDeSessao:
    """Lê `{"sessao": {...}}`. Ausência é o caso normal de uma sessão limpa."""
    bruta = corpo_da_requisicao().get("sessao")
    if bruta is None:
        return EstadoDeSessao()
    if not isinstance(bruta, dict):
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "`sessao` deve ser um objeto.",
        )
    try:
        return EstadoDeSessao.model_validate(bruta)
    except ValidationError as erro:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO, HTTPStatus.BAD_REQUEST, erro.errors(include_url=False)
        ) from erro


def serializar(modelo: ModeloLastro) -> dict[str, Any]:
    """`model_dump(by_alias=True)` — a única serialização permitida (spec 02 §14)."""
    return modelo.model_dump(by_alias=True, mode="json")


def lista_serializada(modelos: Iterable[ModeloLastro]) -> list[dict[str, Any]]:
    return [serializar(modelo) for modelo in modelos]


def serializar_agregado(modelo: ModeloLastro) -> dict[str, Any]:
    """Como `serializar`, mas **omite** as chaves nulas do nível superior.

    Os agregados de `web/types/api.ts` declaram esses campos como opcionais
    (`variacao90d?`, `alertaGerado?`, `cliente?`), não como anuláveis. Omitir é
    o que casa com o tipo; `null` passaria em runtime mas mentiria no contrato.
    Os níveis internos preservam seus `null` legítimos.
    """
    return {
        chave: valor
        for chave, valor in serializar(modelo).items()
        if valor is not None
    }


def data_de_referencia() -> str:
    """Data do dataset (ISO). O motor nunca lê o relógio; a carteira, só aqui."""
    repo = repositorio()
    if repo.fonte.data_referencia:
        return repo.fonte.data_referencia
    for fatos in repo.fonte.fatos_por_cliente.values():
        return fatos.data_referencia
    return date.today().isoformat()


def resposta(dados: Any, status: int = HTTPStatus.OK):
    return jsonify(dados), int(status)
