"""`chapadao-algodoeira` — **exposição elevada**, a maior da carteira (§7.9).

R$ 41.000.000 (16,8% do total) e R$ 23.700.000 desprotegidos em cenário de RJ.
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

ID = "chapadao-algodoeira"
CULTURAS = ["Algodão", "Soja", "Milho safrinha"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Algodoeira Chapadão Grande S.A.",
    nome_fantasia="Chapadão Grande",
    documento="26.734.091/0001-82",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Primavera do Leste",
    uf="MT",
    atividade="Produtor rural — algodão, grãos e beneficiamento",
    cnae_principal="0116-4/01",
    culturas=CULTURAS,
    inicio_relacionamento="2015-01-22",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=11,
        atraso_medio_dias_90d=15,
        pior_atraso_dias_12m=34,
        pct_titulos_pagos_em_dia_12m=0.82,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=2,
        valor_total_em_execucao=1_800_000.0,
        credores_distintos_executando=2,
        protestos_ativos=3,
        protestos_12m=3,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=2_400_000.0, divida_ativa_pgfn_90d_atras=1_600_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=17,
        desvio_precipitacao_pct=-27,
        produtividade_vs_media_regional_pct=-9,
        area_total_ha=14_500,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=19,
        capital_social=12_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=19,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p0=2_400_000.0,
        dias_atraso=19,
        p1=14_100_000.0,
        p2=9_400_000.0,
        p3=8_305_000.0,
        p4=6_795_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — algodão",
        data_op3="2024-06-18",
        barter=barter_de("Algodão", 43_716, PRECO_SACA["algodao"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0091 — 43.716 @ de algodão em pluma",
            13_000_000.0,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.ALIENACAO_FIDUCIARIA,
            "Colhedora de algodão e prensa enfardadeira",
            7_000_000.0,
        ),
        garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de algodão 2026/27", 11_000_000.0),
    ],
    limite_aprovado=42_000_000.0,
    patrimonio_declarado=124_000_000.0,
    faturamento_estimado_anual=186_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.CARTORIO_PROTESTO: "Terceiro protesto ativo lavrado em agosto/2026.",
            FonteId.PGFN: "R$ 2.400.000 em dívida ativa, contra R$ 1.600.000 há 90 dias.",
            FonteId.INTERNO_KRILLTECH: (
                "Maior exposição da carteira: R$ 41.000.000, com R$ 23.700.000 sem cobertura "
                "extraconcursal."
            ),
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.90, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 800_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 1_200_000.0, "divida_ativa_pgfn_90d_atras": 900_000.0},
            "agro": {"quebra_safra_regional_pct": 10, "desvio_precipitacao_pct": -18, "produtividade_vs_media_regional_pct": -4},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 10, "pior_atraso_dias_12m": 25, "pct_titulos_pagos_em_dia_12m": 0.88, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 800_000.0, "credores_distintos_executando": 1, "protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 1_200_000.0, "divida_ativa_pgfn_90d_atras": 1_200_000.0},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.86, "renegociacoes_12m": 1},
            "juridico": {"protestos_ativos": 2, "protestos_12m": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 1_600_000.0, "divida_ativa_pgfn_90d_atras": 1_200_000.0},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -23, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 30, "pct_titulos_pagos_em_dia_12m": 0.85, "renegociacoes_12m": 1},
            "juridico": {"protestos_ativos": 2, "credores_protestantes_180d": 2},
            "fiscal": {"divida_ativa_pgfn": 1_600_000.0, "divida_ativa_pgfn_90d_atras": 1_600_000.0},
            "agro": {"quebra_safra_regional_pct": 15, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 13, "pior_atraso_dias_12m": 32, "pct_titulos_pagos_em_dia_12m": 0.83},
            "agro": {"quebra_safra_regional_pct": 16, "desvio_precipitacao_pct": -26},
        },
    ],
)
