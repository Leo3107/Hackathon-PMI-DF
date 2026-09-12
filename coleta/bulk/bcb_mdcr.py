"""BCB - Matriz de Dados do Credito Rural (fonte 4).

Usa a API OData do SICOR (o dataset nao publica CSV: os unicos recursos de
dados sao os endpoints da API). Dois recursos interessam:

- CusteioInvestimentoComercialIndustrialSemFiltros: quantidade e valor de
  contratos por municipio, com area financiada.
- CusteioMunicipioProduto: valor de custeio por municipio e produto, com
  `cdTipoSeguro` -- a informacao mais proxima de Proagro publicada na matriz.
  Nao ha recurso de acionamentos de Proagro na MDCR.

A chave e o codigo IBGE do municipio: e dado contextual/regional, nunca
individual.

LIMITACAO DO SERVICO (verificada em 2026-09, nao e bug deste codigo):
o deployment Olinda do SICOR aceita apenas `$top` e `$format`.
`$skip` devolve 500 para qualquer valor, `$filter` devolve 400/500 e
`$top` acima de ~5.000 estoura o gateway com 504. Ou seja, a matriz completa
nao e paginavel hoje. O coletor detecta isso em runtime: se `$skip` funcionar,
pagina normalmente; se nao, carrega uma amostra limitada por `$top` e registra
um aviso explicito, deixando as features do BCB parciais em vez de derrubar a
carga inteira.
"""
from __future__ import annotations

from typing import Callable

import duckdb
import polars as pl

from .. import config, http
from ..logging_setup import etapa, get_logger, log_evento
from ..warehouse import apagar_particao, registrar_ingestao

log = get_logger("bulk.bcb")

FONTE = "bcb_mdcr"


def _para_int(valor) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _para_float(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _txt(valor) -> str | None:
    if valor is None:
        return None
    limpo = str(valor).strip().strip('"')
    return limpo or None


def _normaliza_contratos(linhas: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "cod_ibge": _txt(r.get("codMunicIbge")),
                "municipio": _txt(r.get("Municipio")),
                "uf": _txt(r.get("nomeUF")),
                "ano": _para_int(r.get("AnoEmissao")),
                "mes": _para_int(r.get("MesEmissao")),
                "atividade": _txt(r.get("Atividade")),
                "qtd_custeio": _para_int(r.get("QtdCusteio")) or 0,
                "vl_custeio": _para_float(r.get("VlCusteio")) or 0.0,
                "qtd_investimento": _para_int(r.get("QtdInvestimento")) or 0,
                "vl_investimento": _para_float(r.get("VlInvestimento")) or 0.0,
                "qtd_comercializacao": _para_int(r.get("QtdComercializacao")) or 0,
                "vl_comercializacao": _para_float(r.get("VlComercializacao")) or 0.0,
                "qtd_industrializacao": _para_int(r.get("QtdIndustrializacao")) or 0,
                "vl_industrializacao": _para_float(r.get("VlIndustrializacao")) or 0.0,
                "area_custeio": _para_float(r.get("AreaCusteio")) or 0.0,
                "area_investimento": _para_float(r.get("AreaInvestimento")) or 0.0,
            }
            for r in linhas
        ],
        infer_schema_length=None,
    )


def _normaliza_produto(linhas: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "cod_ibge": _txt(r.get("codIbge")),
                "municipio": _txt(r.get("Municipio")),
                "ano": _para_int(r.get("AnoEmissao")),
                "mes": _para_int(r.get("MesEmissao")),
                "nome_produto": _txt(r.get("nomeProduto")),
                "cd_produto": _txt(r.get("cdProduto")),
                "cd_tipo_seguro": _txt(r.get("cdTipoSeguro")),
                "vl_custeio": _para_float(r.get("VlCusteio")) or 0.0,
                "area_custeio": _para_float(r.get("AreaCusteio")) or 0.0,
            }
            for r in linhas
        ],
        infer_schema_length=None,
    )


def _suporta_skip(url: str) -> bool:
    """Descobre se o servico aceita `$skip` sem derrubar a coleta."""
    try:
        http.get_json(url, params={"$top": 1, "$skip": 1, "$format": "json"})
        return True
    except Exception as exc:  # noqa: BLE001 - a ausencia de $skip e esperada
        log_evento(log, "bcb.sem_skip", url=url, erro=str(exc)[:200])
        return False


def _inserir(con: duckdb.DuckDBPyConnection, tabela: str, df: pl.DataFrame) -> int:
    if df.is_empty():
        return 0
    con.register("_bcb_tmp", df)
    try:
        con.execute(f"INSERT INTO {tabela} BY NAME SELECT * FROM _bcb_tmp")
    finally:
        con.unregister("_bcb_tmp")
    return df.height


def _carregar_recurso(
    con: duckdb.DuckDBPyConnection,
    recurso: str,
    tabela: str,
    normalizar: Callable[[list[dict]], pl.DataFrame],
    ano_inicial: int,
    top: int,
) -> int:
    url = f"{config.BCB_SICOR_ODATA}/{recurso}"
    apagar_particao(con, tabela)
    total = 0

    if _suporta_skip(url):
        for pagina in http.paginar_odata(url, page_size=top):
            df = normalizar(pagina).filter(pl.col("ano") >= ano_inicial)
            total += _inserir(con, tabela, df)
            log_evento(log, "bcb.progresso", tabela=tabela, linhas=total)
        return total

    # Caminho degradado: uma unica janela limitada por $top.
    payload = http.get_json(url, params={"$top": top, "$format": "json"})
    df = normalizar(payload.get("value", [])).filter(pl.col("ano") >= ano_inicial)
    total = _inserir(con, tabela, df)
    log_evento(
        log,
        "bcb.carga_parcial",
        tabela=tabela,
        linhas=total,
        aviso=(
            "servico OData do SICOR nao aceita $skip/$filter; dados municipais "
            "carregados apenas ate o limite de $top"
        ),
    )
    return total


def executar(
    con: duckdb.DuckDBPyConnection,
    *,
    ano_inicial: int | None = None,
    top: int | None = None,
) -> int:
    ano_inicial = ano_inicial or config.BCB_ANO_INICIAL
    top = top or config.BCB_PAGE_SIZE
    total = 0
    for recurso, tabela, normalizar, nome in (
        (config.BCB_RECURSO_CONTRATOS, "bcb_mdcr", _normaliza_contratos, "contratos"),
        (
            config.BCB_RECURSO_CUSTEIO_PRODUTO,
            "bcb_mdcr_produto",
            _normaliza_produto,
            "custeio_produto",
        ),
    ):
        with etapa(log, f"bcb.{nome}", ano_inicial=ano_inicial, top=top) as ctx:
            ctx["linhas"] = _carregar_recurso(
                con, recurso, tabela, normalizar, ano_inicial, top
            )
            registrar_ingestao(con, FONTE, str(ano_inicial), tabela, ctx["linhas"])
            total += ctx["linhas"]
    return total
