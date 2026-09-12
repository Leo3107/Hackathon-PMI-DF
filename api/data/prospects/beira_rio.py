"""`beira-rio` — prospect **recusável** por `VETO_CADASTRO_INAPTO` (§11).

Score 595,1 (C) e classificação final **D**: situação cadastral inapta na RFB e
CNAE de transporte rodoviário declarando atividade agrícola.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.enums import (
    EstadoCliente,
    FonteId,
    OrigemCliente,
    RiscoZarc,
    SituacaoCar,
    SituacaoRfb,
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

ID = "beira-rio"
CULTURAS = ["Soja", "Milho"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agrocomercial Beira Rio Ltda",
    nome_fantasia="Beira Rio",
    documento="29.471.863/0001-29",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Paragominas",
    uf="PA",
    atividade="Produtor rural — grãos (atividade declarada)",
    cnae_principal="4930-2/02",
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
        execucoes_titulo_12m=3,
        execucoes_titulo_90d=1,
        valor_total_em_execucao=1_100_000.0,
        credores_distintos_executando=3,
        protestos_ativos=3,
        protestos_12m=3,
        credores_protestantes_180d=2,
    ),
    fiscal=FatosFiscais(
        divida_ativa_pgfn=1_250_000.0,
        divida_ativa_pgfn_90d_atras=800_000.0,
        parcelamento_rompido_12m=True,
    ),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=23,
        desvio_precipitacao_pct=-36,
        produtividade_vs_media_regional_pct=-13,
        area_total_ha=2_400,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        situacao_rfb=SituacaoRfb.INAPTA,
        anos_atividade=7,
        capital_social=1_800_000.0,
        cnae_compativel=False,
        anos_atividade_comprovada=7,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(situacao_car=SituacaoCar.IRREGULAR),
    operacoes=operacao_proposta(
        ID, 5_000_000.0, "Operação em análise — limite pretendido para a safra 2026/27"
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.PENHOR_SAFRA,
            "Penhor da safra de soja 2026/27, proposto",
            3_000_000.0,
            data_avaliacao=DATA_REFERENCIA,
        )
    ],
    limite_aprovado=5_000_000.0,
    patrimonio_declarado=8_600_000.0,
    faturamento_estimado_anual=9_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.RECEITA_FEDERAL: (
                "CNPJ em situação INAPTA. CNAE principal 4930-2/02 (transporte rodoviário "
                "de carga) incompatível com a atividade agrícola declarada."
            ),
            FonteId.DATAJUD_CNJ: "Três execuções de título de três credores distintos.",
            FonteId.PGFN: "R$ 1.250.000 em dívida ativa crescente; parcelamento rompido.",
            FonteId.SICAR: "CAR em situação irregular.",
        },
    ),
)
