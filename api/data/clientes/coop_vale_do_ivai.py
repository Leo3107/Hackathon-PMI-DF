"""`coop-vale-do-ivai` — **teto por CNDT positiva** (§7.18).

Score B (718,5) e rating final C: débito trabalhista de R$ 2.150.000 supera 15%
do patrimônio declarado de R$ 7.400.000.
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
    evidencia,
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "coop-vale-do-ivai"
CULTURAS = ["Soja", "Milho safrinha", "Trigo"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Cooperativa Agroindustrial Vale do Ivaí",
    nome_fantasia="Coop Vale do Ivaí",
    documento="04.827.196/0001-43",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Cascavel",
    uf="PR",
    atividade="Cooperativa agroindustrial — recebimento de grãos e revenda de insumos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2009-04-16",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=11,
        atraso_medio_dias_90d=14,
        pior_atraso_dias_12m=33,
        pct_titulos_pagos_em_dia_12m=0.83,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=1,
        valor_total_em_execucao=520_000.0,
        credores_distintos_executando=1,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
        acoes_trabalhistas_transitadas=3,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=1_900_000.0,
        divida_ativa_pgfn_90d_atras=1_200_000.0,
        cndt_positiva=True,
        valor_debito_trabalhista=2_150_000.0,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=14,
        desvio_precipitacao_pct=-23,
        produtividade_vs_media_regional_pct=-7,
        area_total_ha=7_500,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=37,
        capital_social=4_200_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=37,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=1_100_000.0,
        dias_atraso=16,
        p1=5_040_000.0,
        p2=3_360_000.0,
        p3=5_335_000.0,
        p4=4_365_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-05-14",
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0620 — recebíveis de grãos dos cooperados",
            6_000_000.0,
        ),
        garantia(ID, 2, TipoGarantia.PENHOR_SAFRA, "Penhor de estoque de grãos em armazém próprio", 8_900_000.0),
        garantia(ID, 3, TipoGarantia.AVAL_FIANCA, "Aval solidário do conselho de administração", 5_000_000.0),
    ],
    limite_aprovado=19_800_000.0,
    patrimonio_declarado=7_400_000.0,
    faturamento_estimado_anual=96_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: "Uma execução de título de R$ 520.000; há litígio ativo.",
            FonteId.PGFN: "R$ 1.900.000 em dívida ativa, contra R$ 1.200.000 há 90 dias.",
            FonteId.INTERNO_KRILLTECH: (
                "Exposição de R$ 19.200.000 contra patrimônio de R$ 7.400.000 — concentração "
                "patrimonial acima de 2×."
            ),
        },
        extras=(
            evidencia(
                ID,
                FonteId.TST_CNDT,
                "CNDT positiva com trânsito em julgado",
                "CNDT positiva, débito de R$ 2.150.000 com trânsito em julgado.",
                ("cndt_positiva", "trabalhistas"),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 10, "pior_atraso_dias_12m": 24, "pct_titulos_pagos_em_dia_12m": 0.89},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "acoes_trabalhistas_transitadas": 2, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 1_200_000.0, "divida_ativa_pgfn_90d_atras": 1_000_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0},
            "agro": {"quebra_safra_regional_pct": 10, "desvio_precipitacao_pct": -17, "produtividade_vs_media_regional_pct": -4},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 11, "pior_atraso_dias_12m": 27, "pct_titulos_pagos_em_dia_12m": 0.87},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "acoes_trabalhistas_transitadas": 2, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 1_200_000.0, "divida_ativa_pgfn_90d_atras": 1_200_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -5},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 30, "pct_titulos_pagos_em_dia_12m": 0.86},
            "juridico": {"protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 1_200_000.0, "divida_ativa_pgfn_90d_atras": 1_200_000.0},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -20, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 31, "pct_titulos_pagos_em_dia_12m": 0.85},
            "fiscal": {"divida_ativa_pgfn": 1_500_000.0, "divida_ativa_pgfn_90d_atras": 1_200_000.0},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 11, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 32, "pct_titulos_pagos_em_dia_12m": 0.84},
            "fiscal": {"divida_ativa_pgfn": 1_900_000.0, "divida_ativa_pgfn_90d_atras": 1_500_000.0},
            "agro": {"desvio_precipitacao_pct": -22},
        },
    ],
)
