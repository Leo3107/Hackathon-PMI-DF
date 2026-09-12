"""As 14 fontes públicas e internas do dataset simulado — `specs/06-dados-simulados.md` §10.3.

Rótulos humanos e abreviações usadas na composição dos ids de evidência. Sem
I/O, sem rede: toda consulta deste protótipo é **simulada**.
"""

from __future__ import annotations

from models.enums import FonteId, TipoEvidencia

__all__ = ["ROTULOS_FONTE", "ABREVIACAO_FONTE", "TIPO_POR_FONTE", "FONTES_UNIVERSAIS"]

ROTULOS_FONTE: dict[FonteId, str] = {
    FonteId.RECEITA_FEDERAL: "Receita Federal — CNPJ/CPF",
    FonteId.REDESIM: "Redesim — atos societários",
    FonteId.DATAJUD_CNJ: "DataJud — CNJ",
    FonteId.DJE: "Diário da Justiça Eletrônico",
    FonteId.CARTORIO_PROTESTO: "Central de Protestos — CENPROT",
    FonteId.PGFN: "PGFN — Dívida Ativa da União",
    FonteId.TST_CNDT: "TST — Certidão Negativa de Débitos Trabalhistas",
    FonteId.CAIXA_CRF_FGTS: "Caixa — CRF/FGTS",
    FonteId.SICAR: "SICAR — Cadastro Ambiental Rural",
    FonteId.IBAMA: "IBAMA — embargos e autos de infração",
    FonteId.CONAB: "CONAB — levantamento de safra",
    FonteId.MAPA_ZARC: "MAPA — Zoneamento Agrícola de Risco Climático",
    FonteId.INMET: "INMET — normais climatológicas",
    FonteId.INTERNO_KRILLTECH: "Krill Tech — histórico interno",
}

#: Segmento do id de evidência (`EVID-<CLIENTE>-<ABREV>-<n>`).
ABREVIACAO_FONTE: dict[FonteId, str] = {
    FonteId.RECEITA_FEDERAL: "RFB",
    FonteId.REDESIM: "REDESIM",
    FonteId.DATAJUD_CNJ: "DATAJUD",
    FonteId.DJE: "DJE",
    FonteId.CARTORIO_PROTESTO: "CENPROT",
    FonteId.PGFN: "PGFN",
    FonteId.TST_CNDT: "CNDT",
    FonteId.CAIXA_CRF_FGTS: "FGTS",
    FonteId.SICAR: "SICAR",
    FonteId.IBAMA: "IBAMA",
    FonteId.CONAB: "CONAB",
    FonteId.MAPA_ZARC: "ZARC",
    FonteId.INMET: "INMET",
    FonteId.INTERNO_KRILLTECH: "INTERNO",
}

TIPO_POR_FONTE: dict[FonteId, TipoEvidencia] = {
    FonteId.RECEITA_FEDERAL: TipoEvidencia.CADASTRO,
    FonteId.REDESIM: TipoEvidencia.CADASTRO,
    FonteId.DATAJUD_CNJ: TipoEvidencia.PROCESSO,
    FonteId.DJE: TipoEvidencia.PUBLICACAO,
    FonteId.CARTORIO_PROTESTO: TipoEvidencia.CERTIDAO,
    FonteId.PGFN: TipoEvidencia.CERTIDAO,
    FonteId.TST_CNDT: TipoEvidencia.CERTIDAO,
    FonteId.CAIXA_CRF_FGTS: TipoEvidencia.CERTIDAO,
    FonteId.SICAR: TipoEvidencia.CADASTRO,
    FonteId.IBAMA: TipoEvidencia.CADASTRO,
    FonteId.CONAB: TipoEvidencia.SERIE_HISTORICA,
    FonteId.MAPA_ZARC: TipoEvidencia.LAUDO,
    FonteId.INMET: TipoEvidencia.SERIE_HISTORICA,
    FonteId.INTERNO_KRILLTECH: TipoEvidencia.INTERNO,
}

#: As onze fontes consultadas para **todos** os 22 registros, com os fatores do
#: catálogo de `specs/02-motor-de-risco.md` §4 que cada uma sustenta.
FONTES_UNIVERSAIS: tuple[tuple[FonteId, str, tuple[str, ...]], ...] = (
    (
        FonteId.RECEITA_FEDERAL,
        "Consulta cadastral de CNPJ/CPF",
        ("situacao_cadastral", "tempo_atividade", "cnae_incompativel"),
    ),
    (
        FonteId.DATAJUD_CNJ,
        "Varredura de execuções de título extrajudicial",
        (
            "execucoes_titulo",
            "materialidade_execucao",
            "aceleracao_judicial",
            "pluralidade_credores",
            "sem_litigio",
        ),
    ),
    (
        FonteId.PGFN,
        "Certidão de situação fiscal e dívida ativa da União",
        ("divida_ativa", "divida_ativa_crescente", "certidoes_negativas"),
    ),
    (
        FonteId.TST_CNDT,
        "Certidão negativa de débitos trabalhistas",
        ("cndt_positiva", "trabalhistas"),
    ),
    (
        FonteId.CAIXA_CRF_FGTS,
        "Certificado de regularidade do FGTS",
        ("fgts_irregular",),
    ),
    (
        FonteId.SICAR,
        "Situação do Cadastro Ambiental Rural",
        (
            "car_ausente",
            "car_irregular",
            "car_regular",
            "sobreposicao_app",
            "monocultura",
            "diversificacao",
        ),
    ),
    (
        FonteId.IBAMA,
        "Consulta de embargos e autos de infração ambiental",
        ("embargo_ibama", "auto_infracao"),
    ),
    (
        FonteId.CONAB,
        "Levantamento de safra e produtividade regional",
        ("quebra_safra_regional", "produtividade_abaixo"),
    ),
    (
        FonteId.MAPA_ZARC,
        "Zoneamento agrícola de risco climático da cultura",
        ("zarc_risco",),
    ),
    (
        FonteId.INMET,
        "Precipitação acumulada vs. normal climatológica",
        ("desvio_precipitacao",),
    ),
    (
        FonteId.INTERNO_KRILLTECH,
        "Histórico interno de pagamento e exposição",
        (
            "atraso_medio",
            "pior_atraso",
            "pontualidade",
            "renegociacoes",
            "inadimplencia_tecnica",
            "tendencia_atraso",
            "relacionamento",
            "historico_limpo",
            "barter_sem_lastro",
            "irrigacao_ou_seguro",
            "descoberto_extraconcursal",
            "descoberto_total",
            "utilizacao_limite",
            "concentracao_patrimonial",
            "vencimento_concentrado",
            "sobrecolateral",
        ),
    ),
)
