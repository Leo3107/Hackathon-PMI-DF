"""`frutivale` — fruticultura irrigada do Vale do São Francisco, em recuperação (§7.14).

Único cliente com irrigação integral e o melhor score da carteira: 942,8.
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
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "frutivale"
CULTURAS = ["Manga", "Uva de mesa"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Frutivale Agrícola do Vale Ltda",
    nome_fantasia="Frutivale",
    documento="21.890.345/0001-38",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Petrolina",
    uf="PE",
    atividade="Fruticultura irrigada — manga e uva de mesa",
    cnae_principal="0133-4/99",
    culturas=CULTURAS,
    inicio_relacionamento="2018-11-23",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=5,
        atraso_medio_dias_90d=4,
        pior_atraso_dias_12m=16,
        pct_titulos_pagos_em_dia_12m=0.92,
    ),
    juridico=FatosJuridicos(
        protestos_ativos=2, protestos_12m=2, credores_protestantes_180d=1, sem_litigio_36m=True
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.BAIXO,
        quebra_safra_regional_pct=9,
        desvio_precipitacao_pct=-18,
        produtividade_vs_media_regional_pct=-3,
        area_total_ha=305,
        area_irrigada_ha=305,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=17,
        capital_social=3_200_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=17,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=1_020_000.0,
        p2=680_000.0,
        p3=2_145_000.0,
        p4=1_755_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — manga e uva de mesa",
        data_op3="2024-01-30",
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.ALIENACAO_FIDUCIARIA,
            "Sistema de irrigação por gotejamento e packing house",
            3_000_000.0,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0410 — manga de exportação",
            2_200_000.0,
        ),
        garantia(ID, 3, TipoGarantia.HIPOTECA, "Matrícula 8.331 — lote irrigado do Projeto Senador Nilo Coelho", 4_000_000.0),
    ],
    limite_aprovado=6_000_000.0,
    patrimonio_declarado=62_000_000.0,
    faturamento_estimado_anual=48_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.CARTORIO_PROTESTO: "Baixa de protesto em cartório em julho/2026; dois ativos.",
            FonteId.MAPA_ZARC: "ZARC baixo — fruticultura com irrigação integral.",
            FonteId.INTERNO_KRILLTECH: "Atraso médio caiu de 9 para 5 dias em 12 meses.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 27, "pct_titulos_pagos_em_dia_12m": 0.86},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -27, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 24, "pct_titulos_pagos_em_dia_12m": 0.88},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 7, "pior_atraso_dias_12m": 21, "pct_titulos_pagos_em_dia_12m": 0.90},
            "juridico": {"protestos_ativos": 2, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -22, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.87},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 5, "pior_atraso_dias_12m": 18, "pct_titulos_pagos_em_dia_12m": 0.92},
            "agro": {"quebra_safra_regional_pct": 10, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -4},
        },
    ],
)
