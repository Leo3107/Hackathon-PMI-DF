"""Inferencia: o ponto de entrada da API.

Uso na API Flask (o `lru_cache` garante UMA carga por processo, nao uma por
requisicao -- carregar um joblib a cada chamada e o jeito mais facil de fazer um
endpoint de 5ms levar 400ms):

    from coleta.features import build_features
    from src.modelos.inferencia import scorer_padrao

    @app.get("/api/v1/score/<documento>")
    def score(documento):
        features = build_features(documento, con=cursor)
        return jsonify(scorer_padrao().pontuar(features))

Em lote, numa chamada so (vetorizado, nao um laco de `pontuar`):

    scorer_padrao().pontuar([features_a, features_b, ...])

Tres garantias que este modulo oferece e que a API pode assumir:

1. **Ordem e completude nao importam.** O dicionario de `build_features` pode
   vir com as chaves em qualquer ordem, com campos a mais (ignorados) ou a
   menos (viram NaN, que e o que o modelo viu no treino). A reindexacao usa
   `bundle.colunas_de_entrada`, gravada no artefato no momento do treino.

2. **Nenhuma transformacao fica de fora do artefato.** Log1p, razoes, cap de
   autuacoes, indicadores de bloco ausente e one-hot estao todos dentro do
   `Pipeline` serializado. A API nao repete -- nem pode repetir -- uma linha de
   feature engineering.

3. **Pontuar nunca levanta por dado faltando.** Um CNPJ cuja coleta devolveu 39
   campos nulos recebe score; e o que o modelo aprendeu a dizer sobre um CNPJ
   sobre o qual nao se sabe nada. O que levanta e artefato ausente ou corrompido,
   que e problema de deploy e tem de aparecer no boot, nao na requisicao.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from . import artefatos, dados, esquema

# Score inteiro em 0..1000, monotono na probabilidade: MAIOR = MAIS RISCO.
# Deliberadamente invertido em relacao ao score de bureau (onde 1000 e o melhor
# pagador), porque o consumidor deste numero e uma politica de risco e ler "953
# = critico" e menos sujeito a erro que "47 = critico".
ESCALA_SCORE = 1000


class Scorer:
    """Um bundle carregado, pronto para pontuar."""

    def __init__(self, bundle: artefatos.BundleModelo) -> None:
        self.bundle = bundle
        self._colunas = list(bundle.colunas_de_entrada)

    # ------------------------------------------------------------ carga ------
    @classmethod
    def carregar(
        cls, nome: str | None = None, destino: Path | None = None
    ) -> "Scorer":
        """Carrega um modelo pelo nome, ou o campeao de `campeao.json`."""
        return cls(artefatos.carregar(nome, destino))

    # ------------------------------------------------------------ metadados --
    @property
    def nome(self) -> str:
        return self.bundle.nome

    def info(self) -> dict[str, Any]:
        """Metadados do modelo em producao. Bom para expor num `/saude`."""
        return self.bundle.resumo()

    # ------------------------------------------------------------- pontuar ---
    def probabilidades(self, registros: dict | Iterable[dict]) -> np.ndarray:
        """Apenas o vetor de probabilidades. Caminho quente, sem formatacao."""
        quadro = self.preparar(registros)
        return self.bundle.pipeline.predict_proba(quadro)[:, 1]

    def preparar(self, registros: dict | Iterable[dict]) -> pd.DataFrame:
        """dict(s) -> quadro na ordem que o pipeline espera."""
        quadro = dados.quadro_de_registros(registros)
        faltando = [c for c in self._colunas if c not in quadro.columns]
        for coluna in faltando:
            quadro[coluna] = np.nan
        return quadro[self._colunas]

    def pontuar(
        self,
        registros: dict | Iterable[dict],
        *,
        com_sinais: bool = True,
        com_contribuicoes: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Pontua um registro (devolve dict) ou varios (devolve lista).

        `com_sinais` anexa a leitura descritiva dos campos de risco observados.
        `com_contribuicoes` anexa a decomposicao coeficiente x valor, e so
        funciona em modelo linear -- nos boosters seria preciso SHAP, que nao
        esta nas dependencias de producao de proposito (pesa e e lento para um
        endpoint sincrono).
        """
        unico = isinstance(registros, dict)
        lista = [registros] if unico else list(registros)

        quadro = self.preparar(lista)
        probas = self.bundle.pipeline.predict_proba(quadro)[:, 1]

        contribuicoes = (
            self._contribuicoes(quadro) if com_contribuicoes else [None] * len(lista)
        )

        saidas = []
        for i, (registro, proba) in enumerate(zip(lista, probas)):
            proba = float(proba)
            saida: dict[str, Any] = {
                "documento": registro.get("documento"),
                "probabilidade_inadimplencia": round(proba, 6),
                "score_risco": int(round(proba * ESCALA_SCORE)),
                "faixa_risco": self.bundle.faixa(proba),
                "modelo": self.bundle.nome,
                "modelo_treinado_em": self.bundle.treinado_em,
                "alvo": self.bundle.alvo,
            }
            if com_sinais:
                saida["sinais_observados"] = sinais_de_risco(registro)
                saida["fontes_ausentes"] = _blocos_ausentes(registro)
            if contribuicoes[i] is not None:
                saida["contribuicoes"] = contribuicoes[i]
            saidas.append(saida)

        return saidas[0] if unico else saidas

    # -------------------------------------------------------- contribuicoes --
    def _contribuicoes(
        self, quadro: pd.DataFrame, topo: int = 8
    ) -> list[dict[str, float] | None]:
        """coeficiente x valor por linha. Exato em modelo linear, None no resto."""
        from . import preparo

        pipeline = self.bundle.pipeline
        estimador = getattr(pipeline, "steps", [(None, None)])[-1][1]
        if estimador is None or not hasattr(estimador, "coef_"):
            return [None] * len(quadro)

        try:
            matriz = pipeline[:-1].transform(quadro)
            coeficientes = np.asarray(estimador.coef_, dtype=float).ravel()
            nomes = preparo.nomes_de_features(pipeline) or [
                f"f{i}" for i in range(matriz.shape[1])
            ]
        except Exception:  # noqa: BLE001 - explicabilidade nunca quebra o score
            return [None] * len(quadro)

        saida: list[dict[str, float] | None] = []
        for linha in np.asarray(matriz, dtype=float):
            efeito = linha * coeficientes
            ordem = np.argsort(np.abs(efeito))[::-1][:topo]
            saida.append({nomes[j]: round(float(efeito[j]), 4) for j in ordem})
        return saida


# ------------------------------------------------------------------ sinais ----

# Leitura DESCRITIVA do dado cru: "o que ha no cadastro deste CNPJ". Nao e
# atribuicao causal do score -- o modelo pode ter pesado outra coisa. Serve para
# o analista ver, na mesma resposta, o fato por tras do numero.
_REGRAS: tuple[tuple[str, str], ...] = (
    ("divida_ativa_total", "divida ativa na PGFN"),
    ("divida_ativa_ajuizada", "divida ativa ja ajuizada"),
    ("flag_divida_previdenciaria", "debito previdenciario"),
    ("flag_divida_fgts", "debito de FGTS"),
    ("flag_situacao_irregular", "situacao cadastral irregular na Receita"),
    ("n_autos_infracao", "auto de infracao do IBAMA"),
    ("flag_embargo_ativo", "embargo ambiental ativo"),
    ("n_empresas_do_socio_com_divida_ativa", "socio com outra empresa em divida ativa"),
    ("n_empresas_do_socio_inaptas", "socio com outra empresa inapta"),
    ("n_protestos_ativos", "protesto ativo em cartorio"),
)


def _ausente(valor: Any) -> bool:
    """Ausente e `None` E `NaN`, nao so `None`.

    As duas formas chegam por caminhos diferentes e os dois caminhos sao reais:
    `build_features` devolve `None`, enquanto um registro que veio de um
    DataFrame (CLI `--csv`, escoragem de carteira em lote) traz `float('nan')`,
    porque pandas nao guarda `None` em coluna float. Testar so `is None` fazia
    `fontes_ausentes` voltar vazio para um registro de CSV com o bloco de
    protestos inteiro em branco.
    """
    if valor is None:
        return True
    if isinstance(valor, float):
        return math.isnan(valor)
    # `pd.isna` e o unico teste que cobre os quatro sabores de ausente que
    # circulam aqui: None, float('nan'), np.nan e pd.NA. Tentar `valor != valor`
    # a mao nao serve -- `pd.NA != pd.NA` devolve pd.NA e `bool(pd.NA)` levanta
    # TypeError, que um except amplo transformaria em "presente".
    try:
        resultado = pd.isna(valor)
    except (TypeError, ValueError):
        return False
    # Lista ou array caem aqui: nao sao valor ausente, sao valor composto.
    return bool(resultado) if isinstance(resultado, (bool, np.bool_)) else False


def sinais_de_risco(registro: dict) -> list[str]:
    """Fatos de risco presentes no registro, em texto. Vazio = nada encontrado."""
    sinais: list[str] = []
    for campo, texto in _REGRAS:
        valor = registro.get(campo)
        if _ausente(valor):
            continue
        if isinstance(valor, bool):
            if valor:
                sinais.append(texto)
            continue
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            continue
        if numero > 0:
            sinais.append(texto)

    # Quebra de safra: desvio negativo de produtividade com anomalia de chuva na
    # fase critica e o caso agro classico -- o produtor nao colhe e nao paga.
    desvio = registro.get("desvio_produtividade_vs_media_5a")
    anomalia = registro.get("anomalia_na_fase_critica")
    if not _ausente(desvio) and float(desvio) <= -0.15:
        sinais.append("produtividade municipal abaixo da media de 5 anos")
    if not _ausente(anomalia) and float(anomalia) <= -0.30:
        sinais.append("deficit de chuva na fase critica da cultura")
    return sinais


def _blocos_ausentes(registro: dict) -> list[str]:
    """Blocos de fonte que nao chegaram. Qualifica a confianca no score."""
    return [
        bloco
        for bloco, colunas in esquema.BLOCOS_AUSENCIA.items()
        if all(_ausente(registro.get(c)) for c in colunas)
    ]


# ------------------------------------------------------------------ cache -----

@lru_cache(maxsize=4)
def scorer_padrao(nome: str | None = None) -> Scorer:
    """Scorer carregado uma vez por processo. Use este na API.

    Chame no boot da aplicacao, nao na primeira requisicao: carregar aqui faz o
    processo falhar no start quando o artefato nao foi publicado, em vez de
    devolver 500 para o primeiro cliente.
    """
    return Scorer.carregar(nome)


# -------------------------------------------------------------------- CLI -----

def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Pontua registros de features com um modelo salvo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Nao obrigatorio: `--info` nao le registro nenhum.
    fonte = p.add_mutually_exclusive_group(required=False)
    fonte.add_argument("--json", help="arquivo JSON: um objeto ou uma lista deles")
    fonte.add_argument("--csv", help="CSV com o mesmo esquema do mock (sep ';')")
    fonte.add_argument(
        "--stdin", action="store_true", help="le o JSON da entrada padrao"
    )
    p.add_argument("--modelo", default=None, help="nome do artefato; padrao: campeao")
    p.add_argument("--limite", type=int, default=10, help="linhas a pontuar do CSV")
    p.add_argument("--contribuicoes", action="store_true")
    p.add_argument("--info", action="store_true", help="imprime metadados e sai")
    args = p.parse_args(argv)

    try:
        scorer = Scorer.carregar(args.modelo)
    except (FileNotFoundError, TypeError) as exc:
        print(f"[erro] {exc}", file=sys.stderr)
        return 1

    if args.info:
        print(json.dumps(scorer.info(), ensure_ascii=False, indent=2))
        return 0

    if not (args.json or args.csv or args.stdin):
        p.error("informe --json, --csv ou --stdin (ou use --info)")

    if args.csv:
        bruto = pd.read_csv(
            args.csv, sep=";", dtype=esquema.mapa_dtypes(), low_memory=False
        ).head(args.limite)
        registros = bruto.where(bruto.notna(), None).to_dict("records")
    else:
        texto = sys.stdin.read() if args.stdin else Path(args.json).read_text("utf-8")
        carregado = json.loads(texto)
        registros = carregado if isinstance(carregado, list) else [carregado]

    resultado = scorer.pontuar(registros, com_contribuicoes=args.contribuicoes)
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
    return 0


__all__ = ["ESCALA_SCORE", "Scorer", "scorer_padrao", "sinais_de_risco"]


if __name__ == "__main__":
    raise SystemExit(_main())
