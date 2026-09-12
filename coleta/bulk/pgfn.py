"""PGFN - Divida Ativa da Uniao (fonte 1).

Layouts confirmados em 2026-09 lendo o cabecalho real dos ZIPs publicados.
Observacoes que contrariam o senso comum sobre essa base:

- O CNPJ vem COM mascara ("84.461.748/0001-81"); normalizamos para digitos.
- O CPF de pessoa fisica vem parcialmente ocultado ("XXX735.623XX"). Guardamos
  como veio e marcamos `pf_mascarado = TRUE`. Nao ha tentativa de desmascarar.
- O separador decimal do VALOR_CONSOLIDADO e ponto, nao virgula.
- Os tres sistemas de origem tem layouts diferentes: PREV traz TIPO_CREDITO no
  lugar de RECEITA_PRINCIPAL e nao tem ENTIDADE_RESPONSAVEL/UNIDADE_INSCRICAO.
"""
from __future__ import annotations

import datetime as dt
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

log = get_logger("bulk.pgfn")

FONTE = "pgfn"


def competencia_str(ano: int, trimestre: int) -> str:
    return f"{ano}T{trimestre}"


def url_trimestre(ano: int, trimestre: int, arquivo: str) -> str:
    return f"{config.PGFN_BASE_URL}/{ano}_trimestre_{trimestre:02d}/{arquivo}"


def trimestre_atual(hoje: dt.date | None = None) -> tuple[int, int]:
    hoje = hoje or dt.date.today()
    return hoje.year, (hoje.month - 1) // 3 + 1


def trimestres_candidatos(n: int, hoje: dt.date | None = None) -> list[tuple[int, int]]:
    """Os N trimestres mais recentes, do mais novo para o mais antigo."""
    ano, tri = trimestre_atual(hoje)
    saida: list[tuple[int, int]] = []
    while len(saida) < n and ano >= config.PGFN_PRIMEIRO_ANO:
        saida.append((ano, tri))
        tri -= 1
        if tri == 0:
            tri = 4
            ano -= 1
    return saida


def trimestres_publicados(n: int, hoje: dt.date | None = None) -> list[tuple[int, int]]:
    """Filtra os candidatos pelos que existem de fato no servidor.

    O trimestre corrente so e publicado semanas depois de encerrado, entao o
    primeiro candidato quase sempre ainda nao existe.
    """
    encontrados: list[tuple[int, int]] = []
    # Olha mais fundo que N: os primeiros candidatos podem nao existir ainda.
    for ano, tri in trimestres_candidatos(n + 3, hoje):
        if len(encontrados) >= n:
            break
        arquivo = config.PGFN_ORIGENS["SIDA"]["zip"]
        tamanho = http.tamanho_remoto(url_trimestre(ano, tri, arquivo))
        if tamanho:
            encontrados.append((ano, tri))
        else:
            log_evento(log, "pgfn.trimestre_ausente", ano=ano, trimestre=tri)
    return encontrados


def _select_normalizado(leitura_sql: str, origem: str, competencia: str) -> str:
    """Mapeia o layout de cada origem para o schema comum de `pgfn_divida`."""
    tem_entidade = origem == "FGTS"
    coluna_receita = "TIPO_CREDITO" if origem == "PREV" else "RECEITA_PRINCIPAL"
    entidade = "ENTIDADE_RESPONSAVEL" if tem_entidade else "NULL"
    unidade_insc = "UNIDADE_INSCRICAO" if tem_entidade else "NULL"

    # PF vem mascarada (contem 'X'); so ha documento utilizavel quando PJ.
    eh_mascarado = "CPF_CNPJ ILIKE '%X%'"
    documento = (
        f"CASE WHEN {eh_mascarado} THEN NULL ELSE {sql_digitos('CPF_CNPJ')} END"
    )
    return f"""
    SELECT
        '{competencia}'                        AS competencia,
        '{origem}'                             AS origem,
        {documento}                            AS documento,
        trim(CPF_CNPJ)                         AS cpf_cnpj_raw,
        {eh_mascarado}                         AS pf_mascarado,
        trim(TIPO_PESSOA)                      AS tipo_pessoa,
        trim(TIPO_DEVEDOR)                     AS tipo_devedor,
        trim(NOME_DEVEDOR)                     AS nome_devedor,
        trim(UF_DEVEDOR)                       AS uf_devedor,
        trim(UNIDADE_RESPONSAVEL)              AS unidade_responsavel,
        {entidade}                             AS entidade_responsavel,
        {unidade_insc}                         AS unidade_inscricao,
        trim(NUMERO_INSCRICAO)                 AS numero_inscricao,
        trim(TIPO_SITUACAO_INSCRICAO)          AS tipo_situacao_inscricao,
        trim(SITUACAO_INSCRICAO)               AS situacao_inscricao,
        trim({coluna_receita})                 AS receita_principal,
        {sql_data('DATA_INSCRICAO', '%d/%m/%Y')} AS data_inscricao,
        upper(trim(INDICADOR_AJUIZADO)) IN ('SIM', 'S', 'TRUE', '1')
                                               AS indicador_ajuizado,
        try_cast(nullif(trim(VALOR_CONSOLIDADO), '') AS DOUBLE)
                                               AS valor_consolidado
    FROM {leitura_sql}
    """


def carregar_trimestre(
    con: duckdb.DuckDBPyConnection,
    ano: int,
    trimestre: int,
    *,
    origens: tuple[str, ...] | None = None,
    raw_dir: Path | None = None,
) -> int:
    """Baixa e carrega um trimestre inteiro. Idempotente por (competencia, origem)."""
    competencia = competencia_str(ano, trimestre)
    raw_dir = Path(raw_dir or config.SETTINGS.raw_dir) / "pgfn" / competencia
    origens = origens or tuple(config.PGFN_ORIGENS)
    total = 0

    for origem in origens:
        meta = config.PGFN_ORIGENS[origem]
        url = url_trimestre(ano, trimestre, meta["zip"])
        with etapa(
            log, "pgfn.origem", competencia=competencia, origem=origem
        ) as ctx:
            zip_path = http.baixar(url, raw_dir / meta["zip"])
            # Recarga limpa da particao: rodar duas vezes nao duplica linha.
            apagar_particao(
                con, "pgfn_divida", competencia=competencia, origem=origem
            )
            colunas = colunas_varchar(meta["colunas"])
            linhas_origem = 0
            for csv_path in extrair_membros(
                zip_path, raw_dir / origem, transcodificar_de="cp1252"
            ):
                leitura = read_csv_sql(
                    csv_path, colunas, encoding="utf-8", header=True
                )
                linhas_origem += inserir_select(
                    con, "pgfn_divida", _select_normalizado(leitura, origem, competencia)
                )
            ctx["linhas"] = linhas_origem
            total += linhas_origem
            registrar_ingestao(
                con, FONTE, f"{competencia}/{origem}", "pgfn_divida", linhas_origem
            )
    return total


def executar(
    con: duckdb.DuckDBPyConnection,
    *,
    quarters: int = 8,
    origens: tuple[str, ...] | None = None,
) -> int:
    """Ponto de entrada chamado pela CLI."""
    trimestres = trimestres_publicados(quarters)
    if not trimestres:
        log_evento(log, "pgfn.nada_publicado", quarters=quarters)
        return 0
    log_evento(
        log,
        "pgfn.plano",
        trimestres=[competencia_str(a, t) for a, t in trimestres],
    )
    total = 0
    for ano, tri in trimestres:
        total += carregar_trimestre(con, ano, tri, origens=origens)
    return total
