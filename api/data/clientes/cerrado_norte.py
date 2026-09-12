"""`cerrado-norte` — o cliente da narrativa **712 → 604 em 60 dias** (§7.3 e §9).

T5 (`2026-07-14`) fecha em 712,0 e T6 (`2026-09-12`) em 604,0. A diferença de
−108,00 é decomposta fator a fator pela invariante I6.
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

ID = "cerrado-norte"
CULTURAS = ["Soja", "Milho"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Cerrado Norte Agronegócios S.A.",
    nome_fantasia="Cerrado Norte",
    documento="20.561.738/0001-35",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Balsas",
    uf="MA",
    atividade="Produtor rural — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2017-11-06",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

_CPR_ATUAL = garantia(
    ID, 1, TipoGarantia.CPR_FINANCEIRA, "CPR financeira nº 2026/0455 — 75.681 sc de soja", 7_400_000.0
)
#: Antes do registro da CPR adicional de ago/2026 (§9.1) — único movimento a favor do cliente.
#: O valor de T5 é calibrado para que o snapshot feche em 712,0 exatos: a §9 da spec
#: supôs `vencimento_concentrado` ativo também em 2026-07-14, mas naquela data a janela
#: de 90 dias termina em 2026-10-12 e nenhuma parcela vence dentro dela. A correção é no
#: fato, nunca no motor.
_CPR_EM_T5 = garantia(
    ID, 1, TipoGarantia.CPR_FINANCEIRA, "CPR financeira nº 2026/0455 — 22.879 sc de soja", 2_940_000.0
)
_PENHOR = garantia(ID, 2, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 9_500_000.0)
_AVAL = garantia(ID, 3, TipoGarantia.AVAL_FIANCA, "Aval dos sócios-administradores", 6_000_000.0)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=11,
        atraso_medio_dias_90d=19,
        pior_atraso_dias_12m=44,
        pct_titulos_pagos_em_dia_12m=0.78,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=3,
        execucoes_titulo_90d=2,
        valor_total_em_execucao=2_900_000.0,
        credores_distintos_executando=3,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=1_950_000.0, divida_ativa_pgfn_90d_atras=1_150_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=19,
        desvio_precipitacao_pct=-31,
        produtividade_vs_media_regional_pct=-11,
        area_total_ha=9_800,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=16,
        capital_social=9_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=16,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=1_500_000.0,
        dias_atraso=27,
        p1=7_080_000.0,
        p2=4_720_000.0,
        p3=5_005_000.0,
        p4=4_095_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-03-20",
        barter=barter_de("Soja", 75_681, PRECO_SACA["soja"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[_CPR_ATUAL, _PENHOR, _AVAL],
    limite_aprovado=23_000_000.0,
    patrimonio_declarado=48_000_000.0,
    faturamento_estimado_anual=63_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: (
                "Três execuções de título em 12 meses, duas delas distribuídas em agosto/2026 "
                "por credores distintos — trading, revenda e banco. Valor agregado R$ 2.900.000."
            ),
            FonteId.PGFN: (
                "Nova inscrição em dívida ativa da União em ago/2026: de R$ 1.150.000 "
                "para R$ 1.950.000."
            ),
            FonteId.CONAB: "Revisão do levantamento: quebra de 19% no sul do Maranhão.",
            FonteId.INMET: "Déficit de 31% na precipitação acumulada da janela de plantio.",
            FonteId.MAPA_ZARC: "ZARC da soja em Balsas/MA classificado como alto para 2026/27.",
            FonteId.INTERNO_KRILLTECH: "Atraso médio saltou de 3 para 11 dias entre jul e set/2026.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 4, "pior_atraso_dias_12m": 18, "pct_titulos_pagos_em_dia_12m": 0.90, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 6, "desvio_precipitacao_pct": -14, "produtividade_vs_media_regional_pct": -3},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 5, "pior_atraso_dias_12m": 24, "pct_titulos_pagos_em_dia_12m": 0.88, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 300_000.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -18, "produtividade_vs_media_regional_pct": -5},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 7, "pior_atraso_dias_12m": 31, "pct_titulos_pagos_em_dia_12m": 0.85},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 900_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 600_000.0, "divida_ativa_pgfn_90d_atras": 300_000.0},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -22, "produtividade_vs_media_regional_pct": -8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 38, "pct_titulos_pagos_em_dia_12m": 0.82},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 2_100_000.0, "credores_distintos_executando": 1},
            "fiscal": {"divida_ativa_pgfn": 1_150_000.0, "divida_ativa_pgfn_90d_atras": 600_000.0},
            "agro": {"quebra_safra_regional_pct": 15, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -10},
        },
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 11},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 2_500_000.0, "credores_distintos_executando": 1},
            "fiscal": {"divida_ativa_pgfn": 1_150_000.0, "divida_ativa_pgfn_90d_atras": 1_150_000.0},
            "agro": {"quebra_safra_regional_pct": 17, "desvio_precipitacao_pct": -28, "produtividade_vs_media_regional_pct": -12},
            "garantias": [_CPR_EM_T5, _PENHOR, _AVAL],
        },
    ],
)
