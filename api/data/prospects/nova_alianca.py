"""`nova-alianca` — prospect **aprovável** (§11). Score 976,9 · rating A.

Sem histórico interno: `interno` fica inteiramente no padrão e a dimensão
comportamental resulta em 1000. A UI precisa explicitar *"sem histórico interno;
dimensão comportamental não penalizada por ausência de dado"*.
"""

from __future__ import annotations

from models.cliente import Cliente
from models.enums import (
    EstadoCliente,
    FonteId,
    OrigemCliente,
    RiscoZarc,
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

ID = "nova-alianca"
CULTURAS = ["Soja", "Milho safrinha", "Feijão"]

CLIENTE = Cliente(
    id=ID,
    razao_social="Agropecuária Nova Aliança Ltda",
    nome_fantasia="Nova Aliança",
    documento="50.139.428/0001-98",
    tipo_pessoa=TipoPessoa.PJ,
    municipio="Sinop",
    uf="MT",
    atividade="Produtor rural — grãos e feijão",
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
        protestos_ativos=2, protestos_12m=2, credores_protestantes_180d=1, sem_litigio_36m=True
    ),
    fiscal=FatosFiscais(todas_certidoes_negativas=True),
    agro=FatosAgro(
        risco_zarc=RiscoZarc.MODERADO,
        quebra_safra_regional_pct=12,
        desvio_precipitacao_pct=-28,
        produtividade_vs_media_regional_pct=-7,
        area_total_ha=6_600,
        seguro_agricola_vigente=True,
        safra_referencia="2026/27",
        culturas=CULTURAS,
    ),
    cadastral=FatosCadastrais(
        anos_atividade=16,
        capital_social=7_500_000.0,
        qsa_estavel_5anos=True,
        anos_atividade_comprovada=16,
        possui_inscricao_estadual=True,
        tipo_pessoa=TipoPessoa.PJ,
    ),
    ambiental=FatosAmbientais(),
    operacoes=operacao_proposta(
        ID, 6_000_000.0, "Operação em análise — limite pretendido para a safra 2026/27"
    ),
    garantias=[
        garantia(
            ID,
            1,
            TipoGarantia.CPR_FINANCEIRA,
            "CPR financeira proposta — 35.019 sc de soja",
            4_500_000.0,
            data_avaliacao=DATA_REFERENCIA,
        ),
        garantia(
            ID,
            2,
            TipoGarantia.ALIENACAO_FIDUCIARIA,
            "Colheitadeira e dois tratores, alienação fiduciária proposta",
            2_600_000.0,
            data_avaliacao=DATA_REFERENCIA,
        ),
    ],
    limite_aprovado=6_500_000.0,
    patrimonio_declarado=41_000_000.0,
    faturamento_estimado_anual=33_000_000.0,
    evidencias=evidencias_padrao(
        ID,
        resumos={
            FonteId.DATAJUD_CNJ: "Nenhuma ação ajuizada nos últimos 36 meses.",
            FonteId.PGFN: "Certidões negativas vigentes.",
            FonteId.CARTORIO_PROTESTO: (
                "Dois protestos ativos de R$ 31 mil, contestados administrativamente."
            ),
            FonteId.INTERNO_KRILLTECH: (
                "Sem histórico interno: prospect em due diligence. A dimensão comportamental "
                "não é penalizada por ausência de dado."
            ),
        },
    ),
)
