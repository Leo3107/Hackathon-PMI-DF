"""Camada de MLflow: tracking do treino e diagnostico do DADO.

O diagnostico de dado nao e enfeite. Com `alvo_sintetico` no lugar do alvo real,
o AUC deste pipeline nao mede nada sobre o mundo -- mede se o pre-processamento
esta de pe. O que de fato da para concluir agora e sobre a MATERIA-PRIMA: quanto
de cada fonte chega preenchido, quantos municipios distintos sustentam as 12
features municipais, se alguma coluna e constante, se ha documento duplicado.
Sao esses numeros que dizem se vale coletar mais antes de treinar de verdade, e
por isso eles vao para o MLflow em toda run, ao lado das metricas do modelo.

Tudo aqui degrada em silencio: se o mlflow nao estiver instalado, ou o servidor
de tracking estiver fora, o treino continua e as metricas vao para o stdout. Uma
run de treino nao pode morrer porque o tracking caiu.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from . import esquema

EXPERIMENTO_PADRAO = "risco_inadimplencia_agro"

# SQLite local, nao `file:./mlruns`.
#
# A partir do MLflow 3.x o backend de FILESYSTEM entra em modo de manutencao e
# `start_run` levanta `MlflowException` pedindo um backend de banco (testado e
# confirmado no mlflow 3.16). Como a degradacao deste modulo e silenciosa por
# design, o sintoma seria o pior possivel: o treino roda inteiro, salva o
# artefato, e nenhuma metrica aparece em lugar nenhum. SQLite nao precisa de
# servidor, e a UI abre com:
#
#     mlflow ui --backend-store-uri sqlite:///mlflow.db
#
# Para usar um servidor de tracking do time, passe `--tracking-uri` ou exporte
# MLFLOW_TRACKING_URI; os dois tem precedencia sobre este padrao.
CAMINHO_BD_PADRAO = esquema.RAIZ / "mlflow.db"
TRACKING_URI_PADRAO = f"sqlite:///{CAMINHO_BD_PADRAO.as_posix()}"
# Com backend de banco, o artefato vai para um diretorio proprio.
RAIZ_ARTEFATOS_PADRAO = (esquema.RAIZ / "mlartifacts").as_uri()


def disponivel() -> bool:
    try:
        import mlflow  # noqa: F401
    except ImportError:
        return False
    return True


@contextlib.contextmanager
def run(
    nome_run: str,
    *,
    experimento: str = EXPERIMENTO_PADRAO,
    tracking_uri: str | None = None,
    ativo: bool = True,
    tags: dict[str, str] | None = None,
) -> Iterator[Any]:
    """Context manager que devolve o modulo mlflow, ou None quando desligado.

    Quem chama sempre escreve `if mlf:` antes de logar. Fica verboso, e e o que
    permite rodar `--sem-mlflow` sem um unico `if` espalhado no script de treino.
    """
    if not ativo or not disponivel():
        if ativo:
            print("[rastreio] mlflow indisponivel; seguindo sem tracking")
        yield None
        return

    # INFO destinado a agentes de codigo, impresso em toda run. Desligado no
    # processo (nao no ambiente do usuario) so para o log de treino ficar legivel.
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    import mlflow

    try:
        mlflow.set_tracking_uri(
            tracking_uri or os.environ.get("MLFLOW_TRACKING_URI") or TRACKING_URI_PADRAO
        )
        _garantir_experimento(mlflow, experimento)
        with mlflow.start_run(run_name=nome_run):
            if tags:
                mlflow.set_tags(tags)
            yield mlflow
    except Exception as exc:  # noqa: BLE001 - tracking caido nao derruba treino
        print(f"[rastreio] mlflow falhou ({type(exc).__name__}: {exc}); sem tracking")
        yield None


def _garantir_experimento(mlflow, nome: str) -> None:
    """Cria o experimento com raiz de artefato explicita, ou reusa o existente.

    `set_experiment` sozinho deixa a raiz de artefato relativa ao cwd, e ai o
    mesmo experimento guarda grafico em dois lugares diferentes dependendo de
    onde o treino foi disparado. Fixar na raiz do repo evita isso.
    """
    existente = mlflow.get_experiment_by_name(nome)
    if existente is None:
        mlflow.create_experiment(nome, artifact_location=RAIZ_ARTEFATOS_PADRAO)
    mlflow.set_experiment(nome)


def logar_metricas(mlf, metricas: dict[str, float], *, passo: int | None = None) -> None:
    if not mlf:
        return
    numericas = {
        k: float(v)
        for k, v in metricas.items()
        if isinstance(v, (int, float, np.floating, np.integer))
        and not isinstance(v, bool)
        and np.isfinite(float(v))
    }
    if numericas:
        mlf.log_metrics(numericas, step=passo)


def logar_parametros(mlf, parametros: dict[str, Any]) -> None:
    if not mlf:
        return
    # MLflow corta parametro longo; `str()` explicito evita falha com objeto.
    mlf.log_params({k: str(v)[:480] for k, v in parametros.items()})


def logar_quadro(mlf, df: pd.DataFrame, nome: str) -> None:
    """Salva um DataFrame como CSV de artefato. Tambem imprime no stdout."""
    if df is None or df.empty:
        return
    if mlf:
        caminho = Path(os.environ.get("TEMP", ".")) / nome
        df.to_csv(caminho, index=False, sep=";", encoding="utf-8")
        try:
            mlf.log_artifact(str(caminho))
        except Exception:  # noqa: BLE001
            pass
        finally:
            caminho.unlink(missing_ok=True)


def logar_arquivos(mlf, caminhos: list[Path], subpasta: str = "") -> None:
    if not mlf:
        return
    for caminho in caminhos:
        if caminho and Path(caminho).exists():
            try:
                mlf.log_artifact(str(caminho), artifact_path=subpasta or None)
            except Exception:  # noqa: BLE001
                pass


def logar_modelo(mlf, pipeline, X_exemplo: pd.DataFrame) -> None:
    """Registra o pipeline no MLflow, com assinatura inferida.

    `serialization_format='cloudpickle'` e obrigatorio aqui. O padrao do MLflow
    3.x e `skops`, que recusa tipos que nao estejam na lista de confiavel -- e o
    nosso pipeline tem quatro deles (`EngenhariaAgro`, `SelecionarNumericas`,
    `xgboost.core.Booster`, `XGBClassifier`). Manter skops exigiria uma lista
    `skops_trusted_types` diferente por familia de modelo; cloudpickle e formato
    suportado, lida com classe customizada e nao precisa de manutencao.

    Embrulhado em try/except amplo de proposito: este registro e CONVENIENCIA
    (abrir o modelo pela UI do MLflow). O artefato que a API carrega e o joblib
    de `artefatos/`, entao perder o registro nunca deve custar a run inteira.
    """
    if not mlf:
        return
    try:
        from mlflow.models import infer_signature

        exemplo = X_exemplo.head(3).copy()
        # `object` com None passa pelo inferidor; `string` com pd.NA nao.
        for col in exemplo.columns:
            if str(exemplo[col].dtype) == "string":
                exemplo[col] = exemplo[col].astype(object).where(
                    exemplo[col].notna(), None
                )
        assinatura = infer_signature(exemplo, pipeline.predict_proba(X_exemplo.head(3)))
        mlf.sklearn.log_model(
            pipeline,
            name="modelo",
            signature=assinatura,
            input_example=exemplo,
            serialization_format="cloudpickle",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[rastreio] nao foi possivel registrar o modelo no mlflow: {exc}")


# ------------------------------------------------------- qualidade do dado ---

def metricas_de_dados(
    X: pd.DataFrame, y: pd.Series, grupos: pd.Series
) -> tuple[dict[str, float], pd.DataFrame]:
    """Diagnostico da materia-prima: o que de fato da para concluir hoje.

    Devolve (metricas escalares, tabela de preenchimento por coluna). A tabela
    e o artefato que responde "coletar mais o que?": uma coluna com 90% de nulo
    e, na pratica, uma coluna que o modelo nao tem.
    """
    n = len(X)
    nulos = X.isna().mean()

    # Preenchimento por BLOCO de fonte, que e a unidade em que o dado falta.
    por_bloco: dict[str, float] = {}
    for bloco, colunas in esquema.BLOCOS_AUSENCIA.items():
        presentes = [c for c in colunas if c in X.columns]
        if presentes:
            por_bloco[f"dados_preench_bloco_{bloco}"] = round(
                float(1 - X[presentes].isna().all(axis=1).mean()), 4
            )

    constantes = [c for c in X.columns if X[c].nunique(dropna=True) <= 1]
    quase_vazias = [c for c in X.columns if nulos[c] >= 0.90]

    metricas = {
        "dados_n_linhas": float(n),
        "dados_n_colunas": float(X.shape[1]),
        "dados_prevalencia_alvo": round(float(y.mean()), 6),
        "dados_n_positivos": float(int(y.sum())),
        "dados_n_grupos_municipio": float(grupos.nunique()),
        "dados_linhas_por_municipio_mediana": float(grupos.value_counts().median()),
        "dados_preench_medio": round(float(1 - nulos.mean()), 4),
        "dados_colunas_constantes": float(len(constantes)),
        "dados_colunas_90pct_nulas": float(len(quase_vazias)),
        "dados_linhas_duplicadas": float(int(X.duplicated().sum())),
        # Com 8,9% de positivos e ~100 colunas pos-one-hot, eventos por
        # parametro abaixo de 10 e o regime em que modelo linear comeca a
        # decorar. E o numero que diz "precisamos de mais LINHAS".
        "dados_eventos_por_coluna": round(float(y.sum() / max(X.shape[1], 1)), 3),
    }
    metricas.update(por_bloco)

    tabela = (
        pd.DataFrame(
            {
                "coluna": X.columns,
                "preenchimento": (1 - nulos).round(4).values,
                "n_distintos": [X[c].nunique(dropna=True) for c in X.columns],
                "constante": [c in constantes for c in X.columns],
            }
        )
        .sort_values("preenchimento")
        .reset_index(drop=True)
    )

    if constantes:
        print(f"[dados] colunas constantes (sem sinal): {constantes}")
    if quase_vazias:
        print(f"[dados] colunas com >=90% de nulo: {quase_vazias}")
    return metricas, tabela


def imprimir_bloco(titulo: str, valores: dict[str, Any]) -> None:
    """Saida de terminal legivel, para quando ninguem vai abrir o MLflow."""
    print(f"\n{titulo}")
    print("-" * len(titulo))
    largura = max((len(k) for k in valores), default=0)
    for chave, valor in valores.items():
        if isinstance(valor, float):
            print(f"  {chave:<{largura}}  {valor:.4f}")
        else:
            print(f"  {chave:<{largura}}  {valor}")


def salvar_comparativo(linhas: list[dict[str, Any]], destino: Path) -> Path:
    """Tabela final com os quatro modelos lado a lado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela = pd.DataFrame(linhas)
    tabela.to_csv(destino, index=False, sep=";", encoding="utf-8")
    destino.with_suffix(".json").write_text(
        json.dumps(linhas, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return destino


__all__ = [
    "EXPERIMENTO_PADRAO",
    "TRACKING_URI_PADRAO",
    "disponivel",
    "imprimir_bloco",
    "logar_arquivos",
    "logar_metricas",
    "logar_modelo",
    "logar_parametros",
    "logar_quadro",
    "metricas_de_dados",
    "run",
    "salvar_comparativo",
]
