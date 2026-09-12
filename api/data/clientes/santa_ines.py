"""`santa-ines` — cliente excelente, rating A. Referência superior da carteira.

`specs/06-dados-simulados.md` §7.1. Exposição R$ 14.000.000 · score de calibração 917,9.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.enums import (
    EstadoCliente,
    FonteId,
    OrigemCliente,
    RiscoZarc,
    TipoGarantia,
    TipoOperacao,
    TipoPessoa,
)
from models.fatos import (
    FatosAgro,
    FatosAmbientais,
    FatosCadastrais,
    FatosDoCliente,
    FatosFiscais,
    FatosInternos,
    FatosJuridicos,
)

from .._base import (
    DATA_REFERENCIA,
    PRECO_SACA,
    barter_de,
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "santa-ines"
CULTURAS = ["Soja", "Milho safrinha", "Algodão"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Fazenda Santa Inês Agropecuária Ltda",
    nome_fantasia="Fazenda Santa Inês",
    documento="47.480.012/0001-24",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Sorriso",
    uf="MT",
    atividade="Produtor rural — grãos e fibras",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2016-03-14",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

_GARANTIAS = [
    garantia(
        ID,
        1,
        TipoGarantia.CPR_FINANCEIRA,
        "CPR financeira nº 2026/0114 — 55.020 sc de soja",
        6_500_000.0,
    ),
    garantia(
        ID,
        2,
        TipoGarantia.ALIENACAO_FIDUCIARIA,
        "Colheitadeira e plantadeira, 2 unidades",
        3_200_000.0,
    ),
    garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de algodão 2026/27", 5_000_000.0),
]

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=5,
        atraso_medio_dias_90d=6,
        pior_atraso_dias_12m=18,
        pct_titulos_pagos_em_dia_12m=0.92,
    ),
    juridico=FatosJuridicos(
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=1,
        sem_litigio_36m=True,
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=11,
        desvio_precipitacao_pct=-24,
        produtividade_vs_media_regional_pct=-5,
        area_total_ha=7_100,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=14,
        capital_social=11_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=14,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=2_520_000.0,
        p2=1_680_000.0,
        p3=5_390_000.0,
        p4=4_410_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2023-08-15",
        barter=barter_de("Soja", 55_020, PRECO_SACA["soja"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=_GARANTIAS,
    limite_aprovado=16_000_000.0,
    patrimonio_declarado=96_000_000.0,
    faturamento_estimado_anual=78_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.RECEITA_FEDERAL: "CNPJ ativo desde 2012, CNAE 0115-6/00 compatível.",
            FonteId.DATAJUD_CNJ: "Nenhuma execução de título nos últimos 36 meses.",
            FonteId.PGFN: "Certidão negativa de débitos federais e dívida ativa zerada.",
            FonteId.CARTORIO_PROTESTO: (
                "Dois protestos ativos de fornecedor de combustível, contestados "
                "administrativamente. Ato extrajudicial — não configura litígio."
            ),
            FonteId.MAPA_ZARC: "ZARC moderado para soja em Sorriso/MT na janela 2026/27.",
            FonteId.INTERNO_KRILLTECH: (
                "Atraso médio de 5 dias em 12 meses e 92% dos títulos pagos em dia."
            ),
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {
                "atraso_medio_dias_12m": 3,
                "atraso_medio_dias_90d": 3,
                "pior_atraso_dias_12m": 11,
                "pct_titulos_pagos_em_dia_12m": 0.96,
            },
            "juridico": {"protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "agro": {
                "quebra_safra_regional_pct": 4,
                "desvio_precipitacao_pct": -9,
                "produtividade_vs_media_regional_pct": 4,
            },
        },
        {
            "interno": {
                "atraso_medio_dias_12m": 3,
                "atraso_medio_dias_90d": 4,
                "pior_atraso_dias_12m": 12,
                "pct_titulos_pagos_em_dia_12m": 0.95,
            },
            "juridico": {"protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "agro": {
                "quebra_safra_regional_pct": 6,
                "desvio_precipitacao_pct": -13,
                "produtividade_vs_media_regional_pct": 2,
            },
        },
        {
            "interno": {
                "atraso_medio_dias_12m": 4,
                "atraso_medio_dias_90d": 5,
                "pior_atraso_dias_12m": 14,
                "pct_titulos_pagos_em_dia_12m": 0.94,
            },
            "juridico": {"protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {
                "quebra_safra_regional_pct": 8,
                "desvio_precipitacao_pct": -18,
                "produtividade_vs_media_regional_pct": 0,
            },
        },
        {
            "interno": {
                "atraso_medio_dias_12m": 4,
                "atraso_medio_dias_90d": 5,
                "pior_atraso_dias_12m": 16,
                "pct_titulos_pagos_em_dia_12m": 0.93,
            },
            "juridico": {"protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {
                "quebra_safra_regional_pct": 9,
                "desvio_precipitacao_pct": -21,
                "produtividade_vs_media_regional_pct": -2,
            },
        },
        {
            "interno": {
                "atraso_medio_dias_12m": 5,
                "atraso_medio_dias_90d": 6,
                "pior_atraso_dias_12m": 18,
                "pct_titulos_pagos_em_dia_12m": 0.92,
            },
            "agro": {
                "quebra_safra_regional_pct": 10,
                "desvio_precipitacao_pct": -22,
                "produtividade_vs_media_regional_pct": -4,
            },
        },
    ],
)
