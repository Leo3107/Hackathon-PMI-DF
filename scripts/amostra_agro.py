"""Amostra estratificada de CNPJs agro + export do dataset de features.

Gera dois arquivos:

  data/amostra_agro.csv      identificacao e o perfil de risco de cada CNPJ
  data/features_agro.csv     as 39 features, uma linha por CNPJ, pronto para
                             `pandas.read_csv` e sklearn

A estratificacao existe porque uma amostra aleatoria de CNPJs agro seria quase
toda de microempresa ativa sem nenhum passivo -- o modelo nao teria o que
aprender. Os perfis abaixo forcam a presenca dos casos raros (divida ativa,
passivo ambiental, situacao irregular, socio com empresa inapta).

    python scripts/amostra_agro.py --por-perfil 80
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coleta import config, warehouse  # noqa: E402
from coleta.features import build_features  # noqa: E402
from coleta.models import Features  # noqa: E402

# Colunas que nao entram no dataset de treino: chave, texto livre e metadados.
NAO_FEATURES = {"gerado_em", "fontes_disponiveis", "razao_social"}

SQL_BASE = """
WITH agro AS (
    SELECT e.cnpj, e.cnpj_basico, e.uf, e.municipio AS municipio_rf,
           e.cnae_fiscal_principal AS cnae, e.situacao_cadastral,
           em.razao_social, em.porte, em.capital_social
    FROM rf_estabelecimentos e
    JOIN rf_empresas em
      ON em.cnpj_basico = e.cnpj_basico AND em.competencia = e.competencia
    WHERE e.competencia = (SELECT max(competencia) FROM rf_estabelecimentos)
      AND e.identificador_matriz_filial = '1'
      AND substr(lpad(e.cnae_fiscal_principal, 7, '0'), 1, 2) IN ('01','02','03')
),
sinais AS (
    SELECT a.*,
           coalesce(d.valor, 0)            AS divida,
           coalesce(i.autos, 0)            AS autos,
           coalesce(emb.embargos, 0)       AS embargos,
           coalesce(g.ligadas, 0)          AS empresas_ligadas
    FROM agro a
    LEFT JOIN (
        SELECT documento, sum(valor_consolidado) AS valor
        FROM pgfn_divida
        WHERE competencia = (SELECT max(competencia) FROM pgfn_divida)
        GROUP BY 1
    ) d ON d.documento = a.cnpj
    LEFT JOIN (
        SELECT documento, count(*) AS autos FROM ibama_autos
        WHERE coalesce(upper(sit_cancelado), 'N') <> 'S' GROUP BY 1
    ) i ON i.documento = a.cnpj
    LEFT JOIN (
        SELECT documento, count(*) AS embargos FROM ibama_embargos
        WHERE data_desembargo IS NULL
          AND coalesce(upper(sit_cancelado), 'N') <> 'S' GROUP BY 1
    ) emb ON emb.documento = a.cnpj
    LEFT JOIN (
        SELECT se.cnpj_basico, count(DISTINCT se2.cnpj_basico) AS ligadas
        FROM socio_empresa se
        JOIN socio_empresa se2 USING (socio_id)
        WHERE se2.cnpj_basico <> se.cnpj_basico
        GROUP BY 1
    ) g ON g.cnpj_basico = a.cnpj_basico
),
rotulado AS (
    SELECT *,
        CASE
            WHEN embargos > 0            THEN 'passivo_ambiental_embargo'
            WHEN autos > 0               THEN 'passivo_ambiental_auto'
            WHEN divida > 0              THEN 'divida_ativa'
            WHEN situacao_cadastral <> '02' THEN 'situacao_irregular'
            WHEN empresas_ligadas >= 3   THEN 'grupo_societario'
            ELSE 'limpo'
        END AS perfil
    FROM sinais
)
SELECT cnpj, razao_social, uf, cnae, porte, situacao_cadastral,
       round(divida, 2) AS divida, autos, embargos, empresas_ligadas, perfil
FROM rotulado
QUALIFY row_number() OVER (PARTITION BY perfil ORDER BY random()) <= ?
ORDER BY perfil, uf
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-perfil", type=int, default=80)
    ap.add_argument("--cultura", default=config.CULTURA_PADRAO)
    ap.add_argument("--saida", type=Path, default=config.DATA_DIR)
    ap.add_argument(
        "--reusar", action="store_true",
        help="reaproveita amostra_agro.csv em vez de re-sortear (a query de "
             "amostragem leva ~11 min e devolveria outros CNPJs)",
    )
    ap.add_argument(
        "--features-por-perfil", type=int, default=None, metavar="N",
        help="exporta features de no maximo N CNPJs por perfil. `build_features`"
             " custa ~3 s por CNPJ no warehouse cheio, entao os 720 da amostra"
             " levam ~37 min; com N=20 sai em ~6 min e ainda cobre os 6 perfis.",
    )
    args = ap.parse_args()

    con = warehouse.conectar(read_only=True)
    caminho_amostra = args.saida / "amostra_agro.csv"
    if args.reusar and caminho_amostra.exists():
        with open(caminho_amostra, encoding="utf-8", newline="") as fh:
            leitor = csv.reader(fh, delimiter=";")
            colunas = next(leitor)
            linhas = [tuple(r) for r in leitor]
        print(f"amostra reaproveitada: {len(linhas)} CNPJs", flush=True)
    else:
        linhas = con.execute(SQL_BASE, [args.por_perfil]).fetchall()
        colunas = [d[0] for d in con.description]
        print(f"amostra: {len(linhas)} CNPJs", flush=True)

    contagem: dict[str, int] = {}
    for linha in linhas:
        perfil = linha[colunas.index("perfil")]
        contagem[perfil] = contagem.get(perfil, 0) + 1
    for perfil, n in sorted(contagem.items(), key=lambda x: -x[1]):
        print(f"  {perfil:28s} {n:>5}", flush=True)

    args.saida.mkdir(parents=True, exist_ok=True)
    if not args.reusar:
        with open(caminho_amostra, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(colunas)
            w.writerows(linhas)
        print(f"-> {caminho_amostra}", flush=True)

    # Dataset de features. `permitir_rede=False` mantem tudo reproduzivel: o
    # que nao estiver no warehouse vira None e fica visivel como tal.
    campos = [c for c in Features.model_fields if c not in NAO_FEATURES]
    caminho_features = args.saida / "features_agro.csv"
    inicio = time.time()
    i_cnpj = colunas.index("cnpj")
    i_perfil = colunas.index("perfil")

    # O corte e POR PERFIL, nao um `linhas[:N]`: a amostra sai ordenada por
    # perfil, entao truncar a lista inteira daria um arquivo com os dois
    # primeiros perfis completos e os outros quatro zerados.
    if args.features_por_perfil:
        vistos: dict[str, int] = {}
        selecionadas = []
        for linha in linhas:
            perfil = linha[i_perfil]
            if vistos.get(perfil, 0) >= args.features_por_perfil:
                continue
            vistos[perfil] = vistos.get(perfil, 0) + 1
            selecionadas.append(linha)
        linhas = selecionadas
        print(f"features limitadas a {args.features_por_perfil}/perfil: "
              f"{len(linhas)} CNPJs", flush=True)
    with open(caminho_features, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["perfil"] + campos, delimiter=";")
        w.writeheader()
        for n, linha in enumerate(linhas, 1):
            f = build_features(
                linha[i_cnpj], con=con, cultura=args.cultura, permitir_rede=False
            )
            w.writerow(
                {"perfil": linha[i_perfil], **{c: f.get(c) for c in campos}}
            )
            if n % 100 == 0:
                print(f"  {n}/{len(linhas)}  {time.time()-inicio:.0f}s", flush=True)
    con.close()
    print(f"-> {caminho_features} ({len(linhas)} linhas, {len(campos)} colunas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
