"""`maria-nogueira` — **produtora rural PF elegível a RJ** (§7.17).

Contraste direto com `joao-camargo`: mesma natureza jurídica, elegibilidade
oposta, porque tem 9 anos de atividade comprovada, livro-caixa digital e IE.
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

ID = "maria-nogueira"
CULTURAS = ["Soja", "Algodão"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Maria Aparecida Ferreira Nogueira",
    documento="317.604.928-50",
    tipo_pessoa=TipoPessoa.PF,
    municipio="Luís Eduardo Magalhães",
    uf="BA",
    atividade="Produtora rural pessoa física — grãos e fibras",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento="2017-06-12",
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.CARTEIRA,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(
        atraso_medio_dias_12m=5,
        atraso_medio_dias_90d=5,
        pior_atraso_dias_12m=16,
        pct_titulos_pagos_em_dia_12m=0.93,
    ),
    juridico=FatosJuridicos(
        protestos_ativos=2, protestos_12m=2, credores_protestantes_180d=1, sem_litigio_36m=True
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=11,
        desvio_precipitacao_pct=-22,
        produtividade_vs_media_regional_pct=-4,
        area_total_ha=1_780,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=9,
        # Convenção C2: em PF o campo recebe o patrimônio rural declarado no IRPF.
        capital_social=12_000_000.0,
        qsa_estavel_5anos=False,
        possui_livro_caixa_digital=True,
        possui_inscricao_estadual=True,
        anos_atividade_comprovada=9,
        tipo_pessoa=TipoPessoa.PF,
    ),
    ambiental=FatosAmbientais(),
    operacoes=montar_operacoes(
        ID,
        p1=900_000.0,
        p2=600_000.0,
        p3=1_760_000.0,
        p4=1_440_000.0,
        tipo_op2=TipoOperacao.BARTER,
        descricao_op2="Custeio da safra 2026/27 — soja",
        data_op3="2024-02-26",
        barter=barter_de("Soja", 18_366, PRECO_SACA["soja"], f"GAR-{ID.upper()}-1"),
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira nº 2026/0139 — 18.366 sc de soja",
            2_800_000.0,
        ),
        garantia(ID, 2, TipoGarantia.ALIENACAO_FIDUCIARIA, "Trator e plataforma de corte", 1_400_000.0),
        garantia(ID, 3, TipoGarantia.PENHOR_SAFRA, "Penhor da safra de algodão 2026/27", 1_600_000.0),
    ],
    limite_aprovado=5_200_000.0,
    patrimonio_declarado=31_000_000.0,
    faturamento_estimado_anual=14_600_000.0,
    evidencias=evidencias_padrao(
        ID,
        redesim=False,
        resumos={
            FonteId.RECEITA_FEDERAL: (
                "CPF regular. Produtora rural pessoa física com inscrição estadual e "
                "livro-caixa digital; 9 anos de atividade comprovada — elegível a RJ."
            ),
            FonteId.DATAJUD_CNJ: "Nenhuma ação ajuizada nos últimos 36 meses.",
            FonteId.INTERNO_KRILLTECH: "Contratação de seguro agrícola em fev/2026 — ponto de inflexão.",
        },
    ),
)

SNAPSHOTS = serie_de_snapshots(
    FATOS,
    [
        {
            "interno": {"atraso_medio_dias_12m": 9, "atraso_medio_dias_90d": 9, "pior_atraso_dias_12m": 26, "pct_titulos_pagos_em_dia_12m": 0.87},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 17, "desvio_precipitacao_pct": -31, "produtividade_vs_media_regional_pct": -9, "seguro_agricola_vigente": False},
            "cadastral": {"anos_atividade": 8, "anos_atividade_comprovada": 8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 24, "pct_titulos_pagos_em_dia_12m": 0.88},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 15, "desvio_precipitacao_pct": -28, "produtividade_vs_media_regional_pct": -8, "seguro_agricola_vigente": False},
            "cadastral": {"anos_atividade": 8, "anos_atividade_comprovada": 8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 7, "atraso_medio_dias_90d": 7, "pior_atraso_dias_12m": 22, "pct_titulos_pagos_em_dia_12m": 0.90},
            "juridico": {"protestos_ativos": 2, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 14, "desvio_precipitacao_pct": -26, "produtividade_vs_media_regional_pct": -7},
            "cadastral": {"anos_atividade": 8, "anos_atividade_comprovada": 8},
        },
        {
            "interno": {"atraso_medio_dias_12m": 8, "atraso_medio_dias_90d": 8, "pior_atraso_dias_12m": 23, "pct_titulos_pagos_em_dia_12m": 0.89},
            "juridico": {"protestos_ativos": 3, "protestos_12m": 3, "credores_protestantes_180d": 2},
            "agro": {"quebra_safra_regional_pct": 12, "desvio_precipitacao_pct": -28, "produtividade_vs_media_regional_pct": -6},
        },
        {
            "interno": {"atraso_medio_dias_12m": 6, "atraso_medio_dias_90d": 6, "pior_atraso_dias_12m": 18, "pct_titulos_pagos_em_dia_12m": 0.92},
            "agro": {"quebra_safra_regional_pct": 11, "desvio_precipitacao_pct": -23, "produtividade_vs_media_regional_pct": -5},
        },
    ],
)
