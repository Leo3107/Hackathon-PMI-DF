"""`serra-do-urucui` — **risco climático alto** (§7.7).

Dimensão agroclimática em 118/1000, a mais baixa da carteira: seca progressiva
no sul do Piauí ao longo dos seis snapshots.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.enums import (
    EstadoCliente,
    FonteId,
    OrigemCliente,
    RiscoZarc,
    SituacaoCar,
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

ID = "serra-do-urucui"
CULTURAS = ["Soja", "Milho"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agropecuária Serra do Uruçuí Ltda",
    nome_fantasia="Serra do Uruçuí",
    documento="44.107.266/0001-03",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Uruçuí",
    uf="PI",
    atividade="Produtor rural — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2018-04-25",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=18,
        atraso_medio_dias_90d=26,
        pior_atraso_dias_12m=52,
        pct_titulos_pagos_em_dia_12m=0.72,
        renegociacoes_12m=2,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=1,
        valor_total_em_execucao=300_000.0,
        credores_distintos_executando=1,
        protestos_ativos=1,
        protestos_12m=1,
        credores_protestantes_180d=1,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=520_000.0, divida_ativa_pgfn_90d_atras=520_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.CRITICO,
        quebra_safra_regional_pct=34,
        desvio_precipitacao_pct=-50,
        produtividade_vs_media_regional_pct=-28,
        area_total_ha=4_800,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=12,
        capital_social=4_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=12,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=1_200_000.0,
        dias_atraso=34,
        p1=4_260_000.0,
        p2=2_840_000.0,
        p3=2_365_000.0,
        p4=1_935_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-10-01",
        barter=barter_de("Soja", 40_506, PRECO_SACA["soja"]),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FISICA,
            "CPR física nº 2026/0302 — entrega de 40.500 sc de soja em armazém",
            5_200_000.0,
        ),
        garantia(ID, 2, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 4_800_000.0),
    ],
    limite_aprovado=12_800_000.0,
    patrimonio_declarado=22_000_000.0,
    faturamento_estimado_anual=19_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.CONAB: "Quebra de safra regional de 34% no sul do Piauí.",
            FonteId.PGFN: "R$ 520.000 em dívida ativa, estável em 90 dias.",
            FonteId.INTERNO_KRILLTECH: (
                "Barter de 40.506 sc de soja sem CPR registrada vinculada — a CPR do cliente "
                "é física e não cobre a operação."
            ),
        },
        extras=(
            evidencia(
                ID,
                FonteId.MAPA_ZARC,
                "ZARC crítico para a soja em Uruçuí/PI",
                "ZARC da soja em Uruçuí/PI classificado como crítico para a janela de "
                "plantio 2026/27.",
                ("zarc_risco",),
                numero=2,
            ),
            evidencia(
                ID,
                FonteId.INMET,
                "Déficit hídrico acumulado de 50%",
                "Déficit de 50% na precipitação acumulada out/2025–mar/2026.",
                ("desvio_precipitacao",),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.88, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -16, "produtividade_vs_media_regional_pct": -6},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.85, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "alto", "quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -11},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 12, "atraso_medio_dias_90d": 17, "pior_atraso_dias_12m": 35, "pct_titulos_pagos_em_dia_12m": 0.81, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 300_000.0, "credores_distintos_executando": 1},
            "fiscal": {"divida_ativa_pgfn": 300_000.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "alto", "quebra_safra_regional_pct": 21, "desvio_precipitacao_pct": -33, "produtividade_vs_media_regional_pct": -17},
        },
        {
            "interno": {"atraso_medio_dias_12m": 15, "atraso_medio_dias_90d": 21, "pior_atraso_dias_12m": 43, "pct_titulos_pagos_em_dia_12m": 0.77},
            "fiscal": {"divida_ativa_pgfn": 520_000.0, "divida_ativa_pgfn_90d_atras": 300_000.0},
            "agro": {"quebra_safra_regional_pct": 28, "desvio_precipitacao_pct": -42, "produtividade_vs_media_regional_pct": -23},
        },
        {
            "interno": {"atraso_medio_dias_12m": 17, "atraso_medio_dias_90d": 24, "pior_atraso_dias_12m": 48, "pct_titulos_pagos_em_dia_12m": 0.74},
            "agro": {"quebra_safra_regional_pct": 31, "desvio_precipitacao_pct": -46, "produtividade_vs_media_regional_pct": -26},
        },
    ],
)
