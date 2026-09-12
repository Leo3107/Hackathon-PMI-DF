"""LightGBM: objetivo `binary`, metrica `auc`.

    python -m src.modelos.treino.treinar_lightgbm
    python -m src.modelos.treino.treinar_lightgbm --folhas 15 --amostras-min-folha 40

`objective='binary'` e a mesma entropia cruzada binaria do XGBoost; o que muda e
o crescimento da arvore, que aqui e por FOLHA (leaf-wise) e nao por nivel. Em
3000 linhas isso corta tempo de treino, e cobra um cuidado: leaf-wise aprofunda
onde o ganho e maior e, com `num_leaves` alto, encontra folhas com tres empresas
do mesmo municipio. Os padroes deste arquivo sao deliberadamente conservadores
-- 31 folhas, 30 amostras por folha -- porque 2400 linhas de treino com 214
positivos nao sustentam mais que isso.

Como o XGBoost, recebe os NaN intactos e decide o lado do ausente em cada no.
"""
from __future__ import annotations

import argparse

from lightgbm import LGBMClassifier

from . import _comum


def argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arvores", type=int, default=700)
    p.add_argument("--taxa", type=float, default=0.05, help="learning_rate")
    p.add_argument(
        "--folhas", type=int, default=31,
        help="num_leaves; o parametro de capacidade no crescimento leaf-wise",
    )
    p.add_argument("--amostras-min-folha", type=int, default=30)
    p.add_argument("--subamostra", type=float, default=0.8)
    p.add_argument("--freq-subamostra", type=int, default=1)
    p.add_argument("--colunas-por-arvore", type=float, default=0.7)
    p.add_argument("--l2", type=float, default=2.0, help="reg_lambda")
    p.add_argument("--l1", type=float, default=0.0, help="reg_alpha")


def construir(args: argparse.Namespace, prevalencia: float) -> LGBMClassifier:
    return LGBMClassifier(
        objective="binary",  # = entropia cruzada binaria
        metric="auc",
        n_estimators=120 if args.rapido else args.arvores,
        learning_rate=0.2 if args.rapido else args.taxa,
        num_leaves=15 if args.rapido else args.folhas,
        min_child_samples=args.amostras_min_folha,
        subsample=args.subamostra,
        # LightGBM ignora `subsample` se `subsample_freq` ficar em 0. Erro comum:
        # o parametro aparece no log, parece aplicado, e nao e.
        subsample_freq=args.freq_subamostra,
        colsample_bytree=args.colunas_por_arvore,
        reg_lambda=args.l2,
        reg_alpha=args.l1,
        scale_pos_weight=_comum.peso_positivo(prevalencia) if args.balancear else 1.0,
        n_jobs=-1,
        random_state=args.semente,
        verbose=-1,  # silencia o aviso de "no further splits with positive gain"
    )


ESPEC = _comum.Especificacao(
    nome="lightgbm",
    descricao="LightGBM leaf-wise, objective=binary, NaN tratado nativamente",
    construir=construir,
    nan_nativo=True,
    escalar=False,
    argumentos=argumentos,
)


if __name__ == "__main__":
    _comum.executar(ESPEC)
