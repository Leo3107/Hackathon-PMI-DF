"""`dois-irmaos` — **ruptura societária** (§7.16).

Alteração societária e saída de sócio majoritário em 12 meses, com deterioração
comportamental acompanhando. Dimensão cadastral em 630.
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
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "dois-irmaos"
CULTURAS = ["Soja", "Milho safrinha"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agropastoril Dois Irmãos Ltda",
    nome_fantasia="Agropastoril Dois Irmãos",
    documento="36.510.872/0001-47",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Rondonópolis",
    uf="MT",
    atividade="Produtor rural — grãos e pecuária de corte",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2017-02-28",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=12,
        atraso_medio_dias_90d=18,
        pior_atraso_dias_12m=36,
        pct_titulos_pagos_em_dia_12m=0.81,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=1,
        valor_total_em_execucao=560_000.0,
        credores_distintos_executando=1,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=900_000.0, divida_ativa_pgfn_90d_atras=520_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=15,
        desvio_precipitacao_pct=-26,
        produtividade_vs_media_regional_pct=-11,
        area_total_ha=3_100,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=15,
        capital_social=2_800_000.0,
        alteracao_societaria_180d=True,
        saida_socio_majoritario_12m=True,
        qsa_estavel_5anos=False,
        anos_atividade_comprovada=15,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=600_000.0,
        dias_atraso=21,
        p1=3_600_000.0,
        p2=2_400_000.0,
        p3=2_090_000.0,
        p4=1_710_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-12-03",
        barter=barter_de("Soja", 34_941, PRECO_SACA["soja"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0344 — 34.941 sc de soja",
            4_000_000.0,
        ),
        garantia(ID, 2, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 5_200_000.0),
    ],
    limite_aprovado=10_600_000.0,
    patrimonio_declarado=24_000_000.0,
    faturamento_estimado_anual=22_500_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.REDESIM: "Saída de sócio majoritário registrada na Redesim em julho/2026.",
            FonteId.PGFN: "R$ 900.000 em dívida ativa, contra R$ 520.000 há 90 dias.",
            FonteId.INTERNO_KRILLTECH: "Atraso médio subiu de 6 para 12 dias ao longo de 12 meses.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 20, "pct_titulos_pagos_em_dia_12m": 0.91, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "cadastral": {"alteracao_societaria_180d": False, "saida_socio_majoritario_12m": False, "qsa_estavel_5anos": True},
            "agro": {"quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -17, "produtividade_vs_media_regional_pct": -5},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 10, "pior_atraso_dias_12m": 23, "pct_titulos_pagos_em_dia_12m": 0.89, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "cadastral": {"alteracao_societaria_180d": False, "saida_socio_majoritario_12m": False, "qsa_estavel_5anos": True},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -20, "produtividade_vs_media_regional_pct": -7},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.86, "renegociacoes_12m": 1},
            "juridico": {"protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 520_000.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "cadastral": {"alteracao_societaria_180d": False, "saida_socio_majoritario_12m": False, "qsa_estavel_5anos": True},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -22, "produtividade_vs_media_regional_pct": -8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 15, "pior_atraso_dias_12m": 31, "pct_titulos_pagos_em_dia_12m": 0.84, "renegociacoes_12m": 1},
            "fiscal": {"divida_ativa_pgfn": 520_000.0, "divida_ativa_pgfn_90d_atras": 520_000.0},
            "cadastral": {"saida_socio_majoritario_12m": False},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -9},
        },
        {
            "interno": {"atraso_medio_dias_12m": 11, "atraso_medio_dias_90d": 16, "pior_atraso_dias_12m": 34, "pct_titulos_pagos_em_dia_12m": 0.82},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -10},
        },
    ],
)
