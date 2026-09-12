"""Configuracao central da camada de coleta.

Tudo que muda entre competencias (URLs, codigos de tabela do SIDRA, calendario
agricola) vive aqui, e nao espalhado pelo codigo dos coletores.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- caminhos ---

ROOT = Path(os.environ.get("COLETA_ROOT", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.environ.get("COLETA_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_PATH = Path(os.environ.get("COLETA_WAREHOUSE", DATA_DIR / "warehouse.duckdb"))

# --------------------------------------------------------------- rede/HTTP ---

MAX_REQUESTS_PER_SECOND_PER_HOST = 2.0
HTTP_TIMEOUT_SECONDS = 120.0
HTTP_MAX_RETRIES = 5
HTTP_BACKOFF_BASE_SECONDS = 1.5
USER_AGENT = os.environ.get(
    "COLETA_USER_AGENT",
    "krill-tech-coleta/0.1 (analise de risco de credito agro)",
)

# ---------------------------------------------------------- PGFN (fonte 1) ---
# Confirmado em 2026-09 baixando o inicio dos ZIPs e lendo o cabecalho real.
# Os tres sistemas de origem NAO compartilham o mesmo layout.

PGFN_BASE_URL = "https://dadosabertos.pgfn.gov.br"

PGFN_ORIGENS: dict[str, dict] = {
    "SIDA": {
        "zip": "Dados_abertos_Nao_Previdenciario.zip",
        "colunas": [
            "CPF_CNPJ", "TIPO_PESSOA", "TIPO_DEVEDOR", "NOME_DEVEDOR", "UF_DEVEDOR",
            "UNIDADE_RESPONSAVEL", "NUMERO_INSCRICAO", "TIPO_SITUACAO_INSCRICAO",
            "SITUACAO_INSCRICAO", "RECEITA_PRINCIPAL", "DATA_INSCRICAO",
            "INDICADOR_AJUIZADO", "VALOR_CONSOLIDADO",
        ],
    },
    "FGTS": {
        "zip": "Dados_abertos_FGTS.zip",
        "colunas": [
            "CPF_CNPJ", "TIPO_PESSOA", "TIPO_DEVEDOR", "NOME_DEVEDOR", "UF_DEVEDOR",
            "UNIDADE_RESPONSAVEL", "ENTIDADE_RESPONSAVEL", "UNIDADE_INSCRICAO",
            "NUMERO_INSCRICAO", "TIPO_SITUACAO_INSCRICAO", "SITUACAO_INSCRICAO",
            "RECEITA_PRINCIPAL", "DATA_INSCRICAO", "INDICADOR_AJUIZADO",
            "VALOR_CONSOLIDADO",
        ],
    },
    "PREV": {
        "zip": "Dados_abertos_Previdenciario.zip",
        # Previdenciario traz TIPO_CREDITO no lugar de RECEITA_PRINCIPAL.
        "colunas": [
            "CPF_CNPJ", "TIPO_PESSOA", "TIPO_DEVEDOR", "NOME_DEVEDOR", "UF_DEVEDOR",
            "UNIDADE_RESPONSAVEL", "NUMERO_INSCRICAO", "TIPO_SITUACAO_INSCRICAO",
            "SITUACAO_INSCRICAO", "TIPO_CREDITO", "DATA_INSCRICAO",
            "INDICADOR_AJUIZADO", "VALOR_CONSOLIDADO",
        ],
    },
}
PGFN_DICIONARIO_URL = (
    "https://www.gov.br/pgfn/pt-br/assuntos/divida-ativa-da-uniao/"
    "transparencia-fiscal-1/arquivos-dados-abertos/dicionario_de_campos.xlsx"
)
PGFN_PRIMEIRO_ANO = 2020

# ------------------------------------------------ Receita Federal (fonte 2) --
# O diretorio publico e um Nextcloud (SERPRO+). O compartilhamento publico
# aceita WebDAV usando o token do share como usuario e senha vazia: e a forma
# estavel de listar e baixar sem raspar a SPA.

RF_WEBDAV_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav"
RF_SHARE_TOKEN = os.environ.get("COLETA_RF_SHARE_TOKEN", "YggdBLfdninEJX9")
RF_METADADOS_URL = "https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf"

# Layouts posicionais (CSV sem cabecalho). Confirmados no PDF de metadados.
RF_LAYOUTS: dict[str, list[str]] = {
    "Empresas": [
        "cnpj_basico", "razao_social", "natureza_juridica",
        "qualificacao_responsavel", "capital_social", "porte",
        "ente_federativo_responsavel",
    ],
    "Estabelecimentos": [
        "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
        "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
        "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
        "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
        "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep",
        "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2", "ddd_fax",
        "fax", "correio_eletronico", "situacao_especial", "data_situacao_especial",
    ],
    "Socios": [
        "cnpj_basico", "identificador_socio", "nome_socio", "cnpj_cpf_socio",
        "qualificacao_socio", "data_entrada_sociedade", "pais",
        "representante_legal", "nome_representante",
        "qualificacao_representante", "faixa_etaria",
    ],
    "Simples": [
        "cnpj_basico", "opcao_simples", "data_opcao_simples",
        "data_exclusao_simples", "opcao_mei", "data_opcao_mei",
        "data_exclusao_mei",
    ],
    "Cnaes": ["codigo", "descricao"],
    "Motivos": ["codigo", "descricao"],
    "Municipios": ["codigo", "descricao"],
    "Naturezas": ["codigo", "descricao"],
    "Paises": ["codigo", "descricao"],
    "Qualificacoes": ["codigo", "descricao"],
}
RF_PARTICIONADOS = ("Empresas", "Estabelecimentos", "Socios")
RF_UNICOS = (
    "Simples", "Cnaes", "Motivos", "Municipios", "Naturezas", "Paises",
    "Qualificacoes",
)

# Situacao cadastral: 02 = ATIVA; 04 = INAPTA.
RF_SITUACAO_ATIVA = "02"
RF_SITUACAO_INAPTA = "04"
# Divisoes CNAE consideradas agro: 01-03 (agropecuaria, producao florestal,
# pesca) e 10-11 (industria de alimentos e bebidas).
CNAE_DIVISOES_AGRO = ("01", "02", "03", "10", "11")

# ------------------------------------------------------- IBAMA (fonte 3) -----

IBAMA_AUTOS_URL = (
    "https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/dados/"
    "SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip"
)
IBAMA_EMBARGOS_URL = (
    "https://dadosabertos.ibama.gov.br/dados/SIFISC/termo_embargo/"
    "termo_embargo/termo_embargo.csv"
)

# ---------------------------------------------------------- BCB/MDCR (4) ----

BCB_SICOR_ODATA = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata"
BCB_RECURSO_CONTRATOS = "CusteioInvestimentoComercialIndustrialSemFiltros"
BCB_RECURSO_CUSTEIO_PRODUTO = "CusteioMunicipioProduto"
BCB_PAGE_SIZE = 5000  # acima disso o gateway do Olinda devolve 504
BCB_ANO_INICIAL = 2020

# ------------------------------------------------------- IBGE/SIDRA (5) -----

SIDRA_VALUES_URL = "https://apisidra.ibge.gov.br/values"
IBGE_LOCALIDADES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
IBGE_MALHAS_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios"

# Tabela 5457 (PAM) confirmada em /api/v3/agregados/5457/metadados.
SIDRA_TABELA_PAM = "5457"
SIDRA_TABELA_LSPA = "6588"
SIDRA_CLASSIFICACAO_PRODUTO = "782"
SIDRA_VARIAVEIS_PAM = {
    "area_plantada_ha": "8331",
    "area_colhida_ha": "216",
    "quantidade_produzida_t": "214",
    "rendimento_medio_kg_ha": "112",
}
SIDRA_PRODUTOS = {
    "soja": "40124",
    "milho": "40122",
    "algodao": "40099",
    "cafe": "40104",
    "cana": "40106",
    "feijao": "40112",
    "arroz": "40102",
    "trigo": "40127",
    "sorgo": "40125",
}
SIDRA_ANOS_JANELA = 7  # ano corrente + 6: garante 5 anos completos de base

# ----------------------------------------------------------- clima (6) ------

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_PARAMETROS = "PRECTOTCORR,T2M_MAX,T2M_MIN"
NASA_POWER_FILL_VALUE = -999.0
NORMAL_CLIMATOLOGICA_INICIO = 1991
NORMAL_CLIMATOLOGICA_FIM = 2020

INMET_ESTACOES_URL = "https://apitempo.inmet.gov.br/estacoes/T"
INMET_DIARIO_URL = "https://apitempo.inmet.gov.br/estacao/diaria"

PROVEDOR_CLIMA = os.environ.get("COLETA_PROVEDOR_CLIMA", "nasa_power")


@dataclass(frozen=True)
class CalendarioCultura:
    """Janela de safra de uma cultura, em (mes, dia).

    `fase_critica_offset` e a janela de florescimento/enchimento de graos,
    contada em dias apos a semeadura: e nela que o deficit hidrico derruba
    produtividade de fato.
    """

    nome: str
    semeadura_mes_dia: tuple[int, int]
    colheita_mes_dia: tuple[int, int]
    fase_critica_offset: tuple[int, int]


# Calendario padrao Centro-Oeste / MATOPIBA.
CALENDARIO_CULTURAS: dict[str, CalendarioCultura] = {
    "soja": CalendarioCultura("soja", (10, 15), (3, 15), (55, 95)),
    "milho": CalendarioCultura("milho", (2, 1), (7, 15), (50, 85)),
    "algodao": CalendarioCultura("algodao", (12, 1), (7, 1), (70, 120)),
    "cafe": CalendarioCultura("cafe", (9, 1), (7, 1), (30, 75)),
    "cana": CalendarioCultura("cana", (10, 1), (8, 1), (90, 180)),
    "feijao": CalendarioCultura("feijao", (11, 1), (2, 15), (35, 65)),
    "arroz": CalendarioCultura("arroz", (11, 1), (4, 1), (60, 95)),
    "trigo": CalendarioCultura("trigo", (5, 1), (9, 15), (55, 90)),
    "sorgo": CalendarioCultura("sorgo", (2, 1), (7, 1), (50, 85)),
}
CULTURA_PADRAO = os.environ.get("COLETA_CULTURA_PADRAO", "soja")
DIAS_SEM_CHUVA_LIMIAR_MM = 1.0

# -------------------------------------------------------- protestos (7) -----

PROVEDOR_PROTESTO = os.environ.get("COLETA_PROVEDOR_PROTESTO", "csv_manual")
PROTESTO_CSV_MANUAL = RAW_DIR / "protestos_manual.csv"
PROTESTO_API_BASE_URL = os.environ.get("PROTESTO_API_BASE_URL", "")
PROTESTO_API_TOKEN_ENV = "PROTESTO_API_TOKEN"
PROTESTO_CACHE_TTL_HORAS = 24


@dataclass
class Settings:
    """Agrupa o que a CLI pode sobrescrever em runtime."""

    warehouse_path: Path = WAREHOUSE_PATH
    raw_dir: Path = RAW_DIR
    provedor_clima: str = PROVEDOR_CLIMA
    provedor_protesto: str = PROVEDOR_PROTESTO
    cultura_padrao: str = CULTURA_PADRAO
    extras: dict = field(default_factory=dict)

    def ensure_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.warehouse_path.parent.mkdir(parents=True, exist_ok=True)


SETTINGS = Settings()
