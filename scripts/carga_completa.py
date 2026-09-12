"""Carga completa, sequencial, para montar a base de treino.

Sequencial de proposito: o DuckDB aceita um escritor por vez, entao rodar as
fontes em paralelo so produziria conflito de lock.

A ordem segue as dependencias: PGFN e Receita primeiro (independentes), IBGE
antes do clima (que precisa do centroide dos municipios produtores), BCB por
ultimo porque e o que menos rende.

Uma fonte que falha e registrada e nao impede as seguintes.

    python scripts/carga_completa.py
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coleta import warehouse  # noqa: E402
from coleta.bulk import bcb_mdcr, clima, ibama, ibge_sidra, pgfn, receita  # noqa: E402

# Duas competencias da PGFN sao o minimo para `delta_divida_2_trimestres`
# existir: com um trimestre so, a feature nasce sempre nula.
# Escopo "enxuto": o suficiente para amostrar milhares de CNPJs agro sem
# baixar os 8,4 GB da Receita. A particao 0 fica de fora de proposito -- ela
# sozinha e ~6x uma particao normal (Estabelecimentos0 tem 2,2 GB).
PARTES_RECEITA = (1, 2, 3, 4)
CULTURAS = ("soja", "milho", "cana")
MUNICIPIOS_CLIMA = 40

ETAPAS = [
    ("pgfn", lambda con: pgfn.executar(con, quarters=2)),
    (
        "receita",
        lambda con: receita.executar(
            con, competencia="2026-08", partes=PARTES_RECEITA
        ),
    ),
    ("ibama", lambda con: ibama.executar(con)),
    ("ibge", lambda con: ibge_sidra.executar(con, culturas=CULTURAS)),
    ("bcb", lambda con: bcb_mdcr.executar(con, ano_inicial=2020)),
    (
        "clima",
        lambda con: clima.executar(
            con, limite=MUNICIPIOS_CLIMA, cultura="soja"
        ),
    ),
]


def main() -> int:
    con = warehouse.conectar()
    falhas: list[tuple[str, str]] = []
    try:
        for nome, fn in ETAPAS:
            inicio = time.time()
            print(f"\n=== {nome} ===", flush=True)
            try:
                linhas = fn(con)
                print(
                    f"=== {nome}: {linhas:,} linhas em {time.time()-inicio:.0f}s",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001 - isolamento por fonte
                falhas.append((nome, f"{type(exc).__name__}: {exc}"))
                print(f"=== {nome} FALHOU apos {time.time()-inicio:.0f}s", flush=True)
                traceback.print_exc()
    finally:
        print("\n=== contagens finais ===", flush=True)
        for tabela in (
            "pgfn_divida", "rf_empresas", "rf_estabelecimentos", "rf_socios",
            "rf_simples", "socio_empresa", "ibama_autos", "ibama_embargos",
            "bcb_mdcr", "ibge_producao", "clima_diario",
        ):
            print(f"{tabela:24s} {warehouse.contar(con, tabela):>14,}", flush=True)
        con.close()

    if falhas:
        print("\n=== FALHAS ===", flush=True)
        for nome, erro in falhas:
            print(f"  {nome}: {erro}", flush=True)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
