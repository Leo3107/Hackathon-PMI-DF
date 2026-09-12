"""Envelope de erro uniforme — `03-ux-e-telas.md` §9.4 e `web/types/api.ts`.

Toda falha sai do Flask como `{"erro": CODIGO, "detalhe": ...}` com o status
HTTP correspondente. O cliente do frontend (`web/lib/api/erros.ts`) lê `erro`
para escolher a tela de estado; `detalhe` é diagnóstico, nunca obrigatório.

Nenhuma rota devolve HTML de erro: a tela branca é o estado proibido.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

__all__ = ["ErroApi", "CodigoErro", "payload_de_erro"]


class CodigoErro:
    """Códigos do contrato. Strings, para casar com o union de TypeScript."""

    CORPO_INVALIDO = "CORPO_INVALIDO"
    CLIENTE_NAO_ENCONTRADO = "CLIENTE_NAO_ENCONTRADO"
    DOCUMENTO_NAO_ENCONTRADO = "DOCUMENTO_NAO_ENCONTRADO"
    AVALIACAO_INCONSISTENTE = "AVALIACAO_INCONSISTENTE"
    ROTA_NAO_ENCONTRADA = "ROTA_NAO_ENCONTRADA"
    METODO_NAO_PERMITIDO = "METODO_NAO_PERMITIDO"
    ERRO_INTERNO = "ERRO_INTERNO"


class ErroApi(Exception):
    """Erro de negócio com código e status já decididos na origem."""

    def __init__(
        self,
        codigo: str,
        status: int = HTTPStatus.BAD_REQUEST,
        detalhe: Any = None,
    ) -> None:
        super().__init__(codigo)
        self.codigo = codigo
        self.status = int(status)
        self.detalhe = detalhe

    def como_payload(self) -> dict[str, Any]:
        return payload_de_erro(self.codigo, self.detalhe)


def payload_de_erro(codigo: str, detalhe: Any = None) -> dict[str, Any]:
    corpo: dict[str, Any] = {"erro": codigo}
    if detalhe is not None:
        corpo["detalhe"] = detalhe
    return corpo
