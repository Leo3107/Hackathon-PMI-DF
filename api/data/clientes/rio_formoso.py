"""`rio-formoso` — crítico D, com pedido de falência distribuído (§7.4).

O pedido de falência de T6 **não altera o score** (D2 já saturada em 0) mas
altera o rating por veto: é o caso didático de "veto acima do score".
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
    CovenantRompido,
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

ID = "rio-formoso"
CULTURAS = ["Soja", "Algodão"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Grupo Rio Formoso Comércio de Grãos Ltda",
    nome_fantasia="Rio Formoso Grãos",
    documento="39.204.471/0001-57",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Formosa do Rio Preto",
    uf="BA",
    atividade="Produção e comércio de grãos",
    cnae_principal="4622-2/00",
    culturas=CULTURAS,
    inicio_relacionamento="2021-05-19",
    estado=EstadoCliente.SUSPENSO,
    origem=OrigemCliente.CARTEIRA,
)

_COVENANT = CovenantRompido(
    id="COV-RF-1",
    descricao="Endividamento total acima de 2,5× o patrimônio líquido",
    limite_contratual="2,5×",
    valor_apurado="3,4×",
    data_deteccao="2026-03-04",
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=24,
        atraso_medio_dias_90d=34,
        pior_atraso_dias_12m=84,
        pct_titulos_pagos_em_dia_12m=0.56,
        renegociacoes_12m=2,
        covenants_rompidos=[_COVENANT],
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=6,
        execucoes_titulo_90d=3,
        valor_total_em_execucao=7_100_000.0,
        credores_distintos_executando=5,
        protestos_ativos=5,
        protestos_12m=7,
        credores_protestantes_180d=4,
        acoes_trabalhistas_transitadas=2,
        pedido_falencia=True,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=3_400_000.0,
        divida_ativa_pgfn_90d_atras=2_200_000.0,
        cndt_positiva=True,
        valor_debito_trabalhista=980_000.0,
        crf_fgts_regular=False,
        parcelamento_rompido_12m=True,
        execucoes_fiscais=3,
        valor_execucoes_fiscais=2_600_000.0,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=27,
        desvio_precipitacao_pct=-38,
        produtividade_vs_media_regional_pct=-19,
        area_total_ha=6_100,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=9,
        capital_social=2_500_000.0,
        alteracao_societaria_180d=True,
        saida_socio_majoritario_12m=True,
        anos_atividade_comprovada=9,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(
        auto_infracao_nao_quitado=True, situacao_car=SituacaoCar.PENDENTE
    ),
    operacoes=montar_operacoes(
        ID,
        p0=2_700_000.0,
        dias_atraso=62,
        p1=3_840_000.0,
        p2=2_560_000.0,
        p3=1_485_000.0,
        p4=1_215_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-09-05",
        barter=barter_de("Soja", 31_478, PRECO_SACA["soja"]),
    ),
    garantias=[
        garantia(ID, 1, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 4_000_000.0),
        garantia(ID, 2, TipoGarantia.AVAL_FIANCA, "Aval dos sócios", 3_000_000.0),
    ],
    limite_aprovado=12_000_000.0,
    patrimonio_declarado=14_000_000.0,
    faturamento_estimado_anual=17_500_000.0,
    evidencias=evidencias_padrao(
        ID,
        dje="Pedido de falência distribuído em 2026-09-03, 1ª Vara Cível de Barreiras/BA.",
        resumos={
            FonteId.DATAJUD_CNJ: "Seis execuções de título, cinco credores distintos, R$ 7.100.000.",
            FonteId.TST_CNDT: "CNDT positiva, débito de R$ 980.000.",
            FonteId.CAIXA_CRF_FGTS: "CRF-FGTS irregular desde março/2026.",
            FonteId.PGFN: "R$ 3.400.000 em dívida ativa e três execuções fiscais de R$ 2.600.000.",
            FonteId.IBAMA: "Auto de infração ambiental não quitado.",
            FonteId.REDESIM: "Saída do sócio majoritário registrada em junho/2026.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.84, "renegociacoes_12m": 0, "covenants_rompidos": []},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 700_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1, "pedido_falencia": False},
            "fiscal": {"divida_ativa_pgfn": 900_000.0, "divida_ativa_pgfn_90d_atras": 600_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0, "crf_fgts_regular": True, "parcelamento_rompido_12m": False, "execucoes_fiscais": 0, "valor_execucoes_fiscais": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -7},
            "cadastral": {"alteracao_societaria_180d": False, "saida_socio_majoritario_12m": False},
            "ambiental": {"auto_infracao_nao_quitado": False, "situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 13, "atraso_medio_dias_90d": 18, "pior_atraso_dias_12m": 41, "pct_titulos_pagos_em_dia_12m": 0.76, "renegociacoes_12m": 1, "covenants_rompidos": []},
            "juridico": {"execucoes_titulo_12m": 2, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 1_800_000.0, "credores_distintos_executando": 2, "protestos_ativos": 2, "protestos_12m": 3, "credores_protestantes_180d": 2, "pedido_falencia": False},
            "fiscal": {"divida_ativa_pgfn": 1_500_000.0, "divida_ativa_pgfn_90d_atras": 900_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0, "crf_fgts_regular": True, "parcelamento_rompido_12m": False, "execucoes_fiscais": 0, "valor_execucoes_fiscais": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 17, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -11},
            "cadastral": {"alteracao_societaria_180d": False, "saida_socio_majoritario_12m": False},
            "ambiental": {"auto_infracao_nao_quitado": False, "situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 18, "atraso_medio_dias_90d": 24, "pior_atraso_dias_12m": 58, "pct_titulos_pagos_em_dia_12m": 0.68, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 3, "execucoes_titulo_90d": 2, "valor_total_em_execucao": 3_400_000.0, "credores_distintos_executando": 3, "protestos_ativos": 3, "protestos_12m": 5, "credores_protestantes_180d": 3, "pedido_falencia": False},
            "fiscal": {"divida_ativa_pgfn": 2_200_000.0, "divida_ativa_pgfn_90d_atras": 1_500_000.0, "parcelamento_rompido_12m": False, "execucoes_fiscais": 1, "valor_execucoes_fiscais": 700_000.0},
            "agro": {"quebra_safra_regional_pct": 21, "desvio_precipitacao_pct": -30, "produtividade_vs_media_regional_pct": -14},
            "cadastral": {"saida_socio_majoritario_12m": False},
        },
        {
            "interno": {"atraso_medio_dias_12m": 21, "atraso_medio_dias_90d": 28, "pior_atraso_dias_12m": 70, "pct_titulos_pagos_em_dia_12m": 0.62, "renegociacoes_12m": 2},
            "juridico": {"execucoes_titulo_12m": 4, "execucoes_titulo_90d": 2, "valor_total_em_execucao": 4_900_000.0, "credores_distintos_executando": 3, "protestos_ativos": 3, "protestos_12m": 6, "credores_protestantes_180d": 3, "pedido_falencia": False},
            "fiscal": {"divida_ativa_pgfn": 2_400_000.0, "divida_ativa_pgfn_90d_atras": 2_200_000.0, "parcelamento_rompido_12m": False, "execucoes_fiscais": 2, "valor_execucoes_fiscais": 1_600_000.0},
            "agro": {"quebra_safra_regional_pct": 24, "desvio_precipitacao_pct": -34, "produtividade_vs_media_regional_pct": -17},
            "cadastral": {"saida_socio_majoritario_12m": False},
        },
        {
            "interno": {"atraso_medio_dias_12m": 23, "atraso_medio_dias_90d": 32, "pior_atraso_dias_12m": 79, "pct_titulos_pagos_em_dia_12m": 0.58},
            "juridico": {"execucoes_titulo_12m": 6, "execucoes_titulo_90d": 3, "valor_total_em_execucao": 7_100_000.0, "credores_distintos_executando": 5, "pedido_falencia": False},
        },
    ],
)
