"""Relatório de cobertura — quais das 7 dimensões foram apuradas, e por qual fonte.

Sem este relatório o analista não sabe distinguir **"risco baixo"** de
**"não olhei"**. Os dois produzem score alto; só um deles é informação.

Três políticas para dado ausente, e o relatório é onde elas ficam visíveis:

| Política | Quando | Efeito no motor | Efeito na tela |
|---|---|---|---|
| `NEUTRO` | Nenhuma fonte da dimensão respondeu | A dimensão **sai da média ponderada**: peso 0, redistribuído proporcionalmente entre as apuradas | Dimensão marcada `CEGA`; a nota não fala sobre ela |
| `CONSERVADOR` | A fonte respondeu e o campo veio vazio, e o vazio é sinal | Assume o pior plausível **dentro do score** | Dimensão `APURADA`, com a presunção nomeada |
| `NAO_APURADO` | A dimensão tem fonte, mas aquele fator específico não tem fonte nenhuma na coleta | Impacto **zero** — o fato recebe o valor neutro | Dimensão `PARCIAL`, com o fator listado como cego |

Por que NEUTRO é renormalização de peso, e não "fator não emitido e pronto":
o motor calcula `scoreDimensao = 1000 − Σ penalidades`. Uma dimensão sem
nenhum fator vale **1000** — nota máxima por não ter sido consultada. Com sete
dimensões, quatro cegas entregariam 56% do score de graça. Zerar o peso e
redistribuí-lo entre as apuradas mantém as duas invariantes do motor:

- **I1** — os pesos continuam somando exatamente 1,00.
- **I2** — `score = 1000 + Σ impactoGlobalAjustado` continua fechando, porque
  o fechamento depende apenas de `Σ pesos == 1`.

E diz a verdade: *"a nota é sobre o que eu consegui olhar"*.

Este módulo é puro: sem I/O, sem relógio, sem aleatoriedade.
"""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

from coleta.models import Features
from models.base import ModeloLastro
from models.enums import DimensaoId
from pydantic import Field
from scoring.config import CONFIG_PADRAO, ScoringConfig

__all__ = [
    "Politica",
    "StatusDimensao",
    "FonteDaColeta",
    "ROTULO_DA_FONTE",
    "FONTES_POR_DIMENSAO",
    "CampoNaoApurado",
    "CoberturaDeDimensao",
    "RelatorioDeCobertura",
    "montar_cobertura",
    "pesos_renormalizados",
    "config_da_cobertura",
]


class Politica(StrEnum):
    """O que foi feito com o `None`. Declarada por campo em `features_para_fatos`."""

    MAPEADO = "MAPEADO"
    NEUTRO = "NEUTRO"
    CONSERVADOR = "CONSERVADOR"
    NAO_APURADO = "NAO_APURADO"


class StatusDimensao(StrEnum):
    APURADA = "APURADA"
    #: Tem fonte, mas fatores relevantes da dimensão não têm fonte nenhuma.
    PARCIAL = "PARCIAL"
    #: Nenhuma fonte respondeu. Peso zerado e redistribuído.
    CEGA = "CEGA"


class FonteDaColeta(StrEnum):
    """Chaves de `Features.fontes_disponiveis`, mais as fontes sob demanda.

    Deliberadamente **não** reaproveitam `models.enums.FonteId`: aquele
    catálogo é o das 14 fontes simuladas do protótipo e não tem entrada para
    IBGE/SIDRA nem para NASA POWER. Carimbar `CONAB` numa consulta ao SIDRA
    seria mentir sobre a procedência no exato relatório que existe para
    garantir procedência.
    """

    PGFN = "pgfn"
    RECEITA = "receita"
    GRAFO_SOCIETARIO = "grafo_societario"
    IBAMA_AUTOS = "ibama_autos"
    IBAMA_EMBARGOS = "ibama_embargos"
    BCB_MDCR = "bcb_mdcr"
    IBGE_PRODUCAO = "ibge_producao"
    CLIMA = "clima"
    #: Sob demanda: nunca aparece em `fontes_disponiveis`; inferida dos campos.
    PROTESTOS = "protestos"
    #: Não é fonte pública: é a proposta de operação trazida pelo analista.
    PROPOSTA_KRILL = "proposta_krill"


ROTULO_DA_FONTE: dict[FonteDaColeta, str] = {
    FonteDaColeta.PGFN: "PGFN — Dívida Ativa da União",
    FonteDaColeta.RECEITA: "Receita Federal — CNPJ",
    FonteDaColeta.GRAFO_SOCIETARIO: "Receita Federal — quadro societário",
    FonteDaColeta.IBAMA_AUTOS: "IBAMA — autos de infração",
    FonteDaColeta.IBAMA_EMBARGOS: "IBAMA — embargos",
    FonteDaColeta.BCB_MDCR: "BCB — Matriz de Dados do Crédito Rural",
    FonteDaColeta.IBGE_PRODUCAO: "IBGE/SIDRA — Produção Agrícola Municipal",
    FonteDaColeta.CLIMA: "NASA POWER / INMET — série climática",
    FonteDaColeta.PROTESTOS: "Cartórios de protesto",
    FonteDaColeta.PROPOSTA_KRILL: "Krill Tech — proposta de operação",
}

#: Quais fontes da coleta alimentam cada dimensão do motor (`02` §2).
#:
#: `BCB_MDCR` não aparece: nenhum dos seus cinco campos tem fator no catálogo
#: da §4 (são estatísticas municipais de crédito, não fatos do cliente). Ele é
#: reportado em `fontes_sem_fator` para não parecer que foi esquecido.
FONTES_POR_DIMENSAO: dict[DimensaoId, tuple[FonteDaColeta, ...]] = {
    DimensaoId.COMPORTAMENTAL: (),
    DimensaoId.JURIDICO: (FonteDaColeta.PROTESTOS,),
    DimensaoId.FISCAL: (FonteDaColeta.PGFN,),
    DimensaoId.AGROCLIMATICO: (FonteDaColeta.IBGE_PRODUCAO, FonteDaColeta.CLIMA),
    DimensaoId.CADASTRAL: (FonteDaColeta.RECEITA, FonteDaColeta.GRAFO_SOCIETARIO),
    DimensaoId.AMBIENTAL: (FonteDaColeta.IBAMA_AUTOS, FonteDaColeta.IBAMA_EMBARGOS),
    DimensaoId.GARANTIAS: (FonteDaColeta.PROPOSTA_KRILL,),
}

ROTULOS_DIMENSAO: dict[DimensaoId, str] = dict(CONFIG_PADRAO.rotulos_dimensoes)

#: Dimensões que a coleta pública **não pode** apurar por natureza: dependem do
#: histórico interno da Krill Tech. Nunca deixam de ser cegas para um prospect.
DIMENSOES_SEM_FONTE_PUBLICA: tuple[DimensaoId, ...] = (
    DimensaoId.COMPORTAMENTAL,
    DimensaoId.GARANTIAS,
)

#: Sob cegueira total, a única dimensão sobre a qual existe uma afirmação — e
#: ela é negativa: *nada foi comprovado*. Ver `pesos_renormalizados`.
DIMENSAO_DE_ULTIMO_RECURSO = DimensaoId.CADASTRAL


class CampoNaoApurado(ModeloLastro):
    """Um fator do motor que a coleta não tem como alimentar."""

    fator: str
    dimensao: DimensaoId
    politica: Politica
    motivo: str


class CoberturaDeDimensao(ModeloLastro):
    dimensao: DimensaoId
    rotulo: str
    status: StatusDimensao
    politica: Politica
    peso_original: float
    peso_aplicado: float
    fontes_apuradas: list[str] = Field(default_factory=list)
    fontes_ausentes: list[str] = Field(default_factory=list)
    fatores_cegos: list[CampoNaoApurado] = Field(default_factory=list)
    justificativa: str = ""

    @property
    def apurada(self) -> bool:
        return self.status is not StatusDimensao.CEGA


class RelatorioDeCobertura(ModeloLastro):
    """O que foi olhado, o que não foi, e com que peso cada coisa entrou."""

    documento: str
    dimensoes: list[CoberturaDeDimensao] = Field(default_factory=list)
    fontes_consultadas: list[str] = Field(default_factory=list)
    fontes_ausentes: list[str] = Field(default_factory=list)
    #: Fontes que responderam mas não têm fator correspondente no motor.
    fontes_sem_fator: list[str] = Field(default_factory=list)
    campos_sem_fato: list[str] = Field(default_factory=list)
    #: `False` quando nenhuma dimensão foi apurada — não há o que pontuar.
    analisavel: bool = False
    #: Fração do peso canônico efetivamente coberta por fonte (0..1).
    cobertura_ponderada: float = 0.0

    @property
    def dimensoes_apuradas(self) -> list[DimensaoId]:
        return [c.dimensao for c in self.dimensoes if c.apurada]

    @property
    def dimensoes_cegas(self) -> list[DimensaoId]:
        return [c.dimensao for c in self.dimensoes if not c.apurada]

    def de(self, dimensao: DimensaoId) -> CoberturaDeDimensao:
        for cobertura in self.dimensoes:
            if cobertura.dimensao is dimensao:
                return cobertura
        raise KeyError(dimensao)


# ---------------------------------------------------------------------------
# Detecção de cobertura — "a fonte respondeu sobre ESTE documento?"
# ---------------------------------------------------------------------------
#
# O critério é o campo, não o inventário: `build_features` devolve `None`
# quando não houve dado e um valor (inclusive `0`) quando houve consulta sem
# achado. `fontes_disponiveis` entra só para distinguir os dois casos em que
# isso importa — a Receita, cujo silêncio sobre um CNPJ presente na base é
# sinal (ver `features_para_fatos`), e o IBAMA.


def _fonte_respondeu(features: Features, fonte: FonteDaColeta) -> bool:
    carregadas = set(features.fontes_disponiveis)
    match fonte:
        case FonteDaColeta.PGFN:
            return features.divida_ativa_total is not None
        case FonteDaColeta.RECEITA:
            # A base carregada responde mesmo quando o CNPJ não consta nela:
            # "não achei" é resultado, não ausência de consulta.
            return fonte.value in carregadas or features.situacao_cadastral is not None
        case FonteDaColeta.GRAFO_SOCIETARIO:
            return features.n_empresas_do_socio is not None
        case FonteDaColeta.IBAMA_AUTOS:
            return fonte.value in carregadas or features.n_autos_infracao is not None
        case FonteDaColeta.IBAMA_EMBARGOS:
            return fonte.value in carregadas or features.flag_embargo_ativo is not None
        case FonteDaColeta.BCB_MDCR:
            return features.volume_credito_rural_municipio is not None
        case FonteDaColeta.IBGE_PRODUCAO:
            return features.desvio_produtividade_vs_media_5a is not None
        case FonteDaColeta.CLIMA:
            return features.precipitacao_vs_normal_climatologica is not None
        case FonteDaColeta.PROTESTOS:
            return features.n_protestos_ativos is not None
        case FonteDaColeta.PROPOSTA_KRILL:
            return False  # decidido por parâmetro, não pelas Features
    return False


def montar_cobertura(
    features: Features,
    *,
    fatores_cegos: dict[DimensaoId, list[CampoNaoApurado]] | None = None,
    tem_proposta: bool = False,
    campos_sem_fato: list[str] | None = None,
) -> RelatorioDeCobertura:
    """Relatório de cobertura de um `Features`. Função pura.

    `fatores_cegos` vem do adaptador: são os fatores do catálogo §4 que nenhuma
    fonte da coleta alimenta (política `NAO_APURADO`). `tem_proposta` diz se o
    analista informou o valor da operação pretendida — o único caminho pelo
    qual a dimensão de garantias deixa de ser cega para um prospect.
    """
    cegos = fatores_cegos or {}
    pesos = CONFIG_PADRAO.pesos_dimensoes
    coberturas: list[CoberturaDeDimensao] = []
    consultadas: list[str] = []
    ausentes: list[str] = []

    for dimensao, fontes in FONTES_POR_DIMENSAO.items():
        respondeu = [
            fonte
            for fonte in fontes
            if (tem_proposta if fonte is FonteDaColeta.PROPOSTA_KRILL else _fonte_respondeu(features, fonte))
        ]
        faltou = [fonte for fonte in fontes if fonte not in respondeu]
        consultadas.extend(f.value for f in respondeu if f.value not in consultadas)
        ausentes.extend(f.value for f in faltou if f.value not in ausentes)

        cegos_da_dimensao = cegos.get(dimensao, [])
        if not fontes:
            status, politica = StatusDimensao.CEGA, Politica.NEUTRO
        elif not respondeu:
            status, politica = StatusDimensao.CEGA, Politica.NEUTRO
        elif cegos_da_dimensao:
            status, politica = StatusDimensao.PARCIAL, Politica.NAO_APURADO
        else:
            status, politica = StatusDimensao.APURADA, Politica.MAPEADO

        coberturas.append(
            CoberturaDeDimensao(
                dimensao=dimensao,
                rotulo=ROTULOS_DIMENSAO[dimensao],
                status=status,
                politica=politica,
                peso_original=pesos[dimensao],
                peso_aplicado=0.0,  # preenchido abaixo
                fontes_apuradas=[ROTULO_DA_FONTE[f] for f in respondeu],
                fontes_ausentes=[ROTULO_DA_FONTE[f] for f in faltou],
                fatores_cegos=cegos_da_dimensao,
                justificativa=_justificar(dimensao, status, respondeu, faltou),
            )
        )

    relatorio = RelatorioDeCobertura(
        documento=features.documento,
        dimensoes=coberturas,
        fontes_consultadas=consultadas,
        fontes_ausentes=ausentes,
        fontes_sem_fator=(
            [ROTULO_DA_FONTE[FonteDaColeta.BCB_MDCR]]
            if _fonte_respondeu(features, FonteDaColeta.BCB_MDCR)
            else []
        ),
        campos_sem_fato=campos_sem_fato or [],
        analisavel=any(c.apurada for c in coberturas),
        cobertura_ponderada=round(
            sum(pesos[c.dimensao] for c in coberturas if c.apurada), 4
        ),
    )

    novos_pesos = pesos_renormalizados(relatorio)
    for cobertura in relatorio.dimensoes:
        cobertura.peso_aplicado = round(novos_pesos[cobertura.dimensao], 6)
    return relatorio


def _justificar(
    dimensao: DimensaoId,
    status: StatusDimensao,
    respondeu: list[FonteDaColeta],
    faltou: list[FonteDaColeta],
) -> str:
    if status is StatusDimensao.CEGA and dimensao in DIMENSOES_SEM_FONTE_PUBLICA:
        return (
            "Cega por natureza: depende do histórico interno da Krill Tech, que "
            "não existe em base pública. Para um prospect, esta dimensão não "
            "vota na nota."
        )
    if status is StatusDimensao.CEGA:
        nomes = ", ".join(ROTULO_DA_FONTE[f] for f in faltou)
        return (
            f"Nenhuma fonte respondeu ({nomes}). O peso desta dimensão foi "
            "redistribuído entre as apuradas — a nota não fala sobre ela."
        )
    if status is StatusDimensao.PARCIAL:
        return (
            "Apurada em parte: há fonte para a dimensão, mas fatores do "
            "catálogo continuam sem fonte alguma. Ver `fatoresCegos`."
        )
    return "Apurada por " + ", ".join(ROTULO_DA_FONTE[f] for f in respondeu) + "."


# ---------------------------------------------------------------------------
# Renormalização de pesos — a mecânica da política NEUTRO
# ---------------------------------------------------------------------------


def pesos_renormalizados(relatorio: RelatorioDeCobertura) -> dict[DimensaoId, float]:
    """Pesos das dimensões apuradas, reescalados para somar 1,00.

    Dimensão cega recebe peso 0; o peso liberado é redistribuído em proporção
    ao peso canônico das apuradas, o que preserva a hierarquia da §2 entre
    elas — comportamental continua valendo mais que ambiental *entre as que
    foram olhadas*.

    **Cegueira total.** Quando nada foi apurado não há entre quem redistribuir,
    e pesos todos-zero quebrariam I2 (`score` cairia para 0 enquanto
    `1000 + Σ impactos` continuaria 1000). O peso inteiro vai então para a
    dimensão cadastral, que sob cegueira total carrega a única afirmação
    disponível — *nada comprovado* — pela política CONSERVADOR. O número
    resultante **não deve ser exibido**: `analisavel` é `False` e a rota de due
    diligence responde "não encontrado", com este relatório junto.
    """
    pesos = CONFIG_PADRAO.pesos_dimensoes
    apuradas = [c.dimensao for c in relatorio.dimensoes if c.apurada]
    if not apuradas:
        return {
            dimensao: (1.0 if dimensao is DIMENSAO_DE_ULTIMO_RECURSO else 0.0)
            for dimensao in pesos
        }
    total = sum(pesos[d] for d in apuradas)
    return {
        dimensao: (pesos[dimensao] / total if dimensao in apuradas else 0.0)
        for dimensao in pesos
    }


def config_da_cobertura(
    relatorio: RelatorioDeCobertura, base: ScoringConfig | None = None
) -> ScoringConfig:
    """`ScoringConfig` com os pesos renormalizados pela cobertura.

    É assim que a política NEUTRO chega ao motor sem tocar em `api/scoring/`:
    o motor já aceita uma configuração por chamada (`calcular_risco(fatos,
    config=...)`). A instância base nunca é mutada — `dataclasses.replace`
    devolve uma cópia.
    """
    origem = base if base is not None else CONFIG_PADRAO
    return replace(origem, pesos_dimensoes=pesos_renormalizados(relatorio))
