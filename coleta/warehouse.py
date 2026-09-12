"""Conexao DuckDB e criacao do schema.

Convencoes:
- `documento` e sempre o CPF/CNPJ com apenas digitos (ou a string mascarada da
  PGFN, quando for pessoa fisica e nao houver o que normalizar).
- Toda tabela carregada em lote tem uma coluna de particao (`competencia`,
  `origem`, `fonte_arquivo`) para permitir recarga idempotente.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

from . import config
from .logging_setup import get_logger, log_evento

log = get_logger("warehouse")

SCHEMA_SQL = """
-- ------------------------------------------------------------------ PGFN --
CREATE TABLE IF NOT EXISTS pgfn_divida (
    competencia              VARCHAR NOT NULL,   -- ex.: 2026T1
    origem                   VARCHAR NOT NULL,   -- SIDA | FGTS | PREV
    documento                VARCHAR,            -- apenas digitos, quando PJ
    cpf_cnpj_raw             VARCHAR,
    pf_mascarado             BOOLEAN,
    tipo_pessoa              VARCHAR,
    tipo_devedor             VARCHAR,
    nome_devedor             VARCHAR,
    uf_devedor               VARCHAR,
    unidade_responsavel      VARCHAR,
    entidade_responsavel     VARCHAR,
    unidade_inscricao        VARCHAR,
    numero_inscricao         VARCHAR,
    tipo_situacao_inscricao  VARCHAR,
    situacao_inscricao       VARCHAR,
    receita_principal        VARCHAR,
    data_inscricao           DATE,
    indicador_ajuizado       BOOLEAN,
    valor_consolidado        DOUBLE
);

-- -------------------------------------------------------- Receita Federal --
CREATE TABLE IF NOT EXISTS rf_empresas (
    competencia               VARCHAR NOT NULL,
    cnpj_basico               VARCHAR,
    razao_social              VARCHAR,
    natureza_juridica         VARCHAR,
    qualificacao_responsavel  VARCHAR,
    capital_social            DOUBLE,
    porte                     VARCHAR,
    ente_federativo_responsavel VARCHAR
);

CREATE TABLE IF NOT EXISTS rf_estabelecimentos (
    competencia                 VARCHAR NOT NULL,
    cnpj_basico                 VARCHAR,
    cnpj_ordem                  VARCHAR,
    cnpj_dv                     VARCHAR,
    cnpj                        VARCHAR,
    identificador_matriz_filial VARCHAR,
    nome_fantasia               VARCHAR,
    situacao_cadastral          VARCHAR,
    data_situacao_cadastral     DATE,
    motivo_situacao_cadastral   VARCHAR,
    data_inicio_atividade       DATE,
    cnae_fiscal_principal       VARCHAR,
    cnae_fiscal_secundaria      VARCHAR,
    cep                         VARCHAR,
    uf                          VARCHAR,
    municipio                   VARCHAR,
    situacao_especial           VARCHAR,
    data_situacao_especial      DATE
);

CREATE TABLE IF NOT EXISTS rf_socios (
    competencia               VARCHAR NOT NULL,
    cnpj_basico               VARCHAR,
    identificador_socio       VARCHAR,
    nome_socio                VARCHAR,
    cnpj_cpf_socio            VARCHAR,
    qualificacao_socio        VARCHAR,
    data_entrada_sociedade    DATE,
    pais                      VARCHAR,
    representante_legal       VARCHAR,
    nome_representante        VARCHAR,
    qualificacao_representante VARCHAR,
    faixa_etaria              VARCHAR
);

CREATE TABLE IF NOT EXISTS rf_simples (
    competencia            VARCHAR NOT NULL,
    cnpj_basico            VARCHAR,
    opcao_simples          VARCHAR,
    data_opcao_simples     DATE,
    data_exclusao_simples  DATE,
    opcao_mei              VARCHAR,
    data_opcao_mei         DATE,
    data_exclusao_mei      DATE
);

CREATE TABLE IF NOT EXISTS rf_dominio (
    competencia VARCHAR NOT NULL,
    tabela      VARCHAR NOT NULL,   -- Cnaes | Municipios | Naturezas | ...
    codigo      VARCHAR,
    descricao   VARCHAR
);

-- Grafo societario normalizado (derivado de rf_socios).
CREATE TABLE IF NOT EXISTS socio_empresa (
    competencia  VARCHAR NOT NULL,
    socio_id     VARCHAR NOT NULL,  -- PJ:<cnpj> | PF:<cpf_mascarado>|<nome> | EX:<nome>
    socio_tipo   VARCHAR,           -- PJ | PF | EX
    socio_nome   VARCHAR,
    socio_doc    VARCHAR,
    qualificacao VARCHAR,
    cnpj_basico  VARCHAR NOT NULL
);

-- ----------------------------------------------------------------- IBAMA --
CREATE TABLE IF NOT EXISTS ibama_autos (
    documento             VARCHAR,
    cpf_cnpj_raw          VARCHAR,
    pf_mascarado          BOOLEAN,
    seq_auto_infracao     VARCHAR,
    num_auto_infracao     VARCHAR,
    nome_infrator         VARCHAR,
    tipo_auto             VARCHAR,
    tipo_infracao         VARCHAR,
    des_infracao          VARCHAR,
    valor_auto            DOUBLE,
    sit_cancelado         VARCHAR,
    status_formulario     VARCHAR,
    data_auto             DATE,
    cod_municipio         VARCHAR,
    municipio             VARCHAR,
    uf                    VARCHAR,
    qt_area               DOUBLE,
    latitude              DOUBLE,
    longitude             DOUBLE
);

CREATE TABLE IF NOT EXISTS ibama_embargos (
    documento           VARCHAR,
    cpf_cnpj_raw        VARCHAR,
    pf_mascarado        BOOLEAN,
    seq_tad             VARCHAR,
    num_tad             VARCHAR,
    nome_embargado      VARCHAR,
    data_embargo        DATE,
    sit_cancelado       VARCHAR,
    sit_desembargo      VARCHAR,
    data_desembargo     DATE,
    area_embargada_ha   DOUBLE,
    cod_municipio       VARCHAR,
    municipio           VARCHAR,
    uf                  VARCHAR,
    latitude            DOUBLE,
    longitude           DOUBLE,
    nome_imovel         VARCHAR
);

-- ------------------------------------------------------------- BCB / MDCR --
CREATE TABLE IF NOT EXISTS bcb_mdcr (
    cod_ibge             VARCHAR,
    municipio            VARCHAR,
    uf                   VARCHAR,
    ano                  INTEGER,
    mes                  INTEGER,
    atividade            VARCHAR,
    qtd_custeio          BIGINT,
    vl_custeio           DOUBLE,
    qtd_investimento     BIGINT,
    vl_investimento      DOUBLE,
    qtd_comercializacao  BIGINT,
    vl_comercializacao   DOUBLE,
    qtd_industrializacao BIGINT,
    vl_industrializacao  DOUBLE,
    area_custeio         DOUBLE,
    area_investimento    DOUBLE
);

CREATE TABLE IF NOT EXISTS bcb_mdcr_produto (
    cod_ibge      VARCHAR,
    municipio     VARCHAR,
    ano           INTEGER,
    mes           INTEGER,
    nome_produto  VARCHAR,
    cd_produto    VARCHAR,
    cd_tipo_seguro VARCHAR,
    vl_custeio    DOUBLE,
    area_custeio  DOUBLE
);

-- ------------------------------------------------------------ IBGE/SIDRA --
CREATE TABLE IF NOT EXISTS ibge_producao (
    cod_ibge    VARCHAR,
    municipio   VARCHAR,
    cultura     VARCHAR,
    ano         INTEGER,
    variavel    VARCHAR,   -- area_plantada_ha | area_colhida_ha | ...
    valor       DOUBLE,
    fonte       VARCHAR    -- PAM | LSPA
);

CREATE TABLE IF NOT EXISTS ibge_municipios (
    cod_ibge     VARCHAR PRIMARY KEY,
    nome         VARCHAR,
    nome_norm    VARCHAR,
    uf           VARCHAR,
    regiao       VARCHAR
);

CREATE TABLE IF NOT EXISTS municipio_centroide (
    cod_ibge  VARCHAR PRIMARY KEY,
    latitude  DOUBLE,
    longitude DOUBLE
);

-- --------------------------------------------------------------- clima ----
CREATE TABLE IF NOT EXISTS clima_diario (
    ponto_id       VARCHAR NOT NULL,  -- lat/lon arredondados ou id de estacao
    provedor       VARCHAR NOT NULL,
    latitude       DOUBLE,
    longitude      DOUBLE,
    data           DATE NOT NULL,
    precipitacao_mm DOUBLE,
    t_max          DOUBLE,
    t_min          DOUBLE
);

-- ----------------------------------------------------------- protestos ----
CREATE TABLE IF NOT EXISTS protesto_cache (
    documento        VARCHAR NOT NULL,
    provedor         VARCHAR NOT NULL,
    consultado_em    TIMESTAMP NOT NULL,
    payload_json     VARCHAR
);

-- -------------------------------------------------------- auditoria -------
CREATE TABLE IF NOT EXISTS ingestao_log (
    fonte      VARCHAR,
    particao   VARCHAR,
    tabela     VARCHAR,
    linhas     BIGINT,
    carregado_em TIMESTAMP DEFAULT current_timestamp
);
"""

INDICES_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_pgfn_doc ON pgfn_divida(documento)",
    "CREATE INDEX IF NOT EXISTS ix_rf_est_cnpj ON rf_estabelecimentos(cnpj)",
    "CREATE INDEX IF NOT EXISTS ix_rf_est_basico ON rf_estabelecimentos(cnpj_basico)",
    "CREATE INDEX IF NOT EXISTS ix_rf_emp_basico ON rf_empresas(cnpj_basico)",
    "CREATE INDEX IF NOT EXISTS ix_rf_soc_basico ON rf_socios(cnpj_basico)",
    "CREATE INDEX IF NOT EXISTS ix_socemp_socio ON socio_empresa(socio_id)",
    "CREATE INDEX IF NOT EXISTS ix_socemp_cnpj ON socio_empresa(cnpj_basico)",
    "CREATE INDEX IF NOT EXISTS ix_autos_doc ON ibama_autos(documento)",
    "CREATE INDEX IF NOT EXISTS ix_emb_doc ON ibama_embargos(documento)",
    "CREATE INDEX IF NOT EXISTS ix_mdcr_mun ON bcb_mdcr(cod_ibge)",
    "CREATE INDEX IF NOT EXISTS ix_prod_mun ON ibge_producao(cod_ibge, cultura)",
    "CREATE INDEX IF NOT EXISTS ix_clima_ponto ON clima_diario(ponto_id, data)",
]


def conectar(
    path: Path | None = None, *, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    caminho = Path(path or config.SETTINGS.warehouse_path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho), read_only=read_only)
    if not read_only:
        criar_schema(con)
    return con


def criar_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_SQL)
    for ddl in INDICES_SQL:
        try:
            con.execute(ddl)
        except duckdb.Error:
            # Indice sobre tabela ainda vazia/ausente nao e fatal.
            pass


def tabela_existe(con: duckdb.DuckDBPyConnection, nome: str) -> bool:
    row = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [nome]
    ).fetchone()
    return bool(row and row[0])


def tem_dados(con: duckdb.DuckDBPyConnection, nome: str) -> bool:
    if not tabela_existe(con, nome):
        return False
    row = con.execute(f"SELECT count(*) FROM {nome} LIMIT 1").fetchone()
    return bool(row and row[0])


def apagar_particao(
    con: duckdb.DuckDBPyConnection, tabela: str, /, **chaves: Any
) -> int:
    """Remove uma particao antes de recarregar. E o que garante idempotencia.

    `con` e `tabela` sao posicionais-apenas de proposito: `rf_dominio` tem uma
    COLUNA chamada `tabela`, entao `apagar_particao(con, "rf_dominio",
    tabela="Cnaes")` colidiria com o parametro. A barra manda o nome para
    `chaves`, que e onde ele deve ir.
    """
    if not chaves:
        res = con.execute(f"DELETE FROM {tabela}").fetchone()
    else:
        where = " AND ".join(f"{k} = ?" for k in chaves)
        res = con.execute(
            f"DELETE FROM {tabela} WHERE {where}", list(chaves.values())
        ).fetchone()
    return int(res[0]) if res and res[0] is not None else 0


def registrar_ingestao(
    con: duckdb.DuckDBPyConnection,
    fonte: str,
    particao: str,
    tabela: str,
    linhas: int,
) -> None:
    con.execute(
        "INSERT INTO ingestao_log (fonte, particao, tabela, linhas) VALUES (?,?,?,?)",
        [fonte, particao, tabela, linhas],
    )
    log_evento(
        log, "ingestao", fonte=fonte, particao=particao, tabela=tabela, linhas=linhas
    )


def contar(con: duckdb.DuckDBPyConnection, tabela: str, /, **chaves: Any) -> int:
    """Mesma razao de `apagar_particao` para os parametros posicionais."""
    if chaves:
        where = " AND ".join(f"{k} = ?" for k in chaves)
        sql = f"SELECT count(*) FROM {tabela} WHERE {where}"
        row = con.execute(sql, list(chaves.values())).fetchone()
    else:
        row = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()
    return int(row[0]) if row else 0


_NAO_DIGITO = re.compile(r"\D+")


def so_digitos(valor: str | None) -> str | None:
    if not valor:
        return None
    limpo = _NAO_DIGITO.sub("", valor)
    return limpo or None


def normalizar_documento(valor: str | None) -> str | None:
    """CNPJ/CPF apenas com digitos; None quando nao houver digito algum."""
    return so_digitos(valor)
