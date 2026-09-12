"""IBAMA - autos de infracao e termos de embargo (fonte 3).

Diferente das bases da Fazenda: estes CSVs sao UTF-8 (nao latin-1), tem
cabecalho e usam virgula como separador decimal. O CNPJ do autuado vem sem
mascara; o CPF de pessoa fisica pode vir completo em alguns registros
historicos e mascarado em outros -- guardamos como veio, marcamos
`pf_mascarado` quando ha mascara e nao derivamos nada de CPF.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from .. import config, http
from ..logging_setup import etapa, get_logger
from ..warehouse import apagar_particao, registrar_ingestao
from ._common import (
    colunas_varchar,
    extrair_membros,
    inserir_select,
    read_csv_sql,
    sql_data_multi,
    sql_digitos,
    sql_double_virgula,
)

log = get_logger("bulk.ibama")

FONTE = "ibama"

COLUNAS_AUTOS = [
    "SEQ_AUTO_INFRACAO", "DES_STATUS_FORMULARIO", "DS_SIT_AUTO_AIE",
    "SIT_CANCELADO", "NUM_AUTO_INFRACAO", "SER_AUTO_INFRACAO",
    "CD_ORIGINAL_AUTO_INFRACAO", "TIPO_AUTO", "TIPO_MULTA", "VAL_AUTO_INFRACAO",
    "FUNDAMENTACAO_MULTA", "PATRIMONIO_APURACAO", "GRAVIDADE_INFRACAO",
    "CD_NIVEL_GRAVIDADE", "MOTIVACAO_CONDUTA", "EFEITO_MEIO_AMBIENTE",
    "EFEITO_SAUDE_PUBLICA", "PASSIVEL_RECUPERACAO", "UNID_ARRECADACAO",
    "DES_AUTO_INFRACAO", "DAT_HORA_AUTO_INFRACAO", "FORMA_ENTREGA",
    "DAT_CIENCIA_AUTUACAO", "DT_FATO_INFRACIONAL", "DT_INICIO_ATO_INEQUIVOCO",
    "DT_FIM_ATO_INEQUIVOCO", "DS_UNID_CONCILIACAO", "COD_MUNICIPIO", "MUNICIPIO",
    "UF", "NUM_PROCESSO", "NU_PROCESSO_FORMATADO", "COD_INFRACAO", "DES_INFRACAO",
    "TIPO_INFRACAO", "CD_RECEITA_AUTO_INFRACAO", "DES_RECEITA",
    "TP_PESSOA_INFRATOR", "NUM_PESSOA_INFRATOR", "NOME_INFRATOR",
    "CPF_CNPJ_INFRATOR", "QT_AREA", "INFRACAO_AREA", "DES_OUTROS_TIPO_AREA",
    "CLASSIFICACAO_AREA", "DS_FATOR_AJUSTE", "NUM_LONGITUDE_AUTO",
    "NUM_LATITUDE_AUTO", "DS_WKT", "DES_LOCAL_INFRACAO",
    "DS_REFERENCIA_ACAO_FISCALIZATORIA", "UNIDADE_CONSERVACAO",
    "ID_SICAFI_BIOMAS_ATINGIDOS_INFRACAO", "DS_BIOMAS_ATINGIDOS",
    "SEQ_NOTIFICACAO", "SEQ_ACAO_FISCALIZATORIA", "CD_ACAO_FISCALIZATORIA",
    "UNID_CONTROLE", "TIPO_ACAO", "OPERACAO", "DENUNCIA_SISLIV",
    "SEQ_ORDEM_FISCALIZACAO", "ORDEM_FISCALIZACAO", "UNID_ORDENADORA",
    "SEQ_SOLICITACAO_RECURSO", "SOLICITACAO_RECURSO", "OPERACAO_SOL_RECURSO",
    "DT_LANCAMENTO", "TP_ULT_ALTERACAO", "DT_ULT_ALTERACAO",
    "JUSTIFICATIVA_ALTERACAO", "WKT_GE_AREA_AUTUADA", "DT_ULT_ALTER_GEOM",
    "TP_ORIGEM_GE_AREA_AUTUADA", "DS_ERRO_GE_AREA_AUTUADA",
    "DS_WKT_GE_AREA_AUTUADA_COM_ERRO", "ST_AUTO_MIGRADO_AIE",
    "DS_ENQUADRAMENTO_ADMINISTRATIVO", "DS_ENQUADRAMENTO_NAO_ADMINISTRATIVO",
    "DS_ENQUADRAMENTO_COMPLEMENTAR", "CD_TERMOS_APREENSAO",
    "CD_TERMOS_EMBARGOS", "TP_ORIGEM_REGISTRO_AUTO",
    "ULTIMA_ATUALIZACAO_RELATORIO",
]

COLUNAS_EMBARGOS = [
    "SEQ_TAD", "DES_STATUS_FORMULARIO", "DES_STATUS_FORMULARIO_AIE",
    "SIT_CANCELADO", "NUM_TAD", "SER_TAD", "COD_SUBSTITUICAO", "DAT_EMBARGO",
    "DAT_IMPRESSAO", "FORMA_ENTREGA", "NUM_PESSOA_EMBARGO", "NOME_EMBARGADO",
    "CPF_CNPJ_EMBARGADO", "NUM_PROCESSO", "DES_TAD", "COD_MUNICIPIO",
    "MUNICIPIO", "UF", "DES_LOCALIZACAO", "NUM_LONGITUDE_TAD",
    "NUM_LATITUDE_TAD", "DETER_PRODES", "ID_POLIGONO", "EMBARGA_POLIGONO",
    "QTD_AREA_EMBARGADA", "NOME_IMOVEL", "TIPO_AREA", "GEOM_AREA_EMBARGADA",
    "DAT_ULT_ALTER_GEOM", "UNID_APRESENTACAO", "UNID_CONTROLE",
    "SIT_DESEMBARGO", "TIPO_DESEMBARGO", "DAT_DESEMBARGO", "DES_DESEMBARGO",
    "SEQ_AUTO_INFRACAO", "NUM_AUTO_INFRACAO", "SEQ_NOTIFICACAO",
    "SEQ_ACAO_FISCALIZATORIA", "CD_ACAO_FISCALIZATORIA", "OPERACAO",
    "SEQ_ORDEM_FISCALIZACAO", "ORDEM_FISCALIZACAO", "UNID_ORDENADORA",
    "SEQ_SOLICITACAO_RECURSO", "SOLICITACAO_RECURSO", "OPERACAO_SOL_RECURSO",
    "DAT_ULT_ALTERACAO", "TIPO_ALTERACAO", "JUSTIFICATIVA_ALTERACAO",
    "ULTIMA_ATUALIZACAO_RELATORIO",
]

# Um documento so vira chave de join quando nao contem mascara.
_MASCARADO_AUTOS = "CPF_CNPJ_INFRATOR ILIKE '%X%' OR CPF_CNPJ_INFRATOR LIKE '%*%'"
_MASCARADO_EMB = "CPF_CNPJ_EMBARGADO ILIKE '%X%' OR CPF_CNPJ_EMBARGADO LIKE '%*%'"

# Arquivos antigos trazem so a data; os recentes, data e hora na mesma coluna.
_FORMATOS_DATA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def _DATA(coluna: str) -> str:
    return sql_data_multi(coluna, _FORMATOS_DATA)


def _select_autos(leitura: str) -> str:
    return f"""
    SELECT
        CASE WHEN {_MASCARADO_AUTOS} THEN NULL
             ELSE {sql_digitos('CPF_CNPJ_INFRATOR')} END AS documento,
        trim(CPF_CNPJ_INFRATOR)        AS cpf_cnpj_raw,
        ({_MASCARADO_AUTOS})           AS pf_mascarado,
        trim(SEQ_AUTO_INFRACAO)        AS seq_auto_infracao,
        trim(NUM_AUTO_INFRACAO)        AS num_auto_infracao,
        trim(NOME_INFRATOR)            AS nome_infrator,
        trim(TIPO_AUTO)                AS tipo_auto,
        trim(TIPO_INFRACAO)            AS tipo_infracao,
        trim(DES_INFRACAO)             AS des_infracao,
        {sql_double_virgula('VAL_AUTO_INFRACAO')} AS valor_auto,
        trim(SIT_CANCELADO)            AS sit_cancelado,
        trim(DES_STATUS_FORMULARIO)    AS status_formulario,
        {_DATA('DAT_HORA_AUTO_INFRACAO')} AS data_auto,
        trim(COD_MUNICIPIO)            AS cod_municipio,
        trim(MUNICIPIO)                AS municipio,
        trim(UF)                       AS uf,
        {sql_double_virgula('QT_AREA')} AS qt_area,
        try_cast(NUM_LATITUDE_AUTO AS DOUBLE)  AS latitude,
        try_cast(NUM_LONGITUDE_AUTO AS DOUBLE) AS longitude
    FROM {leitura}
    """


def _select_embargos(leitura: str) -> str:
    return f"""
    SELECT
        CASE WHEN {_MASCARADO_EMB} THEN NULL
             ELSE {sql_digitos('CPF_CNPJ_EMBARGADO')} END AS documento,
        trim(CPF_CNPJ_EMBARGADO)  AS cpf_cnpj_raw,
        ({_MASCARADO_EMB})        AS pf_mascarado,
        trim(SEQ_TAD)             AS seq_tad,
        trim(NUM_TAD)             AS num_tad,
        trim(NOME_EMBARGADO)      AS nome_embargado,
        {_DATA('DAT_EMBARGO')}    AS data_embargo,
        trim(SIT_CANCELADO)       AS sit_cancelado,
        trim(SIT_DESEMBARGO)      AS sit_desembargo,
        {_DATA('DAT_DESEMBARGO')} AS data_desembargo,
        {sql_double_virgula('QTD_AREA_EMBARGADA')} AS area_embargada_ha,
        trim(COD_MUNICIPIO)       AS cod_municipio,
        trim(MUNICIPIO)           AS municipio,
        trim(UF)                  AS uf,
        try_cast(NUM_LATITUDE_TAD AS DOUBLE)  AS latitude,
        try_cast(NUM_LONGITUDE_TAD AS DOUBLE) AS longitude,
        trim(NOME_IMOVEL)         AS nome_imovel
    FROM {leitura}
    """


def carregar_autos(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> int:
    zip_path = http.baixar(config.IBAMA_AUTOS_URL, raw_dir / "auto_infracao_csv.zip")
    apagar_particao(con, "ibama_autos")
    colunas = colunas_varchar(COLUNAS_AUTOS)
    linhas = 0
    for csv_path in extrair_membros(zip_path, raw_dir / "autos"):
        leitura = read_csv_sql(csv_path, colunas, encoding="utf-8", header=True)
        linhas += inserir_select(con, "ibama_autos", _select_autos(leitura))
    return linhas


def carregar_embargos(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> int:
    csv_path = http.baixar(
        config.IBAMA_EMBARGOS_URL, raw_dir / "termo_embargo.csv"
    )
    apagar_particao(con, "ibama_embargos")
    leitura = read_csv_sql(
        csv_path, colunas_varchar(COLUNAS_EMBARGOS), encoding="utf-8", header=True
    )
    return inserir_select(con, "ibama_embargos", _select_embargos(leitura))


def executar(
    con: duckdb.DuckDBPyConnection, *, raw_dir: Path | None = None
) -> int:
    raw_dir = Path(raw_dir or config.SETTINGS.raw_dir) / "ibama"
    total = 0
    with etapa(log, "ibama.autos") as ctx:
        ctx["linhas"] = carregar_autos(con, raw_dir)
        registrar_ingestao(con, FONTE, "full", "ibama_autos", ctx["linhas"])
        total += ctx["linhas"]
    with etapa(log, "ibama.embargos") as ctx:
        ctx["linhas"] = carregar_embargos(con, raw_dir)
        registrar_ingestao(con, FONTE, "full", "ibama_embargos", ctx["linhas"])
        total += ctx["linhas"]
    return total
