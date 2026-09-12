"""Regressao logistica -- a linha de base que tem de ser batida.

    python -m src.modelos.treino.treinar_regressao_logistica
    python -m src.modelos.treino.treinar_regressao_logistica --penalidade elasticnet

Por que ela entra num comparativo com tres modelos de arvore: a logistica
minimiza entropia cruzada binaria por construcao, devolve probabilidade
naturalmente calibrada e e o unico dos quatro em que o coeficiente de cada
feature e auditavel -- em credito, "por que esse CNPJ foi recusado?" e uma
pergunta com consequencia regulatoria.

E, com `alvo_sintetico`, ela tem um papel extra: o alvo do mock vem de uma
logistica de coeficientes conhecidos, entao os coeficientes estimados AQUI
devem reproduzir os sinais de `alvo_coeficientes.json`. Se nao reproduzem, o
defeito esta no pre-processamento -- e o harness reporta essa conferencia na
secao "recuperacao dos sinais do alvo sintetico".
"""
from __future__ import annotations

import argparse

from sklearn.linear_model import LogisticRegression

from . import _comum


def argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--C", type=float, default=0.5, dest="C",
        help="inverso da regularizacao; menor = mais encolhimento",
    )
    p.add_argument("--penalidade", choices=("l2", "l1", "elasticnet"), default="l2")
    p.add_argument(
        "--razao-l1", type=float, default=0.5,
        help="peso do l1 quando penalidade=elasticnet",
    )
    p.add_argument("--max-iter", type=int, default=4000)


def construir(args: argparse.Namespace, prevalencia: float) -> LogisticRegression:
    # `saga` e o unico solver que aceita l1 e elasticnet; para l2 puro, `lbfgs`
    # converge em menos iteracoes. Escolher pelo caso evita 2000 iteracoes
    # desnecessarias no caminho padrao.
    solver = "lbfgs" if args.penalidade == "l2" else "saga"
    return LogisticRegression(
        C=args.C,
        penalty=args.penalidade,
        l1_ratio=args.razao_l1 if args.penalidade == "elasticnet" else None,
        solver=solver,
        max_iter=400 if args.rapido else args.max_iter,
        # `balanced` multiplica a verossimilhanca dos positivos por ~10 com 8,9%
        # de prevalencia. Melhora recall, estraga a calibracao: o modelo passa a
        # prever a probabilidade de um mundo com 50% de inadimplencia.
        class_weight="balanced" if args.balancear else None,
        random_state=args.semente,
        n_jobs=None,
    )


ESPEC = _comum.Especificacao(
    nome="regressao_logistica",
    descricao="Regressao logistica l2 sobre features padronizadas (linha de base)",
    construir=construir,
    nan_nativo=False,  # modelo linear nao engole NaN: imputa mediana
    escalar=True,      # sem padronizar, o l2 pune so as colunas de escala grande
    argumentos=argumentos,
)


if __name__ == "__main__":
    _comum.executar(ESPEC)
