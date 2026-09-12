"""`sao-bento-bioenergia` — **sobrecolateralizado** (§7.8).

Cobertura extraconcursal de 112,6%: o único cliente com `exposicaoEmRiscoEmRJ`
igual a zero. Quatro dimensões saturam para cima — exercita a redistribuição de bônus.
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

ID = "sao-bento-bioenergia"
CULTURAS = ["Cana-de-açúcar"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Usina São Bento Bioenergia S.A.",
    nome_fantasia="Usina São Bento",
    documento="09.381.524/0001-44",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Sertãozinho",
    uf="SP",
    atividade="Usina sucroenergética — cana própria e de fornecedores",
    cnae_principal="0113-0/00",
    culturas=CULTURAS,
    inicio_relacionamento="2012-06-08",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=9,
        atraso_medio_dias_90d=12,
        pior_atraso_dias_12m=30,
        pct_titulos_pagos_em_dia_12m=0.86,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=1,
        acoes_trabalhistas_transitadas=3,
        # V6: o campo mede ações AJUIZADAS em 36 meses; as três reclamações foram
        # ajuizadas em 2020–2021 e transitaram em julgado em 2023-02 (§7.8 e §12.1).
        sem_litigio_36m=True,
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=14,
        desvio_precipitacao_pct=-26,
        produtividade_vs_media_regional_pct=-8,
        area_total_ha=14_000,
        area_irrigada_ha=4_200,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=31,
        capital_social=85_000_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=31,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=4_740_000.0,
        p2=3_160_000.0,
        p3=10_230_000.0,
        p4=8_370_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — cana-de-açúcar",
        data_op3="2023-11-22",
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.ALIENACAO_FIDUCIARIA,
            "Duas colhedoras de cana e frota de transbordo — 11 unidades",
            21_000_000.0,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0077 — moagem da safra 2026/27",
            14_500_000.0,
        ),
        garantia(ID, 3, TipoGarantia.HIPOTECA, "Matrícula 22.118 — área industrial", 12_000_000.0),
        garantia(ID, 4, TipoGarantia.PENHOR_MAQUINA, "Conjunto de moendas e caldeira", 6_000_000.0),
    ],
    limite_aprovado=40_000_000.0,
    patrimonio_declarado=310_000_000.0,
    faturamento_estimado_anual=268_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: (
                "Nenhuma ação ajuizada nos últimos 36 meses. As três reclamações "
                "trabalhistas foram ajuizadas em 2020–2021, com trânsito em julgado em 2023-02."
            ),
            FonteId.TST_CNDT: "CNDT negativa; três reclamações já quitadas.",
            FonteId.PGFN: "Certidões negativas vigentes.",
            FonteId.INTERNO_KRILLTECH: (
                "Garantias extraconcursais de R$ 29.850.000 atualizados para R$ 26.500.000 "
                "de exposição — cobertura de 112,6%."
            ),
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.90, "renegociacoes_12m": 0},
            "juridico": {"acoes_trabalhistas_transitadas": 2, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {"quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -18, "produtividade_vs_media_regional_pct": -4},
        },
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 24, "pct_titulos_pagos_em_dia_12m": 0.89, "renegociacoes_12m": 0},
            "juridico": {"acoes_trabalhistas_transitadas": 2, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -5},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 10, "pior_atraso_dias_12m": 26, "pct_titulos_pagos_em_dia_12m": 0.88},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -23, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 11, "pior_atraso_dias_12m": 28, "pct_titulos_pagos_em_dia_12m": 0.87},
            "agro": {"quebra_safra_regional_pct": 13, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -7},
        },
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 12, "pior_atraso_dias_12m": 29, "pct_titulos_pagos_em_dia_12m": 0.86},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -8},
        },
    ],
)
