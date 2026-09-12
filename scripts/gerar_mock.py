"""Gera um dataset SINTETICO com o schema exato de `features_agro.csv`.

Serve para escrever os scripts de treino antes de a carga real terminar. Os
numeros sao inventados; a forma nao e -- as colunas, os tipos e o padrao de
ausencia vem do proprio `coleta.models.Features`, entao o mock nao pode
divergir do que a API e a CLI devolvem.

Tres propriedades do dado real que o mock reproduz de proposito, porque sao
elas que quebram um pipeline de ML se ignoradas:

1. As 12 features municipais (BCB, IBGE, clima) REPETEM entre empresas do mesmo
   municipio. Split aleatorio vaza informacao entre treino e teste; use
   `GroupKFold` agrupando por `municipio_ibge`.
2. A ausencia e estruturada, nao aleatoria: quando um municipio nao esta no
   PAM, as tres features do IBGE somem JUNTAS. Imputar coluna a coluna
   destroi essa informacao -- vale carregar um indicador de faltante.
3. As categoricas sao CODIGOS em string com zero a esquerda ('02', '0115600').
   Ler com `dtype=str` nessas colunas, senao o pandas come o zero.

    python scripts/gerar_mock.py --linhas 2000

ATENCAO: `alvo_sintetico` e uma variavel-resposta FABRICADA, gerada por uma
funcao logistica conhecida (os coeficientes ficam em `alvo_coeficientes.json`).
Existe para voce validar o pipeline de ponta a ponta: se o modelo nao recuperar
os sinais daqueles coeficientes, o problema esta no seu pre-processamento, nao
nos dados. NAO e inadimplencia real e nao serve para medir performance de
modelo nenhum.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coleta import config  # noqa: E402
from coleta.models import Features  # noqa: E402

# Mesma exclusao usada em scripts/amostra_agro.py.
NAO_FEATURES = {"gerado_em", "fontes_disponiveis", "razao_social"}

PERFIS = [
    ("limpo", 0.68),
    ("divida_ativa", 0.12),
    ("passivo_ambiental_auto", 0.08),
    ("situacao_irregular", 0.06),
    ("grupo_societario", 0.04),
    ("passivo_ambiental_embargo", 0.02),
]

UFS = ["MT", "GO", "PR", "RS", "MS", "BA", "MG", "SP", "TO", "PA", "MA", "PI"]
# CNAEs agro reais: lavoura de soja, milho, cana, algodao, pecuaria, florestal.
CNAES = ["0115600", "0111301", "0113000", "0116401", "0151201", "0210101",
         "0121101", "0133403", "0220901", "0311601"]
PORTES = ["01", "03", "05"]
NATUREZAS = ["2062", "2135", "2240", "2054", "4014"]
SITUACOES_IRREGULARES = ["03", "04", "08"]


def _lognormal(rng: random.Random, mediana: float, sigma: float) -> float:
    """Valores monetarios sao assimetricos; lognormal e a forma certa."""
    return round(math.exp(math.log(mediana) + rng.gauss(0, sigma)), 2)


def _capital_social(rng: random.Random) -> float:
    """Capital social como ele e de verdade no agro: quase sempre zero.

    Medido nas 137.705 matrizes agro (CNAE 01-03) da competencia carregada:

        capital <= R$ 1 ......... 91,1%   (mediana da populacao = R$ 0)
        mediana entre os > R$ 1 .. R$ 40.000
        p95 ..................... R$ 30.000     p99 .. R$ 1.100.000

    Uma lognormal pura -- que era o que este gerador fazia -- nunca produz
    zero, e entregava mediana de R$ 189.561 para uma populacao cuja mediana e
    R$ 0. O efeito colateral nao era cosmetico: `divida_ativa_total/capital`
    ficava limitada a ~1.200 no treino e chegava a 55.776.835 no dado real,
    saturando o logit e colando o score em 1,000 para metade da carteira agro.

    Os dois patamares de zero sao os dois modos reais da Receita (8,8 mi de
    `0.00` e 2,2 mi de `1.00`): quem nao declara e quem declara o minimo.
    """
    x = rng.random()
    if x < 0.729:
        return 0.0
    if x < 0.911:
        return 1.0
    return _lognormal(rng, 40_000, 1.6)


def _sorteia_perfil(rng: random.Random) -> str:
    x = rng.random()
    acumulado = 0.0
    for nome, peso in PERFIS:
        acumulado += peso
        if x <= acumulado:
            return nome
    return PERFIS[0][0]


def _municipios(rng: random.Random, quantos: int) -> list[dict]:
    """Cada municipio carrega seu proprio bloco de features regionais.

    Um quarto deles fica sem PAM e sem clima -- e o que acontece de verdade
    com municipio que nao produz a cultura de referencia.
    """
    saida = []
    for i in range(quantos):
        uf = rng.choice(UFS)
        cod = f"{rng.randint(11, 53)}{rng.randint(10000, 99999)}"
        tem_pam = rng.random() > 0.25
        tem_bcb = rng.random() > 0.35
        tem_clima = tem_pam and rng.random() > 0.10

        prod = round(rng.gauss(3200, 600), 1) if tem_pam else None
        muni = {
            "municipio_ibge": cod,
            "uf": uf,
            # --- BCB ---
            "volume_credito_rural_municipio": (
                _lognormal(rng, 8_000_000, 1.2) if tem_bcb else None
            ),
            "n_contratos_municipio": (
                rng.randint(5, 4000) if tem_bcb else None
            ),
            "credito_por_hectare_municipio": (
                round(rng.uniform(900, 6500), 2) if tem_bcb else None
            ),
            # A MDCR nao publica acionamento de Proagro: sempre nulo, de fato.
            "acionamentos_proagro_municipio": None,
            # --- IBGE ---
            "produtividade_municipal_cultura": prod,
            "desvio_produtividade_vs_media_5a": (
                round(rng.gauss(-0.02, 0.18), 4) if tem_pam else None
            ),
            "area_plantada_municipio_cultura": (
                _lognormal(rng, 25_000, 1.4) if tem_pam else None
            ),
            # --- clima ---
            "precipitacao_acumulada_ciclo": (
                round(rng.gauss(950, 260), 1) if tem_clima else None
            ),
            "precipitacao_vs_normal_climatologica": (
                round(rng.gauss(-0.05, 0.22), 4) if tem_clima else None
            ),
            "dias_secos_consecutivos_max": (
                max(0, int(rng.gauss(18, 9))) if tem_clima else None
            ),
            "anomalia_na_fase_critica": (
                round(rng.gauss(-0.06, 0.28), 4) if tem_clima else None
            ),
        }
        if tem_bcb:
            muni["ticket_medio_municipio"] = round(
                muni["volume_credito_rural_municipio"]
                / max(muni["n_contratos_municipio"], 1),
                2,
            )
        else:
            muni["ticket_medio_municipio"] = None
        saida.append(muni)
    return saida


def _dv_cnpj(base: str) -> str:
    def calcular(numeros: str, pesos: list[int]) -> str:
        soma = sum(int(d) * p for d, p in zip(numeros, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = calcular(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return d1 + calcular(base + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])


# Coeficientes do alvo sintetico. Documentados para voce conferir se o seu
# pipeline recupera os sinais: e um teste do pre-processamento, nao do modelo.
# Os termos em log sao CENTRADOS numa referencia, senao o intercepto deixa de
# controlar a taxa base: log1p(capital) sozinho vale ~12 e afunda o logit.
REFERENCIAS = {
    "idade_empresa_meses": 240.0,
    # Zero porque a mediana real do capital social agro e zero (ver
    # `_capital_social`). Centrar em R$ 180.000 somava +2,18 ao logit de 91%
    # das linhas e a taxa base deixava de ser controlada pelo intercepto.
    "capital_social": 0.0,
}

COEFICIENTES = {
    "intercepto": -3.80,
    "log1p_divida_ativa_total": 0.20,
    "flag_situacao_irregular": 1.10,
    "n_empresas_do_socio_inaptas": 0.28,
    "n_autos_infracao": 0.14,
    "flag_embargo_ativo": 0.75,
    "log1p_idade_empresa_meses": -0.45,
    "log1p_capital_social": -0.18,
    "desvio_produtividade_vs_media_5a": -0.90,
    "anomalia_na_fase_critica": -0.55,
    "n_protestos_ativos": 0.40,
}


def _alvo(rng: random.Random, f: dict) -> int:
    c = COEFICIENTES
    z = c["intercepto"]
    z += c["log1p_divida_ativa_total"] * math.log1p(f["divida_ativa_total"] or 0)
    z += c["flag_situacao_irregular"] * (1 if f["flag_situacao_irregular"] else 0)
    z += c["n_empresas_do_socio_inaptas"] * (f["n_empresas_do_socio_inaptas"] or 0)
    z += c["n_autos_infracao"] * min(f["n_autos_infracao"] or 0, 10)
    z += c["flag_embargo_ativo"] * (1 if f["flag_embargo_ativo"] else 0)
    z += c["log1p_idade_empresa_meses"] * (
        math.log1p(f["idade_empresa_meses"] or 0)
        - math.log1p(REFERENCIAS["idade_empresa_meses"])
    )
    z += c["log1p_capital_social"] * (
        math.log1p(f["capital_social"] or 0)
        - math.log1p(REFERENCIAS["capital_social"])
    )
    # Ausente entra como zero: e a mesma escolha que voce tera de fazer.
    z += c["desvio_produtividade_vs_media_5a"] * (
        f["desvio_produtividade_vs_media_5a"] or 0.0
    )
    z += c["anomalia_na_fase_critica"] * (f["anomalia_na_fase_critica"] or 0.0)
    z += c["n_protestos_ativos"] * (f["n_protestos_ativos"] or 0)
    return 1 if rng.random() < 1 / (1 + math.exp(-z)) else 0


def gerar_linha(rng: random.Random, muni: dict, cultura: str) -> tuple[str, dict]:
    perfil = _sorteia_perfil(rng)
    base = f"{rng.randint(10_000_000, 99_999_999)}"
    cnpj = base + "0001" + _dv_cnpj(base + "0001")

    irregular = perfil == "situacao_irregular"
    situacao = rng.choice(SITUACOES_IRREGULARES) if irregular else "02"
    tem_divida = perfil == "divida_ativa" or rng.random() < 0.06
    tem_auto = perfil.startswith("passivo_ambiental") or rng.random() < 0.03
    tem_embargo = perfil == "passivo_ambiental_embargo"
    ligadas = (
        rng.randint(3, 25) if perfil == "grupo_societario" else rng.randint(0, 2)
    )
    divida = _lognormal(rng, 45_000, 1.8) if tem_divida else 0.0
    autos = rng.randint(1, 14) if tem_auto else 0
    # Protestos so existem quando ha provedor configurado; na maioria das
    # linhas a fonte simplesmente nao respondeu.
    tem_protesto_consultado = rng.random() < 0.12

    f: dict = {
        "documento": cnpj,
        "cnpj_basico": base,
        "uf": muni["uf"],
        "municipio_ibge": muni["municipio_ibge"],
        "cultura_referencia": cultura,
        # --- PGFN ---
        "divida_ativa_total": divida,
        "divida_ativa_ajuizada": round(divida * rng.uniform(0, 1), 2),
        "n_inscricoes": rng.randint(1, 9) if tem_divida else 0,
        # Passivo contingente: aparece em poucos CNPJs mas com valor alto.
        "divida_ativa_corresponsavel": (
            _lognormal(rng, 900_000, 2.2) if rng.random() < 0.04 else 0.0
        ),
        "delta_divida_2_trimestres": (
            round(divida * rng.uniform(-0.3, 0.5), 2) if tem_divida else 0.0
        ),
        "flag_divida_previdenciaria": bool(tem_divida and rng.random() < 0.4),
        "flag_divida_fgts": bool(tem_divida and rng.random() < 0.5),
        # --- Receita ---
        "idade_empresa_meses": rng.randint(6, 560),
        "capital_social": _capital_social(rng),
        "porte": rng.choice(PORTES),
        "natureza_juridica": rng.choice(NATUREZAS),
        "situacao_cadastral": situacao,
        "flag_situacao_irregular": irregular,
        "cnae_principal": rng.choice(CNAES),
        "flag_cnae_agro": True,
        "n_filiais": max(0, int(rng.expovariate(1 / 0.7))),
        "n_socios": rng.randint(1, 8),
        # --- grafo societario ---
        "n_empresas_do_socio": ligadas,
        "n_empresas_do_socio_com_divida_ativa": (
            rng.randint(0, ligadas) if ligadas else 0
        ),
        "n_empresas_do_socio_inaptas": (
            rng.randint(0, max(ligadas // 2, 0)) if ligadas else 0
        ),
        # --- IBAMA ---
        "n_autos_infracao": autos,
        "valor_multas_ambientais": (
            _lognormal(rng, 90_000, 2.0) if autos else 0.0
        ),
        "flag_embargo_ativo": tem_embargo,
        "area_embargada_ha": (
            round(rng.uniform(5, 3000), 2) if tem_embargo else 0.0
        ),
        # --- protestos ---
        "n_protestos_ativos": (
            rng.randint(0, 6) if tem_protesto_consultado else None
        ),
    }
    n_prot = f["n_protestos_ativos"]
    f["valor_total_protestado"] = (
        _lognormal(rng, 30_000, 1.5) if n_prot else (0.0 if n_prot == 0 else None)
    )
    f["dias_desde_protesto_mais_recente"] = (
        rng.randint(3, 900) if n_prot else None
    )
    f["n_cartorios_distintos"] = (
        rng.randint(1, min(n_prot, 3)) if n_prot else (0 if n_prot == 0 else None)
    )

    # Bloco municipal: identico para toda empresa do mesmo municipio.
    for chave, valor in muni.items():
        if chave not in ("uf", "municipio_ibge"):
            f[chave] = valor
    return perfil, f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--linhas", type=int, default=2000)
    ap.add_argument("--municipios", type=int, default=45)
    ap.add_argument("--cultura", default="soja")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--saida", type=Path, default=config.DATA_DIR / "mock")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    args.saida.mkdir(parents=True, exist_ok=True)
    campos = [c for c in Features.model_fields if c not in NAO_FEATURES]

    municipios = _municipios(rng, args.municipios)
    linhas: list[dict] = []
    for _ in range(args.linhas):
        muni = rng.choice(municipios)
        perfil, f = gerar_linha(rng, muni, args.cultura)
        # Passar pelo modelo garante que o mock nao possa divergir do real:
        # campo novo ou tipo errado estoura aqui, nao no seu notebook.
        validado = Features(**f).to_dict()
        linha = {"perfil": perfil, **{c: validado.get(c) for c in campos}}
        linha["alvo_sintetico"] = _alvo(rng, validado)
        linhas.append(linha)

    destino = args.saida / "features_agro_mock.csv"
    colunas = ["perfil"] + campos + ["alvo_sintetico"]
    with open(destino, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=colunas, delimiter=";")
        w.writeheader()
        w.writerows(linhas)

    with open(args.saida / "alvo_coeficientes.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "aviso": (
                    "alvo_sintetico e FABRICADO. Serve para validar o pipeline, "
                    "nao para medir performance. Nao use como inadimplencia real."
                ),
                "forma": "sigmoide(intercepto + soma(coef * termo))",
                "coeficientes": COEFICIENTES,
                "referencias_de_centragem": REFERENCIAS,
                "nota": (
                    "os termos log1p de idade_empresa_meses e capital_social "
                    "sao centrados nas referencias acima"
                ),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    # Esquema legivel: o que cada coluna e, para montar o ColumnTransformer.
    CATEGORICAS = {"porte", "natureza_juridica", "situacao_cadastral",
                   "cnae_principal", "uf", "cultura_referencia"}
    CHAVES = {"documento", "cnpj_basico", "municipio_ibge"}
    MUNICIPAIS = {k for k in municipios[0] if k not in ("uf", "municipio_ibge")}
    with open(args.saida / "esquema.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["coluna", "papel", "tipo_pandas", "nivel"])
        for c in colunas:
            if c in CHAVES:
                papel, tipo = "chave", "str"
            elif c == "perfil":
                papel, tipo = "rotulo_descritivo", "str"
            elif c == "alvo_sintetico":
                papel, tipo = "alvo_SINTETICO", "int"
            elif c in CATEGORICAS:
                papel, tipo = "categorica", "str"
            else:
                ann = str(Features.model_fields[c].annotation)
                papel = "numerica"
                tipo = "float" if "float" in ann else (
                    "boolean" if "bool" in ann else "Int64"
                )
            nivel = "municipio" if c in MUNICIPAIS else "empresa"
            w.writerow([c, papel, tipo, nivel])

    n_alvo = sum(x["alvo_sintetico"] for x in linhas)
    print(f"-> {destino}  ({len(linhas)} linhas x {len(colunas)} colunas)")
    print(f"-> {args.saida / 'esquema.csv'}")
    print(f"-> {args.saida / 'alvo_coeficientes.json'}")
    print(f"   municipios distintos: {args.municipios} "
          f"(features municipais repetem dentro de cada um)")
    print(f"   alvo_sintetico positivo: {n_alvo} ({n_alvo/len(linhas):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
