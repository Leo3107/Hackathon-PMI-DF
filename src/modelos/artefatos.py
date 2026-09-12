"""Serializacao do modelo: o contrato entre o treino e a API.

Um `.joblib` aqui nao guarda so o estimador. Guarda o pipeline INTEIRO (da
coluna crua da coleta ate a probabilidade) mais os metadados sem os quais a
inferencia nao e reproduzivel:

- `colunas_de_entrada`: a ordem canonica que o pipeline espera. A inferencia
  reindexa por esta lista, entao a API pode mandar as chaves em qualquer ordem
  e pode mandar campos a mais (ignorados) ou a menos (viram NaN).
- `limiares_faixa`: os cortes de BAIXO/MEDIO/ALTO/CRITICO, calculados nos
  quantis do score de treino. Ficam no artefato, nao no codigo da API: mudar de
  modelo muda a distribuicao do score, e um corte chumbado em `0.3` deixa de
  significar a mesma coisa.
- `metricas` e `versao_libs`: para responder "de onde veio esse numero?" seis
  meses depois sem abrir o MLflow.

Um aviso sobre `joblib`: o pickle guarda o CAMINHO das classes, nao o codigo.
Carregar este bundle exige que `src.modelos.preparo` esteja importavel no
processo da API -- e por isso que `EngenhariaAgro` vive num modulo estavel e
nao numa funcao local do script de treino.
"""
from __future__ import annotations

import datetime as dt
import json
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from . import esquema

DIR_ARTEFATOS = Path(__file__).resolve().parent / "artefatos"
PONTEIRO_CAMPEAO = DIR_ARTEFATOS / "campeao.json"

# Nomes das faixas, do menor para o maior risco.
FAIXAS = ("BAIXO", "MEDIO", "ALTO", "CRITICO")
# Quantis do score de treino que separam as faixas. 0.80/0.95/0.99 coloca ~20%
# da carteira em atencao, 5% em analise manual e 1% em recusa sugerida -- uma
# politica inicial razoavel que a area de credito deve recalibrar com o apetite
# de risco real.
QUANTIS_FAIXA = (0.80, 0.95, 0.99)


@dataclass
class BundleModelo:
    """Pipeline treinado mais tudo que a inferencia precisa saber sobre ele."""

    nome: str
    pipeline: Any
    colunas_de_entrada: list[str] = field(
        default_factory=lambda: list(esquema.features_de_entrada())
    )
    limiares_faixa: list[float] = field(default_factory=list)
    metricas: dict[str, float] = field(default_factory=dict)
    parametros: dict[str, Any] = field(default_factory=dict)
    alvo: str = esquema.ALVO
    prevalencia_treino: float | None = None
    treinado_em: str = field(
        default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds")
    )
    mlflow_run_id: str | None = None
    observacao: str = ""
    versao_libs: dict[str, str] = field(default_factory=dict)
    versao_formato: int = 1

    # --------------------------------------------------------------- faixas --
    def calibrar_faixas(self, proba_treino: np.ndarray) -> None:
        """Define os cortes de faixa nos quantis da distribuicao de treino."""
        p = np.asarray(proba_treino, dtype=float)
        p = p[~np.isnan(p)]
        if p.size == 0:
            self.limiares_faixa = []
            return
        self.limiares_faixa = [
            float(np.quantile(p, q)) for q in QUANTIS_FAIXA
        ]

    def faixa(self, proba: float) -> str:
        """Probabilidade -> rotulo de faixa. Sem limiares calibrados, volta ''."""
        if not self.limiares_faixa:
            return ""
        posicao = int(np.searchsorted(self.limiares_faixa, proba, side="right"))
        return FAIXAS[min(posicao, len(FAIXAS) - 1)]

    # ---------------------------------------------------------------- disco --
    def caminho(self, destino: Path | None = None) -> Path:
        return (destino or DIR_ARTEFATOS) / f"{self.nome}.joblib"

    def salvar(self, destino: Path | None = None, *, campeao: bool = False) -> Path:
        destino = destino or DIR_ARTEFATOS
        destino.mkdir(parents=True, exist_ok=True)
        if not self.versao_libs:
            self.versao_libs = _versoes()

        caminho = self.caminho(destino)
        joblib.dump(self, caminho, compress=3)

        # Espelho legivel: da para inspecionar metrica e faixa sem importar
        # sklearn, o que ajuda no CI e no code review.
        (destino / f"{self.nome}.json").write_text(
            json.dumps(self.resumo(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if campeao:
            marcar_campeao(self.nome, destino)
        return caminho

    def resumo(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "alvo": self.alvo,
            "treinado_em": self.treinado_em,
            "mlflow_run_id": self.mlflow_run_id,
            "prevalencia_treino": self.prevalencia_treino,
            "n_colunas_de_entrada": len(self.colunas_de_entrada),
            "faixas": dict(zip(FAIXAS[1:], self.limiares_faixa)),
            "quantis_faixa": list(QUANTIS_FAIXA),
            "metricas": {
                k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.metricas.items()
            },
            "parametros": _serializavel(self.parametros),
            "observacao": self.observacao,
            "versao_libs": self.versao_libs,
            "versao_formato": self.versao_formato,
        }


def _versoes() -> dict[str, str]:
    import importlib.metadata as meta

    saida = {"python": platform.python_version()}
    for pacote in ("scikit-learn", "xgboost", "lightgbm", "numpy", "pandas", "joblib"):
        try:
            saida[pacote] = meta.version(pacote)
        except meta.PackageNotFoundError:
            continue
    return saida


def _serializavel(valor: Any) -> Any:
    """Deixa o dict de parametros passar pelo json.dumps sem reclamar."""
    if isinstance(valor, dict):
        return {str(k): _serializavel(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_serializavel(v) for v in valor]
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    return str(valor)


# --------------------------------------------------------------- ponteiro ----

def marcar_campeao(nome: str, destino: Path | None = None) -> Path:
    """Aponta `campeao.json` para um modelo.

    A API carrega pelo ponteiro, nao pelo nome: trocar o modelo em producao e
    reescrever um json de duas linhas, sem deploy de codigo.
    """
    destino = destino or DIR_ARTEFATOS
    destino.mkdir(parents=True, exist_ok=True)
    ponteiro = destino / "campeao.json"
    ponteiro.write_text(
        json.dumps(
            {
                "nome": nome,
                "arquivo": f"{nome}.joblib",
                "atualizado_em": dt.datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return ponteiro


def nome_do_campeao(destino: Path | None = None) -> str | None:
    ponteiro = (destino or DIR_ARTEFATOS) / "campeao.json"
    if not ponteiro.exists():
        return None
    try:
        return json.loads(ponteiro.read_text(encoding="utf-8")).get("nome")
    except (json.JSONDecodeError, OSError):
        return None


def listar(destino: Path | None = None) -> list[str]:
    destino = destino or DIR_ARTEFATOS
    if not destino.exists():
        return []
    return sorted(p.stem for p in destino.glob("*.joblib"))


def carregar(nome: str | None = None, destino: Path | None = None) -> BundleModelo:
    """Carrega um bundle pelo nome, ou o campeao quando `nome` e None."""
    destino = destino or DIR_ARTEFATOS
    nome = nome or nome_do_campeao(destino)

    if nome is None:
        disponiveis = listar(destino)
        if not disponiveis:
            raise FileNotFoundError(
                f"nenhum modelo em {destino}. Rode "
                "`python -m src.modelos.treino.treinar_todos` (ou "
                "`salvar_modelos` para gerar artefatos de fumaca)."
            )
        raise FileNotFoundError(
            f"{destino / 'campeao.json'} nao existe. Modelos disponiveis: "
            f"{disponiveis}. Aponte um com "
            "`python -m src.modelos.treino.treinar_todos --promover <nome>`."
        )

    caminho = destino / f"{nome}.joblib"
    if not caminho.exists():
        raise FileNotFoundError(
            f"modelo '{nome}' nao encontrado em {destino}. "
            f"Disponiveis: {listar(destino)}"
        )
    bundle = joblib.load(caminho)
    if not isinstance(bundle, BundleModelo):
        raise TypeError(
            f"{caminho} nao contem um BundleModelo (veio {type(bundle).__name__}); "
            "provavelmente foi salvo por uma versao antiga do treino."
        )
    return bundle


__all__ = [
    "BundleModelo",
    "DIR_ARTEFATOS",
    "FAIXAS",
    "QUANTIS_FAIXA",
    "carregar",
    "listar",
    "marcar_campeao",
    "nome_do_campeao",
]
