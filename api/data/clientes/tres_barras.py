"""`tres-barras` — **inadimplência técnica sem nenhum atraso financeiro** (§7.12).

Zero dia de atraso, zero parcela vencida, e ainda assim uma red flag de
severidade ALTA: dois covenants rompidos e vigentes. É o caso que prova a tese.
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
    evidencia,
    evidencias_padrao,
    garantia,
    montar_operacoes,
    serie_de_snapshots,
)

ID = "tres-barras"
CULTURAS = ["Soja", "Trigo", "Milho"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Fazenda Três Barras Agropecuária Ltda",
    nome_fantasia="Fazenda Três Barras",
    documento="12.975.603/0001-98",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Não-Me-Toque",
    uf="RS",
    atividade="Produtor rural — grãos de verão e inverno",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2016-08-09",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

_COV_1 = CovenantRompido(
    id="COV-TB-1",
    descricao="Endividamento total acima de 2,5× o patrimônio líquido",
    limite_contratual="2,5×",
    valor_apurado="2,53×",
    data_deteccao="2026-03-19",
)
_COV_2 = CovenantRompido(
    id="COV-TB-2",
    descricao="Manutenção de seguro agrícola vigente sobre a área financiada",
    limite_contratual="100% da área",
    valor_apurado="0% — apólice não renovada",
    data_deteccao="2026-06-27",
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=0,
        atraso_medio_dias_90d=0,
        pior_atraso_dias_12m=0,
        pct_titulos_pagos_em_dia_12m=1.0,
        renegociacoes_12m=0,
        sem_atraso_relevante_24m=True,
        covenants_rompidos=[_COV_1, _COV_2],
    ),
    juridico=FatosJuridicos(),
    fiscal=FatosFiscais(divida_ativa_pgfn=3_000_000.0, divida_ativa_pgfn_90d_atras=1_350_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.CRITICO,
        quebra_safra_regional_pct=18,
        desvio_precipitacao_pct=-28,
        produtividade_vs_media_regional_pct=-10,
        area_total_ha=2_300,
        seguro_agricola_vigente=False,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=13,
        capital_social=1_200_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=13,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=montar_operacoes(
        ID,
        p1=2_580_000.0,
        p2=1_720_000.0,
        p3=1_540_000.0,
        p4=1_260_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-08-28",
    ),
    garantias=[
        garantia(ID, 1, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de soja 2026/27", 3_900_000.0)
    ],
    limite_aprovado=7_200_000.0,
    patrimonio_declarado=3_400_000.0,
    faturamento_estimado_anual=16_200_000.0,
    evidencias=evidencias_padrao(
        ID,
        protesto=False,
        resumos={
            FonteId.DATAJUD_CNJ: "Nenhum processo localizado.",
            FonteId.PGFN: "R$ 3.000.000 em dívida ativa, contra R$ 1.350.000 há 90 dias.",
            FonteId.MAPA_ZARC: "ZARC crítico para soja no Planalto Médio gaúcho em 2026/27.",
        },
        extras=(
            evidencia(
                ID,
                FonteId.INTERNO_KRILLTECH,
                "Apuração de covenants do contrato 2024/0318",
                "Apuração de covenants do contrato 2024/0318: endividamento total em 2,53× o "
                "patrimônio líquido e apólice de seguro agrícola não renovada. "
                "Zero dia de atraso em toda a série.",
                ("inadimplencia_tecnica", "historico_limpo", "concentracao_patrimonial"),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"covenants_rompidos": []},
            "fiscal": {"divida_ativa_pgfn": 800_000.0, "divida_ativa_pgfn_90d_atras": 600_000.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -14, "produtividade_vs_media_regional_pct": -3, "seguro_agricola_vigente": True},
            "patrimonio_declarado": 6_900_000.0,
        },
        {
            "interno": {"covenants_rompidos": []},
            "fiscal": {"divida_ativa_pgfn": 1_100_000.0, "divida_ativa_pgfn_90d_atras": 800_000.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -18, "produtividade_vs_media_regional_pct": -5, "seguro_agricola_vigente": True},
            "patrimonio_declarado": 6_200_000.0,
        },
        {
            "interno": {"covenants_rompidos": []},
            "fiscal": {"divida_ativa_pgfn": 1_350_000.0, "divida_ativa_pgfn_90d_atras": 1_100_000.0},
            "agro": {"risco_zarc": "alto", "quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -21, "produtividade_vs_media_regional_pct": -7, "seguro_agricola_vigente": True},
            "patrimonio_declarado": 5_400_000.0,
        },
        {
            "interno": {"covenants_rompidos": [_COV_1]},
            "fiscal": {"divida_ativa_pgfn": 2_400_000.0, "divida_ativa_pgfn_90d_atras": 1_350_000.0},
            "agro": {"quebra_safra_regional_pct": 16, "desvio_precipitacao_pct": -24, "produtividade_vs_media_regional_pct": -8, "seguro_agricola_vigente": True},
            "patrimonio_declarado": 4_300_000.0,
        },
        {
            "interno": {"covenants_rompidos": [_COV_1]},
            "fiscal": {"divida_ativa_pgfn": 2_600_000.0, "divida_ativa_pgfn_90d_atras": 1_350_000.0},
            "agro": {"quebra_safra_regional_pct": 17, "desvio_precipitacao_pct": -26, "produtividade_vs_media_regional_pct": -9, "seguro_agricola_vigente": True},
            "patrimonio_declarado": 3_800_000.0,
        },
    ],
)
