"""`ponta-verde` — **RJ em curso, Stay Period ativo** (§7.10).

Distribuída em 2026-06-23, deferida em 2026-07-08: 66 dias decorridos e 114
restantes em 2026-09-12. É a ficha que liga o painel de Stay Period.
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
    RecuperacaoJudicial,
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

ID = "ponta-verde"
CULTURAS = ["Milho", "Soja"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agroindustrial Ponta Verde S.A.",
    nome_fantasia="Ponta Verde",
    documento="33.849.157/0001-45",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Rio Verde",
    uf="GO",
    atividade="Agroindústria — milho e soja",
    cnae_principal="0111-3/02",
    culturas=CULTURAS,
    inicio_relacionamento="2013-03-27",
    estado=EstadoCliente.RJ_EM_CURSO,
    origem=OrigemCliente.CARTEIRA,
)

_COV_1 = CovenantRompido(
    id="COV-PV-1",
    descricao="Índice de liquidez corrente inferior a 1,2",
    limite_contratual="1,2",
    valor_apurado="0,71",
    data_deteccao="2025-11-18",
)
_COV_2 = CovenantRompido(
    id="COV-PV-2",
    descricao="Endividamento líquido acima de 3,0× EBITDA",
    limite_contratual="3,0×",
    valor_apurado="5,4×",
    data_deteccao="2026-02-09",
)
_RJ = RecuperacaoJudicial(
    data_distribuicao="2026-06-23", data_deferimento="2026-07-08", dias_prorrogados_stay=0
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=34,
        atraso_medio_dias_90d=52,
        pior_atraso_dias_12m=118,
        pct_titulos_pagos_em_dia_12m=0.44,
        renegociacoes_12m=2,
        covenants_rompidos=[_COV_1, _COV_2],
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=2,
        valor_total_em_execucao=4_800_000.0,
        credores_distintos_executando=4,
        protestos_ativos=3,
        protestos_12m=4,
        credores_protestantes_180d=3,
        acoes_trabalhistas_transitadas=3,
        recuperacao_judicial=_RJ,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=2_100_000.0,
        divida_ativa_pgfn_90d_atras=1_700_000.0,
        cndt_positiva=True,
        valor_debito_trabalhista=1_400_000.0,
        crf_fgts_regular=False,
        parcelamento_rompido_12m=True,
        execucoes_fiscais=2,
        valor_execucoes_fiscais=1_900_000.0,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=16,
        desvio_precipitacao_pct=-19,
        produtividade_vs_media_regional_pct=-9,
        area_total_ha=5_300,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=21,
        capital_social=7_000_000.0,
        alteracao_societaria_180d=True,
        anos_atividade_comprovada=21,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=4_100_000.0,
        dias_atraso=74,
        p1=7_740_000.0,
        p2=5_160_000.0,
        p3=715_000.0,
        p4=585_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — milho",
        data_op3="2024-02-14",
        barter=barter_de("Milho", 94_758, PRECO_SACA["milho"]),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.ALIENACAO_FIDUCIARIA,
            "Frota de caminhões graneleiros — 6 unidades",
            5_200_000.0,
        ),
        garantia(ID, 2, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de milho 2026/27", 6_500_000.0),
        garantia(ID, 3, TipoGarantia.AVAL_FIANCA, "Aval dos controladores", 4_000_000.0),
    ],
    limite_aprovado=18_500_000.0,
    patrimonio_declarado=26_000_000.0,
    faturamento_estimado_anual=41_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        dje=(
            "Decisão de deferimento do processamento da RJ, 3ª Vara Cível de Rio Verde/GO, "
            "publicada em 2026-07-08."
        ),
        resumos={
            FonteId.DATAJUD_CNJ: "Duas execuções de título e quatro credores distintos em cobrança.",
            FonteId.TST_CNDT: "CNDT positiva, débito trabalhista de R$ 1.400.000.",
            FonteId.CAIXA_CRF_FGTS: "CRF-FGTS irregular.",
            FonteId.REDESIM: "Troca do administrador registrada em maio/2026.",
            FonteId.INTERNO_KRILLTECH: (
                "Dois covenants rompidos e vigentes; a alienação fiduciária de R$ 5.200.000 "
                "declarados permanece excutível por ser crédito extraconcursal."
            ),
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 11, "atraso_medio_dias_90d": 16, "pior_atraso_dias_12m": 38, "pct_titulos_pagos_em_dia_12m": 0.78, "renegociacoes_12m": 1, "covenants_rompidos": []},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 1_200_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1, "acoes_trabalhistas_transitadas": 2, "recuperacao_judicial": None},
            "fiscal": {"divida_ativa_pgfn": 900_000.0, "divida_ativa_pgfn_90d_atras": 700_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0, "crf_fgts_regular": True, "parcelamento_rompido_12m": False, "execucoes_fiscais": 0, "valor_execucoes_fiscais": 0.0},
            "cadastral": {"alteracao_societaria_180d": False},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -12, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 16, "atraso_medio_dias_90d": 23, "pior_atraso_dias_12m": 55, "pct_titulos_pagos_em_dia_12m": 0.70, "renegociacoes_12m": 1, "covenants_rompidos": [_COV_1]},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 1_900_000.0, "credores_distintos_executando": 2, "protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2, "acoes_trabalhistas_transitadas": 2, "recuperacao_judicial": None},
            "fiscal": {"divida_ativa_pgfn": 1_300_000.0, "divida_ativa_pgfn_90d_atras": 900_000.0, "cndt_positiva": False, "valor_debito_trabalhista": 0.0, "crf_fgts_regular": True, "parcelamento_rompido_12m": False, "execucoes_fiscais": 0, "valor_execucoes_fiscais": 0.0},
            "cadastral": {"alteracao_societaria_180d": False},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -15, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 22, "atraso_medio_dias_90d": 32, "pior_atraso_dias_12m": 79, "pct_titulos_pagos_em_dia_12m": 0.60, "covenants_rompidos": [_COV_1, _COV_2]},
            "juridico": {"execucoes_titulo_12m": 2, "valor_total_em_execucao": 3_100_000.0, "credores_distintos_executando": 3, "protestos_ativos": 2, "protestos_12m": 3, "credores_protestantes_180d": 2, "recuperacao_judicial": None},
            "fiscal": {"divida_ativa_pgfn": 1_700_000.0, "divida_ativa_pgfn_90d_atras": 1_300_000.0, "execucoes_fiscais": 1, "valor_execucoes_fiscais": 900_000.0},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -17, "produtividade_vs_media_regional_pct": -8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 24, "atraso_medio_dias_90d": 36, "pior_atraso_dias_12m": 96, "pct_titulos_pagos_em_dia_12m": 0.55},
            "juridico": {"execucoes_titulo_12m": 2, "valor_total_em_execucao": 4_100_000.0, "credores_distintos_executando": 3, "recuperacao_judicial": None},
            "fiscal": {"divida_ativa_pgfn": 1_700_000.0, "divida_ativa_pgfn_90d_atras": 1_700_000.0},
            "agro": {"quebra_safra_regional_pct": 15, "desvio_precipitacao_pct": -18},
        },
        {
            "interno": {"atraso_medio_dias_12m": 32, "atraso_medio_dias_90d": 48, "pior_atraso_dias_12m": 110, "pct_titulos_pagos_em_dia_12m": 0.47},
            "juridico": {"valor_total_em_execucao": 4_600_000.0},
        },
    ],
)
