"""Fatos brutos — "o que as fontes disseram". É o que um dia virá de API.

Regra de ouro de `specs/01-modelo-de-dados.md`: **se um valor pode ser derivado,
ele não existe aqui**. Score, PD, rating, coberturas, red flags e recomendação
são todos calculados por `scoring.calcular_risco`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ModeloLastro
from .enums import FonteId, RiscoZarc, SituacaoCar, SituacaoRfb, TipoEvidencia, TipoPessoa
from .exposicao import Garantia, Operacao

__all__ = [
    "CovenantRompido",
    "RecuperacaoJudicial",
    "FatosInternos",
    "FatosJuridicos",
    "FatosFiscais",
    "FatosAgro",
    "FatosCadastrais",
    "FatosAmbientais",
    "Evidencia",
    "FatosDoCliente",
]


class CovenantRompido(ModeloLastro):
    """Inadimplência TÉCNICA: covenant contratual rompido e ainda vigente."""

    id: str
    #: ex.: 'Endividamento total acima de 2,5× o patrimônio'
    descricao: str
    limite_contratual: str = ""
    valor_apurado: str = ""
    #: ISO date
    data_deteccao: str = ""


class RecuperacaoJudicial(ModeloLastro):
    """RJ ajuizada ou deferida. Ver Stay Period em `02-motor-de-risco.md` §9."""

    #: ISO date
    data_distribuicao: str
    #: ISO date
    data_deferimento: str | None = None
    dias_prorrogados_stay: int = 0


class FatosInternos(ModeloLastro):
    atraso_medio_dias_12m: float = 0.0
    atraso_medio_dias_90d: float = 0.0
    pior_atraso_dias_12m: float = 0.0
    #: 0..1
    pct_titulos_pagos_em_dia_12m: float = 1.0
    renegociacoes_12m: int = 0
    sem_atraso_relevante_24m: bool = False
    covenants_rompidos: list[CovenantRompido] = Field(default_factory=list)


class FatosJuridicos(ModeloLastro):
    execucoes_titulo_12m: int = 0
    execucoes_titulo_90d: int = 0
    valor_total_em_execucao: float = 0.0
    credores_distintos_executando: int = 0
    protestos_ativos: int = 0
    protestos_12m: int = 0
    credores_protestantes_180d: int = 0
    acoes_trabalhistas_transitadas: int = 0
    pedido_falencia: bool = False
    recuperacao_judicial: RecuperacaoJudicial | None = None
    sem_litigio_36m: bool = False
    fraude_confirmada: bool = False
    lista_suja_trabalho_escravo: bool = False


class FatosFiscais(ModeloLastro):
    divida_ativa_pgfn: float = 0.0
    divida_ativa_pgfn_90d_atras: float = 0.0
    cndt_positiva: bool = False
    valor_debito_trabalhista: float = 0.0
    crf_fgts_regular: bool = True
    parcelamento_rompido_12m: bool = False
    execucoes_fiscais: int = 0
    valor_execucoes_fiscais: float = 0.0
    todas_certidoes_negativas: bool = False


class FatosAgro(ModeloLastro):
    risco_zarc: RiscoZarc = RiscoZarc.BAIXO
    #: 0..100
    quebra_safra_regional_pct: float = 0.0
    #: pode ser negativo
    desvio_precipitacao_pct: float = 0.0
    #: negativo = abaixo da média
    produtividade_vs_media_regional_pct: float = 0.0
    area_total_ha: float = 0.0
    area_irrigada_ha: float = 0.0
    seguro_agricola_vigente: bool = False
    #: ex.: '2025/26'
    safra_referencia: str = ""
    #: Culturas exploradas. Necessário pelos fatores `monocultura` e
    #: `diversificacao` (02 §4, D4), que a spec 01 só previa em `Cliente`.
    #: Quando vazio, o motor aceita a lista vinda de `Cliente` como fallback.
    culturas: list[str] = Field(default_factory=list)


class FatosCadastrais(ModeloLastro):
    situacao_rfb: SituacaoRfb = SituacaoRfb.ATIVA
    anos_atividade: float = 0.0
    capital_social: float = 0.0
    alteracao_societaria_180d: bool = False
    saida_socio_majoritario_12m: bool = False
    qsa_estavel_5anos: bool = False
    cnae_compativel: bool = True
    #: Lei 14.112/2020 — habilita produtor rural PF a pedir RJ.
    possui_livro_caixa_digital: bool = False
    possui_inscricao_estadual: bool = False
    anos_atividade_comprovada: float = 0.0
    #: Necessário à elegibilidade de RJ (02 §7), que a spec 01 só previa em
    #: `Cliente`. Quando ausente, o motor aceita o valor vindo de `Cliente`.
    tipo_pessoa: TipoPessoa | None = None


class FatosAmbientais(ModeloLastro):
    embargo_ibama_vigente: bool = False
    #: Agrava para gatilho de veto: embargo recai sobre bem dado em garantia.
    embargo_sobre_imovel_em_garantia: bool = False
    auto_infracao_nao_quitado: bool = False
    situacao_car: SituacaoCar = SituacaoCar.ATIVO_REGULAR
    sobreposicao_app_ou_reserva: bool = False


class Evidencia(ModeloLastro):
    id: str
    fonte: FonteId
    #: rótulo humano: 'DataJud — CNJ'
    nome_fonte: str
    tipo: TipoEvidencia
    titulo: str
    resumo: str = ""
    #: ISO date
    data_consulta: str = ""
    data_documento: str | None = None
    #: Sempre true nesta versão. Renderiza o selo "consulta simulada".
    simulada: Literal[True] = True
    url_ficticia: str | None = None
    #: Fatores do motor que esta evidência sustenta. Liga evidência → número.
    fatores_relacionados: list[str] = Field(default_factory=list)


class FatosDoCliente(ModeloLastro):
    cliente_id: str
    #: Data de referência dos fatos. O motor NUNCA lê o relógio; recebe esta data.
    data_referencia: str

    interno: FatosInternos = Field(default_factory=FatosInternos)
    juridico: FatosJuridicos = Field(default_factory=FatosJuridicos)
    fiscal: FatosFiscais = Field(default_factory=FatosFiscais)
    agro: FatosAgro = Field(default_factory=FatosAgro)
    cadastral: FatosCadastrais = Field(default_factory=FatosCadastrais)
    ambiental: FatosAmbientais = Field(default_factory=FatosAmbientais)
    operacoes: list[Operacao] = Field(default_factory=list)
    garantias: list[Garantia] = Field(default_factory=list)
    limite_aprovado: float = 0.0
    patrimonio_declarado: float = 0.0
    faturamento_estimado_anual: float = 0.0

    #: Evidências que sustentam estes fatos. Toda red flag aponta para uma.
    evidencias: list[Evidencia] = Field(default_factory=list)
