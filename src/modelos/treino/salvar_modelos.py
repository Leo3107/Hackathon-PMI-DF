"""Gera os quatro artefatos numa passada curta, para destravar a API.

    python -m src.modelos.treino.salvar_modelos

NAO E TREINO. Roda cada modelo com `--rapido` (poucas arvores, taxa alta), sem
cross-validation, sem MLflow e sem grafico: o objetivo e ter um `.joblib` valido
em `src/modelos/artefatos/` para que o endpoint de score possa ser escrito e
testado de ponta a ponta enquanto o treino de verdade nao rodou.

As metricas que aparecem aqui nao significam nada por dois motivos somados: os
hiperparametros sao de fumaca E o alvo e `alvo_sintetico`, fabricado. Cada bundle
sai com `observacao` dizendo isso, e `campeao.json` aponta para um artefato de
fumaca -- que e justamente o que o treino real sobrescreve, pelo mesmo nome.

Treino de verdade:

    python -m src.modelos.treino.treinar_todos --promover-melhor
"""
from __future__ import annotations

import argparse
import sys
import traceback

import pandas as pd

from .. import artefatos
from . import _comum
from .treinar_todos import ESPECS

NOTA = (
    "ARTEFATO DE FUMACA: hiperparametros --rapido, sem CV, alvo sintetico. "
    "Existe para validar a integracao com a API; sobrescreva com "
    "`python -m src.modelos.treino.treinar_todos --promover-melhor`."
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--modelos", nargs="+", choices=list(ESPECS), default=list(ESPECS))
    p.add_argument("--dados", default=None)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument(
        "--campeao", default=None,
        help="qual artefato apontar em campeao.json; padrao: melhor AUC de holdout",
    )
    p.add_argument(
        "--com-mlflow", action="store_true",
        help="registra tambem no MLflow (por padrao nao registra: run de fumaca "
             "no experimento polui a comparacao depois)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    repassado = [
        "--rapido",
        "--sem-cv",
        "--sem-graficos",
        "--semente", str(args.semente),
        "--nota", NOTA,
    ]
    if not args.com_mlflow:
        repassado.append("--sem-mlflow")
    if args.dados:
        repassado += ["--dados", args.dados]

    linhas: list[dict] = []
    for nome in args.modelos:
        print("\n" + "-" * 70)
        print(f"  {nome}  (fumaca)")
        print("-" * 70)
        try:
            linhas.append(_comum.executar(ESPECS[nome], repassado))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            print(f"[erro] {nome}: {type(exc).__name__}: {exc}", file=sys.stderr)

    if not linhas:
        print("[erro] nenhum artefato gerado", file=sys.stderr)
        return 1

    tabela = pd.DataFrame(linhas)[
        ["familia", "teste_auc", "teste_logloss", "teste_ks", "teste_brier"]
    ].sort_values("teste_auc", ascending=False)

    print("\n" + "=" * 70)
    print("  artefatos de fumaca gerados")
    print("=" * 70)
    print(tabela.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    campeao = args.campeao or tabela.iloc[0]["familia"]
    artefatos.marcar_campeao(campeao)
    print(f"\ncampeao -> {campeao}")
    print(f"artefatos em {artefatos.DIR_ARTEFATOS}")
    print(
        "\nLEMBRETE: estes numeros sao de fumaca sobre alvo sintetico. "
        "Nao reporte como performance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
