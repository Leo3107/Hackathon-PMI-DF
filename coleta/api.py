"""API Flask da camada de coleta.

Desenhada como Blueprint para plugar no backend existente:

    from coleta.api import features_bp
    app.register_blueprint(features_bp, url_prefix="/api/v1")

Ou de pe sozinha, para desenvolvimento:

    flask --app coleta.api:criar_app run

Sobre a conexao com o DuckDB, que e o ponto que decide o desenho:

- O warehouse abre em **somente leitura** por padrao. DuckDB aceita varios
  leitores simultaneos (processos e threads), mas um unico escritor -- entao
  read-only e o que permite rodar com varios workers de gunicorn ao lado do
  agendador que roda as cargas.
- Cada requisicao usa um `cursor()` proprio sobre a conexao compartilhada. E a
  forma suportada de concorrencia no DuckDB; testado com 16 threads.
- Em modo leitura, `permitir_rede` fica desligado: as consultas sob demanda
  (clima e protestos) precisam gravar no cache, e gravar e justamente o que
  read-only proibe. Na pratica isso nao custa dado -- quem preenche esse cache
  e o `bulk --source clima`, rodado pelo agendador. Para um deploy de um worker
  so, `COLETA_SOMENTE_LEITURA=0` habilita a consulta ao vivo.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

import duckdb
from flask import Blueprint, Flask, current_app, g, jsonify, request

from . import config, warehouse
from .features import build_features
from .logging_setup import get_logger, log_evento, setup_logging

log = get_logger("api")

features_bp = Blueprint("coleta_features", __name__)

CHAVE_EXT = "coleta"
LOTE_MAX_PADRAO = 200


def _agora() -> dt.datetime:
    return dt.datetime.now()


# --------------------------------------------------------------- conexao ----

def _estado() -> dict:
    """Estado por app, guardado em `app.extensions`."""
    return current_app.extensions.setdefault(CHAVE_EXT, {})


def _conexao_base() -> duckdb.DuckDBPyConnection:
    """Conexao compartilhada, aberta na primeira requisicao."""
    estado = _estado()
    if estado.get("con") is None:
        caminho = Path(
            current_app.config.get("COLETA_WAREHOUSE", config.WAREHOUSE_PATH)
        )
        somente_leitura = bool(
            current_app.config.get("COLETA_SOMENTE_LEITURA", True)
        )
        if somente_leitura and not caminho.exists():
            raise FileNotFoundError(
                f"warehouse nao encontrado em {caminho}. "
                "Rode `python -m coleta.cli init` e ao menos uma carga."
            )
        estado["con"] = warehouse.conectar(caminho, read_only=somente_leitura)
        estado["caminho"] = caminho
        estado["somente_leitura"] = somente_leitura
        log_evento(
            log, "api.warehouse_aberto", caminho=str(caminho),
            somente_leitura=somente_leitura,
        )
    return estado["con"]


def _cursor() -> duckdb.DuckDBPyConnection:
    """Um cursor por requisicao; fechado no teardown."""
    if "coleta_cur" not in g:
        g.coleta_cur = _conexao_base().cursor()
    return g.coleta_cur


@features_bp.teardown_app_request
def _fechar_cursor(_exc: BaseException | None) -> None:
    cur = g.pop("coleta_cur", None)
    if cur is not None:
        try:
            cur.close()
        except Exception:  # noqa: BLE001 - fechar cursor nunca quebra a resposta
            pass


def fechar_conexao(app: Flask) -> None:
    """Fecha a conexao compartilhada. Chamar no shutdown do processo."""
    estado = app.extensions.get(CHAVE_EXT) or {}
    con = estado.pop("con", None)
    if con is not None:
        con.close()


def _permitir_rede() -> bool:
    """Consulta ao vivo so faz sentido quando da para gravar no cache."""
    padrao = not _estado().get("somente_leitura", True)
    return bool(current_app.config.get("COLETA_PERMITIR_REDE", padrao))


# ------------------------------------------------------------- validacao ----

def _dv_cnpj(base: str) -> str:
    """Digitos verificadores pelo modulo 11, como manda a Receita."""
    def calcular(numeros: str, pesos: list[int]) -> str:
        soma = sum(int(d) * p for d, p in zip(numeros, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = calcular(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = calcular(base + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return d1 + d2


def validar_documento(documento: str) -> tuple[str | None, str | None]:
    """Devolve (documento normalizado, mensagem de erro).

    Aceita CNPJ completo (14 digitos) ou a base (8 digitos), com ou sem
    mascara. Um CNPJ com digito verificador errado e rejeitado: devolver 39
    campos nulos para um numero digitado errado esconde o erro em vez de
    mostra-lo.
    """
    doc = warehouse.normalizar_documento(documento or "")
    if not doc:
        return None, "documento vazio ou sem digitos"
    if len(doc) == 8:
        return doc, None
    if len(doc) != 14:
        return None, (
            f"documento deve ter 8 digitos (base do CNPJ) ou 14 (CNPJ completo); "
            f"recebido: {len(doc)}"
        )
    if doc[12:] != _dv_cnpj(doc[:12]):
        return None, "digito verificador do CNPJ invalido"
    return doc, None


# -------------------------------------------------------------- endpoints ---

@features_bp.get("/saude")
def saude():
    """Liveness com o estado real do warehouse, nao um 'ok' vazio."""
    try:
        cur = _cursor()
    except FileNotFoundError as exc:
        return jsonify({"status": "degradado", "erro": str(exc)}), 503

    fontes = [
        nome
        for nome, tabela in _TABELAS_POR_FONTE.items()
        if warehouse.tem_dados(cur, tabela)
    ]
    estado = _estado()
    return jsonify(
        {
            "status": "ok" if fontes else "vazio",
            "warehouse": str(estado.get("caminho")),
            "somente_leitura": estado.get("somente_leitura"),
            "consulta_ao_vivo": _permitir_rede(),
            "fontes_carregadas": fontes,
        }
    )


_TABELAS_POR_FONTE = {
    "pgfn": "pgfn_divida",
    "receita": "rf_estabelecimentos",
    "grafo_societario": "socio_empresa",
    "ibama_autos": "ibama_autos",
    "ibama_embargos": "ibama_embargos",
    "bcb_mdcr": "bcb_mdcr",
    "ibge_producao": "ibge_producao",
    "clima": "clima_diario",
}


@features_bp.get("/fontes")
def fontes():
    """Frescor por fonte: quando cada tabela foi carregada e com quantas linhas.

    E o endpoint que responde "esse dado esta velho?" sem abrir o banco.
    """
    try:
        cur = _cursor()
    except FileNotFoundError as exc:
        return jsonify({"erro": str(exc)}), 503

    cargas = cur.execute(
        """
        SELECT fonte, tabela, max(carregado_em) AS ultima_carga,
               count(*) AS particoes_registradas
        FROM ingestao_log
        GROUP BY fonte, tabela
        ORDER BY ultima_carga DESC
        """
    ).fetchall()

    saida = []
    for fonte, tabela, quando, particoes in cargas:
        # A contagem vem da tabela, nao do somatorio do log: recarregar uma
        # particao soma duas entradas no log e continua sendo uma linha so.
        saida.append(
            {
                "fonte": fonte,
                "tabela": tabela,
                "ultima_carga": quando.isoformat() if quando else None,
                "dias_desde_a_carga": (
                    round((_agora() - quando).total_seconds() / 86400, 1)
                    if quando
                    else None
                ),
                "linhas_na_tabela": warehouse.contar(cur, tabela),
                "particoes_registradas": int(particoes),
            }
        )
    return jsonify({"cargas": saida})


def _montar(documento: str, cultura: str | None, rede: bool) -> dict[str, Any]:
    return build_features(
        documento, con=_cursor(), cultura=cultura, permitir_rede=rede
    )


@features_bp.get("/features/<path:documento>")
def features_documento(documento: str):
    """Dicionario de features de um CNPJ.

    Query params:
      cultura=soja   cultura de referencia das features agricolas
      rede=0|1       forca ou desliga a consulta ao vivo (clima e protestos)
    """
    doc, erro = validar_documento(documento)
    if erro:
        return jsonify({"erro": "documento invalido", "detalhe": erro}), 400

    cultura = request.args.get("cultura") or None
    if cultura and cultura not in config.CALENDARIO_CULTURAS:
        return (
            jsonify(
                {
                    "erro": "cultura desconhecida",
                    "detalhe": f"culturas: {', '.join(config.CALENDARIO_CULTURAS)}",
                }
            ),
            400,
        )

    rede = _permitir_rede()
    if (param := request.args.get("rede")) is not None:
        rede = param not in ("0", "false", "nao", "no")
        if rede and _estado().get("somente_leitura", True):
            return (
                jsonify(
                    {
                        "erro": "consulta ao vivo indisponivel",
                        "detalhe": (
                            "o warehouse esta aberto em somente leitura; "
                            "clima e protestos precisam gravar no cache. "
                            "Suba com COLETA_SOMENTE_LEITURA=0 ou pre-aqueca o "
                            "cache com `bulk --source clima`."
                        ),
                    }
                ),
                409,
            )

    try:
        return jsonify(_montar(doc, cultura, rede))
    except FileNotFoundError as exc:
        return jsonify({"erro": str(exc)}), 503


@features_bp.post("/features/lote")
def features_lote():
    """Varios documentos numa chamada, para escorar uma carteira inteira.

    Corpo: {"documentos": ["12345678000190", ...], "cultura": "soja"}

    Um documento invalido nao invalida o lote: ele vai para `erros` e os
    demais sao processados.
    """
    corpo = request.get_json(silent=True) or {}
    documentos = corpo.get("documentos")
    if not isinstance(documentos, list) or not documentos:
        return (
            jsonify(
                {
                    "erro": "corpo invalido",
                    "detalhe": 'esperado {"documentos": ["<cnpj>", ...]}',
                }
            ),
            400,
        )

    limite = int(current_app.config.get("COLETA_LOTE_MAX", LOTE_MAX_PADRAO))
    if len(documentos) > limite:
        return (
            jsonify(
                {
                    "erro": "lote grande demais",
                    "detalhe": f"maximo de {limite} documentos por chamada",
                }
            ),
            413,
        )

    cultura = corpo.get("cultura") or None
    if cultura and cultura not in config.CALENDARIO_CULTURAS:
        return jsonify({"erro": "cultura desconhecida"}), 400

    rede = _permitir_rede()
    resultados: list[dict] = []
    erros: list[dict] = []
    for bruto in documentos:
        doc, erro = validar_documento(str(bruto))
        if erro:
            erros.append({"documento": bruto, "detalhe": erro})
            continue
        try:
            resultados.append(_montar(doc, cultura, rede))
        except Exception as exc:  # noqa: BLE001 - um CNPJ nao derruba o lote
            log_evento(log, "api.lote_falhou", documento=doc, erro=str(exc)[:200])
            erros.append({"documento": bruto, "detalhe": f"{type(exc).__name__}"})

    return jsonify(
        {"total": len(resultados), "features": resultados, "erros": erros}
    )


# ----------------------------------------------------------------- fabrica --

def criar_app(**overrides: Any) -> Flask:
    """App standalone. Para produção, registre o Blueprint no app de voces."""
    setup_logging()
    app = Flask(__name__)
    app.config.update(
        COLETA_WAREHOUSE=os.environ.get(
            "COLETA_WAREHOUSE", str(config.WAREHOUSE_PATH)
        ),
        COLETA_SOMENTE_LEITURA=os.environ.get("COLETA_SOMENTE_LEITURA", "1")
        not in ("0", "false", "nao"),
        COLETA_LOTE_MAX=int(os.environ.get("COLETA_LOTE_MAX", LOTE_MAX_PADRAO)),
        JSON_SORT_KEYS=False,
    )
    app.config.update(overrides)
    app.register_blueprint(features_bp, url_prefix="/api/v1")

    # So no app standalone: registrar isso no app de voces sobrescreveria o
    # tratamento de 404 do resto do backend.
    @app.errorhandler(404)
    def _nao_encontrado(_e):
        return jsonify({"erro": "rota nao encontrada"}), 404

    return app


__all__ = ["criar_app", "features_bp", "fechar_conexao", "validar_documento"]
