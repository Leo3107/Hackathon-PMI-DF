"""`/api/auditoria` — trilha de decisão do analista (`03-ux-e-telas.md` §8).

Leitura em `GET`: a trilha não depende do estado de sessão do cálculo.

Escrita em `POST`: a interface manda a decisão e o servidor **carimba** id,
data-hora e `divergiuDaRecomendacao` pela tabela de equivalência da §8.3. A
tela não decide o que é divergência — se decidisse, dois clientes do mesmo
registro poderiam discordar. Nada é persistido em disco (D3); a trilha
definitiva vive no `localStorage` (D11.3).
"""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint
from pydantic import ValidationError
from repository import ClienteNaoEncontrado

from .comum import (
    corpo_da_requisicao,
    lista_serializada,
    repositorio,
    resposta,
    serializar,
)
from .erros import CodigoErro, ErroApi

auditoria_bp = Blueprint("auditoria", __name__)


@auditoria_bp.get("/api/auditoria")
def listar_auditoria():
    return resposta(lista_serializada(repositorio().listar_auditoria()))


@auditoria_bp.post("/api/auditoria")
def registrar_decisao():
    corpo = corpo_da_requisicao()
    if not corpo:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "Corpo vazio: a decisão do analista é obrigatória.",
        )
    try:
        registro = repositorio().registrar_decisao(corpo)
    except ValidationError as erro:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO, HTTPStatus.BAD_REQUEST, erro.errors(include_url=False)
        ) from erro
    except ClienteNaoEncontrado as erro:
        raise ErroApi(
            CodigoErro.CLIENTE_NAO_ENCONTRADO,
            HTTPStatus.NOT_FOUND,
            f"Nenhum cliente com id `{erro.cliente_id}`.",
        ) from erro
    return resposta(serializar(registro), HTTPStatus.CREATED)
