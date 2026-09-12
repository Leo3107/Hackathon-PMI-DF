"""`ribeirao-claro` — prospect **limítrofe** (§11). Score 650,5 · rating B · RJ12 22,50%.

É o caso em que a decisão é humana, e a aplicação tem de deixar isso explícito.
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

from .._base import DATA_REFERENCIA, evidencias_padrao, garantia, operacao_proposta

ID = "ribeirao-claro"
CULTURAS = ["Soja", "Milho safrinha"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Fazenda Ribeirão Claro Agro Ltda",
    nome_fantasia="Ribeirão Claro",
    documento="38.726.514/0001-00",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Jataí",
    uf="GO",
    atividade="Produtor rural — grãos",
    cnae_principal="0115-6/00",
    culturas=CULTURAS,
    inicio_relacionamento=DATA_REFERENCIA,
    estado=EstadoCliente.ATIVO,
    origem=OrigemCliente.PROSPECT,
)

FATOS = FatosDoCliente(
    cliente_id=ID,
    data_referencia=DATA_REFERENCIA,
    interno=FatosInternos(),
    juridico=FatosJuridicos(
        execucoes_titulo_12m=2,
        execucoes_titulo_90d=2,
        valor_total_em_execucao=900_000.0,
        credores_distintos_executando=3,
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(divida_ativa_pgfn=1_400_000.0, divida_ativa_pgfn_90d_atras=950_000.0),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.CRITICO,
        quebra_safra_regional_pct=24,
        desvio_precipitacao_pct=-40,
        produtividade_vs_media_regional_pct=-20,
        area_total_ha=1_600,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=4,
        capital_social=1_600_000.0,
        anos_atividade_comprovada=4,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
    operacoes=operacao_proposta(
        ID, 4_500_000.0, "Operação em análise — custeio pretendido da safra 2026/27"
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.PENHOR_SAFRA,
            "Penhor da safra de soja 2026/27, proposto",
            3_200_000.0,
            data_avaliacao=DATA_REFERENCIA,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.AVAL_FIANCA,
            "Aval dos sócios, proposto",
            1_500_000.0,
            data_avaliacao=DATA_REFERENCIA,
        ),
    ],
    limite_aprovado=4_500_000.0,
    patrimonio_declarado=6_200_000.0,
    faturamento_estimado_anual=11_200_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: (
                "Duas execuções de título distribuídas em 90 dias por três credores distintos, "
                "valor agregado R$ 900.000."
            ),
            FonteId.PGFN: "R$ 1.400.000 em dívida ativa, contra R$ 950.000 há 90 dias.",
            FonteId.MAPA_ZARC: "ZARC crítico para a soja em Jataí/GO na janela 2026/27.",
            FonteId.INTERNO_KRILLTECH: (
                "Sem histórico interno. Concentração de 54,1% do custeio em um único "
                "fornecedor — contexto narrativo, não fator do motor."
            ),
        },
    ),
)
