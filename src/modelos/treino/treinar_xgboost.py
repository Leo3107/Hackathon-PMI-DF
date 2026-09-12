"""XGBoost: `binary:logistic` com AUC como metrica de avaliacao.

    python -m src.modelos.treino.treinar_xgboost
    python -m src.modelos.treino.treinar_xgboost --taxa 0.03 --arvores 1200

`objective='binary:logistic'` E a entropia cruzada binaria -- o gradiente que o
booster desce e exatamente o da log-loss. `eval_metric='auc'` nao muda o treino,
so o que o XGBoost reporta; a selecao entre modelos acontece no CV agrupado do
harness, que e onde o AUC nao esta contaminado pelo municipio.

O que este modelo faz melhor que os outros tres: ele recebe os NaN intactos
(`nan_nativo=True`, sem imputador no pipeline) e aprende, no-a-no, para que lado
manda um valor ausente. Com 42% de nulo no bloco de clima e 88% no de protestos,
isso deixa de ser detalhe -- a ausencia aqui e sinal, nao lacuna.

Sem early stopping de proposito: dentro de um `Pipeline` avaliado por CV
agrupado, o conjunto de validacao do early stopping sairia do mesmo municipio do
treino e pararia cedo pelo motivo errado. O controle e taxa baixa + muitas
arvores + regularizacao, com o numero de arvores calibrado pelo desvio do CV.
"""
from __future__ import annotations

import argparse

from xgboost import XGBClassifier

from . import _comum


def argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arvores", type=int, default=700)
    p.add_argument("--taxa", type=float, default=0.05, help="learning_rate")
    p.add_argument("--profundidade", type=int, default=4)
    p.add_argument("--subamostra", type=float, default=0.8)
    p.add_argument("--colunas-por-arvore", type=float, default=0.7)
    p.add_argument(
        "--peso-min-folha", type=float, default=5.0,
        help="min_child_weight; maior = folha mais conservadora",
    )
    p.add_argument("--l2", type=float, default=2.0, help="reg_lambda")
    p.add_argument("--l1", type=float, default=0.0, help="reg_alpha")
    p.add_argument("--gama", type=float, default=0.0, help="ganho minimo p/ dividir")


def construir(args: argparse.Namespace, prevalencia: float) -> XGBClassifier:
    return XGBClassifier(
        objective="binary:logistic",  # = entropia cruzada binaria
        eval_metric="auc",
        n_estimators=120 if args.rapido else args.arvores,
        learning_rate=0.2 if args.rapido else args.taxa,
        max_depth=args.profundidade,
        subsample=args.subamostra,
        colsample_bytree=args.colunas_por_arvore,
        min_child_weight=args.peso_min_folha,
        reg_lambda=args.l2,
        reg_alpha=args.l1,
        gamma=args.gama,
        # `hist` e o unico tree_method que aceita NaN e e rapido em dado tabular
        # deste tamanho; `missing=nan` torna explicito o que ja e o padrao.
        tree_method="hist",
        missing=float("nan"),
        scale_pos_weight=_comum.peso_positivo(prevalencia) if args.balancear else 1.0,
        n_jobs=-1,
        random_state=args.semente,
        verbosity=0,
    )


ESPEC = _comum.Especificacao(
    nome="xgboost",
    descricao="XGBoost hist, binary:logistic, NaN tratado nativamente",
    construir=construir,
    nan_nativo=True,  # sem imputador: a ausencia em bloco vira sinal no split
    escalar=False,
    argumentos=argumentos,
)


if __name__ == "__main__":
    _comum.executar(ESPEC)
