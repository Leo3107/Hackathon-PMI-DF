"""Metricas e graficos de um score de risco.

A metrica pedida e AUC e a perda e entropia cruzada binaria, mas um score de
credito nao se julga so por AUC: duas coisas a mais entram aqui de proposito.

- **Calibracao** (Brier e a curva de confiabilidade). AUC mede ORDENACAO. Um
  modelo com AUC 0.85 pode dizer "40% de chance de inadimplencia" para um grupo
  que inadimple 8% das vezes -- a ordem esta certa e o numero esta errado. Como
  este score vai alimentar decisao de credito, o numero importa.

- **Captura no decil mais arriscado.** E a pergunta que a mesa de credito faz:
  "se eu recusar os 10% piores, quantos inadimplentes eu evito?". Traduz AUC em
  uma frase que da para defender numa reuniao.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)

from . import esquema


def ks(y_verdadeiro: np.ndarray, proba: np.ndarray) -> float:
    """Kolmogorov-Smirnov: maior distancia entre as acumuladas de bom e mau.

    Convencao de mercado em credito; sai de graca da curva ROC (tpr - fpr).
    """
    fpr, tpr, _ = roc_curve(y_verdadeiro, proba)
    return float(np.max(tpr - fpr))


def captura_no_topo(
    y_verdadeiro: np.ndarray, proba: np.ndarray, fracao: float = 0.10
) -> float:
    """Fracao dos inadimplentes que cai no `fracao` de maior score."""
    positivos = float(np.sum(y_verdadeiro))
    if positivos == 0:
        return float("nan")
    k = max(1, int(round(len(proba) * fracao)))
    topo = np.argsort(proba)[::-1][:k]
    return float(np.sum(np.asarray(y_verdadeiro)[topo]) / positivos)


def metricas(
    y_verdadeiro, proba, *, prefixo: str = "", fracao_topo: float = 0.10
) -> dict[str, float]:
    """Bloco completo de metricas. `prefixo` separa treino/teste no MLflow."""
    y = np.asarray(y_verdadeiro).astype(int)
    p = np.asarray(proba, dtype=float)
    p_seguro = np.clip(p, 1e-15, 1 - 1e-15)

    if len(np.unique(y)) < 2:
        # Fold degenerado: devolver NaN em vez de explodir, para o loop de CV
        # seguir e o relatorio mostrar onde faltou positivo.
        vazio = float("nan")
        auc = aupr = k = vazio
    else:
        auc = float(roc_auc_score(y, p))
        aupr = float(average_precision_score(y, p))
        k = ks(y, p)

    saida = {
        "auc": auc,
        "gini": 2 * auc - 1 if auc == auc else float("nan"),
        "aupr": aupr,
        "ks": k,
        # A perda que os quatro modelos otimizam. Reportada sempre, porque AUC
        # alto com logloss ruim significa ordenacao boa e probabilidade errada.
        "logloss": float(log_loss(y, p_seguro, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p_seguro)),
        f"captura_top{int(fracao_topo * 100)}": captura_no_topo(y, p, fracao_topo),
        "prevalencia": float(y.mean()),
        "n": int(len(y)),
    }
    return {f"{prefixo}{k2}": v for k2, v in saida.items()} if prefixo else saida


def avaliar_cv(
    pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    cv,
    *,
    fracao_topo: float = 0.10,
) -> tuple[dict[str, float], pd.DataFrame]:
    """CV agrupado com predicao out-of-fold.

    Escrito na mao em vez de `cross_val_predict` por um motivo: precisamos das
    metricas POR FOLD para reportar o desvio-padrao. Com 45 municipios, um AUC
    de 0.82 +/- 0.09 e uma conclusao bem diferente de 0.82 +/- 0.01 -- o segundo
    e um modelo, o primeiro e sorte de particao.
    """
    from sklearn.base import clone

    oof = np.full(len(y), np.nan)
    linhas = []
    for i, (tr, va) in enumerate(cv.split(X, y, groups=grupos), start=1):
        modelo = clone(pipeline)
        modelo.fit(X.iloc[tr], y.iloc[tr])
        p = modelo.predict_proba(X.iloc[va])[:, 1]
        oof[va] = p
        linhas.append({"fold": i, **metricas(y.iloc[va], p, fracao_topo=fracao_topo)})

    por_fold = pd.DataFrame(linhas)
    resumo: dict[str, float] = {}
    for coluna in por_fold.columns:
        if coluna in ("fold", "n"):
            continue
        resumo[f"cv_{coluna}_media"] = float(por_fold[coluna].mean())
        resumo[f"cv_{coluna}_desvio"] = float(por_fold[coluna].std(ddof=1))
    # Metricas sobre o vetor out-of-fold inteiro: menos ruidosas que a media dos
    # folds e a estimativa que melhor representa "o modelo", nao "os folds".
    resumo.update(metricas(y, oof, prefixo="oof_", fracao_topo=fracao_topo))
    resumo["oof_proba"] = oof  # type: ignore[assignment]
    return resumo, por_fold


def tabela_de_importancia(pipeline, limite: int = 30) -> pd.DataFrame:
    """Importancia ou coeficiente, o que o estimador final oferecer."""
    from . import preparo

    nomes = preparo.nomes_de_features(pipeline)
    estimador = pipeline.steps[-1][1]
    # Desembrulha calibrador, que esconde o estimador real uma camada abaixo.
    estimador = getattr(estimador, "estimator", estimador)
    estimador = getattr(estimador, "estimator", estimador)

    if hasattr(estimador, "feature_importances_"):
        valores = np.asarray(estimador.feature_importances_, dtype=float)
        rotulo = "importancia"
    elif hasattr(estimador, "coef_"):
        valores = np.asarray(estimador.coef_, dtype=float).ravel()
        rotulo = "coeficiente"
    else:
        return pd.DataFrame(columns=["feature", "valor", "tipo"])

    if len(nomes) != len(valores):
        nomes = [f"f{i}" for i in range(len(valores))]

    tabela = pd.DataFrame({"feature": nomes, "valor": valores, "tipo": rotulo})
    return tabela.reindex(
        tabela["valor"].abs().sort_values(ascending=False).index
    ).head(limite).reset_index(drop=True)


def teto_do_alvo_sintetico(
    X: pd.DataFrame, y: pd.Series, caminho_coeficientes: Path | None = None
) -> dict[str, float]:
    """AUC de Bayes do mock: o maximo alcancavel por QUALQUER modelo.

    So existe porque `alvo_sintetico` e fabricado e a funcao geradora esta
    publicada. Reaplicando os coeficientes de `alvo_coeficientes.json` obtemos a
    probabilidade VERDADEIRA de cada linha; o AUC dela contra o `y` realmente
    sorteado e o teto, porque o alvo e um sorteio de Bernoulli -- a aleatoriedade
    do `rng.random() < p` nao e aprendivel por ninguem.

    E o numero que da escala a todos os outros: 0.79 de AUC nao e "79% de 1.0",
    e ~97% do que e possivel. AUC acima do teto nao e modelo bom, e vazamento.

    Em dado real devolve `{}` -- nao ha funcao geradora conhecida para reaplicar.
    """
    caminho = caminho_coeficientes or (
        esquema.RAIZ / "data" / "mock" / "alvo_coeficientes.json"
    )
    if not caminho.exists():
        return {}
    spec = json.loads(caminho.read_text(encoding="utf-8"))
    coef = spec.get("coeficientes") or {}
    ref = spec.get("referencias_de_centragem") or {}
    if "intercepto" not in coef:
        return {}

    def col(nome: str) -> np.ndarray:
        if nome not in X.columns:
            return np.zeros(len(X))
        # `or 0` do gerador: ausente entra como zero.
        return pd.to_numeric(X[nome], errors="coerce").fillna(0.0).to_numpy(float)

    z = np.full(len(X), float(coef["intercepto"]))
    z += coef.get("log1p_divida_ativa_total", 0.0) * np.log1p(
        np.clip(col("divida_ativa_total"), 0, None)
    )
    z += coef.get("flag_situacao_irregular", 0.0) * col("flag_situacao_irregular")
    z += coef.get("n_empresas_do_socio_inaptas", 0.0) * col("n_empresas_do_socio_inaptas")
    # O cap de 10 esta APENAS no codigo de `scripts/gerar_mock.py` (`min(..., 10)`),
    # nao no json. Sem ele o teto sai errado para quem tem muitos autos.
    z += coef.get("n_autos_infracao", 0.0) * np.clip(col("n_autos_infracao"), None, 10)
    z += coef.get("flag_embargo_ativo", 0.0) * col("flag_embargo_ativo")
    for campo, chave in (
        ("idade_empresa_meses", "log1p_idade_empresa_meses"),
        ("capital_social", "log1p_capital_social"),
    ):
        if chave in coef and campo in ref:
            z += coef[chave] * (
                np.log1p(np.clip(col(campo), 0, None)) - np.log1p(float(ref[campo]))
            )
    z += coef.get("desvio_produtividade_vs_media_5a", 0.0) * col(
        "desvio_produtividade_vs_media_5a"
    )
    z += coef.get("anomalia_na_fase_critica", 0.0) * col("anomalia_na_fase_critica")
    z += coef.get("n_protestos_ativos", 0.0) * col("n_protestos_ativos")

    p_verdadeiro = 1.0 / (1.0 + np.exp(-z))
    alvo = np.asarray(y).astype(int)
    if len(np.unique(alvo)) < 2:
        return {}
    return {
        "teto_auc_bayes": float(roc_auc_score(alvo, p_verdadeiro)),
        "teto_logloss_bayes": float(log_loss(alvo, np.clip(p_verdadeiro, 1e-15, 1 - 1e-15))),
        "teto_prevalencia_esperada": float(p_verdadeiro.mean()),
    }


def conferir_recuperacao_do_alvo(
    pipeline, caminho_coeficientes: Path | None = None
) -> dict[str, float]:
    """Checa se o pipeline recuperou os sinais do alvo SINTETICO.

    So faz sentido com o mock: `alvo_sintetico` vem de uma logistica de
    coeficientes conhecidos, publicados em `alvo_coeficientes.json`. Se o sinal
    (sinal algebrico, nao magnitude) dos coeficientes estimados nao casa com os
    verdadeiros, o defeito esta no PRE-PROCESSAMENTO, nao no modelo -- e essa e
    a unica coisa que o mock mede de verdade. Em dado real, ignore.

    Compare SINAL, nunca magnitude: o termo verdadeiro vale 0.14 e o estimado
    0.39 sem que nada esteja errado, porque features correlacionadas dividem o
    efeito entre si de forma diferente da parametrizacao original.

    `flag_embargo_ativo` e o termo INSTAVEL, e oscilar nele nao indica bug. O
    gerador faz `tem_auto = perfil.startswith("passivo_ambiental")`, o que torna o
    perfil de embargo um subconjunto ESTRITO do perfil com auto de infracao --
    48 de 48 embargados tambem tem auto, com media de 8,7 autos contra 0,79 no
    resto. Sobra pouco residuo para identificar o efeito do embargo separado do
    efeito dos autos, e o coeficiente muda de sinal entre sorteios: em duas
    regeracoes do mesmo gerador saiu -0.008 (residuo de 17,0% contra 16,4% de
    inadimplencia) e +0.15 (20,8% contra 11,7%). Trate 9/10 e 10/10 como o mesmo
    resultado; desconfie abaixo de 9/10. Em dado real do IBAMA os dois eventos
    nao sao aninhados assim.
    """
    caminho = caminho_coeficientes or (
        esquema.RAIZ / "data" / "mock" / "alvo_coeficientes.json"
    )
    if not caminho.exists():
        return {}

    verdadeiros = json.loads(caminho.read_text(encoding="utf-8"))["coeficientes"]
    verdadeiros.pop("intercepto", None)

    # Nome do coeficiente no json -> nome da feature que a engenharia produz.
    equivalencia = {
        "log1p_divida_ativa_total": "log1p_divida_ativa_total",
        "flag_situacao_irregular": "flag_situacao_irregular",
        "n_empresas_do_socio_inaptas": "n_empresas_do_socio_inaptas",
        "n_autos_infracao": "n_autos_infracao_cap",
        "flag_embargo_ativo": "flag_embargo_ativo",
        "log1p_idade_empresa_meses": "log1p_idade_empresa_meses_centrado",
        "log1p_capital_social": "log1p_capital_social_centrado",
        "desvio_produtividade_vs_media_5a": "desvio_produtividade_vs_media_5a",
        "anomalia_na_fase_critica": "anomalia_na_fase_critica",
        "n_protestos_ativos": "n_protestos_ativos",
    }

    estimados = tabela_de_importancia(pipeline, limite=10_000)
    if estimados.empty or estimados["tipo"].iloc[0] != "coeficiente":
        return {}
    mapa = dict(zip(estimados["feature"], estimados["valor"]))

    acertos, total = 0, 0
    detalhe: dict[str, float] = {}
    for nome_json, coef in verdadeiros.items():
        nome_feature = equivalencia.get(nome_json)
        if nome_feature is None or nome_feature not in mapa:
            continue
        total += 1
        estimado = float(mapa[nome_feature])
        detalhe[f"coef_{nome_feature}"] = round(estimado, 4)
        if np.sign(estimado) == np.sign(coef):
            acertos += 1

    if not total:
        return {}
    detalhe["recuperacao_sinais_frac"] = round(acertos / total, 3)
    detalhe["recuperacao_sinais_n"] = total
    return detalhe


# ------------------------------------------------------------------ plots ---

def salvar_graficos(
    y_verdadeiro, proba, destino: Path, *, titulo: str = ""
) -> list[Path]:
    """ROC, calibracao e distribuicao de score. Devolve os caminhos gerados.

    Importa matplotlib aqui dentro para que a inferencia em producao, que nunca
    chama esta funcao, nao precise do pacote instalado.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve

    y = np.asarray(y_verdadeiro).astype(int)
    p = np.asarray(proba, dtype=float)
    destino.mkdir(parents=True, exist_ok=True)
    gerados: list[Path] = []

    fig, eixos = plt.subplots(1, 3, figsize=(16, 4.6))

    fpr, tpr, _ = roc_curve(y, p)
    auc = roc_auc_score(y, p)
    eixos[0].plot(fpr, tpr, lw=2, label=f"AUC = {auc:.4f}")
    eixos[0].plot([0, 1], [0, 1], "--", color="gray", lw=1, label="aleatorio")
    i_ks = int(np.argmax(tpr - fpr))
    eixos[0].vlines(
        fpr[i_ks], fpr[i_ks], tpr[i_ks], color="crimson", lw=2,
        label=f"KS = {tpr[i_ks] - fpr[i_ks]:.4f}",
    )
    eixos[0].set(xlabel="falso positivo", ylabel="verdadeiro positivo", title="ROC")
    eixos[0].legend(loc="lower right", fontsize=9)

    n_bins = min(10, max(3, len(np.unique(p)) // 20))
    frac, media = calibration_curve(y, p, n_bins=n_bins, strategy="quantile")
    eixos[1].plot(media, frac, "o-", lw=2, label="observado")
    eixos[1].plot([0, 1], [0, 1], "--", color="gray", lw=1, label="perfeito")
    eixos[1].set(
        xlabel="probabilidade prevista",
        ylabel="inadimplencia observada",
        title=f"calibracao (Brier = {brier_score_loss(y, p):.4f})",
    )
    eixos[1].legend(loc="upper left", fontsize=9)

    bins = np.linspace(0, max(p.max(), 1e-6), 40)
    eixos[2].hist(p[y == 0], bins=bins, alpha=0.65, label="adimplente", density=True)
    eixos[2].hist(p[y == 1], bins=bins, alpha=0.65, label="inadimplente", density=True)
    eixos[2].set(xlabel="probabilidade prevista", ylabel="densidade",
                 title="separacao das classes")
    eixos[2].legend(fontsize=9)

    if titulo:
        fig.suptitle(titulo, fontsize=12)
    fig.tight_layout()
    caminho = destino / "diagnostico.png"
    fig.savefig(caminho, dpi=120, bbox_inches="tight")
    plt.close(fig)
    gerados.append(caminho)
    return gerados


__all__ = [
    "avaliar_cv",
    "captura_no_topo",
    "conferir_recuperacao_do_alvo",
    "ks",
    "metricas",
    "salvar_graficos",
    "tabela_de_importancia",
    "teto_do_alvo_sintetico",
]
