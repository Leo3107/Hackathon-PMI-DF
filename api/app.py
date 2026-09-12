"""Serviço Flask do Lastro — motor de risco, dados simulados e camada de linguagem.

    flask --app app run --port 5001 --debug

────────────────────────────────────────────────────────────────────────────────
⚠️  ESTE SERVIÇO RODA COM **PROCESSO ÚNICO**. NÃO SUBIR COM VÁRIOS WORKERS.
────────────────────────────────────────────────────────────────────────────────

O ledger de custo da camada de linguagem (`llm/ledger.py`, spec 04 §5) é estado
**em memória do processo**: gasto acumulado em dólares, contagem de chamadas,
tokens e o disjuntor do teto de orçamento. Com dois ou mais workers, cada um
enxergaria apenas a própria fração do gasto e o teto de `LASTRO_LLM_BUDGET_USD`
seria dividido silenciosamente entre eles — na prática, multiplicado. Com o
orçamento de US$ 10 desta conta (HANDOFF §3), isso é gasto real perdido.

Consequências práticas:

- Desenvolvimento: `flask run` (servidor de desenvolvimento, thread única por padrão).
- Se um dia for para trás de um WSGI de produção: `gunicorn -w 1` ou
  `waitress-serve --threads=N` — **um processo**, nunca `-w 4`.
- Vale também para a trilha de decisões de `POST /api/auditoria`, que é lista de
  processo, e para a memoização de avaliações de snapshot no repositório.

Nada disso é limitação de arquitetura: é o desenho escolhido para um protótipo
sem banco de dados (D3, D12).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from http import HTTPStatus

from dotenv import load_dotenv
from flask import Flask, jsonify
from pydantic import ValidationError
from repository import ClienteNaoEncontrado, FonteDeDados, RepositorioEmMemoria
from werkzeug.exceptions import HTTPException

from routes import registrar_blueprints
from routes.agregados import RespostaSaude
from routes.comum import CHAVE_REPOSITORIO
from routes.erros import CodigoErro, ErroApi, payload_de_erro

__all__ = ["criar_app", "app", "NOME_DO_SERVICO", "VERSAO"]

NOME_DO_SERVICO = "lastro-api"
VERSAO = "0.1.0"

_log = logging.getLogger(__name__)


def _em_desenvolvimento(app: Flask) -> bool:
    """CORS só aqui. Em produção a origem é uma só — o Next faz proxy (D3)."""
    return app.debug or os.getenv("LASTRO_ENV", "development") == "development"


def _llm_habilitado() -> bool:
    return os.getenv("LASTRO_LLM_ENABLED", "true").strip().lower() not in {
        "false",
        "0",
        "no",
    }


def criar_app(
    repositorio: RepositorioEmMemoria | None = None,
    fonte: FonteDeDados | None = None,
    testando: bool = False,
) -> Flask:
    """Fábrica de aplicação.

    `repositorio` e `fonte` existem para a suíte injetar um dataset próprio sem
    depender de `data/` estar escrito. Em execução normal ambos são `None` e o
    repositório carrega `data/`.
    """
    load_dotenv()
    app = Flask(__name__)
    app.config["TESTING"] = testando
    app.config["JSON_SORT_KEYS"] = False
    app.json.sort_keys = False

    repo = repositorio or RepositorioEmMemoria(fonte)
    app.extensions[CHAVE_REPOSITORIO] = repo
    if not testando:
        # Sem isto a carteira sobe vazia a cada reinício: as declarações de
        # operação vivem só no processo (D3), e o CSV de Features não traz
        # nenhuma (`routes/semeadura.py`). `/api/carteira/semear` continua
        # disponível para re-semear ou trocar a amostra manualmente.
        repo.semear_carteira_de_demonstracao()

    registrar_blueprints(app)
    _registrar_saude(app)
    _registrar_camada_de_coleta(app)
    _registrar_camada_de_linguagem(app)
    _registrar_tratamento_de_erro(app)
    _registrar_cors(app)
    return app


def _registrar_saude(app: Flask) -> None:
    @app.get("/api/saude")
    def saude():
        """Sonda da faixa global da interface (`03-ux-e-telas.md` §9.4)."""
        corpo = RespostaSaude(
            ok=True,
            servico=NOME_DO_SERVICO,
            versao=VERSAO,
            llmHabilitado=_llm_habilitado(),
            dataHora=datetime.now().astimezone().isoformat(),
        )
        return jsonify(corpo.model_dump(by_alias=True, mode="json"))


def _registrar_camada_de_coleta(app: Flask) -> None:
    """Registra `coleta.api.features_bp` sob `/api/coleta` (`coleta/README.md`).

    Expõe `/api/coleta/saude`, `/api/coleta/fontes`, `/api/coleta/features/<cnpj>`
    e `/api/coleta/features/lote` — o inventário de frescor por fonte é o que
    permite à interface responder "esse dado está velho?" sem abrir o banco.

    **Registro tolerante, em duas camadas.** O `ImportError` cobre a coleta não
    estar no `sys.path` ou faltar `duckdb`; a ausência do warehouse não é
    tratada aqui de propósito — o próprio Blueprint devolve `503` com a
    explicação em vez de falhar na subida, que é o comportamento certo para um
    serviço que precisa subir mesmo sem carga feita.
    """
    try:
        import adaptadores  # noqa: F401, PLC0415 — põe a raiz do repo no sys.path
        from coleta.api import features_bp  # noqa: PLC0415 — registro condicional
    except ImportError as erro:
        _log.warning(
            "`coleta.api.features_bp` indisponível (%s); as rotas `/api/coleta/*` "
            "não foram registradas. A due diligence segue com o dataset simulado.",
            erro,
        )
        return
    app.register_blueprint(features_bp, url_prefix="/api/coleta")


def _registrar_camada_de_linguagem(app: Flask) -> None:
    """Registra `llm.blueprint.llm_bp` — as rotas de narrativa, copiloto e custo.

    O registro é condicional porque `llm/blueprint.py` pertence a outro
    workstream e pode não existir ainda. Sem ele, `/api/narrativa/*`,
    `/api/copiloto` e `/api/llm/custo` devolvem 404 com o envelope padrão, e a
    interface degrada para a narrativa determinística — que é exatamente o
    comportamento previsto por D5 e pelo ensaio com `LASTRO_LLM_ENABLED=false`.
    """
    try:
        from llm.blueprint import llm_bp  # noqa: PLC0415 — registro condicional
    except ImportError:
        _log.warning(
            "`llm.blueprint.llm_bp` indisponível; as rotas da camada de "
            "linguagem não foram registradas."
        )
        return
    app.register_blueprint(llm_bp)


def _registrar_tratamento_de_erro(app: Flask) -> None:
    """Todo erro sai como `{erro, detalhe}`. Nunca HTML, nunca tela branca."""

    @app.errorhandler(ErroApi)
    def _erro_de_negocio(erro: ErroApi):
        return jsonify(erro.como_payload()), erro.status

    @app.errorhandler(ClienteNaoEncontrado)
    def _cliente_ausente(erro: ClienteNaoEncontrado):
        return (
            jsonify(
                payload_de_erro(
                    CodigoErro.CLIENTE_NAO_ENCONTRADO,
                    f"Nenhum cliente com id `{erro.cliente_id}`.",
                )
            ),
            HTTPStatus.NOT_FOUND,
        )

    @app.errorhandler(ValidationError)
    def _corpo_invalido(erro: ValidationError):
        return (
            jsonify(payload_de_erro(CodigoErro.CORPO_INVALIDO, erro.errors(include_url=False))),
            HTTPStatus.BAD_REQUEST,
        )

    @app.errorhandler(HTTPException)
    def _erro_http(erro: HTTPException):
        codigo = (
            CodigoErro.ROTA_NAO_ENCONTRADA
            if erro.code == HTTPStatus.NOT_FOUND
            else CodigoErro.METODO_NAO_PERMITIDO
            if erro.code == HTTPStatus.METHOD_NOT_ALLOWED
            else CodigoErro.ERRO_INTERNO
        )
        return (
            jsonify(payload_de_erro(codigo, erro.description)),
            erro.code or HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    @app.errorhandler(Exception)
    def _erro_inesperado(erro: Exception):
        _log.exception("Falha não tratada em %s", erro.__class__.__name__)
        return (
            jsonify(payload_de_erro(CodigoErro.ERRO_INTERNO, str(erro))),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


def _registrar_cors(app: Flask) -> None:
    if not _em_desenvolvimento(app):
        return
    try:
        from flask_cors import CORS  # noqa: PLC0415 — dependência só de desenvolvimento
    except ImportError:  # pragma: no cover
        _log.warning("flask-cors ausente; seguindo sem CORS.")
        return
    CORS(app, resources={r"/api/*": {"origins": "*"}})


#: Alvo de `flask --app app run`.
app = criar_app()


if __name__ == "__main__":  # pragma: no cover
    app.run(port=int(os.getenv("PORT", "5001")), debug=True)
