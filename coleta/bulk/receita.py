"""Receita Federal - Dados Abertos do CNPJ (fonte 2).

O diretorio publico e um Nextcloud (SERPRO+): a pagina HTML e uma SPA e os
caminhos "diretos" devolvem 404. O compartilhamento publico, porem, expoe
WebDAV com o token do share como usuario e senha vazia, que e o jeito estavel
de listar competencias e baixar arquivos.

Volume: ~6 GB comprimidos e ~20 GB descomprimidos por competencia. Nada disso
passa por pandas: os membros do ZIP sao extraidos um por vez e lidos
diretamente pelo `read_csv` do DuckDB, e o CSV extraido e apagado em seguida.

Os CSVs nao tem cabecalho -- as colunas sao posicionais e estao declaradas em
`config.RF_LAYOUTS`, conforme o PDF de metadados da RFB.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

from .. import config, http
from ..logging_setup import etapa, get_logger, log_evento
from ..warehouse import apagar_particao, registrar_ingestao
from ._common import (
    colunas_varchar,
    extrair_membros,
    inserir_select,
    read_csv_sql,
    sql_data,
    sql_digitos,
)

log = get_logger("bulk.receita")

FONTE = "receita"
_AUTH = (config.RF_SHARE_TOKEN, "")

TABELA_POR_ARQUIVO = {
    "Empresas": "rf_empresas",
    "Estabelecimentos": "rf_estabelecimentos",
    "Socios": "rf_socios",
    "Simples": "rf_simples",
}


# ------------------------------------------------------------- descoberta ---

def listar_competencias() -> list[str]:
    """Lista as pastas AAAA-MM disponiveis via PROPFIND no share publico."""
    resp = http.request(
        "PROPFIND",
        f"{config.RF_WEBDAV_URL}/",
        headers={"Depth": "1"},
        auth=_AUTH,
    )
    resp.raise_for_status()
    return sorted(set(re.findall(r"(\d{4}-\d{2})", resp.text)))


def competencia_mais_recente() -> str:
    competencias = listar_competencias()
    if not competencias:
        raise RuntimeError("nenhuma competencia encontrada no share da RFB")
    return competencias[-1]


def listar_arquivos(competencia: str) -> list[str]:
    resp = http.request(
        "PROPFIND",
        f"{config.RF_WEBDAV_URL}/{competencia}/",
        headers={"Depth": "1"},
        auth=_AUTH,
    )
    resp.raise_for_status()
    nomes = re.findall(r"/([^/<>]+\.zip)</d:href>", resp.text, flags=re.IGNORECASE)
    return sorted(set(nomes))


def arquivos_esperados() -> list[str]:
    nomes = [f"{base}{i}.zip" for base in config.RF_PARTICIONADOS for i in range(10)]
    nomes += [f"{base}.zip" for base in config.RF_UNICOS]
    return nomes


def _familia(nome_zip: str) -> str:
    """'Estabelecimentos3.zip' -> 'Estabelecimentos'."""
    return re.sub(r"\d*\.zip$", "", nome_zip, flags=re.IGNORECASE)


# ------------------------------------------------------------ normalizacao --

def _select_empresas(leitura: str, competencia: str) -> str:
    return f"""
    SELECT
        '{competencia}'                 AS competencia,
        trim(cnpj_basico)               AS cnpj_basico,
        trim(razao_social)              AS razao_social,
        trim(natureza_juridica)         AS natureza_juridica,
        trim(qualificacao_responsavel)  AS qualificacao_responsavel,
        try_cast(replace(nullif(trim(capital_social), ''), ',', '.') AS DOUBLE)
                                        AS capital_social,
        trim(porte)                     AS porte,
        trim(ente_federativo_responsavel) AS ente_federativo_responsavel
    FROM {leitura}
    """


def _select_estabelecimentos(leitura: str, competencia: str) -> str:
    return f"""
    SELECT
        '{competencia}'                     AS competencia,
        trim(cnpj_basico)                   AS cnpj_basico,
        trim(cnpj_ordem)                    AS cnpj_ordem,
        trim(cnpj_dv)                       AS cnpj_dv,
        trim(cnpj_basico) || trim(cnpj_ordem) || trim(cnpj_dv) AS cnpj,
        trim(identificador_matriz_filial)   AS identificador_matriz_filial,
        trim(nome_fantasia)                 AS nome_fantasia,
        trim(situacao_cadastral)            AS situacao_cadastral,
        {sql_data('data_situacao_cadastral', '%Y%m%d')} AS data_situacao_cadastral,
        trim(motivo_situacao_cadastral)     AS motivo_situacao_cadastral,
        {sql_data('data_inicio_atividade', '%Y%m%d')}   AS data_inicio_atividade,
        trim(cnae_fiscal_principal)         AS cnae_fiscal_principal,
        trim(cnae_fiscal_secundaria)        AS cnae_fiscal_secundaria,
        trim(cep)                           AS cep,
        trim(uf)                            AS uf,
        trim(municipio)                     AS municipio,
        trim(situacao_especial)             AS situacao_especial,
        {sql_data('data_situacao_especial', '%Y%m%d')}  AS data_situacao_especial
    FROM {leitura}
    """


def _select_socios(leitura: str, competencia: str) -> str:
    return f"""
    SELECT
        '{competencia}'                   AS competencia,
        trim(cnpj_basico)                 AS cnpj_basico,
        trim(identificador_socio)         AS identificador_socio,
        trim(nome_socio)                  AS nome_socio,
        trim(cnpj_cpf_socio)              AS cnpj_cpf_socio,
        trim(qualificacao_socio)          AS qualificacao_socio,
        {sql_data('data_entrada_sociedade', '%Y%m%d')} AS data_entrada_sociedade,
        trim(pais)                        AS pais,
        trim(representante_legal)         AS representante_legal,
        trim(nome_representante)          AS nome_representante,
        trim(qualificacao_representante)  AS qualificacao_representante,
        trim(faixa_etaria)                AS faixa_etaria
    FROM {leitura}
    """


def _select_simples(leitura: str, competencia: str) -> str:
    return f"""
    SELECT
        '{competencia}'                 AS competencia,
        trim(cnpj_basico)               AS cnpj_basico,
        trim(opcao_simples)             AS opcao_simples,
        {sql_data('data_opcao_simples', '%Y%m%d')}    AS data_opcao_simples,
        {sql_data('data_exclusao_simples', '%Y%m%d')} AS data_exclusao_simples,
        trim(opcao_mei)                 AS opcao_mei,
        {sql_data('data_opcao_mei', '%Y%m%d')}        AS data_opcao_mei,
        {sql_data('data_exclusao_mei', '%Y%m%d')}     AS data_exclusao_mei
    FROM {leitura}
    """


def _select_dominio(leitura: str, competencia: str, tabela: str) -> str:
    return f"""
    SELECT
        '{competencia}' AS competencia,
        '{tabela}'      AS tabela,
        trim(codigo)    AS codigo,
        trim(descricao) AS descricao
    FROM {leitura}
    """


SELECTS = {
    "Empresas": _select_empresas,
    "Estabelecimentos": _select_estabelecimentos,
    "Socios": _select_socios,
    "Simples": _select_simples,
}


# ------------------------------------------------------------------ carga ---

def carregar_arquivo(
    con: duckdb.DuckDBPyConnection,
    competencia: str,
    nome_zip: str,
    raw_dir: Path,
) -> int:
    familia = _familia(nome_zip)
    if familia not in config.RF_LAYOUTS:
        log_evento(log, "receita.arquivo_desconhecido", arquivo=nome_zip)
        return 0

    url = f"{config.RF_WEBDAV_URL}/{competencia}/{nome_zip}"
    zip_path = http.baixar(url, raw_dir / nome_zip, auth=_AUTH)
    colunas = colunas_varchar(config.RF_LAYOUTS[familia])
    tabela = TABELA_POR_ARQUIVO.get(familia, "rf_dominio")

    linhas = 0
    for csv_path in extrair_membros(
        zip_path, raw_dir / "extraido", transcodificar_de="cp1252"
    ):
        leitura = read_csv_sql(csv_path, colunas, encoding="utf-8", header=False)
        if familia in SELECTS:
            select = SELECTS[familia](leitura, competencia)
        else:
            select = _select_dominio(leitura, competencia, familia)
        linhas += inserir_select(con, tabela, select)
    return linhas


def construir_grafo_societario(
    con: duckdb.DuckDBPyConnection, competencia: str
) -> int:
    """Normaliza `rf_socios` em `socio_empresa`.

    A identidade do socio e o problema real: o CPF vem mascarado (***123456**),
    entao nao serve sozinho como chave. Combinamos CPF mascarado + nome, o que
    e suficientemente discriminante na pratica. Para socio PJ usamos o CNPJ,
    que vem completo, e para estrangeiro so resta o nome.
    """
    apagar_particao(con, "socio_empresa", competencia=competencia)
    select = f"""
    SELECT
        competencia,
        CASE identificador_socio
            WHEN '1' THEN 'PJ:' || {sql_digitos('cnpj_cpf_socio')}
            WHEN '2' THEN 'PF:' || coalesce(trim(cnpj_cpf_socio), '')
                         || '|' || upper(coalesce(trim(nome_socio), ''))
            ELSE 'EX:' || upper(coalesce(trim(nome_socio), ''))
        END AS socio_id,
        CASE identificador_socio
            WHEN '1' THEN 'PJ' WHEN '2' THEN 'PF' ELSE 'EX'
        END AS socio_tipo,
        upper(trim(nome_socio))  AS socio_nome,
        trim(cnpj_cpf_socio)     AS socio_doc,
        trim(qualificacao_socio) AS qualificacao,
        trim(cnpj_basico)        AS cnpj_basico
    FROM rf_socios
    WHERE competencia = '{competencia}'
      AND cnpj_basico IS NOT NULL
      AND coalesce(trim(nome_socio), trim(cnpj_cpf_socio), '') <> ''
    """
    return inserir_select(con, "socio_empresa", select)


def _parte(nome_zip: str) -> int | None:
    """'Estabelecimentos3.zip' -> 3; 'Simples.zip' -> None."""
    achado = re.search(r"(\d+)\.zip$", nome_zip, flags=re.IGNORECASE)
    return int(achado.group(1)) if achado else None


def executar(
    con: duckdb.DuckDBPyConnection,
    *,
    competencia: str | None = None,
    apenas: tuple[str, ...] | None = None,
    partes: tuple[int, ...] | None = None,
    raw_dir: Path | None = None,
) -> int:
    competencia = competencia or competencia_mais_recente()
    raw_dir = Path(raw_dir or config.SETTINGS.raw_dir) / "receita" / competencia

    try:
        disponiveis = listar_arquivos(competencia)
    except Exception as exc:  # noqa: BLE001 - cai para a lista esperada
        log_evento(log, "receita.listagem_falhou", erro=str(exc))
        disponiveis = arquivos_esperados()
    if not disponiveis:
        disponiveis = arquivos_esperados()

    if apenas:
        familias = {a.capitalize() for a in apenas}
        disponiveis = [z for z in disponiveis if _familia(z) in familias]

    if partes is not None:
        # Carga parcial: util para montar uma amostra sem baixar os 8,4 GB.
        # As tabelas de dominio e o Simples nao sao particionados e entram
        # sempre -- sao pequenos e o resto do pipeline depende deles.
        disponiveis = [
            z for z in disponiveis
            if _parte(z) is None or _parte(z) in partes
        ]
        log_evento(
            log, "receita.carga_parcial", partes=list(partes),
            arquivos=len(disponiveis),
            aviso="cobertura reduzida do cadastro; nao use para producao",
        )

    # Uma recarga limpa por familia de tabela antes do primeiro arquivo dela.
    familias_vistas: set[str] = set()
    total = 0
    for nome_zip in disponiveis:
        familia = _familia(nome_zip)
        with etapa(
            log, "receita.arquivo", competencia=competencia, arquivo=nome_zip
        ) as ctx:
            if familia not in familias_vistas:
                tabela = TABELA_POR_ARQUIVO.get(familia, "rf_dominio")
                if tabela == "rf_dominio":
                    apagar_particao(
                        con, "rf_dominio", competencia=competencia, tabela=familia
                    )
                else:
                    apagar_particao(con, tabela, competencia=competencia)
                familias_vistas.add(familia)
            linhas = carregar_arquivo(con, competencia, nome_zip, raw_dir)
            ctx["linhas"] = linhas
            total += linhas
            registrar_ingestao(
                con,
                FONTE,
                f"{competencia}/{nome_zip}",
                TABELA_POR_ARQUIVO.get(familia, "rf_dominio"),
                linhas,
            )

    if "Socios" in familias_vistas:
        with etapa(log, "receita.grafo_societario", competencia=competencia) as ctx:
            ctx["linhas"] = construir_grafo_societario(con, competencia)
            registrar_ingestao(
                con, FONTE, competencia, "socio_empresa", ctx["linhas"]
            )
    return total
