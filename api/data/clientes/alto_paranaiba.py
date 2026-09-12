"""`alto-paranaiba` — nota boa, **risco jurídico recém-surgido** (§7.6).

Score A (766,2) com dimensão jurídica em 330 e risco de RJ de 12,85%: o cliente
que mostra por que um número só não basta.
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

ID = "alto-paranaiba"
CULTURAS = ["Café arábica"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Sementes e Café Alto Paranaíba Ltda",
    nome_fantasia="Café Alto Paranaíba",
    documento="15.432.987/0001-90",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Patrocínio",
    uf="MG",
    atividade="Produtor rural — café arábica",
    cnae_principal="0134-2/00",
    culturas=CULTURAS,
    inicio_relacionamento="2014-09-30",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=6,
        atraso_medio_dias_90d=9,
        pior_atraso_dias_12m=20,
        pct_titulos_pagos_em_dia_12m=0.90,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=3,
        execucoes_titulo_90d=2,
        valor_total_em_execucao=2_400_000.0,
        credores_distintos_executando=3,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=14,
        desvio_precipitacao_pct=-25,
        produtividade_vs_media_regional_pct=-6,
        area_total_ha=1_180,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=22,
        capital_social=4_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=22,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=1_230_000.0,
        p2=820_000.0,
        p3=2_392_000.0,
        p4=1_958_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — café arábica",
        data_op3="2024-05-08",
        barter=barter_de("Café arábica", 1_622, PRECO_SACA["cafe"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0188 — 1.622 sc de café arábica",
            3_900_000.0,
        ),
        garantia(
            ID, 2, TipoGarantia.ALIENACAO_FIDUCIARIA, "Duas colhedoras de café automotrizes", 1_800_000.0
        ),
        garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de café 2026/27", 2_200_000.0),
    ],
    limite_aprovado=7_000_000.0,
    patrimonio_declarado=39_000_000.0,
    faturamento_estimado_anual=28_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: (
                "Duas execuções de título ajuizadas em 30 dias, três credores distintos, "
                "valor agregado R$ 2.400.000 — risco jurídico recém-surgido."
            ),
            FonteId.PGFN: "Certidões negativas vigentes; dívida ativa zerada.",
            FonteId.INTERNO_KRILLTECH: "Atraso médio de 6 dias; 90% dos títulos pagos em dia.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 3, "atraso_medio_dias_90d": 5, "pior_atraso_dias_12m": 11, "pct_titulos_pagos_em_dia_12m": 0.96},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "agro": {"quebra_safra_regional_pct": 8, "desvio_precipitacao_pct": -16, "produtividade_vs_media_regional_pct": -1},
        },
        {
            "interno": {"atraso_medio_dias_12m": 4, "atraso_medio_dias_90d": 6, "pior_atraso_dias_12m": 13, "pct_titulos_pagos_em_dia_12m": 0.95},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 0, "protestos_12m": 0, "credores_protestantes_180d": 0},
            "agro": {"quebra_safra_regional_pct": 10, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -2},
        },
        {
            "interno": {"atraso_medio_dias_12m": 4, "atraso_medio_dias_90d": 6, "pior_atraso_dias_12m": 15, "pct_titulos_pagos_em_dia_12m": 0.94},
            "juridico": {"execucoes_titulo_12m": 0, "execucoes_titulo_90d": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -3},
        },
        {
            "interno": {"atraso_medio_dias_12m": 5, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 17, "pct_titulos_pagos_em_dia_12m": 0.92},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 700_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -23, "produtividade_vs_media_regional_pct": -4},
        },
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 19, "pct_titulos_pagos_em_dia_12m": 0.90},
            "juridico": {"execucoes_titulo_12m": 1, "execucoes_titulo_90d": 1, "valor_total_em_execucao": 700_000.0, "credores_distintos_executando": 1},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -5},
        },
    ],
)
