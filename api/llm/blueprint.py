"""Blueprint HTTP da camada de linguagem — `specs/04-camada-llm.md` §2.1.

════════════════════════════════════════════════════════════════════════════════
 INTEGRAÇÃO COM `api/app.py` — contrato estável, é isto que deve ser importado
════════════════════════════════════════════════════════════════════════════════

    from llm.blueprint import llm_bp        # objeto flask.Blueprint, nome "llm"
    app.register_blueprint(llm_bp)          # sem url_prefix: as rotas já trazem /api

  ou, equivalente e preferível porque também prepara o ledger:

    from llm.blueprint import registrar_llm
    registrar_llm(app)                      # assinatura: (app: Flask) -> None

  Ambos são idempotentes do ponto de vista do chamador e não exigem nenhuma
  configuração prévia. O registro pode ser condicional (`try/except ImportError`),
  como `api/app.py` já faz: sem o blueprint, as rotas devolvem 404 com o
  envelope padrão e a interface degrada para a narrativa determinística.

════════════════════════════════════════════════════════════════════════════════

| Método | Caminho | Corpo | Resposta |
|---|---|---|---|
| POST | `/api/narrativa/parecer` | `PedidoNarrativa` | stream NDJSON |
| POST | `/api/narrativa/score` | `PedidoNarrativa` | stream NDJSON |
| POST | `/api/narrativa/recomendacao` | `PedidoNarrativa` | stream NDJSON |
| POST | `/api/copiloto` | `PedidoCopiloto` | stream NDJSON |
| GET | `/api/llm/custo` | — | JSON `RespostaCusto` (§5.5) |

Streaming sem buffer: `direct_passthrough=True`, `X-Accel-Buffering: no` e
`Cache-Control: no-store, no-transform`. Qualquer um dos três faltando faz o
texto chegar de uma vez ao fim da geração, e o efeito de streaming some sem
erro nenhum — é o risco técnico nº 1 da §10.

Erros **antes** do primeiro byte são HTTP (400/404/422). Depois disso o status
já é 200 e toda falha vira evento `substituir` ou `erro` dentro do stream.

Nota de nomenclatura: a spec chama este módulo `routes.py`.
"""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any, Iterator

from flask import Blueprint, Flask, Response, current_app, jsonify, request, stream_with_context
from pydantic import ValidationError
from repository import ClienteNaoEncontrado, RepositorioEmMemoria

from . import ledger as _ledger
from .contexto import ContextoNarrativo, serializar_contexto
from .engine import MODELO_PADRAO, TarefaNarrativa, diagnosticar_selecao
from .executor import executar_resposta_imediata, executar_tarefa
from .guardas import numeros_da_pergunta, pre_filtrar
from .pedidos import PedidoCopiloto, PedidoNarrativa

__all__ = ["llm_bp", "registrar_llm", "TAREFAS_DE_GERACAO", "MIMETYPE_NDJSON"]

#: Nome do blueprint no Flask. Mantê-lo estável: o `url_for` do serviço usa-o.
NOME_DO_BLUEPRINT = "llm"

MIMETYPE_NDJSON = "application/x-ndjson"
_CHARSET = "application/x-ndjson; charset=utf-8"

TAREFAS_DE_GERACAO: frozenset[str] = frozenset({"parecer", "score", "recomendacao"})

#: Mesma chave usada por `routes.comum`; replicada para não acoplar os pacotes.
CHAVE_REPOSITORIO = "lastro.repositorio"

#: Tolerância da auditoria de fechamento (I2). Acima disso, nada é serializado.
TOLERANCIA_DE_FECHAMENTO = 0.5

_CABECALHOS_DO_STREAM = {
    "Cache-Control": "no-store, no-transform",
    "X-Accel-Buffering": "no",
}

llm_bp = Blueprint(NOME_DO_BLUEPRINT, __name__)


# ---------------------------------------------------------------------------
# Infraestrutura local
# ---------------------------------------------------------------------------


def _erro(codigo: str, status: HTTPStatus, detalhe: Any = None):
    corpo: dict[str, Any] = {"erro": codigo}
    if detalhe is not None:
        corpo["detalhe"] = detalhe
    return jsonify(corpo), status


def _repositorio() -> RepositorioEmMemoria:
    repositorio = current_app.extensions.get(CHAVE_REPOSITORIO)
    if repositorio is None:  # pragma: no cover - app sem o motor registrado
        repositorio = RepositorioEmMemoria()
        current_app.extensions[CHAVE_REPOSITORIO] = repositorio
    return repositorio


def _corpo() -> dict:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _resposta_ndjson(stream: Iterator[str]) -> Response:
    return Response(
        stream_with_context(stream),
        mimetype=MIMETYPE_NDJSON,
        content_type=_CHARSET,
        headers=_CABECALHOS_DO_STREAM,
        direct_passthrough=True,
    )


def _montar_contexto(
    tarefa: TarefaNarrativa, pedido: PedidoNarrativa
) -> ContextoNarrativo:
    """Repositório → motor → contexto. Levanta `ClienteNaoEncontrado` e `ValueError`."""
    repositorio = _repositorio()
    cliente = repositorio.obter_cliente(pedido.cliente_id)
    if cliente is None:
        raise ClienteNaoEncontrado(pedido.cliente_id)
    fatos = repositorio.obter_fatos_atuais(pedido.cliente_id)
    avaliacao = repositorio.avaliar_fatos(fatos, pedido.sessao)
    if abs(avaliacao.auditoria.diferenca) > TOLERANCIA_DE_FECHAMENTO:
        raise ValueError(avaliacao.auditoria.diferenca)
    variacao = repositorio.comparacao_na_janela(pedido.cliente_id, avaliacao)
    return serializar_contexto(cliente, fatos, avaliacao, variacao, tarefa)


def _outros_clientes(cliente_id: str) -> list[str]:
    """Nomes e ids de todos os demais clientes — insumo do pré-filtro do §8."""
    nomes: list[str] = []
    for cliente in _repositorio().fonte.todos_os_perfis():
        if cliente.id == cliente_id:
            continue
        nomes.append(cliente.razao_social)
        nomes.append(cliente.id)
        if cliente.nome_fantasia:
            nomes.append(cliente.nome_fantasia)
    return nomes


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@llm_bp.post("/api/narrativa/<tarefa>")
def narrativa(tarefa: str):
    """Parecer, explicação do score e justificativa da recomendação (§3.a–3.c)."""
    if tarefa not in TAREFAS_DE_GERACAO:
        return _erro("TAREFA_INVALIDA", HTTPStatus.NOT_FOUND, tarefa)
    try:
        pedido = PedidoNarrativa.model_validate(_corpo())
    except ValidationError as erro:
        return _erro("CORPO_INVALIDO", HTTPStatus.BAD_REQUEST, erro.errors(include_url=False))
    try:
        contexto = _montar_contexto(tarefa, pedido)  # type: ignore[arg-type]
    except ClienteNaoEncontrado:
        return _erro("CLIENTE_NAO_ENCONTRADO", HTTPStatus.NOT_FOUND, pedido.cliente_id)
    except ValueError as erro:
        return _erro(
            "AVALIACAO_INCONSISTENTE", HTTPStatus.UNPROCESSABLE_ENTITY, str(erro)
        )
    return _resposta_ndjson(executar_tarefa(tarefa, contexto))  # type: ignore[arg-type]


@llm_bp.post("/api/copiloto")
def copiloto():
    """Copiloto de análise (§3.d), com os pré-filtros adversariais do §8."""
    try:
        pedido = PedidoCopiloto.model_validate(_corpo())
    except ValidationError as erro:
        return _erro("CORPO_INVALIDO", HTTPStatus.BAD_REQUEST, erro.errors(include_url=False))
    try:
        contexto = _montar_contexto("copiloto", pedido)
    except ClienteNaoEncontrado:
        return _erro("CLIENTE_NAO_ENCONTRADO", HTTPStatus.NOT_FOUND, pedido.cliente_id)
    except ValueError as erro:
        return _erro(
            "AVALIACAO_INCONSISTENTE", HTTPStatus.UNPROCESSABLE_ENTITY, str(erro)
        )

    imediata = pre_filtrar(pedido.pergunta, contexto, _outros_clientes(pedido.cliente_id))
    if imediata is not None:
        return _resposta_ndjson(
            executar_resposta_imediata("copiloto", contexto, imediata.texto)
        )
    return _resposta_ndjson(
        executar_tarefa(
            "copiloto",
            contexto,
            pergunta=pedido.pergunta,
            historico=pedido.historico,
            extras_do_verificador=numeros_da_pergunta(pedido.pergunta),
        )
    )


@llm_bp.get("/api/llm/custo")
def custo():
    """Contador de custo do cabeçalho e do rodapé do PDF (§5.5)."""
    ledger = _ledger.LEDGER
    engine_ativo, motivo = diagnosticar_selecao(ledger, 0.0)
    habilitado = (
        os.environ.get("LASTRO_LLM_ENABLED", "true").strip().lower() == "true"
    )
    modelo = (
        os.environ.get("LASTRO_LLM_MODEL", MODELO_PADRAO)
        if engine_ativo == "openai"
        else None
    )
    return jsonify(ledger.resumo(habilitado, engine_ativo, modelo, motivo))


def registrar_llm(app: Flask) -> None:
    """Registra as cinco rotas no app. Assinatura estável: `(app: Flask) -> None`."""
    app.register_blueprint(llm_bp)
    app.extensions.setdefault("lastro.llm.ledger", _ledger.LEDGER)
