"""CLI da camada de coleta.

    python -m coleta.cli bulk --source pgfn --quarters 8
    python -m coleta.cli bulk --source receita --competencia 2026-08
    python -m coleta.cli bulk --all
    python -m coleta.cli features --documento 12345678000190
"""
from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from . import config, warehouse
from .bulk import bcb_mdcr, clima, ibama, ibge_sidra, pgfn, receita
from .features import build_features
from .logging_setup import get_logger, log_evento, setup_logging
from .ondemand import protestos as protestos_mod

app = typer.Typer(add_completion=False, help="Coleta de dados para risco de credito agro")
log = get_logger("cli")

ORDEM_FONTES = ("pgfn", "receita", "ibama", "bcb", "ibge", "clima")


def _lista(valor: Optional[str]) -> tuple[str, ...] | None:
    if not valor:
        return None
    return tuple(p.strip() for p in valor.split(",") if p.strip())


@app.command()
def bulk(
    source: Optional[str] = typer.Option(
        None, "--source", help=f"Fonte a carregar: {', '.join(ORDEM_FONTES)}"
    ),
    todas: bool = typer.Option(
        False, "--all", help="Carrega todas as fontes, na ordem de dependencia"
    ),
    quarters: int = typer.Option(8, "--quarters", help="PGFN: quantos trimestres"),
    competencia: Optional[str] = typer.Option(
        None, "--competencia", help="Receita: competencia AAAA-MM (padrao: a mais recente)"
    ),
    apenas: Optional[str] = typer.Option(
        None, "--apenas", help="Receita: subconjunto de arquivos (ex.: empresas,socios)"
    ),
    partes: Optional[str] = typer.Option(
        None, "--partes",
        help="Receita: particoes a carregar (ex.: 1,2,3,4). Padrao: todas",
    ),
    culturas: Optional[str] = typer.Option(
        None, "--culturas", help="IBGE: culturas separadas por virgula (padrao: soja,milho)"
    ),
    municipios: Optional[str] = typer.Option(
        None, "--municipios", help="Clima: codigos IBGE separados por virgula"
    ),
    limite_clima: int = typer.Option(
        50, "--limite-clima", help="Clima: quantos municipios pre-aquecer"
    ),
    ano_inicial: Optional[int] = typer.Option(
        None, "--ano-inicial", help="BCB: primeiro ano de emissao a carregar"
    ),
) -> None:
    """Carga em lote. Uma fonte que falha nao derruba as outras."""
    setup_logging()
    config.SETTINGS.ensure_dirs()

    if not source and not todas:
        typer.echo("informe --source <fonte> ou --all", err=True)
        raise typer.Exit(code=2)

    fontes = ORDEM_FONTES if todas else (source,)
    con = warehouse.conectar()
    falhas: list[str] = []
    try:
        for fonte in fontes:
            try:
                _executar_fonte(
                    con,
                    fonte,
                    quarters=quarters,
                    competencia=competencia,
                    apenas=_lista(apenas),
                    partes=_lista(partes),
                    culturas=_lista(culturas),
                    municipios=_lista(municipios),
                    limite_clima=limite_clima,
                    ano_inicial=ano_inicial,
                )
            except Exception as exc:  # noqa: BLE001 - isolamento por fonte
                falhas.append(fonte)
                log_evento(
                    log,
                    "bulk.fonte_falhou",
                    fonte=fonte,
                    erro=f"{type(exc).__name__}: {exc}",
                )
    finally:
        con.close()

    if falhas:
        typer.echo(f"fontes com falha: {', '.join(falhas)}", err=True)
        raise typer.Exit(code=1)


def _executar_fonte(con, fonte: str, **kw) -> None:
    if fonte == "pgfn":
        pgfn.executar(con, quarters=kw["quarters"])
    elif fonte == "receita":
        partes = kw.get("partes")
        receita.executar(
            con,
            competencia=kw["competencia"],
            apenas=kw["apenas"],
            partes=tuple(int(p) for p in partes) if partes else None,
        )
    elif fonte == "ibama":
        ibama.executar(con)
    elif fonte == "bcb":
        bcb_mdcr.executar(con, ano_inicial=kw["ano_inicial"])
    elif fonte == "ibge":
        ibge_sidra.executar(con, culturas=kw["culturas"])
    elif fonte == "clima":
        clima.executar(
            con,
            municipios=kw["municipios"],
            limite=kw["limite_clima"],
            cultura=config.SETTINGS.cultura_padrao,
        )
    else:
        raise ValueError(f"fonte desconhecida: {fonte}")


@app.command()
def features(
    documento: str = typer.Option(..., "--documento", help="CNPJ (com ou sem mascara)"),
    cultura: Optional[str] = typer.Option(
        None, "--cultura", help=f"Cultura de referencia (padrao: {config.CULTURA_PADRAO})"
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Nao consulta rede; usa apenas o que esta no warehouse"
    ),
) -> None:
    """Imprime o dicionario de features em JSON."""
    setup_logging()
    config.SETTINGS.ensure_dirs()
    saida = build_features(documento, cultura=cultura, permitir_rede=not offline)
    json.dump(saida, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


@app.command()
def init() -> None:
    """Cria diretorios, o schema do warehouse e o CSV modelo de protestos."""
    setup_logging()
    config.SETTINGS.ensure_dirs()
    con = warehouse.conectar()
    con.close()
    if not config.PROTESTO_CSV_MANUAL.exists():
        config.PROTESTO_CSV_MANUAL.write_text(
            protestos_mod.exemplo_csv(), encoding="utf-8"
        )
    typer.echo(f"warehouse: {config.SETTINGS.warehouse_path}")
    typer.echo(f"raw:       {config.SETTINGS.raw_dir}")
    typer.echo(f"protestos: {config.PROTESTO_CSV_MANUAL}")


@app.command()
def status() -> None:
    """Contagem de linhas por tabela e ultimas cargas registradas."""
    setup_logging()
    con = warehouse.conectar(read_only=False)
    try:
        tabelas = [
            "pgfn_divida", "rf_empresas", "rf_estabelecimentos", "rf_socios",
            "rf_simples", "rf_dominio", "socio_empresa", "ibama_autos",
            "ibama_embargos", "bcb_mdcr", "bcb_mdcr_produto", "ibge_producao",
            "ibge_municipios", "municipio_centroide", "clima_diario",
            "protesto_cache",
        ]
        for tabela in tabelas:
            typer.echo(f"{tabela:24s} {warehouse.contar(con, tabela):>12,}")
        typer.echo("")
        linhas = con.execute(
            "SELECT fonte, particao, tabela, linhas, carregado_em "
            "FROM ingestao_log ORDER BY carregado_em DESC LIMIT 15"
        ).fetchall()
        for fonte, particao, tabela, n, quando in linhas:
            typer.echo(f"{quando:%Y-%m-%d %H:%M}  {fonte:10s} {particao:22s} "
                       f"{tabela:20s} {n:>10,}")
    finally:
        con.close()


if __name__ == "__main__":
    app()
