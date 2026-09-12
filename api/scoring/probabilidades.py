"""PD 6/12/24 (§6) e risco de recuperação judicial (§7).

Os dois eixos são **independentes** e nunca compartilham escala: inadimplência
é um evento bilateral com a Krill Tech; RJ é insolvência coletiva, dirigida por
pluralidade de credores. Ver `00-decisoes.md` D7 e o briefing §5.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from models.avaliacao import ProbabilidadeDeDefault, RiscoRJ, SinalRJ
from models.enums import TipoPessoa, Tendencia
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .exposicao import ResumoDeExposicao
from .util import NEUTRO, arredondar, clamp, limitar, razao_segura

__all__ = [
    "pd12_do_score",
    "calcular_pd_a_partir_de_pd12",
    "calcular_pd",
    "Elegibilidade",
    "elegibilidade_para_rj",
    "calcular_rj_index",
    "probabilidade_de_rj",
    "calcular_risco_rj",
]

#: Complemento de uma probabilidade: 1 − p.
_TOTAL: float = 1.0


def pd12_do_score(score: float, config: ScoringConfig | None = None) -> float:
    """`PD12(score) = L / (1 + exp((score − s0) / k))` — §6."""
    cfg = resolver_config(config)
    return cfg.pd_l / (_TOTAL + exp((score - cfg.pd_s0) / cfg.pd_k))


def calcular_pd_a_partir_de_pd12(
    pd12: float,
    tendencia: Tendencia,
    config: ScoringConfig | None = None,
) -> ProbabilidadeDeDefault:
    """PD 6/24 por hazard constante ajustado pela tendência, a partir de um PD12 já dado — §6.

    `PD6 < PD12 < PD24` vale por construção: o expoente de 6 meses é sempre
    menor que 1 e o de 24 meses sempre maior que 1.

    Separado de `calcular_pd` para que o PD12 possa vir de **qualquer** fonte —
    da sigmoide sobre o score (`pd12_do_score`, o caso geral do motor) ou do
    modelo preditivo de `scoring.modelo_pd` (a base real de CNPJs, Tarefa 1). A
    derivação de PD6/PD24 por hazard é a mesma nos dois casos.
    """
    cfg = resolver_config(config)
    sobrevivencia = _TOTAL - pd12
    psi = cfg.psi_por_tendencia[tendencia]
    theta = cfg.theta_por_tendencia[tendencia]

    pd6 = _TOTAL - sobrevivencia ** (cfg.expoente_horizonte_pd6 * psi)
    pd24 = _TOTAL - sobrevivencia ** (cfg.expoente_horizonte_pd24 * theta)

    return ProbabilidadeDeDefault(
        pd6m=arredondar(pd6, cfg.casas_probabilidade),
        pd12m=arredondar(pd12, cfg.casas_probabilidade),
        pd24m=arredondar(pd24, cfg.casas_probabilidade),
        metodo=cfg.texto_metodo_pd,
    )


def calcular_pd(
    score: float,
    tendencia: Tendencia,
    config: ScoringConfig | None = None,
) -> ProbabilidadeDeDefault:
    """PD 6/12/24 por hazard constante ajustado pela tendência — §6.

    Caso geral do motor: deriva o PD12 do score via sigmoide (`pd12_do_score`).
    Quando há um modelo de PD dedicado (Tarefa 1, base real de CNPJs), quem
    chama `calcular_risco` passa `modelo_pd=...` e esta função **não** é usada
    — ver `calcular_pd_a_partir_de_pd12`.
    """
    cfg = resolver_config(config)
    pd12 = pd12_do_score(score, cfg)
    return calcular_pd_a_partir_de_pd12(pd12, tendencia, cfg)


# ---------------------------------------------------------------------------
# §7 · Risco de RJ
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Elegibilidade:
    elegivel: bool
    motivo: str | None


def elegibilidade_para_rj(
    fatos: FatosDoCliente, config: ScoringConfig | None = None
) -> Elegibilidade:
    """Lei 14.112/2020 — PJ sempre; PF rural só com atividade comprovada."""
    cfg = resolver_config(config)
    cadastral = fatos.cadastral
    tipo_pessoa = cadastral.tipo_pessoa or cfg.tipo_pessoa_padrao

    if tipo_pessoa is TipoPessoa.PJ:
        return Elegibilidade(elegivel=True, motivo=None)

    comprova_atividade = (
        cadastral.anos_atividade_comprovada >= cfg.anos_minimos_atividade_rj_pf
        and (cadastral.possui_livro_caixa_digital or cadastral.possui_inscricao_estadual)
    )
    if comprova_atividade:
        return Elegibilidade(elegivel=True, motivo=None)
    return Elegibilidade(elegivel=False, motivo=cfg.motivo_inelegibilidade_rj)


def _sinal(chave: str, pontos: float, cfg: ScoringConfig) -> SinalRJ | None:
    if pontos == NEUTRO:
        return None
    return SinalRJ(
        rotulo=cfg.rotulos_sinais_rj[chave], pontos=arredondar(pontos, cfg.casas_pontos)
    )


def calcular_rj_index(
    fatos: FatosDoCliente,
    resumo: ResumoDeExposicao,
    config: ScoringConfig | None = None,
) -> tuple[float, list[SinalRJ]]:
    """Índice de propensão a RJ (0–100) e os sinais que o compõem — §7."""
    cfg = resolver_config(config)
    juridico = fatos.juridico
    fiscal = fatos.fiscal
    agro = fatos.agro
    cadastral = fatos.cadastral
    exposicao_total = resumo.calculada.exposicao_total

    endividamento_judicializado = juridico.valor_total_em_execucao
    if cfg.rj_inclui_execucoes_fiscais:
        endividamento_judicializado += fiscal.valor_execucoes_fiscais

    pontos_agro = max(
        cfg.pontos_rj_zarc[agro.risco_zarc],
        cfg.pontos_rj_quebra_safra
        if agro.quebra_safra_regional_pct > cfg.limiar_rj_quebra_safra_pct
        else NEUTRO,
    )

    houve_alteracao_admin = (
        cadastral.alteracao_societaria_180d or cadastral.saida_socio_majoritario_12m
    )
    em_crise = (
        juridico.execucoes_titulo_12m > NEUTRO
        or juridico.protestos_ativos > NEUTRO
        or fiscal.divida_ativa_pgfn > NEUTRO
    )
    patrimonio_forte = (
        fatos.patrimonio_declarado
        >= cfg.multiplo_patrimonio_redutor_rj * exposicao_total
        and juridico.execucoes_titulo_12m == NEUTRO
    )

    candidatos = [
        _sinal(
            "pluralidade_credores",
            cfg.pontos_rj_pluralidade_credores
            if juridico.credores_distintos_executando >= cfg.minimo_credores_distintos
            else NEUTRO,
            cfg,
        ),
        _sinal(
            "endividamento_judicializado",
            limitar(
                razao_segura(endividamento_judicializado, exposicao_total)
                * cfg.coef_rj_endividamento,
                cfg.teto_rj_endividamento,
            ),
            cfg,
        ),
        _sinal(
            "protestos_credores_distintos",
            limitar(
                juridico.credores_protestantes_180d * cfg.coef_rj_protestos,
                cfg.teto_rj_protestos,
            ),
            cfg,
        ),
        _sinal(
            "divida_ativa_sobre_faturamento",
            limitar(
                razao_segura(fiscal.divida_ativa_pgfn, fatos.faturamento_estimado_anual)
                * cfg.coef_rj_divida_ativa,
                cfg.teto_rj_divida_ativa,
            ),
            cfg,
        ),
        _sinal("estresse_agroclimatico", limitar(pontos_agro, cfg.teto_rj_agro), cfg),
        _sinal(
            "pedido_falencia",
            cfg.pontos_rj_pedido_falencia if juridico.pedido_falencia else NEUTRO,
            cfg,
        ),
        _sinal(
            "parcelamento_rompido",
            cfg.pontos_rj_parcelamento_rompido if fiscal.parcelamento_rompido_12m else NEUTRO,
            cfg,
        ),
        _sinal(
            "covenant_rompido",
            cfg.pontos_rj_covenant_rompido if fatos.interno.covenants_rompidos else NEUTRO,
            cfg,
        ),
        _sinal(
            "alteracao_admin_em_crise",
            cfg.pontos_rj_alteracao_admin_em_crise
            if (houve_alteracao_admin and em_crise)
            else NEUTRO,
            cfg,
        ),
        _sinal(
            "patrimonio_forte",
            cfg.redutor_rj_patrimonio_forte if patrimonio_forte else NEUTRO,
            cfg,
        ),
    ]

    sinais = [sinal for sinal in candidatos if sinal is not None]
    indice = clamp(
        sum(sinal.pontos for sinal in sinais), cfg.rj_index_minimo, cfg.rj_index_maximo
    )
    return arredondar(indice, cfg.casas_pontos), sinais


def probabilidade_de_rj(rj_index_efetivo: float, config: ScoringConfig | None = None) -> float:
    """`RJ12 = 0,45 / (1 + exp(−(rjIndexEfetivo − 55) / 9))` — §7."""
    cfg = resolver_config(config)
    return cfg.rj_l / (
        _TOTAL + exp(-(rj_index_efetivo - cfg.rj_centro) / cfg.rj_escala)
    )


def calcular_risco_rj(
    fatos: FatosDoCliente,
    resumo: ResumoDeExposicao,
    config: ScoringConfig | None = None,
) -> RiscoRJ:
    """Índice, elegibilidade, atenuação de PF e conversão em probabilidade — §7."""
    cfg = resolver_config(config)
    indice, sinais = calcular_rj_index(fatos, resumo, cfg)
    elegibilidade = elegibilidade_para_rj(fatos, cfg)

    indice_efetivo = (
        indice if elegibilidade.elegivel else indice * cfg.fator_atenuacao_rj_inelegivel
    )
    evento_ja_ocorrido = fatos.juridico.recuperacao_judicial is not None
    probabilidade = (
        cfg.probabilidade_rj_evento_ocorrido
        if evento_ja_ocorrido
        else probabilidade_de_rj(indice_efetivo, cfg)
    )

    return RiscoRJ(
        probabilidade_12m=arredondar(probabilidade, cfg.casas_probabilidade),
        evento_ja_ocorrido=evento_ja_ocorrido,
        rj_index=arredondar(indice, cfg.casas_pontos),
        rj_index_efetivo=arredondar(indice_efetivo, cfg.casas_pontos),
        elegivel=elegibilidade.elegivel,
        motivo_inelegibilidade=elegibilidade.motivo,
        sinais=sinais,
    )
