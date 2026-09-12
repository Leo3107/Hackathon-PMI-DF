"""Treina os quatro modelos na MESMA particao e compara.

    python -m src.modelos.treino.treinar_todos
    python -m src.modelos.treino.treinar_todos --promover-melhor
    python -m src.modelos.treino.treinar_todos --modelos xgboost lightgbm --calibrar sigmoide
    python -m src.modelos.treino.treinar_todos --promover xgboost   # sem treinar

A comparacao so tem sentido porque os quatro passam pelo mesmo `--semente` e
pelo mesmo split agrupado: qualquer diferenca de AUC entre eles e diferenca de
modelo, nao de particao.

Sobre como o campeao e escolhido: pelo AUC MEDIO DO CV, nao pelo AUC do holdout.
Com 9 municipios e ~52 positivos no holdout, o intervalo de confianca do AUC de
teste e largo o bastante para que escolher por ele seja escolher por sorte de
particao. O CV da 5 estimativas e, de quebra, o desvio-padrao -- que e o numero
que diz se a diferenca entre o primeiro e o segundo colocado significa algo.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import pandas as pd

from .. import artefatos, rastreio
from . import (
    _comum,
    treinar_lightgbm,
    treinar_random_forest,
    treinar_regressao_logistica,
    treinar_xgboost,
)

ESPECS = {
    "regressao_logistica": treinar_regressao_logistica.ESPEC,
    "random_forest": treinar_random_forest.ESPEC,
    "xgboost": treinar_xgboost.ESPEC,
    "lightgbm": treinar_lightgbm.ESPEC,
}

# Ordem de preferencia do critatio de selecao. CV primeiro; holdout so como
# desempate quando o CV foi desligado com --sem-cv.
CRITERIOS = ("cv_auc_media", "oof_auc", "teste_auc")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--modelos", nargs="+", choices=list(ESPECS), default=list(ESPECS))
    p.add_argument(
        "--promover-melhor", action="store_true",
        help="aponta campeao.json para o melhor AUC de CV ao terminar",
    )
    p.add_argument(
        "--promover", metavar="NOME", default=None,
        help="so aponta campeao.json para um artefato ja existente e sai",
    )
    # Repassados aos scripts individuais, que e como os quatro ficam na mesma
    # particao: mesma semente, mesmo --fracao-teste, mesmos folds.
    p.add_argument("--dados", default=None)
    p.add_argument("--alvo", default=None)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--fracao-teste", type=float, default=0.2)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--balancear", action="store_true")
    p.add_argument("--calibrar", choices=("nenhuma", "sigmoide", "isotonica"),
                   default="nenhuma")
    p.add_argument("--rapido", action="store_true")
    p.add_argument("--sem-cv", action="store_true")
    p.add_argument("--sem-graficos", action="store_true")
    p.add_argument("--sem-mlflow", action="store_true")
    p.add_argument("--sufixo", default="")
    p.add_argument("--experimento", default=rastreio.EXPERIMENTO_PADRAO)
    p.add_argument("--tracking-uri", default=None)
    return p


def _argv_repassado(args: argparse.Namespace) -> list[str]:
    """Monta o argv de cada script a partir dos argumentos comuns."""
    argv: list[str] = [
        "--folds", str(args.folds),
        "--fracao-teste", str(args.fracao_teste),
        "--semente", str(args.semente),
        "--calibrar", args.calibrar,
        "--experimento", args.experimento,
    ]
    if args.dados:
        argv += ["--dados", args.dados]
    if args.alvo:
        argv += ["--alvo", args.alvo]
    if args.sufixo:
        argv += ["--sufixo", args.sufixo]
    if args.tracking_uri:
        argv += ["--tracking-uri", args.tracking_uri]
    for flag, ativo in (
        ("--balancear", args.balancear),
        ("--rapido", args.rapido),
        ("--sem-cv", args.sem_cv),
        ("--sem-graficos", args.sem_graficos),
        ("--sem-mlflow", args.sem_mlflow),
    ):
        if ativo:
            argv.append(flag)
    return argv


def _melhor(linhas: list[dict]) -> dict | None:
    validas = [linha for linha in linhas if "erro" not in linha]
    if not validas:
        return None
    for criterio in CRITERIOS:
        candidatas = [
            linha for linha in validas
            if isinstance(linha.get(criterio), float) and linha[criterio] == linha[criterio]
        ]
        if candidatas:
            return max(candidatas, key=lambda linha: linha[criterio])
    return validas[0]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.promover:
        if args.promover not in artefatos.listar():
            print(
                f"[erro] '{args.promover}' nao esta em {artefatos.DIR_ARTEFATOS}. "
                f"Disponiveis: {artefatos.listar()}",
                file=sys.stderr,
            )
            return 1
        ponteiro = artefatos.marcar_campeao(args.promover)
        print(f"campeao -> {args.promover}  ({ponteiro})")
        return 0

    repassado = _argv_repassado(args)
    linhas: list[dict] = []

    for nome in args.modelos:
        print("\n" + "=" * 78)
        print(f"  {nome}")
        print("=" * 78)
        try:
            linhas.append(_comum.executar(ESPECS[nome], repassado))
        except Exception as exc:  # noqa: BLE001 - um modelo nao derruba a bateria
            traceback.print_exc()
            print(f"[erro] {nome} falhou: {type(exc).__name__}: {exc}", file=sys.stderr)
            linhas.append({"nome": nome, "familia": nome, "erro": f"{type(exc).__name__}: {exc}"})

    if not linhas:
        return 1

    tabela = pd.DataFrame(linhas)
    colunas = [
        c for c in (
            "familia", "cv_auc_media", "cv_auc_desvio", "oof_auc", "teste_auc",
            "teste_logloss", "teste_ks", "teste_brier", "teste_captura_top10", "erro",
        )
        if c in tabela.columns
    ]
    ordenada = tabela[colunas]
    if "cv_auc_media" in ordenada.columns:
        ordenada = ordenada.sort_values("cv_auc_media", ascending=False)

    print("\n" + "=" * 78)
    print("  comparativo (ordenado por AUC medio do CV agrupado)")
    print("=" * 78)
    print(ordenada.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    destino = _comum.DIR_RELATORIOS / "comparativo.csv"
    rastreio.salvar_comparativo(linhas, destino)
    print(f"\ncomparativo salvo em {destino}")

    melhor = _melhor(linhas)
    if melhor:
        criterio = next(
            (c for c in CRITERIOS if isinstance(melhor.get(c), float)
             and melhor[c] == melhor[c]),
            "teste_auc",
        )
        print(f"melhor: {melhor['nome']}  ({criterio} = {melhor.get(criterio):.4f})")
        if args.promover_melhor:
            artefatos.marcar_campeao(melhor["nome"])
            print(f"campeao -> {melhor['nome']}  (campeao.json atualizado)")
        else:
            print(
                "nenhum campeao promovido. Para promover: "
                f"`python -m src.modelos.treino.treinar_todos --promover {melhor['nome']}`"
            )

    if (args.alvo or "alvo_sintetico") == "alvo_sintetico":
        print(
            "\nAVISO: o alvo e `alvo_sintetico`, FABRICADO por uma logistica de\n"
            "coeficientes conhecidos. Estes AUC medem se o pipeline esta de pe,\n"
            "NAO a performance em inadimplencia real. O que vale ler agora e a\n"
            "secao de dados no MLflow (preenchimento por bloco de fonte) e a\n"
            "recuperacao dos sinais do alvo pela regressao logistica."
        )

    return 0 if any("erro" not in linha for linha in linhas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
