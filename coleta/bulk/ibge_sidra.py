"""IBGE - producao agricola municipal via SIDRA (fonte 5).

O IBGE nao publica clima. O que ele publica, e que serve para medir quebra de
safra, e a PAM (Producao Agricola Municipal, tabela 5457, anual) e a LSPA
(estimativas mais recentes). Os codigos de tabela, variavel e classificacao
estao em `config`, nunca embutidos no meio do codigo.

Estrategia de consulta: uma requisicao por (variavel, ano, cultura) cobrindo
todos os municipios (`/n6/all`). Pedir varias variaveis e anos de uma vez
derruba a API do SIDRA; fatiado assim, cada chamada devolve ~5.5 mil linhas em
cerca de 10 segundos.

Este modulo tambem cuida de duas tabelas de apoio de que o resto do projeto
depende:

- `ibge_municipios`: lista oficial de municipios, para traduzir o codigo de
  municipio da Receita (que e proprio da RFB) em codigo IBGE, por nome + UF.
- `municipio_centroide`: centroide aproximado da malha municipal, usado como
  ponto de consulta do clima.
"""
from __future__ import annotations

import duckdb

from .. import config, http
from ..logging_setup import etapa, get_logger, log_evento
from ..warehouse import apagar_particao, registrar_ingestao, tem_dados
from ._common import normalizar_nome

log = get_logger("bulk.ibge")

FONTE = "ibge_sidra"


# ----------------------------------------------------------- municipios -----

def carregar_municipios(con: duckdb.DuckDBPyConnection) -> int:
    dados = http.get_json(config.IBGE_LOCALIDADES_URL)

    def _uf(m: dict) -> dict:
        """A UF aparece em duas hierarquias e qualquer uma pode vir nula."""
        for caminho in (
            ("microrregiao", "mesorregiao", "UF"),
            ("regiao-imediata", "regiao-intermediaria", "UF"),
        ):
            no = m
            for chave in caminho:
                no = (no or {}).get(chave) or {}
            if no:
                return no
        return {}

    linhas = []
    for m in dados:
        uf = _uf(m)
        linhas.append(
            (
                str(m["id"]),
                m["nome"],
                normalizar_nome(m["nome"]),
                uf.get("sigla"),
                (uf.get("regiao") or {}).get("sigla"),
            )
        )
    con.execute("DELETE FROM ibge_municipios")
    con.executemany(
        "INSERT INTO ibge_municipios (cod_ibge, nome, nome_norm, uf, regiao) "
        "VALUES (?,?,?,?,?)",
        linhas,
    )
    return len(linhas)


def centroide(con: duckdb.DuckDBPyConnection, cod_ibge: str) -> tuple[float, float] | None:
    """Centroide aproximado (media do bounding box da malha), com cache."""
    row = con.execute(
        "SELECT latitude, longitude FROM municipio_centroide WHERE cod_ibge = ?",
        [cod_ibge],
    ).fetchone()
    if row:
        return float(row[0]), float(row[1])

    try:
        geo = http.get_json(
            f"{config.IBGE_MALHAS_URL}/{cod_ibge}",
            params={"formato": "application/vnd.geo+json", "qualidade": "minima"},
        )
    except Exception as exc:  # noqa: BLE001 - fonte opcional
        log_evento(log, "ibge.malha_falhou", cod_ibge=cod_ibge, erro=str(exc)[:200])
        return None

    lats: list[float] = []
    lons: list[float] = []

    def _percorrer(coords) -> None:
        if (
            isinstance(coords, list)
            and len(coords) == 2
            and all(isinstance(c, (int, float)) for c in coords)
        ):
            lons.append(float(coords[0]))
            lats.append(float(coords[1]))
            return
        if isinstance(coords, list):
            for item in coords:
                _percorrer(item)

    for feature in geo.get("features", []):
        _percorrer(feature.get("geometry", {}).get("coordinates", []))
    if not lats:
        return None

    lat = (min(lats) + max(lats)) / 2
    lon = (min(lons) + max(lons)) / 2
    con.execute(
        "INSERT OR REPLACE INTO municipio_centroide (cod_ibge, latitude, longitude) "
        "VALUES (?,?,?)",
        [cod_ibge, lat, lon],
    )
    return lat, lon


def mapear_municipio_rf(
    con: duckdb.DuckDBPyConnection, cod_rf: str | None, uf: str | None
) -> str | None:
    """Traduz o codigo de municipio da RFB em codigo IBGE, por nome + UF.

    A tabela de dominio da Receita traz apenas codigo e descricao, sem UF; a UF
    vem do estabelecimento. Nome + UF resolve a ambiguidade de municipios
    homonimos em estados diferentes.
    """
    if not cod_rf or not uf:
        return None
    row = con.execute(
        """
        SELECT m.cod_ibge
        FROM rf_dominio d
        JOIN ibge_municipios m
          ON m.nome_norm = upper(strip_accents(d.descricao))
         AND m.uf = ?
        WHERE d.tabela = 'Municipios' AND d.codigo = ?
        LIMIT 1
        """,
        [uf.upper(), cod_rf],
    ).fetchone()
    return row[0] if row else None


# ------------------------------------------------------------- producao -----

def _anos_janela(ano_final: int | None = None) -> list[int]:
    import datetime as dt

    # A PAM sai com cerca de um ano de defasagem.
    ano_final = ano_final or (dt.date.today().year - 1)
    return list(range(ano_final - config.SIDRA_ANOS_JANELA + 1, ano_final + 1))


def _consultar_sidra(
    tabela: str, variavel: str, ano: int, produto: str
) -> list[dict]:
    url = (
        f"{config.SIDRA_VALUES_URL}/t/{tabela}/n6/all/v/{variavel}/p/{ano}"
        f"/c{config.SIDRA_CLASSIFICACAO_PRODUTO}/{produto}"
    )
    dados = http.get_json(url)
    # A primeira linha e o cabecalho descritivo, nao um dado.
    return dados[1:] if len(dados) > 1 else []


def carregar_pam(
    con: duckdb.DuckDBPyConnection,
    *,
    culturas: tuple[str, ...] | None = None,
    ano_final: int | None = None,
) -> int:
    culturas = culturas or ("soja", "milho")
    anos = _anos_janela(ano_final)
    total = 0
    for cultura in culturas:
        produto = config.SIDRA_PRODUTOS.get(cultura)
        if not produto:
            log_evento(log, "ibge.cultura_desconhecida", cultura=cultura)
            continue
        apagar_particao(con, "ibge_producao", cultura=cultura, fonte="PAM")
        for nome_var, cod_var in config.SIDRA_VARIAVEIS_PAM.items():
            for ano in anos:
                try:
                    registros = _consultar_sidra(
                        config.SIDRA_TABELA_PAM, cod_var, ano, produto
                    )
                except Exception as exc:  # noqa: BLE001 - ano/variavel opcional
                    log_evento(
                        log,
                        "ibge.consulta_falhou",
                        cultura=cultura,
                        variavel=nome_var,
                        ano=ano,
                        erro=str(exc)[:200],
                    )
                    continue
                linhas = []
                for r in registros:
                    valor = r.get("V")
                    # '...' e '-' sao marcadores de dado ausente no SIDRA.
                    try:
                        valor_num = float(valor)
                    except (TypeError, ValueError):
                        continue
                    linhas.append(
                        (
                            r.get("D1C"),
                            r.get("D1N"),
                            cultura,
                            ano,
                            nome_var,
                            valor_num,
                            "PAM",
                        )
                    )
                if not linhas:
                    continue
                con.executemany(
                    "INSERT INTO ibge_producao "
                    "(cod_ibge, municipio, cultura, ano, variavel, valor, fonte) "
                    "VALUES (?,?,?,?,?,?,?)",
                    linhas,
                )
                total += len(linhas)
                log_evento(
                    log,
                    "ibge.carga",
                    cultura=cultura,
                    variavel=nome_var,
                    ano=ano,
                    linhas=len(linhas),
                )
    return total


def executar(
    con: duckdb.DuckDBPyConnection,
    *,
    culturas: tuple[str, ...] | None = None,
    ano_final: int | None = None,
) -> int:
    total = 0
    with etapa(log, "ibge.municipios") as ctx:
        if tem_dados(con, "ibge_municipios"):
            ctx["linhas"] = 0
        else:
            ctx["linhas"] = carregar_municipios(con)
            registrar_ingestao(
                con, FONTE, "localidades", "ibge_municipios", ctx["linhas"]
            )
        total += ctx["linhas"]
    with etapa(log, "ibge.pam", culturas=list(culturas or ("soja", "milho"))) as ctx:
        ctx["linhas"] = carregar_pam(con, culturas=culturas, ano_final=ano_final)
        registrar_ingestao(con, FONTE, "PAM", "ibge_producao", ctx["linhas"])
        total += ctx["linhas"]
    return total
