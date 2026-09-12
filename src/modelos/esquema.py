"""Papeis das colunas, lidos de `data/mock/esquema.csv` quando ele existe.

Por que nao uma lista chumbada: `esquema.csv` e gerado pelo mesmo script que
gera o mock, a partir de `coleta.models.Features`. Quem adiciona uma feature na
coleta mexe em um lugar so. As constantes abaixo sao o FALLBACK para quando o
esquema nao esta em disco (ex.: servidor de inferencia, que nao versiona o
mock) -- e o bundle salvo carrega a sua propria copia da lista de colunas,
entao a inferencia nunca depende deste arquivo estar sincronizado.
"""
from __future__ import annotations

import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ESQUEMA_CSV = RAIZ / "data" / "mock" / "esquema.csv"

ALVO = "alvo_sintetico"
GRUPO = "municipio_ibge"

# `perfil` e o rotulo do gerador sintetico: saber que a empresa e do perfil
# "divida_ativa" e saber metade da resposta. Fora. As chaves tambem saem --
# `municipio_ibge` volta como GRUPO do cross-validation, nunca como feature
# (45 municipios em 3000 linhas viram um id memorizavel).
COLUNAS_EXCLUIDAS = frozenset(
    {
        "perfil",
        "documento",
        "cnpj_basico",
        "municipio_ibge",
        "razao_social",
        "gerado_em",
        "fontes_disponiveis",
        ALVO,
        # A MDCR nao publica acionamentos de Proagro: a coluna existe no
        # contrato da coleta e vem 100% nula tanto no mock quanto em producao.
        # Manter uma coluna constante-nula so adiciona ruido ao one-hot.
        "acionamentos_proagro_municipio",
    }
)

CATEGORICAS = (
    "uf",
    "cultura_referencia",
    "porte",
    "natureza_juridica",
    "situacao_cadastral",
    "cnae_principal",
)

# Codigos com zero a esquerda: '02', '0115600'. Ler como int come o zero e
# '02' vira 2, que nao casa com o que a API manda. dtype=str obrigatorio.
COLUNAS_TEXTO = CATEGORICAS + ("perfil", "documento", "cnpj_basico", "municipio_ibge")

BOOLEANAS = (
    "flag_divida_previdenciaria",
    "flag_divida_fgts",
    "flag_situacao_irregular",
    "flag_cnae_agro",
    "flag_embargo_ativo",
)

INTEIRAS = (
    "n_inscricoes",
    "idade_empresa_meses",
    "n_filiais",
    "n_socios",
    "n_empresas_do_socio",
    "n_empresas_do_socio_com_divida_ativa",
    "n_empresas_do_socio_inaptas",
    "n_autos_infracao",
    "n_contratos_municipio",
    "acionamentos_proagro_municipio",
    "dias_secos_consecutivos_max",
    "n_protestos_ativos",
    "dias_desde_protesto_mais_recente",
    "n_cartorios_distintos",
)

FLUTUANTES = (
    "divida_ativa_total",
    "divida_ativa_ajuizada",
    "delta_divida_2_trimestres",
    "capital_social",
    "valor_multas_ambientais",
    "area_embargada_ha",
    "volume_credito_rural_municipio",
    "ticket_medio_municipio",
    "credito_por_hectare_municipio",
    "produtividade_municipal_cultura",
    "desvio_produtividade_vs_media_5a",
    "area_plantada_municipio_cultura",
    "precipitacao_acumulada_ciclo",
    "precipitacao_vs_normal_climatologica",
    "anomalia_na_fase_critica",
    "valor_total_protestado",
)

# ---------------------------------------------------------------------------
# Blocos de ausencia.
#
# A ausencia NAO e aleatoria: quando um municipio nao esta no PAM do IBGE, as
# tres features de producao somem JUNTAS. Imputar coluna a coluna joga essa
# informacao fora. A sentinela de cada bloco gera UM indicador `falta_<bloco>`
# -- um por bloco, nao um por coluna, que e o que mantem o one-hot enxuto e o
# sinal legivel.
# ---------------------------------------------------------------------------
BLOCOS_AUSENCIA: dict[str, tuple[str, ...]] = {
    "bcb": (
        "volume_credito_rural_municipio",
        "n_contratos_municipio",
        "ticket_medio_municipio",
        "credito_por_hectare_municipio",
    ),
    "ibge": (
        "produtividade_municipal_cultura",
        "desvio_produtividade_vs_media_5a",
        "area_plantada_municipio_cultura",
    ),
    "clima": (
        "precipitacao_acumulada_ciclo",
        "precipitacao_vs_normal_climatologica",
        "dias_secos_consecutivos_max",
        "anomalia_na_fase_critica",
    ),
    "protestos": (
        "n_protestos_ativos",
        "valor_total_protestado",
        "dias_desde_protesto_mais_recente",
        "n_cartorios_distintos",
    ),
}

# Referencias de centragem dos termos log1p. Iguais as de
# `data/mock/alvo_coeficientes.json` de proposito: log1p(capital_social) sozinho
# vale ~12 e domina o intercepto de um modelo linear.
REFERENCIAS_LOG = {
    "idade_empresa_meses": 240.0,
    # Mediana real do capital social agro e R$ 0 (91% das matrizes declaram
    # <= R$ 1). Tem de bater com `REFERENCIAS` de `scripts/gerar_mock.py`.
    "capital_social": 0.0,
}


def _ler_esquema_csv(caminho: Path = ESQUEMA_CSV) -> dict[str, dict[str, str]]:
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8", newline="") as fh:
        return {linha["coluna"]: linha for linha in csv.DictReader(fh, delimiter=";")}


def colunas_brutas() -> list[str]:
    """Ordem canonica das colunas de entrada, do esquema em disco se houver."""
    do_csv = _ler_esquema_csv()
    if do_csv:
        return list(do_csv)
    return [
        "perfil", "documento", "cnpj_basico", "uf", "municipio_ibge",
        "cultura_referencia", *FLUTUANTES[:2], "n_inscricoes",
        "delta_divida_2_trimestres", *BOOLEANAS[:2], "idade_empresa_meses",
        "capital_social", "porte", "natureza_juridica", "situacao_cadastral",
        "flag_situacao_irregular", "cnae_principal", "flag_cnae_agro",
        "n_filiais", "n_socios", "n_empresas_do_socio",
        "n_empresas_do_socio_com_divida_ativa", "n_empresas_do_socio_inaptas",
        "n_autos_infracao", "valor_multas_ambientais", "flag_embargo_ativo",
        "area_embargada_ha", *BLOCOS_AUSENCIA["bcb"],
        "acionamentos_proagro_municipio", *BLOCOS_AUSENCIA["ibge"],
        *BLOCOS_AUSENCIA["clima"], *BLOCOS_AUSENCIA["protestos"], ALVO,
    ]


def features_de_entrada() -> list[str]:
    """Colunas que o pipeline consome, na ordem. Sem alvo, chaves ou rotulos."""
    return [c for c in colunas_brutas() if c not in COLUNAS_EXCLUIDAS]


def mapa_dtypes() -> dict[str, str]:
    """dtype por coluna para `pd.read_csv`. Só as de texto precisam ser fixadas."""
    return {c: "string" for c in COLUNAS_TEXTO}


__all__ = [
    "ALVO", "GRUPO", "BLOCOS_AUSENCIA", "BOOLEANAS", "CATEGORICAS",
    "COLUNAS_EXCLUIDAS", "COLUNAS_TEXTO", "FLUTUANTES", "INTEIRAS",
    "REFERENCIAS_LOG", "colunas_brutas", "features_de_entrada", "mapa_dtypes",
]
