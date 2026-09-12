"""Camada de modelagem: score de risco de inadimplencia agro.

Tres modulos importam em producao (`esquema`, `preparo`, `inferencia`); o resto
existe para treinar. A fronteira e deliberada: o servidor da API carrega um
bundle com `joblib` e precisa apenas que as CLASSES do pipeline estejam
importaveis -- nao precisa de mlflow nem de matplotlib.

    from src.modelos.inferencia import Scorer
    scorer = Scorer.carregar()          # pega o campeao em src/modelos/artefatos
    scorer.pontuar(build_features(doc)) # dict da coleta -> score
"""
from __future__ import annotations

__all__ = ["esquema", "preparo", "dados", "avaliacao", "inferencia"]
