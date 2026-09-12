"""`santa-helena-norte` — prospect **recusável** por composição de vetos (§11).

Score 748,5 (B) e classificação final **D**: `VETO_LISTA_SUJA` e `VETO_FRAUDE`
compõem. O embargo do IBAMA **não** recai sobre bem em garantia (a hipoteca é de
outra matrícula), então `VETO_EMBARGO_GARANTIA` não dispara — distinção que o
teste de vetos cobre.
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

ID = "santa-helena-norte"
CULTURAS = ["Soja"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agrícola Santa Helena do Norte Ltda",
    nome_fantasia="Santa Helena do Norte",
    documento="17.605.342/0001-38",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Confresa",
    uf="MT",
    atividade="Produtor rural — soja",
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
        protestos_ativos=2,
        protestos_12m=2,
        credores_protestantes_180d=1,
        fraude_confirmada=True,
        lista_suja_trabalho_escravo=True,
    ),
    fiscal=FatosFiscais(),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.ALTO,
        quebra_safra_regional_pct=20,
        desvio_precipitacao_pct=-28,
        produtividade_vs_media_regional_pct=-14,
        area_total_ha=3_000,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=11,
        capital_social=3_500_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=11,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(
        embargo_ibama_vigente=True,
        # O embargo recai sobre gleba distinta da hipotecada — VETO_EMBARGO_GARANTIA não dispara.
        embargo_sobre_imovel_em_garantia=False,
        auto_infracao_nao_quitado=True,
        situacao_car=SituacaoCar.IRREGULAR,
        sobreposicao_app_ou_reserva=True,
    ),
    operacoes=operacao_proposta(
        ID, 7_000_000.0, "Operação em análise — limite pretendido para a safra 2026/27"
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.HIPOTECA,
            "Matrícula 31.845 — gleba não alcançada pelo termo de embargo",
            4_600_000.0,
            data_avaliacao=DATA_REFERENCIA,
        )
    ],
    limite_aprovado=7_500_000.0,
    patrimonio_declarado=22_000_000.0,
    faturamento_estimado_anual=19_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.TST_CNDT: (
                "Inclusão no Cadastro de Empregadores que submeteram trabalhadores a condição "
                "análoga à de escravo."
            ),
            FonteId.DATAJUD_CNJ: (
                "Fraude confirmada em auditoria de campo: simulação de área plantada para "
                "obtenção de crédito."
            ),
            FonteId.IBAMA: (
                "Embargo vigente e auto de infração não quitado sobre gleba distinta da "
                "oferecida em hipoteca."
            ),
            FonteId.SICAR: "CAR irregular, com sobreposição de reserva legal.",
        },
    ),
)
