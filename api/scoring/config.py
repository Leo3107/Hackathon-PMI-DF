"""Todos os coeficientes do motor de risco.

Fonte: `specs/02-motor-de-risco.md`. **Nenhum número mágico pode aparecer no
corpo de uma função do pacote `scoring`** — se um número existe, ele está aqui,
com nome. Mudar o comportamento do motor é mudar este arquivo.

`ScoringConfig` é uma dataclass congelada cujos padrões são exatamente as
constantes deste módulo; qualquer campo pode ser sobrescrito com
`dataclasses.replace(CONFIG_PADRAO, peso_x=...)`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.enums import (
    CodigoRecomendacao,
    DimensaoId,
    EfeitoVeto,
    FonteId,
    Rating,
    RiscoZarc,
    Severidade,
    SituacaoCar,
    Tendencia,
    TipoGarantia,
    TipoPessoa,
)
from models.tabelas import HAIRCUT_POR_TIPO_GARANTIA, NATUREZA_POR_TIPO_GARANTIA

# ---------------------------------------------------------------------------
# §2 · Dimensões e pesos
# ---------------------------------------------------------------------------

PESOS_DIMENSOES: dict[DimensaoId, float] = {
    DimensaoId.COMPORTAMENTAL: 0.22,
    DimensaoId.JURIDICO: 0.20,
    DimensaoId.FISCAL: 0.14,
    DimensaoId.AGROCLIMATICO: 0.15,
    DimensaoId.CADASTRAL: 0.10,
    DimensaoId.AMBIENTAL: 0.09,
    DimensaoId.GARANTIAS: 0.10,
}

ROTULOS_DIMENSOES: dict[DimensaoId, str] = {
    DimensaoId.COMPORTAMENTAL: "Comportamental / histórico interno",
    DimensaoId.JURIDICO: "Jurídico & processual",
    DimensaoId.FISCAL: "Fiscal & trabalhista",
    DimensaoId.AGROCLIMATICO: "Agro & climático",
    DimensaoId.CADASTRAL: "Cadastral & societário",
    DimensaoId.AMBIENTAL: "Ambiental",
    DimensaoId.GARANTIAS: "Garantias & exposição",
}

FONTE_PADRAO_DIMENSAO: dict[DimensaoId, FonteId] = {
    DimensaoId.COMPORTAMENTAL: FonteId.INTERNO_KRILLTECH,
    DimensaoId.JURIDICO: FonteId.DATAJUD_CNJ,
    DimensaoId.FISCAL: FonteId.PGFN,
    DimensaoId.AGROCLIMATICO: FonteId.MAPA_ZARC,
    DimensaoId.CADASTRAL: FonteId.RECEITA_FEDERAL,
    DimensaoId.AMBIENTAL: FonteId.SICAR,
    DimensaoId.GARANTIAS: FonteId.INTERNO_KRILLTECH,
}

#: Sobrescreve a fonte padrão da dimensão para fatores com origem específica.
FONTE_POR_FATOR: dict[str, FonteId] = {
    "protestos": FonteId.CARTORIO_PROTESTO,
    "protesto_recorrente": FonteId.CARTORIO_PROTESTO,
    "rj_distribuida": FonteId.DJE,
    "pedido_falencia": FonteId.DJE,
    "trabalhistas": FonteId.TST_CNDT,
    "cndt_positiva": FonteId.TST_CNDT,
    "fgts_irregular": FonteId.CAIXA_CRF_FGTS,
    "quebra_safra_regional": FonteId.CONAB,
    "desvio_precipitacao": FonteId.INMET,
    "produtividade_abaixo": FonteId.CONAB,
    "monocultura": FonteId.SICAR,
    "diversificacao": FonteId.SICAR,
    "barter_sem_lastro": FonteId.INTERNO_KRILLTECH,
    "irrigacao_ou_seguro": FonteId.INTERNO_KRILLTECH,
    "alteracao_societaria": FonteId.REDESIM,
    "saida_socio_majoritario": FonteId.REDESIM,
    "qsa_estavel": FonteId.REDESIM,
    "embargo_ibama": FonteId.IBAMA,
    "auto_infracao": FonteId.IBAMA,
}

# ---------------------------------------------------------------------------
# §3 · Escala do score
# ---------------------------------------------------------------------------

SCORE_BASE: float = 1000.0
SCORE_MINIMO: float = 0.0
SCORE_MAXIMO: float = 1000.0

SINAL_RISCO: float = -1.0
SINAL_PROTECAO: float = 1.0

#: Arredondamentos de saída. Mantêm o JSON legível sem comprometer as
#: invariantes de fechamento (erro acumulado muito abaixo da tolerância 0,5).
CASAS_SCORE: int = 4
CASAS_PONTOS: int = 4
CASAS_PROBABILIDADE: int = 6
CASAS_MOEDA: int = 2
CASAS_FRACAO: int = 6

#: Tolerância das invariantes I2 e I6, em pontos de score.
TOLERANCIA_FECHAMENTO: float = 0.5

#: Conversão de dias corridos em anos (tempo de relacionamento, de atividade).
DIAS_POR_ANO: float = 365.25

#: Tipos de garantia que caracterizam CPR registrada cobrindo um barter (D4).
TIPOS_CPR: tuple[TipoGarantia, ...] = (TipoGarantia.CPR_FINANCEIRA, TipoGarantia.CPR_FISICA)

# ---------------------------------------------------------------------------
# §4 · D1 — Comportamental
# ---------------------------------------------------------------------------

TETO_ATRASO_MEDIO: float = 250.0
COEF_ATRASO_MEDIO: float = 12.0
TETO_PIOR_ATRASO: float = 200.0
COEF_PIOR_ATRASO: float = 5.0
COEF_PONTUALIDADE: float = 300.0
PONTUALIDADE_PLENA: float = 1.0
TETO_RENEGOCIACOES: float = 180.0
COEF_RENEGOCIACOES: float = 60.0
TETO_INADIMPLENCIA_TECNICA: float = 240.0
COEF_INADIMPLENCIA_TECNICA: float = 120.0
TETO_TENDENCIA_ATRASO: float = 120.0
COEF_TENDENCIA_ATRASO: float = 10.0
TETO_RELACIONAMENTO: float = 120.0
COEF_RELACIONAMENTO: float = 15.0
PONTOS_HISTORICO_LIMPO: float = 80.0

# ---------------------------------------------------------------------------
# §4 · D2 — Jurídico & processual
# ---------------------------------------------------------------------------

TETO_EXECUCOES_TITULO: float = 300.0
COEF_EXECUCOES_TITULO: float = 70.0
TETO_MATERIALIDADE_EXECUCAO: float = 200.0
COEF_MATERIALIDADE_EXECUCAO: float = 400.0
PONTOS_ACELERACAO_JUDICIAL: float = 100.0
MINIMO_EXECUCOES_90D_ACELERACAO: int = 2
TETO_PROTESTOS: float = 180.0
COEF_PROTESTOS: float = 45.0
PONTOS_PROTESTO_RECORRENTE: float = 80.0
MINIMO_PROTESTOS_12M_RECORRENTE: int = 3
PONTOS_PEDIDO_FALENCIA: float = 400.0
PONTOS_RJ_DISTRIBUIDA: float = 900.0
TETO_TRABALHISTAS: float = 100.0
COEF_TRABALHISTAS: float = 25.0
PONTOS_PLURALIDADE_CREDORES: float = 120.0
MINIMO_CREDORES_DISTINTOS: int = 3
PONTOS_SEM_LITIGIO: float = 60.0

# ---------------------------------------------------------------------------
# §4 · D3 — Fiscal & trabalhista
# ---------------------------------------------------------------------------

TETO_DIVIDA_ATIVA: float = 320.0
COEF_DIVIDA_ATIVA: float = 500.0
PONTOS_DIVIDA_ATIVA_CRESCENTE: float = 90.0
PONTOS_CNDT_POSITIVA: float = 200.0
PONTOS_FGTS_IRREGULAR: float = 120.0
PONTOS_PARCELAMENTO_ROMPIDO: float = 150.0
PONTOS_CERTIDOES_NEGATIVAS: float = 80.0

# ---------------------------------------------------------------------------
# §4 · D4 — Agro & climático
# ---------------------------------------------------------------------------

PONTOS_ZARC: dict[RiscoZarc, float] = {
    RiscoZarc.BAIXO: 0.0,
    RiscoZarc.MODERADO: 90.0,
    RiscoZarc.ALTO: 200.0,
    RiscoZarc.CRITICO: 320.0,
}
TETO_QUEBRA_SAFRA: float = 200.0
COEF_QUEBRA_SAFRA: float = 6.0
TETO_DESVIO_PRECIPITACAO: float = 150.0
COEF_DESVIO_PRECIPITACAO: float = 3.0
PONTOS_MONOCULTURA: float = 60.0
MINIMO_CULTURAS_DIVERSIFICACAO: int = 3
TETO_PRODUTIVIDADE_ABAIXO: float = 120.0
COEF_PRODUTIVIDADE_ABAIXO: float = 4.0
PONTOS_BARTER_SEM_LASTRO: float = 100.0
PONTOS_IRRIGACAO_OU_SEGURO: float = 100.0
#: "área irrigada relevante" — fração mínima da área total para contar como proteção.
FRACAO_MINIMA_AREA_IRRIGADA: float = 0.20
PONTOS_DIVERSIFICACAO: float = 60.0

# ---------------------------------------------------------------------------
# §4 · D5 — Cadastral & societário
# ---------------------------------------------------------------------------

PONTOS_SITUACAO_CADASTRAL: float = 400.0
#: (<limite de anos, pontos) avaliado em ordem; acima da última faixa, 0.
FAIXAS_TEMPO_ATIVIDADE: tuple[tuple[float, float], ...] = ((3.0, 200.0), (5.0, 100.0))
PONTOS_ALTERACAO_SOCIETARIA: float = 120.0
PONTOS_SAIDA_SOCIO_MAJORITARIO: float = 100.0
#: (<razão capital÷exposição, pontos) avaliado em ordem; acima da última faixa, 0.
FAIXAS_CAPITAL_VS_EXPOSICAO: tuple[tuple[float, float], ...] = ((0.5, 150.0), (1.0, 80.0))
PONTOS_CNAE_INCOMPATIVEL: float = 80.0
PONTOS_QSA_ESTAVEL: float = 80.0

# ---------------------------------------------------------------------------
# §4 · D6 — Ambiental
# ---------------------------------------------------------------------------

PONTOS_EMBARGO_IBAMA: float = 500.0
PONTOS_AUTO_INFRACAO: float = 200.0
PONTOS_CAR_AUSENTE: float = 300.0
PONTOS_CAR_IRREGULAR: float = 150.0
PONTOS_SOBREPOSICAO_APP: float = 180.0
PONTOS_CAR_REGULAR: float = 60.0
SITUACOES_CAR_IRREGULARES: tuple[SituacaoCar, ...] = (
    SituacaoCar.PENDENTE,
    SituacaoCar.IRREGULAR,
)

# ---------------------------------------------------------------------------
# §4 · D7 — Garantias & exposição
# ---------------------------------------------------------------------------

COEF_DESCOBERTO_EXTRACONCURSAL: float = 400.0
COEF_DESCOBERTO_TOTAL: float = 250.0
COBERTURA_MAXIMA_NO_CALCULO: float = 1.0
LIMIAR_UTILIZACAO_ALTA: float = 0.85
PONTOS_UTILIZACAO_ALTA: float = 120.0
LIMIAR_UTILIZACAO_CRITICA: float = 0.95
PONTOS_UTILIZACAO_CRITICA: float = 80.0
TETO_UTILIZACAO_LIMITE: float = 200.0
PONTOS_CONCENTRACAO_PATRIMONIAL: float = 150.0
MULTIPLO_PATRIMONIO_CONCENTRACAO: float = 2.0
PONTOS_VENCIMENTO_CONCENTRADO: float = 80.0
FRACAO_VENCIMENTO_CONCENTRADO: float = 0.50
PONTOS_SOBRECOLATERAL: float = 120.0
COBERTURA_MINIMA_SOBRECOLATERAL: float = 1.0

# ---------------------------------------------------------------------------
# §5 · Rating
# ---------------------------------------------------------------------------

#: (piso inclusive, rating), avaliado do mais alto para o mais baixo.
FAIXAS_RATING: tuple[tuple[float, Rating], ...] = (
    (750.0, Rating.A),
    (600.0, Rating.B),
    (400.0, Rating.C),
    (0.0, Rating.D),
)

ROTULOS_RATING: dict[Rating, str] = {
    Rating.A: "Baixo risco",
    Rating.B: "Risco moderado",
    Rating.C: "Risco elevado",
    Rating.D: "Risco crítico / Alerta de RJ",
}

#: Ordem de severidade: maior número = mais severo. Usado na composição de vetos.
SEVERIDADE_DO_RATING: dict[Rating, int] = {
    Rating.A: 0,
    Rating.B: 1,
    Rating.C: 2,
    Rating.D: 3,
}

# ---------------------------------------------------------------------------
# §6 · Probabilidade de inadimplência
# ---------------------------------------------------------------------------

PD_L: float = 0.62
PD_S0: float = 500.0
PD_K: float = 108.0

EXPOENTE_HORIZONTE_PD6: float = 0.5
EXPOENTE_HORIZONTE_PD24: float = 2.0

#: ψ — ajuste de hazard de curto prazo por tendência.
PSI_POR_TENDENCIA: dict[Tendencia, float] = {
    Tendencia.MELHORANDO: 0.85,
    Tendencia.ESTAVEL: 1.00,
    Tendencia.DETERIORANDO: 1.15,
    Tendencia.DETERIORACAO_ACELERADA: 1.30,
}

#: θ — ajuste de hazard de longo prazo por tendência.
THETA_POR_TENDENCIA: dict[Tendencia, float] = {
    Tendencia.MELHORANDO: 0.80,
    Tendencia.ESTAVEL: 0.92,
    Tendencia.DETERIORANDO: 1.10,
    Tendencia.DETERIORACAO_ACELERADA: 1.25,
}

TEXTO_METODO_PD: str = (
    "Curva logística sobre o score (L=0,62 · s0=500 · k=108), com PD de 6 e 24 meses "
    "derivadas por hazard constante ajustado pela tendência — garante PD6 < PD12 < PD24 "
    "por construção."
)

# ---------------------------------------------------------------------------
# §7 · Risco de Recuperação Judicial
# ---------------------------------------------------------------------------

PONTOS_RJ_PLURALIDADE_CREDORES: float = 20.0
TETO_RJ_ENDIVIDAMENTO: float = 25.0
COEF_RJ_ENDIVIDAMENTO: float = 50.0
#: Execuções fiscais são dívida judicializada e entram no numerador do sinal.
RJ_INCLUI_EXECUCOES_FISCAIS: bool = True
TETO_RJ_PROTESTOS: float = 12.0
COEF_RJ_PROTESTOS: float = 4.0
TETO_RJ_DIVIDA_ATIVA: float = 10.0
COEF_RJ_DIVIDA_ATIVA: float = 40.0
TETO_RJ_AGRO: float = 12.0
PONTOS_RJ_ZARC: dict[RiscoZarc, float] = {
    RiscoZarc.BAIXO: 0.0,
    RiscoZarc.MODERADO: 0.0,
    RiscoZarc.ALTO: 8.0,
    RiscoZarc.CRITICO: 12.0,
}
PONTOS_RJ_QUEBRA_SAFRA: float = 8.0
LIMIAR_RJ_QUEBRA_SAFRA_PCT: float = 25.0
PONTOS_RJ_PEDIDO_FALENCIA: float = 15.0
PONTOS_RJ_PARCELAMENTO_ROMPIDO: float = 6.0
PONTOS_RJ_COVENANT_ROMPIDO: float = 8.0
PONTOS_RJ_ALTERACAO_ADMIN_EM_CRISE: float = 5.0
REDUTOR_RJ_PATRIMONIO_FORTE: float = -15.0
MULTIPLO_PATRIMONIO_REDUTOR_RJ: float = 3.0

RJ_INDEX_MINIMO: float = 0.0
RJ_INDEX_MAXIMO: float = 100.0

RJ_L: float = 0.45
RJ_CENTRO: float = 55.0
RJ_ESCALA: float = 9.0

#: Quando os fatos não informam o tipo de pessoa, o motor assume PJ — que é o
#: caso da maioria da carteira e o cenário conservador (PJ é sempre elegível a RJ).
TIPO_PESSOA_PADRAO: TipoPessoa = TipoPessoa.PJ

#: Lei 14.112/2020 — produtor rural PF precisa de ≥2 anos comprovados.
ANOS_MINIMOS_ATIVIDADE_RJ_PF: float = 2.0
FATOR_ATENUACAO_RJ_INELEGIVEL: float = 0.15
PROBABILIDADE_RJ_EVENTO_OCORRIDO: float = 1.0

MOTIVO_INELEGIBILIDADE_RJ: str = (
    "Não elegível a RJ — produtor rural PF sem 2 anos de atividade comprovada "
    "(Lei 14.112/2020). Risco migra para execução individual."
)

ROTULOS_SINAIS_RJ: dict[str, str] = {
    "pluralidade_credores": "Pluralidade de credores executando (≥3 credores distintos)",
    "endividamento_judicializado": "Endividamento judicializado ÷ exposição total",
    "protestos_credores_distintos": "Protestos de credores distintos em 180 dias",
    "divida_ativa_sobre_faturamento": "Dívida ativa PGFN ÷ faturamento estimado",
    "estresse_agroclimatico": "Risco ZARC alto/crítico ou quebra de safra acima do limiar",
    "pedido_falencia": "Pedido de falência distribuído (RJ defensiva é resposta comum)",
    "parcelamento_rompido": "Parcelamento fiscal rompido",
    "covenant_rompido": "Covenant rompido (inadimplência técnica)",
    "alteracao_admin_em_crise": "Alteração de administrador em período de crise",
    "patrimonio_forte": "Patrimônio líquido ≥ 3× exposição e zero execuções",
}

# ---------------------------------------------------------------------------
# §8 · Gatilhos de veto
# ---------------------------------------------------------------------------

LIMIAR_EXEC_FISCAL_SOBRE_EXPOSICAO: float = 0.50
LIMIAR_CNDT_SOBRE_PATRIMONIO: float = 0.15


@dataclass(frozen=True)
class RegraDeVeto:
    id: str
    rotulo: str
    efeito: EfeitoVeto
    justificativa: str


REGRAS_DE_VETO: tuple[RegraDeVeto, ...] = (
    RegraDeVeto(
        id="VETO_RJ",
        rotulo="Recuperação judicial ajuizada ou deferida",
        efeito=EfeitoVeto.FORCA_D,
        justificativa=(
            "Crédito anterior ao pedido entra no plano com deságio severo. "
            "Stay Period suspende execuções."
        ),
    ),
    RegraDeVeto(
        id="VETO_FALENCIA",
        rotulo="Pedido de falência distribuído",
        efeito=EfeitoVeto.FORCA_D,
        justificativa="Risco iminente de liquidação do devedor.",
    ),
    RegraDeVeto(
        id="VETO_EMBARGO_GARANTIA",
        rotulo="Embargo do IBAMA sobre imóvel oferecido em garantia",
        efeito=EfeitoVeto.FORCA_D,
        justificativa=(
            "Garantia juridicamente comprometida: bem embargado tem excussão inviabilizada."
        ),
    ),
    RegraDeVeto(
        id="VETO_CADASTRO_INAPTO",
        rotulo="Situação cadastral inapta, suspensa ou baixada na RFB",
        efeito=EfeitoVeto.FORCA_D,
        justificativa="Impedimento cadastral para operar a prazo.",
    ),
    RegraDeVeto(
        id="VETO_LISTA_SUJA",
        rotulo="Inclusão no Cadastro de Empregadores (trabalho análogo ao escravo)",
        efeito=EfeitoVeto.FORCA_D,
        justificativa="Risco reputacional e de cadeia; vedação de política de crédito.",
    ),
    RegraDeVeto(
        id="VETO_FRAUDE",
        rotulo="Indício de fraude ou irregularidade grave confirmada",
        efeito=EfeitoVeto.FORCA_D,
        justificativa="Quebra de confiança; caso para análise especializada.",
    ),
    RegraDeVeto(
        id="TETO_EXEC_FISCAL",
        rotulo="Execuções fiscais acima de 50% da exposição total",
        efeito=EfeitoVeto.TETO_C,
        justificativa="Concorrência de crédito com preferência fiscal.",
    ),
    RegraDeVeto(
        id="TETO_CNDT",
        rotulo="CNDT positiva com débito acima de 15% do patrimônio declarado",
        efeito=EfeitoVeto.TETO_C,
        justificativa="Passivo trabalhista com preferência sobre quirografários.",
    ),
)

RATING_FORCADO_POR_EFEITO: dict[EfeitoVeto, Rating] = {
    EfeitoVeto.FORCA_D: Rating.D,
    EfeitoVeto.TETO_C: Rating.C,
}

# ---------------------------------------------------------------------------
# §9 · Stay Period
# ---------------------------------------------------------------------------

STAY_PERIOD_DIAS: int = 180

BLOQUEIOS_STAY_PERIOD: tuple[str, ...] = (
    "Executar judicialmente o crédito concursal",
    "Excutir garantias concursais (penhor de safra, penhor de máquina, hipoteca)",
    "Protestar títulos vencidos anteriores ao pedido",
    "Rescindir o contrato de fornecimento apenas em razão da RJ",
)

PERMITIDO_STAY_PERIOD: tuple[str, ...] = (
    "Excutir garantia com alienação fiduciária — crédito extraconcursal, fora dos efeitos da RJ",
    "Cobrar créditos constituídos após a distribuição do pedido (extraconcursais)",
    "Habilitar o crédito concursal e acompanhar o plano na assembleia de credores",
    "Exigir pagamento à vista em novos fornecimentos",
)

# ---------------------------------------------------------------------------
# §10 · Exposição, garantias e coberturas
# ---------------------------------------------------------------------------

JANELA_A_VENCER_DIAS: int = 90
HAIRCUT_POR_TIPO_GARANTIA_PADRAO: dict[TipoGarantia, float] = dict(HAIRCUT_POR_TIPO_GARANTIA)
NATUREZA_POR_TIPO_GARANTIA_PADRAO: dict = dict(NATUREZA_POR_TIPO_GARANTIA)

# ---------------------------------------------------------------------------
# §11 · Tendência
# ---------------------------------------------------------------------------

JANELA_TENDENCIA_DIAS: int = 90
LIMIAR_MELHORANDO: float = 25.0
LIMIAR_DETERIORANDO: float = -25.0
LIMIAR_DETERIORACAO_ACELERADA: float = -80.0

#: Fatores cuja materialização é, por definição, um evento dos últimos 90 dias.
#: Na ausência de histórico, a variação de 90 dias é estimada pela soma dos
#: impactos destes fatores — é o que a spec descreve como deterioração recente.
FATORES_DE_JANELA_90D: tuple[str, ...] = (
    "tendencia_atraso",
    "aceleracao_judicial",
    "divida_ativa_crescente",
    "inadimplencia_tecnica",
    "rj_distribuida",
    "pedido_falencia",
)

# ---------------------------------------------------------------------------
# §12 · Recomendação operacional
# ---------------------------------------------------------------------------

ROTULOS_RECOMENDACAO: dict[CodigoRecomendacao, str] = {
    CodigoRecomendacao.APROVAR: "Aprovar",
    CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO: (
        "Aprovar com monitoramento intensivo"
    ),
    CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE: "Aprovar com revisão de limite",
    CodigoRecomendacao.APROVAR_COM_RESTRICOES: "Aprovar com restrições",
    CodigoRecomendacao.SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: (
        "Suspender nova exposição a prazo"
    ),
    CodigoRecomendacao.SUSPENDER_EXPOSICAO: "Suspender exposição",
}

PRAZO_REAVALIACAO_POR_RATING: dict[Rating, int] = {
    Rating.A: 180,
    Rating.B: 90,
    Rating.C: 30,
    Rating.D: 7,
}

#: Percentual de redução de limite por rating e tendência (§12).
REDUCAO_LIMITE_POR_RATING_E_TENDENCIA: dict[Rating, dict[Tendencia, float]] = {
    Rating.A: {
        Tendencia.MELHORANDO: 0.0,
        Tendencia.ESTAVEL: 0.0,
        Tendencia.DETERIORANDO: 0.10,
        Tendencia.DETERIORACAO_ACELERADA: 0.15,
    },
    Rating.B: {
        Tendencia.MELHORANDO: 0.0,
        Tendencia.ESTAVEL: 0.10,
        Tendencia.DETERIORANDO: 0.20,
        Tendencia.DETERIORACAO_ACELERADA: 0.30,
    },
    Rating.C: {
        Tendencia.MELHORANDO: 0.25,
        Tendencia.ESTAVEL: 0.30,
        Tendencia.DETERIORANDO: 0.40,
        Tendencia.DETERIORACAO_ACELERADA: 0.50,
    },
    Rating.D: {
        Tendencia.MELHORANDO: 0.60,
        Tendencia.ESTAVEL: 0.70,
        Tendencia.DETERIORANDO: 0.85,
        Tendencia.DETERIORACAO_ACELERADA: 1.00,
    },
}

#: "tendência deteriorando" da §12 abrange também a deterioração acelerada.
TENDENCIAS_DE_DETERIORACAO: tuple[Tendencia, ...] = (
    Tendencia.DETERIORANDO,
    Tendencia.DETERIORACAO_ACELERADA,
)

#: Rótulos humanos dos tipos de garantia, para o texto das ações.
ROTULOS_TIPO_GARANTIA: dict[TipoGarantia, str] = {
    TipoGarantia.ALIENACAO_FIDUCIARIA: "alienação fiduciária",
    TipoGarantia.CPR_FINANCEIRA: "CPR financeira",
    TipoGarantia.CPR_FISICA: "CPR física",
    TipoGarantia.PENHOR_SAFRA: "penhor de safra",
    TipoGarantia.PENHOR_MAQUINA: "penhor de máquina",
    TipoGarantia.HIPOTECA: "hipoteca",
    TipoGarantia.AVAL_FIANCA: "aval ou fiança",
}

LIMIAR_EXPOSICAO_RJ_RATING_B: float = 0.40
LIMIAR_UTILIZACAO_REVISAO_DE_LIMITE: float = 0.90
FATOR_REDUCAO_DE_PRAZO: float = 0.50
PRAZO_MINIMO_DIAS: int = 30
VALOR_MINIMO_GARANTIA_CONCURSAL_RELEVANTE: float = 1.0
PRIORIDADE_ALTA: int = 1
PRIORIDADE_MEDIA: int = 2
PRIORIDADE_BAIXA: int = 3

# ---------------------------------------------------------------------------
# §13 · Red flags
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegraDeRedFlag:
    """Derivação automática de red flag a partir de um fator já calculado."""

    fator_id: str
    severidade: Severidade
    titulo: str
    #: Emite só quando o fator atingiu ao menos estes pontos — é como as
    #: condições qualitativas da §13 ("ZARC alto", "quebra > 20%") viram regra.
    pontos_minimos: float = 0.0


REGRAS_DE_RED_FLAG: tuple[RegraDeRedFlag, ...] = (
    RegraDeRedFlag("rj_distribuida", Severidade.CRITICA, "Recuperação judicial em curso"),
    RegraDeRedFlag("pedido_falencia", Severidade.CRITICA, "Pedido de falência distribuído"),
    RegraDeRedFlag(
        "aceleracao_judicial", Severidade.ALTA, "Aceleração judicial: ≥2 execuções em 90 dias"
    ),
    RegraDeRedFlag("protesto_recorrente", Severidade.ALTA, "Protestos recorrentes em 12 meses"),
    RegraDeRedFlag("divida_ativa_crescente", Severidade.ALTA, "Dívida ativa em crescimento"),
    RegraDeRedFlag(
        "inadimplencia_tecnica",
        Severidade.ALTA,
        "Inadimplência técnica: covenant contratual rompido",
    ),
    RegraDeRedFlag("cndt_positiva", Severidade.ALTA, "CNDT positiva"),
    RegraDeRedFlag("pluralidade_credores", Severidade.ALTA, "Pluralidade de credores executando"),
    RegraDeRedFlag("alteracao_societaria", Severidade.MEDIA, "Alteração societária relevante"),
    RegraDeRedFlag(
        "saida_socio_majoritario", Severidade.MEDIA, "Saída de sócio majoritário em 12 meses"
    ),
    RegraDeRedFlag(
        "zarc_risco",
        Severidade.MEDIA,
        "Risco ZARC elevado para alto ou crítico",
        pontos_minimos=PONTOS_ZARC[RiscoZarc.ALTO],
    ),
    RegraDeRedFlag(
        "quebra_safra_regional",
        Severidade.MEDIA,
        "Quebra de safra regional acima de 20%",
        #: 20% × COEF_QUEBRA_SAFRA — a condição qualitativa expressa em pontos.
        pontos_minimos=20.0 * COEF_QUEBRA_SAFRA,
    ),
    RegraDeRedFlag("car_irregular", Severidade.MEDIA, "CAR em situação irregular ou pendente"),
    RegraDeRedFlag("car_ausente", Severidade.MEDIA, "Imóvel sem CAR"),
    RegraDeRedFlag(
        "materialidade_execucao", Severidade.MEDIA, "Endividamento judicializado crescente"
    ),
    RegraDeRedFlag("cnae_incompativel", Severidade.BAIXA, "CNAE incompatível com a atividade"),
    RegraDeRedFlag(
        "desvio_precipitacao", Severidade.BAIXA, "Variação climática relevante na região"
    ),
)

@dataclass(frozen=True)
class RegraDeRedFlagDeVeto:
    """Red flag que nasce de um gatilho de veto, não de um fator pontuado."""

    veto_id: str
    severidade: Severidade
    titulo: str
    fonte: FonteId
    #: Fator cujo `impactoGlobal` alimenta `impactoEmPontos`, quando existe.
    fator_relacionado: str | None = None


REGRAS_DE_RED_FLAG_POR_VETO: tuple[RegraDeRedFlagDeVeto, ...] = (
    RegraDeRedFlagDeVeto(
        veto_id="VETO_EMBARGO_GARANTIA",
        severidade=Severidade.CRITICA,
        titulo="Embargo do IBAMA sobre bem dado em garantia",
        fonte=FonteId.IBAMA,
        fator_relacionado="embargo_ibama",
    ),
    RegraDeRedFlagDeVeto(
        veto_id="VETO_LISTA_SUJA",
        severidade=Severidade.CRITICA,
        titulo="Inclusão no Cadastro de Empregadores (trabalho análogo ao escravo)",
        fonte=FonteId.TST_CNDT,
    ),
    RegraDeRedFlagDeVeto(
        veto_id="VETO_FRAUDE",
        severidade=Severidade.CRITICA,
        titulo="Fraude ou irregularidade grave confirmada",
        fonte=FonteId.INTERNO_KRILLTECH,
    ),
    RegraDeRedFlagDeVeto(
        veto_id="VETO_CADASTRO_INAPTO",
        severidade=Severidade.CRITICA,
        titulo="Situação cadastral impeditiva na Receita Federal",
        fonte=FonteId.RECEITA_FEDERAL,
        fator_relacionado="situacao_cadastral",
    ),
)

#: Ordem de exibição das red flags: da mais severa para a menos severa.
ORDEM_DE_SEVERIDADE: dict[Severidade, int] = {
    Severidade.CRITICA: 0,
    Severidade.ALTA: 1,
    Severidade.MEDIA: 2,
    Severidade.BAIXA: 3,
}

#: Fonte das red flags que não nascem de um fator com fonte própria.
FONTE_RED_FLAG_DERIVADA: FonteId = FonteId.INTERNO_KRILLTECH

#: Prefixo dos ids de red flag derivada.
PREFIXO_ID_RED_FLAG: str = "rf"

#: Queda de score superior a 80 pontos em 90 dias (§13, severidade ALTA).
TITULO_RED_FLAG_QUEDA_DE_SCORE: str = "Queda acentuada de score nos últimos 90 dias"
TENDENCIAS_DE_QUEDA_ACENTUADA: tuple[Tendencia, ...] = (Tendencia.DETERIORACAO_ACELERADA,)

#: Certidão vencida (§13, severidade MÉDIA) — não há fator pontuado correspondente.
TITULO_RED_FLAG_CERTIDAO_VENCIDA: str = "Certidões fiscais não integralmente negativas"

# ---------------------------------------------------------------------------
# ScoringConfig — tudo acima, sobrescrevível
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoringConfig:
    """Parâmetros do motor. Padrões = constantes deste módulo."""

    # §2
    pesos_dimensoes: dict = field(default_factory=lambda: dict(PESOS_DIMENSOES))
    rotulos_dimensoes: dict = field(default_factory=lambda: dict(ROTULOS_DIMENSOES))
    fonte_padrao_dimensao: dict = field(default_factory=lambda: dict(FONTE_PADRAO_DIMENSAO))
    fonte_por_fator: dict = field(default_factory=lambda: dict(FONTE_POR_FATOR))

    # §3
    score_base: float = SCORE_BASE
    score_minimo: float = SCORE_MINIMO
    score_maximo: float = SCORE_MAXIMO
    sinal_risco: float = SINAL_RISCO
    sinal_protecao: float = SINAL_PROTECAO
    casas_score: int = CASAS_SCORE
    casas_pontos: int = CASAS_PONTOS
    casas_probabilidade: int = CASAS_PROBABILIDADE
    casas_moeda: int = CASAS_MOEDA
    casas_fracao: int = CASAS_FRACAO
    tolerancia_fechamento: float = TOLERANCIA_FECHAMENTO

    # §4 D1
    dias_por_ano: float = DIAS_POR_ANO
    tipos_cpr: tuple = TIPOS_CPR
    teto_atraso_medio: float = TETO_ATRASO_MEDIO
    coef_atraso_medio: float = COEF_ATRASO_MEDIO
    teto_pior_atraso: float = TETO_PIOR_ATRASO
    coef_pior_atraso: float = COEF_PIOR_ATRASO
    coef_pontualidade: float = COEF_PONTUALIDADE
    pontualidade_plena: float = PONTUALIDADE_PLENA
    teto_renegociacoes: float = TETO_RENEGOCIACOES
    coef_renegociacoes: float = COEF_RENEGOCIACOES
    teto_inadimplencia_tecnica: float = TETO_INADIMPLENCIA_TECNICA
    coef_inadimplencia_tecnica: float = COEF_INADIMPLENCIA_TECNICA
    teto_tendencia_atraso: float = TETO_TENDENCIA_ATRASO
    coef_tendencia_atraso: float = COEF_TENDENCIA_ATRASO
    teto_relacionamento: float = TETO_RELACIONAMENTO
    coef_relacionamento: float = COEF_RELACIONAMENTO
    pontos_historico_limpo: float = PONTOS_HISTORICO_LIMPO

    # §4 D2
    teto_execucoes_titulo: float = TETO_EXECUCOES_TITULO
    coef_execucoes_titulo: float = COEF_EXECUCOES_TITULO
    teto_materialidade_execucao: float = TETO_MATERIALIDADE_EXECUCAO
    coef_materialidade_execucao: float = COEF_MATERIALIDADE_EXECUCAO
    pontos_aceleracao_judicial: float = PONTOS_ACELERACAO_JUDICIAL
    minimo_execucoes_90d_aceleracao: int = MINIMO_EXECUCOES_90D_ACELERACAO
    teto_protestos: float = TETO_PROTESTOS
    coef_protestos: float = COEF_PROTESTOS
    pontos_protesto_recorrente: float = PONTOS_PROTESTO_RECORRENTE
    minimo_protestos_12m_recorrente: int = MINIMO_PROTESTOS_12M_RECORRENTE
    pontos_pedido_falencia: float = PONTOS_PEDIDO_FALENCIA
    pontos_rj_distribuida: float = PONTOS_RJ_DISTRIBUIDA
    teto_trabalhistas: float = TETO_TRABALHISTAS
    coef_trabalhistas: float = COEF_TRABALHISTAS
    pontos_pluralidade_credores: float = PONTOS_PLURALIDADE_CREDORES
    minimo_credores_distintos: int = MINIMO_CREDORES_DISTINTOS
    pontos_sem_litigio: float = PONTOS_SEM_LITIGIO

    # §4 D3
    teto_divida_ativa: float = TETO_DIVIDA_ATIVA
    coef_divida_ativa: float = COEF_DIVIDA_ATIVA
    pontos_divida_ativa_crescente: float = PONTOS_DIVIDA_ATIVA_CRESCENTE
    pontos_cndt_positiva: float = PONTOS_CNDT_POSITIVA
    pontos_fgts_irregular: float = PONTOS_FGTS_IRREGULAR
    pontos_parcelamento_rompido: float = PONTOS_PARCELAMENTO_ROMPIDO
    pontos_certidoes_negativas: float = PONTOS_CERTIDOES_NEGATIVAS

    # §4 D4
    pontos_zarc: dict = field(default_factory=lambda: dict(PONTOS_ZARC))
    teto_quebra_safra: float = TETO_QUEBRA_SAFRA
    coef_quebra_safra: float = COEF_QUEBRA_SAFRA
    teto_desvio_precipitacao: float = TETO_DESVIO_PRECIPITACAO
    coef_desvio_precipitacao: float = COEF_DESVIO_PRECIPITACAO
    pontos_monocultura: float = PONTOS_MONOCULTURA
    minimo_culturas_diversificacao: int = MINIMO_CULTURAS_DIVERSIFICACAO
    teto_produtividade_abaixo: float = TETO_PRODUTIVIDADE_ABAIXO
    coef_produtividade_abaixo: float = COEF_PRODUTIVIDADE_ABAIXO
    pontos_barter_sem_lastro: float = PONTOS_BARTER_SEM_LASTRO
    pontos_irrigacao_ou_seguro: float = PONTOS_IRRIGACAO_OU_SEGURO
    fracao_minima_area_irrigada: float = FRACAO_MINIMA_AREA_IRRIGADA
    pontos_diversificacao: float = PONTOS_DIVERSIFICACAO

    # §4 D5
    pontos_situacao_cadastral: float = PONTOS_SITUACAO_CADASTRAL
    faixas_tempo_atividade: tuple = FAIXAS_TEMPO_ATIVIDADE
    pontos_alteracao_societaria: float = PONTOS_ALTERACAO_SOCIETARIA
    pontos_saida_socio_majoritario: float = PONTOS_SAIDA_SOCIO_MAJORITARIO
    faixas_capital_vs_exposicao: tuple = FAIXAS_CAPITAL_VS_EXPOSICAO
    pontos_cnae_incompativel: float = PONTOS_CNAE_INCOMPATIVEL
    pontos_qsa_estavel: float = PONTOS_QSA_ESTAVEL

    # §4 D6
    pontos_embargo_ibama: float = PONTOS_EMBARGO_IBAMA
    pontos_auto_infracao: float = PONTOS_AUTO_INFRACAO
    pontos_car_ausente: float = PONTOS_CAR_AUSENTE
    pontos_car_irregular: float = PONTOS_CAR_IRREGULAR
    pontos_sobreposicao_app: float = PONTOS_SOBREPOSICAO_APP
    pontos_car_regular: float = PONTOS_CAR_REGULAR
    situacoes_car_irregulares: tuple = SITUACOES_CAR_IRREGULARES

    # §4 D7
    coef_descoberto_extraconcursal: float = COEF_DESCOBERTO_EXTRACONCURSAL
    coef_descoberto_total: float = COEF_DESCOBERTO_TOTAL
    cobertura_maxima_no_calculo: float = COBERTURA_MAXIMA_NO_CALCULO
    limiar_utilizacao_alta: float = LIMIAR_UTILIZACAO_ALTA
    pontos_utilizacao_alta: float = PONTOS_UTILIZACAO_ALTA
    limiar_utilizacao_critica: float = LIMIAR_UTILIZACAO_CRITICA
    pontos_utilizacao_critica: float = PONTOS_UTILIZACAO_CRITICA
    teto_utilizacao_limite: float = TETO_UTILIZACAO_LIMITE
    pontos_concentracao_patrimonial: float = PONTOS_CONCENTRACAO_PATRIMONIAL
    multiplo_patrimonio_concentracao: float = MULTIPLO_PATRIMONIO_CONCENTRACAO
    pontos_vencimento_concentrado: float = PONTOS_VENCIMENTO_CONCENTRADO
    fracao_vencimento_concentrado: float = FRACAO_VENCIMENTO_CONCENTRADO
    pontos_sobrecolateral: float = PONTOS_SOBRECOLATERAL
    cobertura_minima_sobrecolateral: float = COBERTURA_MINIMA_SOBRECOLATERAL

    # §5
    faixas_rating: tuple = FAIXAS_RATING
    rotulos_rating: dict = field(default_factory=lambda: dict(ROTULOS_RATING))
    severidade_do_rating: dict = field(default_factory=lambda: dict(SEVERIDADE_DO_RATING))

    # §6
    pd_l: float = PD_L
    pd_s0: float = PD_S0
    pd_k: float = PD_K
    expoente_horizonte_pd6: float = EXPOENTE_HORIZONTE_PD6
    expoente_horizonte_pd24: float = EXPOENTE_HORIZONTE_PD24
    psi_por_tendencia: dict = field(default_factory=lambda: dict(PSI_POR_TENDENCIA))
    theta_por_tendencia: dict = field(default_factory=lambda: dict(THETA_POR_TENDENCIA))
    texto_metodo_pd: str = TEXTO_METODO_PD

    # §7
    pontos_rj_pluralidade_credores: float = PONTOS_RJ_PLURALIDADE_CREDORES
    teto_rj_endividamento: float = TETO_RJ_ENDIVIDAMENTO
    coef_rj_endividamento: float = COEF_RJ_ENDIVIDAMENTO
    rj_inclui_execucoes_fiscais: bool = RJ_INCLUI_EXECUCOES_FISCAIS
    teto_rj_protestos: float = TETO_RJ_PROTESTOS
    coef_rj_protestos: float = COEF_RJ_PROTESTOS
    teto_rj_divida_ativa: float = TETO_RJ_DIVIDA_ATIVA
    coef_rj_divida_ativa: float = COEF_RJ_DIVIDA_ATIVA
    teto_rj_agro: float = TETO_RJ_AGRO
    pontos_rj_zarc: dict = field(default_factory=lambda: dict(PONTOS_RJ_ZARC))
    pontos_rj_quebra_safra: float = PONTOS_RJ_QUEBRA_SAFRA
    limiar_rj_quebra_safra_pct: float = LIMIAR_RJ_QUEBRA_SAFRA_PCT
    pontos_rj_pedido_falencia: float = PONTOS_RJ_PEDIDO_FALENCIA
    pontos_rj_parcelamento_rompido: float = PONTOS_RJ_PARCELAMENTO_ROMPIDO
    pontos_rj_covenant_rompido: float = PONTOS_RJ_COVENANT_ROMPIDO
    pontos_rj_alteracao_admin_em_crise: float = PONTOS_RJ_ALTERACAO_ADMIN_EM_CRISE
    redutor_rj_patrimonio_forte: float = REDUTOR_RJ_PATRIMONIO_FORTE
    multiplo_patrimonio_redutor_rj: float = MULTIPLO_PATRIMONIO_REDUTOR_RJ
    rj_index_minimo: float = RJ_INDEX_MINIMO
    rj_index_maximo: float = RJ_INDEX_MAXIMO
    rj_l: float = RJ_L
    rj_centro: float = RJ_CENTRO
    rj_escala: float = RJ_ESCALA
    tipo_pessoa_padrao: TipoPessoa = TIPO_PESSOA_PADRAO
    anos_minimos_atividade_rj_pf: float = ANOS_MINIMOS_ATIVIDADE_RJ_PF
    fator_atenuacao_rj_inelegivel: float = FATOR_ATENUACAO_RJ_INELEGIVEL
    probabilidade_rj_evento_ocorrido: float = PROBABILIDADE_RJ_EVENTO_OCORRIDO
    motivo_inelegibilidade_rj: str = MOTIVO_INELEGIBILIDADE_RJ
    rotulos_sinais_rj: dict = field(default_factory=lambda: dict(ROTULOS_SINAIS_RJ))

    # §8
    limiar_exec_fiscal_sobre_exposicao: float = LIMIAR_EXEC_FISCAL_SOBRE_EXPOSICAO
    limiar_cndt_sobre_patrimonio: float = LIMIAR_CNDT_SOBRE_PATRIMONIO
    regras_de_veto: tuple = REGRAS_DE_VETO
    rating_forcado_por_efeito: dict = field(
        default_factory=lambda: dict(RATING_FORCADO_POR_EFEITO)
    )

    # §9
    stay_period_dias: int = STAY_PERIOD_DIAS
    bloqueios_stay_period: tuple = BLOQUEIOS_STAY_PERIOD
    permitido_stay_period: tuple = PERMITIDO_STAY_PERIOD

    # §10
    janela_a_vencer_dias: int = JANELA_A_VENCER_DIAS
    haircut_por_tipo_garantia: dict = field(
        default_factory=lambda: dict(HAIRCUT_POR_TIPO_GARANTIA_PADRAO)
    )
    natureza_por_tipo_garantia: dict = field(
        default_factory=lambda: dict(NATUREZA_POR_TIPO_GARANTIA_PADRAO)
    )

    # §11
    janela_tendencia_dias: int = JANELA_TENDENCIA_DIAS
    limiar_melhorando: float = LIMIAR_MELHORANDO
    limiar_deteriorando: float = LIMIAR_DETERIORANDO
    limiar_deterioracao_acelerada: float = LIMIAR_DETERIORACAO_ACELERADA
    fatores_de_janela_90d: tuple = FATORES_DE_JANELA_90D

    # §12
    rotulos_recomendacao: dict = field(default_factory=lambda: dict(ROTULOS_RECOMENDACAO))
    prazo_reavaliacao_por_rating: dict = field(
        default_factory=lambda: dict(PRAZO_REAVALIACAO_POR_RATING)
    )
    reducao_limite_por_rating_e_tendencia: dict = field(
        default_factory=lambda: {
            rating: dict(tabela)
            for rating, tabela in REDUCAO_LIMITE_POR_RATING_E_TENDENCIA.items()
        }
    )
    tendencias_de_deterioracao: tuple = TENDENCIAS_DE_DETERIORACAO
    rotulos_tipo_garantia: dict = field(
        default_factory=lambda: dict(ROTULOS_TIPO_GARANTIA)
    )
    limiar_exposicao_rj_rating_b: float = LIMIAR_EXPOSICAO_RJ_RATING_B
    limiar_utilizacao_revisao_de_limite: float = LIMIAR_UTILIZACAO_REVISAO_DE_LIMITE
    fator_reducao_de_prazo: float = FATOR_REDUCAO_DE_PRAZO
    prazo_minimo_dias: int = PRAZO_MINIMO_DIAS
    valor_minimo_garantia_concursal_relevante: float = (
        VALOR_MINIMO_GARANTIA_CONCURSAL_RELEVANTE
    )
    prioridade_alta: int = PRIORIDADE_ALTA
    prioridade_media: int = PRIORIDADE_MEDIA
    prioridade_baixa: int = PRIORIDADE_BAIXA

    # §13
    regras_de_red_flag: tuple = REGRAS_DE_RED_FLAG
    regras_de_red_flag_por_veto: tuple = REGRAS_DE_RED_FLAG_POR_VETO
    ordem_de_severidade: dict = field(default_factory=lambda: dict(ORDEM_DE_SEVERIDADE))
    fonte_red_flag_derivada: FonteId = FONTE_RED_FLAG_DERIVADA
    prefixo_id_red_flag: str = PREFIXO_ID_RED_FLAG
    titulo_red_flag_queda_de_score: str = TITULO_RED_FLAG_QUEDA_DE_SCORE
    tendencias_de_queda_acentuada: tuple = TENDENCIAS_DE_QUEDA_ACENTUADA
    titulo_red_flag_certidao_vencida: str = TITULO_RED_FLAG_CERTIDAO_VENCIDA


#: Instância padrão, usada quando `calcular_risco` recebe `config=None`.
CONFIG_PADRAO = ScoringConfig()


def resolver_config(config: ScoringConfig | None) -> ScoringConfig:
    """Normaliza o parâmetro opcional de configuração."""
    return config if config is not None else CONFIG_PADRAO
