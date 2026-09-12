"""Endpoints de scoring: CNPJ -> features -> probabilidade de inadimplencia.

Blueprint SEPARADO do `features_bp` de proposito. A camada de coleta nao
depende de sklearn: quem so quer os dados registra `features_bp` e nao precisa
instalar `requirements-ml.txt`. Quem quer o score registra os dois:

    from coleta.api import features_bp
    from coleta.api_score import score_bp

    app.register_blueprint(features_bp, url_prefix="/api/v1")
    app.register_blueprint(score_bp, url_prefix="/api/v1")

Por isso todo import de `src.modelos` acontece DENTRO de `_scorer()`, e nao no
topo do modulo: `import coleta.api_score` tem de funcionar num processo sem
sklearn instalado, falhando so quando alguem efetivamente pedir um score -- e
falhando com 503 e um texto que diz o que rodar, nao com ImportError no boot.

O modelo em si e carregado uma vez por processo (`scorer_padrao` tem
`lru_cache`) e vem do ponteiro `src/modelos/artefatos/campeao.json`: trocar o
modelo em producao e reescrever um json, sem deploy de codigo.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from .api import LOTE_MAX_PADRAO, _montar, _permitir_rede, validar_documento
from .logging_setup import get_logger, log_evento

log = get_logger("api.score")

score_bp = Blueprint("coleta_score", __name__)

# A raiz do repo precisa estar no sys.path para `src.modelos` resolver: nao ha
# pyproject, entao o pacote nao esta instalado -- ele e importado pela posicao.
_RAIZ = Path(__file__).resolve().parent.parent

_AJUDA_ARTEFATO = (
    "modelo indisponivel. Treine e promova um campeao com "
    "`python -m src.modelos.treino.treinar_todos --promover-melhor`."
)


def _scorer(nome: str | None = None):
    """Devolve o Scorer, ou levanta RuntimeError com texto acionavel."""
    if str(_RAIZ) not in sys.path:
        sys.path.insert(0, str(_RAIZ))
    try:
        from src.modelos.inferencia import scorer_padrao
    except ImportError as exc:  # sklearn/joblib ausentes
        raise RuntimeError(
            f"camada de modelagem indisponivel ({exc}). "
            "Instale com `pip install -r requirements-ml.txt`."
        ) from exc

    try:
        return scorer_padrao(nome or current_app.config.get("COLETA_MODELO"))
    except (FileNotFoundError, TypeError) as exc:
        raise RuntimeError(f"{_AJUDA_ARTEFATO} Detalhe: {exc}") from exc


def aquecer(app) -> str | None:
    """Carrega o modelo no boot. Devolve o nome, ou None se nao deu.

    Chamar no start da aplicacao e o que faz um artefato ausente aparecer no
    log de subida em vez de virar 503 para o primeiro cliente. Nao levanta de
    proposito: a API de features continua util sem o modelo.
    """
    with app.app_context():
        try:
            nome = _scorer().nome
        except RuntimeError as exc:
            log_evento(log, "score.modelo_indisponivel", erro=str(exc)[:200])
            return None
        log_evento(log, "score.modelo_carregado", modelo=nome)
        return nome


def _flag(nome: str, padrao: bool = False) -> bool:
    valor = request.args.get(nome)
    if valor is None:
        return padrao
    return valor not in ("0", "false", "nao", "no", "")


# -------------------------------------------------------------- endpoints ---

@score_bp.get("/modelo")
def modelo():
    """Metadados do modelo em producao: metricas, faixas e versoes de lib.

    E o endpoint que responde "de onde veio esse numero?" -- inclusive qual era
    o alvo, que hoje e sintetico e precisa aparecer na resposta, nao so no README.
    """
    try:
        scorer = _scorer()
    except RuntimeError as exc:
        return jsonify({"erro": str(exc)}), 503

    info = scorer.info()
    info["aviso_alvo"] = (
        "alvo `alvo_sintetico`: rotulo de inadimplencia nao e dado publico no "
        "Brasil. As metricas atestam que o pipeline esta de pe, nao a "
        "performance em inadimplencia real. As FEATURES sao reais."
    ) if info.get("alvo") == "alvo_sintetico" else None
    return jsonify(info)


@score_bp.get("/score/<path:documento>")
def score_documento(documento: str):
    """Score de risco de um CNPJ, das fontes cruas ate a probabilidade.

    Query params:
      cultura=soja    cultura de referencia das features agricolas
      explicar=1      anexa a decomposicao coeficiente x valor (so em linear)
      features=1      anexa o dicionario de features que alimentou o modelo
      modelo=<nome>   pontua com outro artefato em vez do campeao
    """
    doc, erro = validar_documento(documento)
    if erro:
        return jsonify({"erro": "documento invalido", "detalhe": erro}), 400

    try:
        scorer = _scorer(request.args.get("modelo"))
    except RuntimeError as exc:
        return jsonify({"erro": str(exc)}), 503

    try:
        features = _montar(doc, request.args.get("cultura") or None, _permitir_rede())
    except FileNotFoundError as exc:
        return jsonify({"erro": str(exc)}), 503

    saida: dict[str, Any] = scorer.pontuar(
        features, com_contribuicoes=_flag("explicar")
    )
    if _flag("features"):
        saida["features"] = features
    return jsonify(saida)


@score_bp.post("/score/lote")
def score_lote():
    """Escora uma carteira numa chamada so.

    Corpo: {"documentos": ["12345678000190", ...], "cultura": "soja"}

    O `predict_proba` roda UMA vez sobre a matriz inteira, nao uma por
    documento: e a diferenca entre escorar 200 CNPJs em um overhead de modelo e
    em duzentos. A coleta de features continua sendo por documento -- e o
    DuckDB que manda ali, nao o sklearn.
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

    try:
        scorer = _scorer(corpo.get("modelo"))
    except RuntimeError as exc:
        return jsonify({"erro": str(exc)}), 503

    cultura = corpo.get("cultura") or None
    rede = _permitir_rede()

    registros: list[dict] = []
    erros: list[dict] = []
    for bruto in documentos:
        doc, erro = validar_documento(str(bruto))
        if erro:
            erros.append({"documento": bruto, "detalhe": erro})
            continue
        try:
            registros.append(_montar(doc, cultura, rede))
        except Exception as exc:  # noqa: BLE001 - um CNPJ nao derruba o lote
            log_evento(log, "score.lote_falhou", documento=doc, erro=str(exc)[:200])
            erros.append({"documento": bruto, "detalhe": f"{type(exc).__name__}"})

    scores = scorer.pontuar(registros) if registros else []
    # Carteira: o que o analista abre primeiro e o pior risco.
    scores.sort(key=lambda s: s.get("score_risco") or 0, reverse=True)

    return jsonify(
        {
            "total": len(scores),
            "modelo": scorer.nome,
            "scores": scores,
            "erros": erros,
        }
    )


__all__ = ["aquecer", "score_bp"]
