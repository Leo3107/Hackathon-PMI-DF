"""Carga do dataset e particionamento AGRUPADO por municipio.

O ponto que decide o desenho deste modulo: as 12 features municipais (BCB,
IBGE, clima) sao identicas para todas as empresas do mesmo municipio. Com 45
municipios em 3000 linhas, um `train_test_split` aleatorio coloca empresas do
mesmo municipio nos dois lados e o modelo "acerta" o teste porque decorou o
municipio. O AUC sai inflado e o numero nao sobrevive a producao, onde o
municipio do pedido pode nunca ter aparecido no treino.

Por isso todo split aqui e por GRUPO: `StratifiedGroupKFold` agrupando por
`municipio_ibge` e estratificando pelo alvo -- com 8,9% de positivos, um
`GroupKFold` puro pode devolver fold sem positivo nenhum e o AUC viraria NaN.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from . import esquema

RAIZ = esquema.RAIZ
MOCK_CSV = RAIZ / "data" / "mock" / "features_agro_mock.csv"
SEPARADOR = ";"


@dataclass(frozen=True)
class Particao:
    """Treino e teste ja separados, com os grupos de cada lado."""

    X_treino: pd.DataFrame
    y_treino: pd.Series
    g_treino: pd.Series
    X_teste: pd.DataFrame
    y_teste: pd.Series
    g_teste: pd.Series

    def resumo(self) -> dict[str, float]:
        return {
            "n_treino": int(len(self.y_treino)),
            "n_teste": int(len(self.y_teste)),
            "prevalencia_treino": round(float(self.y_treino.mean()), 4),
            "prevalencia_teste": round(float(self.y_teste.mean()), 4),
            "municipios_treino": int(self.g_treino.nunique()),
            "municipios_teste": int(self.g_teste.nunique()),
            # Tem de ser zero. Se nao for, o holdout esta vazando municipio.
            "municipios_em_comum": int(len(set(self.g_treino) & set(self.g_teste))),
        }


def _para_binario(s: pd.Series) -> pd.Series:
    """bool/texto/numero -> 1.0 / 0.0 / NaN.

    O NaN sobrevive de proposito: "nao sei" nao e "nao". Uma flag ausente
    significa que a fonte nao foi carregada para aquele documento, e isso e
    informacao diferente de flag negativa.
    """
    if s.dtype == bool:
        return s.astype("float64")

    mapa = {
        "true": 1.0, "t": 1.0, "sim": 1.0, "yes": 1.0, "1": 1.0, "1.0": 1.0,
        "false": 0.0, "f": 0.0, "nao": 0.0, "não": 0.0, "no": 0.0,
        "0": 0.0, "0.0": 0.0,
    }
    texto = s.astype("string").str.strip().str.lower()
    convertido = texto.map(mapa).astype("float64")

    # Valor numerico que nao casou no mapa (coluna que ja veio 0/1 em float).
    faltando = convertido.isna() & texto.notna()
    if faltando.any():
        numerico = pd.to_numeric(s[faltando], errors="coerce")
        convertido.loc[faltando] = numerico.where(numerico.isna(), numerico > 0)
    return convertido.astype("float64")


def normalizar_quadro(df: pd.DataFrame) -> pd.DataFrame:
    """Coage cada coluna para o tipo do esquema, venha de CSV ou de dict.

    Existe porque as duas fontes de dado discordam na forma: o CSV entrega
    'True'/'False' e '' para nulo, enquanto `build_features` entrega `True` e
    `None`. Depois desta funcao as duas viram a mesma coisa -- e e isso que faz
    o treino e a inferencia verem exatamente o mesmo quadro.
    """
    df = df.copy()

    for col in esquema.COLUNAS_TEXTO:
        if col in df.columns:
            texto = df[col].astype("string").str.strip()
            # dtype='string' no read_csv nao converte '' em NA, e '' e o que o
            # DuckDB devolve para texto vazio.
            df[col] = texto.replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})

    for col in esquema.BOOLEANAS:
        if col in df.columns:
            df[col] = _para_binario(df[col])

    for col in (*esquema.INTEIRAS, *esquema.FLUTUANTES):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    return df


def carregar(
    caminho: str | Path = MOCK_CSV, *, alvo: str = esquema.ALVO
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Le o dataset e devolve (X, y, grupos).

    `X` sai com as colunas de `esquema.features_de_entrada()`, na ordem
    canonica. Coluna do esquema ausente no arquivo entra como NaN em vez de
    levantar: a coleta pode estar com uma fonte a menos e o treino ainda roda.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"dataset nao encontrado em {caminho}. "
            "Gere o mock com `python scripts/gerar_mock.py`."
        )

    bruto = pd.read_csv(
        caminho, sep=SEPARADOR, dtype=esquema.mapa_dtypes(), low_memory=False
    )
    if alvo not in bruto.columns:
        raise KeyError(
            f"coluna-alvo '{alvo}' ausente em {caminho.name}; "
            f"colunas encontradas: {list(bruto.columns)[:8]}..."
        )

    bruto = normalizar_quadro(bruto)

    colunas = esquema.features_de_entrada()
    ausentes = [c for c in colunas if c not in bruto.columns]
    for col in ausentes:
        bruto[col] = np.nan
    if ausentes:
        print(
            f"[dados] aviso: {len(ausentes)} coluna(s) do esquema ausentes no "
            f"arquivo, preenchidas com NaN: {ausentes}"
        )

    X = bruto[colunas]
    y = pd.to_numeric(bruto[alvo], errors="coerce").fillna(0).astype(int)

    if esquema.GRUPO in bruto.columns:
        grupos = bruto[esquema.GRUPO].astype("string").fillna("SEM_MUNICIPIO")
    else:
        # Sem municipio nao ha vazamento municipal a evitar: cada linha e o seu
        # proprio grupo e o StratifiedGroupKFold degenera para estratificado.
        grupos = pd.Series(bruto.index.astype(str), index=bruto.index)

    return X, y, grupos


def separar_treino_teste(
    X: pd.DataFrame,
    y: pd.Series,
    grupos: pd.Series,
    *,
    fracao_teste: float = 0.2,
    semente: int = 42,
) -> Particao:
    """Holdout por municipio: nenhum municipio aparece nos dois lados.

    Implementado como "pegue o primeiro fold de um StratifiedGroupKFold" porque
    e a unica rotina do sklearn que respeita grupo E estrato ao mesmo tempo --
    `GroupShuffleSplit` ignora o estrato e, com 8,9% de positivos, entrega
    holdout com prevalencia bem diferente da do treino.
    """
    n_splits = max(2, round(1 / fracao_teste))
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=semente)
    idx_treino, idx_teste = next(cv.split(X, y, groups=grupos))
    return Particao(
        X_treino=X.iloc[idx_treino].reset_index(drop=True),
        y_treino=y.iloc[idx_treino].reset_index(drop=True),
        g_treino=grupos.iloc[idx_treino].reset_index(drop=True),
        X_teste=X.iloc[idx_teste].reset_index(drop=True),
        y_teste=y.iloc[idx_teste].reset_index(drop=True),
        g_teste=grupos.iloc[idx_teste].reset_index(drop=True),
    )


def cv_agrupado(n_splits: int = 5, semente: int = 42) -> StratifiedGroupKFold:
    """O CV que todos os scripts de treino usam. Um lugar so para mudar."""
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=semente)


def quadro_de_registros(registros: dict | list[dict]) -> pd.DataFrame:
    """dict(s) de `coleta.features.build_features` -> quadro pronto pro pipeline.

    Caminho de entrada da inferencia. Campo que a coleta nao devolveu entra como
    NaN, que e exatamente o que o pipeline espera: ele foi treinado com o mesmo
    padrao de ausencia.
    """
    if isinstance(registros, dict):
        registros = [registros]
    registros = list(registros)
    if not registros:
        raise ValueError("nenhum registro para pontuar")

    colunas = esquema.features_de_entrada()
    df = pd.DataFrame(registros)
    for col in colunas:
        if col not in df.columns:
            df[col] = np.nan
    return normalizar_quadro(df)[colunas]


__all__ = [
    "MOCK_CSV",
    "Particao",
    "carregar",
    "cv_agrupado",
    "normalizar_quadro",
    "quadro_de_registros",
    "separar_treino_teste",
]
