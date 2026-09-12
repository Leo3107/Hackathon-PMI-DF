"""Utilidades compartilhadas pelos coletores em lote."""
from __future__ import annotations

import shutil
import unicodedata
import zipfile
from collections.abc import Iterator
from pathlib import Path

import duckdb

from ..logging_setup import get_logger, log_evento

log = get_logger("bulk")


def extrair_membros(
    zip_path: Path,
    destino: Path,
    *,
    sufixo: str = ".csv",
    apagar_apos_uso: bool = True,
    transcodificar_de: str | None = None,
) -> Iterator[Path]:
    """Extrai um membro por vez e apaga depois de usado.

    Descompactar o ZIP inteiro dos dados abertos da Receita custaria ~20 GB de
    disco; extrair sob demanda mantem o pico proximo ao maior arquivo isolado.

    `transcodificar_de` converte o arquivo para UTF-8 durante a extracao. Os
    CSVs da Receita e da PGFN sao descritos como latin-1, mas trazem bytes da
    faixa 0x80-0x9F (aspas e travessoes do Windows-1252) que o leitor latin-1
    do DuckDB recusa -- transcodificar aqui resolve de uma vez. Como cp1252 e
    de byte unico, nao ha risco de partir caractere no limite do bloco.
    """
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        nomes = [n for n in zf.namelist() if not n.endswith("/")]
        if sufixo:
            filtrados = [n for n in nomes if n.lower().endswith(sufixo)]
            # Varios arquivos da Receita nao usam extensao .csv (ex.: .EMPRECSV).
            nomes = filtrados or nomes
        for nome in sorted(nomes):
            alvo = destino / Path(nome).name
            with zf.open(nome) as origem, open(alvo, "wb") as saida:
                if transcodificar_de:
                    while bloco := origem.read(1 << 20):
                        saida.write(
                            bloco.decode(transcodificar_de, errors="replace")
                            .encode("utf-8")
                        )
                else:
                    shutil.copyfileobj(origem, saida, length=1 << 20)
            try:
                yield alvo
            finally:
                if apagar_apos_uso and alvo.exists():
                    alvo.unlink()


def read_csv_sql(
    caminho: Path | str,
    colunas: dict[str, str],
    *,
    encoding: str = "latin-1",
    delim: str = ";",
    header: bool = False,
    decimal: str = ".",
    quote: str = '"',
) -> str:
    """Monta a chamada `read_csv` do DuckDB com colunas declaradas.

    As colunas sao sempre lidas como VARCHAR e convertidas no SELECT: os CSVs
    de governo trazem lixo suficiente para que a inferencia de tipo do DuckDB
    aborte a carga inteira por causa de uma linha.
    """
    spec = ", ".join(f"'{nome}': '{tipo}'" for nome, tipo in colunas.items())
    caminho_sql = str(caminho).replace("\\", "/").replace("'", "''")
    return (
        f"read_csv('{caminho_sql}', "
        f"columns={{{spec}}}, "
        f"delim='{delim}', quote='{quote}', escape='{quote}', "
        f"header={'true' if header else 'false'}, "
        f"encoding='{encoding}', decimal_separator='{decimal}', "
        f"nullstr='', ignore_errors=true, parallel=true)"
    )


def colunas_varchar(nomes: list[str]) -> dict[str, str]:
    return {nome: "VARCHAR" for nome in nomes}


def normalizar_nome(texto: str | None) -> str | None:
    """Uppercase sem acento, para casar nomes de municipio entre bases."""
    if not texto:
        return None
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.upper().split())


def inserir_select(
    con: duckdb.DuckDBPyConnection, tabela: str, select_sql: str
) -> int:
    """INSERT ... BY NAME e devolve o numero de linhas inseridas."""
    antes = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    con.execute(f"INSERT INTO {tabela} BY NAME {select_sql}")
    depois = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    linhas = int(depois - antes)
    log_evento(log, "carga.tabela", tabela=tabela, linhas=linhas)
    return linhas


# Expressoes SQL reutilizadas na normalizacao ------------------------------

def sql_data(coluna: str, formato: str) -> str:
    """try_strptime devolve NULL em vez de estourar em datas invalidas."""
    return f"try_strptime(nullif(trim({coluna}), ''), '{formato}')::DATE"


def sql_data_multi(coluna: str, formatos: tuple[str, ...]) -> str:
    """Primeiro formato que casar; NULL se nenhum casar.

    Necessario no IBAMA, onde os arquivos antigos trazem so a data e os
    recentes trazem data e hora na mesma coluna.
    """
    tentativas = ", ".join(
        f"try_strptime(nullif(trim({coluna}), ''), '{f}')" for f in formatos
    )
    return f"coalesce({tentativas})::DATE"


def sql_digitos(coluna: str) -> str:
    return f"nullif(regexp_replace({coluna}, '[^0-9]', '', 'g'), '')"


def sql_double_virgula(coluna: str) -> str:
    """Converte '1.234,56' ou '1234,56' em DOUBLE."""
    return (
        f"try_cast(replace(replace(nullif(trim({coluna}), ''), '.', ''), ',', '.') "
        f"AS DOUBLE)"
    )
