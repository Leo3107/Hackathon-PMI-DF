"""Scripts de treino. Cada modelo e um modulo executavel.

    python -m src.modelos.treino.treinar_regressao_logistica
    python -m src.modelos.treino.treinar_random_forest
    python -m src.modelos.treino.treinar_xgboost
    python -m src.modelos.treino.treinar_lightgbm

    python -m src.modelos.treino.treinar_todos --promover-melhor
    python -m src.modelos.treino.salvar_modelos          # artefatos de fumaca

Todos compartilham `_comum.executar`, entao todos usam o mesmo split agrupado,
o mesmo CV, as mesmas metricas e o mesmo formato de artefato. O que cada script
define e so o estimador e a grade de hiperparametros -- que e exatamente a
diferenca que a comparacao entre eles deve isolar.
"""
from __future__ import annotations

__all__ = ["_comum"]
