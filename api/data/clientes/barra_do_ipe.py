"""`barra-do-ipe` — **veto por embargo do IBAMA sobre imóvel dado em garantia** (§7.5).

Score calculado C (571,6), classificação final **D**. É a ficha que a UI usa
para mostrar "score calculado" ao lado de "classificação final" com o motivo nomeado.
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

ID = "barra-do-ipe"
CULTURAS = ["Soja"]
_DATA_REAVALIACAO = "2026-08-24"

CLIENTE = Cliente(
    id=ID,
    razao_social="Fazenda Barra do Ipê Agrícola Ltda",
    nome_fantasia="Fazenda Barra do Ipê",
    documento="28.615.390/0001-23",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Querência",
    uf="MT",
    atividade="Produtor rural — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2022-02-11",
    estado=EstadoCliente.EM_OBSERVACAO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=14,
        atraso_medio_dias_90d=20,
        pior_atraso_dias_12m=45,
        pct_titulos_pagos_em_dia_12m=0.76,
        renegociacoes_12m=1,
    ),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=2,
        valor_total_em_execucao=900_000.0,
        credores_distintos_executando=2,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=700_000.0, divida_ativa_pgfn_90d_atras=440_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=18,
        desvio_precipitacao_pct=-28,
        produtividade_vs_media_regional_pct=-12,
        area_total_ha=5_200,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=8,
        capital_social=3_600_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=8,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(
        embargo_ibama_vigente=True,
        embargo_sobre_imovel_em_garantia=True,
        auto_infracao_nao_quitado=True,
        situacao_car=SituacaoCar.IRREGULAR,
        sobreposicao_app_ou_reserva=True,
    ),
    operacoes=montar_operacoes(
        ID,
        p0=600_000.0,
        dias_atraso=23,
        p1=1_860_000.0,
        p2=1_240_000.0,
        p3=3_025_000.0,
        p4=2_475_000.0,
        tipo_op2=TipoOperacao.CPR,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-11-12",
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.HIPOTECA,
            "Matrícula 14.702, Fazenda Barra do Ipê, gleba de 1.860 ha",
            7_000_000.0,
            data_avaliacao=_DATA_REAVALIACAO,
            bem_embargado=True,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.PENHOR_SAFRA,
            "Penhor da safra de soja 2026/27",
            2_600_000.0,
            data_avaliacao=_DATA_REAVALIACAO,
        ),
    ],
    limite_aprovado=9_600_000.0,
    patrimonio_declarado=27_000_000.0,
    faturamento_estimado_anual=15_800_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: "Duas execuções de título de dois credores distintos.",
            FonteId.PGFN: "R$ 700.000 em dívida ativa, contra R$ 440.000 há 90 dias.",
            FonteId.MAPA_ZARC: "ZARC da soja em Querência/MT elevado de moderado para alto.",
        },
        extras=(
            evidencia(
                ID,
                FonteId.IBAMA,
                "Termo de Embargo nº 0092/2026",
                "Termo de Embargo nº 0092/2026 — Fazenda Barra do Ipê, gleba de 1.860 ha, "
                "matrícula 14.702, dada em hipoteca à Krill Tech.",
                ("embargo_ibama", "auto_infracao"),
                numero=2,
                data_documento="2026-08-24",
            ),
            evidencia(
                ID,
                FonteId.SICAR,
                "CAR MT-5107065-A3F2 em situação irregular",
                "CAR MT-5107065-A3F2 em situação irregular, com sobreposição de 112 ha "
                "de reserva legal.",
                ("car_irregular", "sobreposicao_app"),
                numero=2,
            ),
        ),
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 20, "pct_titulos_pagos_em_dia_12m": 0.90, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 9, "desvio_precipitacao_pct": -15, "produtividade_vs_media_regional_pct": -4},
            "ambiental": {"embargo_ibama_vigente": False, "embargo_sobre_imovel_em_garantia": False, "auto_infracao_nao_quitado": False, "situacao_car": "ATIVO_REGULAR", "sobreposicao_app_ou_reserva": False},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 11, "pior_atraso_dias_12m": 26, "pct_titulos_pagos_em_dia_12m": 0.87, "renegociacoes_12m": 0},
            "juridico": {"execucoes_titulo_12m": 0, "valor_total_em_execucao": 0.0, "credores_distintos_executando": 0, "protestos_ativos": 1, "protestos_12m": 1, "credores_protestantes_180d": 1},
            "fiscal": {"divida_ativa_pgfn": 0.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -19, "produtividade_vs_media_regional_pct": -6},
            "ambiental": {"embargo_ibama_vigente": False, "embargo_sobre_imovel_em_garantia": False, "auto_infracao_nao_quitado": False, "situacao_car": "PENDENTE", "sobreposicao_app_ou_reserva": False},
        },
        {
            "interno": {"atraso_medio_dias_12m": 10, "atraso_medio_dias_90d": 14, "pior_atraso_dias_12m": 32, "pct_titulos_pagos_em_dia_12m": 0.84, "renegociacoes_12m": 1},
            "juridico": {"execucoes_titulo_12m": 1, "valor_total_em_execucao": 420_000.0, "credores_distintos_executando": 1},
            "fiscal": {"divida_ativa_pgfn": 440_000.0, "divida_ativa_pgfn_90d_atras": 0.0},
            "agro": {"risco_zarc": "moderado", "quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -22, "produtividade_vs_media_regional_pct": -8},
            "ambiental": {"embargo_ibama_vigente": False, "embargo_sobre_imovel_em_garantia": False, "auto_infracao_nao_quitado": False, "situacao_car": "PENDENTE", "sobreposicao_app_ou_reserva": False},
        },
        {
            "interno": {"atraso_medio_dias_12m": 12, "atraso_medio_dias_90d": 17, "pior_atraso_dias_12m": 39, "pct_titulos_pagos_em_dia_12m": 0.80, "renegociacoes_12m": 1},
            "fiscal": {"divida_ativa_pgfn": 440_000.0, "divida_ativa_pgfn_90d_atras": 440_000.0},
            "agro": {"quebra_safra_regional_pct": 16, "desvio_precipitacao_pct": -25, "produtividade_vs_media_regional_pct": -10},
            "ambiental": {"embargo_ibama_vigente": False, "embargo_sobre_imovel_em_garantia": False, "situacao_car": "PENDENTE"},
        },
        {
            "interno": {"atraso_medio_dias_12m": 13, "atraso_medio_dias_90d": 18, "pior_atraso_dias_12m": 42, "pct_titulos_pagos_em_dia_12m": 0.78},
            "ambiental": {"embargo_ibama_vigente": False, "embargo_sobre_imovel_em_garantia": False},
        },
    ],
)
