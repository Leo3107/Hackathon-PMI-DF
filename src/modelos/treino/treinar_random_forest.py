"""Random forest com criterio de entropia cruzada.

    python -m src.modelos.treino.treinar_random_forest
    python -m src.modelos.treino.treinar_random_forest --folhas-min 10 --arvores 1000

`criterion='log_loss'` em vez do `gini` padrao: a divisao passa a ser escolhida
pela mesma perda que o problema pede (entropia cruzada binaria), o que alinha o
criterio de split a metrica de avaliacao. Custa um pouco mais de tempo de treino
e nao muda a API.

`min_samples_leaf` alto (20) e a regra que mais importa aqui: com 2400 linhas de
treino e 214 positivos, folha de 1 amostra memoriza o ruido do municipio. A
random forest e tambem o modelo menos sensivel a ausencia estruturada do dado
-- ela ve a mediana imputada mais os quatro indicadores `falta_*`, e distingue
"sem divida" de "sem a fonte da divida" com uma divisao binaria.
"""
from __future__ import annotations

import argparse

from sklearn.ensemble import RandomForestClassifier

from . import _comum


def argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arvores", type=int, default=600)
    p.add_argument(
        "--profundidade-max", type=int, default=None,
        help="None deixa crescer, controlado por --folhas-min",
    )
    p.add_argument(
        "--folhas-min", type=int, default=20,
        help="minimo de amostras por folha; o freio principal do overfit",
    )
    p.add_argument("--divisao-min", type=int, default=10)
    p.add_argument(
        "--features-max", default="sqrt",
        help="'sqrt', 'log2', fracao (0.3) ou inteiro",
    )


def _features_max(valor: str):
    if valor in ("sqrt", "log2", "None", "none"):
        return None if valor.lower() == "none" else valor
    try:
        numero = float(valor)
    except ValueError:
        return "sqrt"
    return int(numero) if numero.is_integer() and numero > 1 else numero


def construir(args: argparse.Namespace, prevalencia: float) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=80 if args.rapido else args.arvores,
        criterion="log_loss",  # a perda pedida, aplicada na escolha do split
        max_depth=args.profundidade_max,
        min_samples_leaf=args.folhas_min,
        min_samples_split=args.divisao_min,
        max_features=_features_max(str(args.features_max)),
        # `balanced_subsample` repondera DENTRO de cada bootstrap, que e o
        # correto numa floresta: `balanced` usa a proporcao global e ignora que
        # cada arvore ve uma amostra diferente.
        class_weight="balanced_subsample" if args.balancear else None,
        bootstrap=True,
        oob_score=False,  # o CV agrupado ja cobre isso, e o OOB ignora o grupo
        n_jobs=-1,
        random_state=args.semente,
    )


ESPEC = _comum.Especificacao(
    nome="random_forest",
    descricao="Random forest com criterion='log_loss' e folha minima de 20",
    construir=construir,
    nan_nativo=False,
    escalar=False,  # arvore nao liga para escala
    argumentos=argumentos,
)


if __name__ == "__main__":
    _comum.executar(ESPEC)
