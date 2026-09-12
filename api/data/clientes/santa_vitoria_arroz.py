"""`santa-vitoria-arroz` — **teto por execução fiscal** (§7.15).

Score B (723,4) e rating final C: R$ 3.700.000 de execuções fiscais superam 50%
da exposição de R$ 6.800.000. Demonstra teto C sem força D — rating ≠ score.
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

ID = "santa-vitoria-arroz"
CULTURAS = ["Arroz irrigado", "Soja"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Arrozeira Santa Vitória Ltda",
    nome_fantasia="Arrozeira Santa Vitória",
    documento="07.456.231/0001-53",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Uruguaiana",
    uf="RS",
    atividade="Produtor rural — arroz irrigado e soja",
    cnae_principal="0111-3/01",
    culturas=CULTURAS,
    inicio_relacionamento="2011-07-05",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=10,
        atraso_medio_dias_90d=12,
        pior_atraso_dias_12m=32,
        pct_titulos_pagos_em_dia_12m=0.84,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=1,
        valor_total_em_execucao=290_000.0,
        credores_distintos_executando=1,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=1,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=3_800_000.0,
        divida_ativa_pgfn_90d_atras=3_800_000.0,
        parcelamento_rompido_12m=True,
        execucoes_fiscais=4,
        valor_execucoes_fiscais=3_700_000.0,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=13,
        desvio_precipitacao_pct=-22,
        produtividade_vs_media_regional_pct=-8,
        area_total_ha=1_950,
        area_irrigada_ha=1_350,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=24,
        capital_social=2_200_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=24,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p0=300_000.0,
        dias_atraso=14,
        p1=1_560_000.0,
        p2=1_040_000.0,
        p3=2_145_000.0,
        p4=1_755_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — arroz irrigado",
        data_op3="2024-09-19",
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0512 — arroz em casca da safra 2026/27",
            2_600_000.0,
        ),
        garantia(ID, 2, TipoGarantia.PENHOR_MAQUINA, "Conjunto de secadores e engenho", 2_400_000.0),
        garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de arroz 2026/27", 2_000_000.0),
    ],
    limite_aprovado=7_000_000.0,
    patrimonio_declarado=28_000_000.0,
    faturamento_estimado_anual=21_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: "Uma execução de título de R$ 290.000.",
            FonteId.INTERNO_KRILLTECH: "Atraso médio de 10 dias; uma renegociação em 12 meses.",
        },
        extras=(
            evidencia(
                ID,
                FonteId.PGFN,
                "Quatro execuções fiscais em curso",
                "Quatro execuções fiscais em curso, valor agregado R$ 3.700.000 — 54% da "
                "exposição de R$ 6.800.000.",
                ("divida_ativa", "divida_ativa_crescente"),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.90, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 2_900_000.0, "divida_ativa_pgfn_90d_atras": 2_700_000.0, "parcelamento_rompido_12m": False, "execucoes_fiscais": 2, "valor_execucoes_fiscais": 1_900_000.0},
            "agro": {"quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -15, "produtividade_vs_media_regional_pct": -4},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 25, "pct_titulos_pagos_em_dia_12m": 0.88, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 3_200_000.0, "divida_ativa_pgfn_90d_atras": 2_900_000.0, "parcelamento_rompido_12m": False, "execucoes_fiscais": 3, "valor_execucoes_fiscais": 2_600_000.0},
            "agro": {"quebra_safra_regional_pct": 10, "desvio_precipitacao_pct": -17, "produtividade_vs_media_regional_pct": -5},
            "ambiental": {"situacao_car": "ATIVO_REGULAR"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 11, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.86, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 290_000.0, "credores_distintos_executando": 1, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 3_500_000.0, "divida_ativa_pgfn_90d_atras": 3_200_000.0, "execucoes_fiscais": 3, "valor_execucoes_fiscais": 3_100_000.0},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 30, "pct_titulos_pagos_em_dia_12m": 0.85, "renegociacoes_12m": 1},
            "fiscal": {"divida_ativa_pgfn": 3_800_000.0, "divida_ativa_pgfn_90d_atras": 3_500_000.0},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -20, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 31, "pct_titulos_pagos_em_dia_12m": 0.84},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -21},
        },
    ],
)
