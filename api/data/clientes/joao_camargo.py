"""`joao-camargo` — **produtor rural PF inelegível a RJ** e lado B da invariante I5 (§7.11).

PD 12m de 31,26% com risco de RJ de 0,14%: sem via de recuperação judicial, o
risco migra para execução individual.
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
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "joao-camargo"
CULTURAS = ["Soja", "Milho safrinha"]

CLIENTE = Cliente(
    id=ID,
    razao_social="João Batista Moreira Camargo",
    documento="482.910.573-97",
    tipo_pessoa=TipoPessoa.PF,
    municipio="Cristalina",
    uf="GO",
    atividade="Produtor rural pessoa física — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2024-01-15",
    estado=EstadoCliente.SUSPENSO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=32,
        atraso_medio_dias_90d=44,
        pior_atraso_dias_12m=110,
        pct_titulos_pagos_em_dia_12m=0.42,
        renegociacoes_12m=3,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=2,
        valor_total_em_execucao=680_000.0,
        # Dois credores — abaixo do limiar de pluralidade. É o que mantém o RJ baixo.
        credores_distintos_executando=2,
        protestos_ativos=3,
        protestos_12m=3,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=340_000.0,
        divida_ativa_pgfn_90d_atras=190_000.0,
        crf_fgts_regular=False,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=18,
        desvio_precipitacao_pct=-28,
        produtividade_vs_media_regional_pct=-20,
        area_total_ha=900,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=2.6,
        # Convenção C2: em PF o campo recebe o patrimônio rural declarado no IRPF.
        capital_social=1_400_000.0,
        possui_livro_caixa_digital=False,
        possui_inscricao_estadual=False,
        anos_atividade_comprovada=1.4,
        tipo_pessoa=TipoPessoa.PF,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=450_000.0,
        dias_atraso=58,
        p1=1_440_000.0,
        p2=960_000.0,
        p3=578_000.0,
        p4=472_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2025-04-16",
    ),
    garantias=[
        garantia(ID, 1, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 2_600_000.0),
        garantia(ID, 2, TipoGarantia.AVAL_FIANCA, "Aval do cônjuge", 1_200_000.0),
    ],
    limite_aprovado=3_950_000.0,
    patrimonio_declarado=9_400_000.0,
    faturamento_estimado_anual=6_800_000.0,
    evidencias=evidencias_padrao(
        ID,
        redesim=False,
        resumos={
            FonteId.RECEITA_FEDERAL: (
                "CPF regular. Produtor rural pessoa física sem inscrição estadual e sem "
                "livro-caixa digital; 1,4 ano de atividade comprovada."
            ),
            FonteId.DATAJUD_CNJ: "Duas execuções de título de dois credores distintos.",
            FonteId.CAIXA_CRF_FGTS: "CRF-FGTS irregular desde junho/2026.",
            FonteId.INTERNO_KRILLTECH: (
                "Terceira renegociação em 12 meses; 42% dos títulos pagos em dia."
            ),
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 31, "pct_titulos_pagos_em_dia_12m": 0.79, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0, "crf_fgts_regular": True},
            "cadastral": {"anos_atividade": 1.7, "anos_atividade_comprovada": 0.5},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -17, "produtividade_vs_media_regional_pct": -9},
        },
        {
            "interno": {"atraso_medio_dias_12m": 14, "atraso_medio_dias_90d": 19, "pior_atraso_dias_12m": 48, "pct_titulos_pagos_em_dia_12m": 0.70, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0, "crf_fgts_regular": True},
            "cadastral": {"anos_atividade": 1.9, "anos_atividade_comprovada": 0.7},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -20, "produtividade_vs_media_regional_pct": -12},
        },
        {
            "interno": {"atraso_medio_dias_12m": 20, "atraso_medio_dias_90d": 27, "pior_atraso_dias_12m": 70, "pct_titulos_pagos_em_dia_12m": 0.60, "renegociacoes_12m": 2},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 300_000.0, "credores_distintos_executando": 1, "protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 120_000.0, "divida_ativa_pgfn_90d_atras": 0.0, "crf_fgts_regular": True},
            "cadastral": {"anos_atividade": 2.1, "anos_atividade_comprovada": 0.9},
            "agro": {"quebra_safra_regional_pct": 15, "desvio_precipitacao_pct": -23, "produtividade_vs_media_regional_pct": -15},
        },
        {
            "interno": {"atraso_medio_dias_12m": 26, "atraso_medio_dias_90d": 35, "pior_atraso_dias_12m": 92, "pct_titulos_pagos_em_dia_12m": 0.51, "renegociacoes_12m": 2},
            "juridico": {"valor_total_em_execucao": 540_000.0, "protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 190_000.0, "divida_ativa_pgfn_90d_atras": 120_000.0},
            "cadastral": {"anos_atividade": 2.4, "anos_atividade_comprovada": 1.2},
            "agro": {"quebra_safra_regional_pct": 16, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -17},
        },
        {
            "interno": {"atraso_medio_dias_12m": 29, "atraso_medio_dias_90d": 40, "pior_atraso_dias_12m": 102, "pct_titulos_pagos_em_dia_12m": 0.46},
            "juridico": {"valor_total_em_execucao": 620_000.0},
            "fiscal": {"divida_ativa_pgfn": 190_000.0, "divida_ativa_pgfn_90d_atras": 190_000.0},
            "cadastral": {"anos_atividade": 2.5, "anos_atividade_comprovada": 1.3},
            "agro": {"quebra_safra_regional_pct": 17, "desvio_precipitacao_pct": -27, "produtividade_vs_media_regional_pct": -19},
        },
    ],
)
