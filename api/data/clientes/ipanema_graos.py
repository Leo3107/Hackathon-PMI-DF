"""`ipanema-graos` — lado A da invariante I5: **PD moderado com risco de RJ alto** (§7.13).

Paga a Krill Tech praticamente em dia (D1 em 882,9) e tem quatro credores
distintos executando R$ 7,9 milhões — o precursor clássico de insolvência coletiva.
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
    evidencia,
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "ipanema-graos"
CULTURAS = ["Soja", "Milho safrinha"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agrícola Ipanema Ltda",
    nome_fantasia="Agrícola Ipanema",
    documento="45.621.889/0001-62",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Barreiras",
    uf="BA",
    atividade="Produtor rural — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2014-10-17",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=5,
        atraso_medio_dias_90d=5,
        pior_atraso_dias_12m=15,
        pct_titulos_pagos_em_dia_12m=0.94,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=4,
        execucoes_titulo_90d=2,
        valor_total_em_execucao=7_900_000.0,
        credores_distintos_executando=4,
        protestos_ativos=3,
        protestos_12m=3,
        credores_protestantes_180d=3,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=2_900_000.0,
        divida_ativa_pgfn_90d_atras=2_900_000.0,
        parcelamento_rompido_12m=True,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=15,
        desvio_precipitacao_pct=-30,
        produtividade_vs_media_regional_pct=-9,
        area_total_ha=5_100,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=17,
        capital_social=8_500_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=17,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=3_060_000.0,
        p2=2_040_000.0,
        p3=5_885_000.0,
        p4=4_815_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-04-22",
        barter=barter_de("Soja", 61_673, PRECO_SACA["soja"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0266 — 61.673 sc de soja",
            8_600_000.0,
        ),
        garantia(
            ID, 2, TipoGarantia.ALIENACAO_FIDUCIARIA, "Dois tratores e um pulverizador autopropelido", 3_400_000.0
        ),
        garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 4_200_000.0),
    ],
    limite_aprovado=17_000_000.0,
    patrimonio_declarado=34_000_000.0,
    faturamento_estimado_anual=29_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.PGFN: "R$ 2.900.000 em dívida ativa, estável em 90 dias; parcelamento rompido.",
            FonteId.INTERNO_KRILLTECH: (
                "Atraso médio de 5 dias e 94% de pontualidade: a crise de liquidez está fora "
                "da relação com a Krill Tech."
            ),
        },
        extras=(
            evidencia(
                ID,
                FonteId.DATAJUD_CNJ,
                "Quatro execuções de título de credores distintos",
                "Quatro execuções de título extrajudicial de credores distintos, valor "
                "agregado R$ 7.900.000 — 50% da exposição.",
                ("execucoes_titulo", "materialidade_execucao", "pluralidade_credores", "aceleracao_judicial"),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 3, "pior_atraso_dias_12m": 9, "pct_titulos_pagos_em_dia_12m": 0.97},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0, "parcelamento_rompido_12m": False},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -3},
        },
        {
            "interno": {"atraso_medio_dias_12m": 4, "atraso_medio_dias_90d": 4, "pior_atraso_dias_12m": 11, "pct_titulos_pagos_em_dia_12m": 0.96},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 1_600_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 900_000.0, "divida_ativa_pgfn_90d_atras": 0.0, "parcelamento_rompido_12m": False},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -22, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 4, "atraso_medio_dias_90d": 5, "pior_atraso_dias_12m": 13, "pct_titulos_pagos_em_dia_12m": 0.95},
            "juridico": {"execucoes_titulo_12m": 2, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 3_400_000.0, "credores_distintos_executando": 2, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 1_800_000.0, "divida_ativa_pgfn_90d_atras": 900_000.0, "parcelamento_rompido_12m": False},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 5, "atraso_medio_dias_90d": 4, "pior_atraso_dias_12m": 14, "pct_titulos_pagos_em_dia_12m": 0.94},
            "juridico": {"execucoes_titulo_12m": 3, "execucoes_titulo_90d": 2, "valor_total_em_execucao": 6_200_000.0, "credores_distintos_executando": 3, "protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 2_900_000.0, "divida_ativa_pgfn_90d_atras": 1_800_000.0},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -27, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 5, "atraso_medio_dias_90d": 5, "pior_atraso_dias_12m": 15, "pct_titulos_pagos_em_dia_12m": 0.94},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -29, "produtividade_vs_media_regional_pct": -8},
        },
    ],
)
