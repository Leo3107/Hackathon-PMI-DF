"""Recomendação operacional determinística — `specs/02-motor-de-risco.md` §12.

**Qual** recomendação e **quais** ações são decididas por regra, nesta ordem; o
LLM só escreve a prosa em volta (`04-camada-llm.md`). Nenhuma ação é genérica:
todo rótulo já vem parametrizado com os números reais do cliente — o limite em
reais, o percentual da tabela de política, o prazo em dias, o valor da garantia
que precisa virar alienação fiduciária.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from models.avaliacao import AcaoRecomendada, Recomendacao, VetoAtivo
from models.enums import CodigoRecomendacao, EfeitoVeto, Rating, Tendencia
from models.exposicao import ExposicaoCalculada
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .exposicao import ResumoDeExposicao
from .formatacao import moeda, percentual_de_fracao, plural_dias
from .util import NEUTRO

__all__ = [
    "ContextoDaRecomendacao",
    "ROTULOS_TENDENCIA",
    "ACOES_POR_RECOMENDACAO",
    "escolher_codigo",
    "montar_acoes",
    "montar_recomendacao",
]

#: Rótulos de tendência em pt-BR para o texto corrido das ações.
ROTULOS_TENDENCIA: dict[Tendencia, str] = {
    Tendencia.MELHORANDO: "em melhora",
    Tendencia.ESTAVEL: "estável",
    Tendencia.DETERIORANDO: "em deterioração",
    Tendencia.DETERIORACAO_ACELERADA: "em deterioração acelerada",
}

_ROTULO_ALIENACAO_FIDUCIARIA = "alienação fiduciária"
_CASAS_PERCENTUAL_INTEIRO = 0
_SINAL_DE_REDUCAO = "−"
#: O todo, do qual a redução percentual é subtraída — mesmo papel de `_TOTAL`
#: em `scoring.probabilidades`.
_TOTAL: float = 1.0


@dataclass(frozen=True)
class ContextoDaRecomendacao:
    """Tudo que uma ação precisa para se parametrizar. Só leitura."""

    rating_final: Rating
    tendencia: Tendencia
    fatos: FatosDoCliente
    resumo: ResumoDeExposicao
    vetos: list[VetoAtivo]
    cfg: ScoringConfig

    @property
    def exposicao(self) -> ExposicaoCalculada:
        return self.resumo.calculada


# ---------------------------------------------------------------------------
# §12 · Árvore de decisão — avaliada em ordem, a primeira que casar vence
# ---------------------------------------------------------------------------


def _tem_veto_de_forca_d(vetos: list[VetoAtivo]) -> bool:
    return any(veto.efeito is EfeitoVeto.FORCA_D for veto in vetos)


def escolher_codigo(
    rating_final: Rating,
    tendencia: Tendencia,
    vetos: list[VetoAtivo],
    resumo: ResumoDeExposicao,
    config: ScoringConfig | None = None,
) -> CodigoRecomendacao:
    """A tabela da §12, linha por linha, na ordem em que está escrita."""
    cfg = resolver_config(config)
    exposicao = resumo.calculada
    fracao_em_risco_em_rj = (
        exposicao.exposicao_em_risco_em_rj / exposicao.exposicao_total
        if exposicao.exposicao_total > NEUTRO
        else NEUTRO
    )

    if _tem_veto_de_forca_d(vetos):
        return CodigoRecomendacao.SUSPENDER_EXPOSICAO
    if rating_final is Rating.D:
        return CodigoRecomendacao.SUSPENDER_EXPOSICAO
    if rating_final is Rating.C and tendencia is Tendencia.DETERIORACAO_ACELERADA:
        return CodigoRecomendacao.SUSPENDER_NOVA_EXPOSICAO_A_PRAZO
    if rating_final is Rating.C:
        return CodigoRecomendacao.APROVAR_COM_RESTRICOES
    if rating_final is Rating.B and fracao_em_risco_em_rj > cfg.limiar_exposicao_rj_rating_b:
        return CodigoRecomendacao.APROVAR_COM_RESTRICOES
    if rating_final is Rating.B and tendencia in cfg.tendencias_de_deterioracao:
        return CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO
    if rating_final is Rating.B:
        return CodigoRecomendacao.APROVAR
    if (
        rating_final is Rating.A
        and exposicao.limite_utilizado_pct > cfg.limiar_utilizacao_revisao_de_limite
    ):
        return CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE
    return CodigoRecomendacao.APROVAR


# ---------------------------------------------------------------------------
# §12 · Ações concretas, parametrizadas pelos números do cliente
# ---------------------------------------------------------------------------


def _acao(
    acao_id: str, rotulo: str, prioridade: int, detalhe: str | None = None
) -> AcaoRecomendada:
    return AcaoRecomendada(
        id=acao_id, rotulo=rotulo, detalhe=detalhe, prioridade=prioridade
    )


def _reduzir_limite(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    limite = ctx.exposicao.limite_aprovado
    reducao = ctx.cfg.reducao_limite_por_rating_e_tendencia[ctx.rating_final][ctx.tendencia]
    if limite <= NEUTRO or reducao <= NEUTRO:
        return None
    novo_limite = limite * (_TOTAL - reducao)
    return _acao(
        "reduzir_limite",
        (
            f"Reduzir limite aprovado de {moeda(limite)} para {moeda(novo_limite)} "
            f"({_SINAL_DE_REDUCAO}"
            f"{percentual_de_fracao(reducao, casas=_CASAS_PERCENTUAL_INTEIRO)})"
        ),
        ctx.cfg.prioridade_alta,
        detalhe=(
            f"Percentual da política de limite para rating {ctx.rating_final.value} "
            f"com carteira {ROTULOS_TENDENCIA[ctx.tendencia]}."
        ),
    )


def _exigir_garantia_adicional(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    descoberto = ctx.exposicao.exposicao_em_risco
    if descoberto <= NEUTRO:
        return None
    return _acao(
        "exigir_garantia_adicional",
        f"Exigir garantia adicional de {moeda(descoberto)} para cobrir a exposição desprotegida",
        ctx.cfg.prioridade_alta,
        detalhe=(
            f"Cobertura total atual de "
            f"{percentual_de_fracao(ctx.exposicao.cobertura_total)} sobre "
            f"{moeda(ctx.exposicao.exposicao_total)} de exposição."
        ),
    )


def _converter_para_extraconcursal(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    garantia = ctx.resumo.maior_garantia_concursal
    if (
        garantia is None
        or garantia.valor_atualizado < ctx.cfg.valor_minimo_garantia_concursal_relevante
    ):
        return None
    return _acao(
        "converter_para_extraconcursal",
        (
            f"Converter {ctx.cfg.rotulos_tipo_garantia[garantia.tipo]} "
            f"({moeda(garantia.valor_atualizado)}) em {_ROTULO_ALIENACAO_FIDUCIARIA} "
            "para blindar o crédito em cenário de RJ"
        ),
        ctx.cfg.prioridade_media,
        detalhe=(
            f"{moeda(ctx.exposicao.exposicao_em_risco_em_rj)} perdem proteção efetiva "
            "se o cliente pedir recuperação judicial, porque garantia concursal entra no plano."
        ),
    )


def _reduzir_prazo(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    prazo = ctx.resumo.prazo_medio_dias
    if prazo <= ctx.cfg.prazo_minimo_dias:
        return None
    novo_prazo = max(
        ctx.cfg.prazo_minimo_dias, int(round(prazo * ctx.cfg.fator_reducao_de_prazo))
    )
    if novo_prazo >= prazo:
        return None
    return _acao(
        "reduzir_prazo",
        f"Reduzir prazo de pagamento de {plural_dias(prazo)} para {plural_dias(novo_prazo)}",
        ctx.cfg.prioridade_media,
        detalhe=(
            f"{moeda(ctx.exposicao.a_vencer_90d)} já vencem nos próximos "
            f"{plural_dias(ctx.cfg.janela_a_vencer_dias)}."
        ),
    )


def _monitoramento_intensivo(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    return _acao(
        "monitoramento_intensivo",
        (
            "Ativar monitoramento intensivo das fontes públicas sobre "
            f"{moeda(ctx.exposicao.exposicao_total)} de exposição"
        ),
        ctx.cfg.prioridade_media,
        detalhe=(
            "Reconsulta automática de execuções, protestos, dívida ativa e certidões "
            f"até a reavaliação em {plural_dias(ctx.cfg.prazo_reavaliacao_por_rating[ctx.rating_final])}."
        ),
    )


def _bloquear_aumento_limite(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    limite = ctx.exposicao.limite_aprovado
    if limite <= NEUTRO:
        return None
    return _acao(
        "bloquear_aumento_limite",
        f"Bloquear aumento do limite aprovado de {moeda(limite)}",
        ctx.cfg.prioridade_media,
        detalhe=(
            f"Utilização atual de {percentual_de_fracao(ctx.exposicao.limite_utilizado_pct)} "
            f"({moeda(ctx.exposicao.exposicao_total)})."
        ),
    )


def _exigir_pagamento_a_vista(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    return _acao(
        "exigir_pagamento_a_vista",
        "Exigir pagamento à vista em novos fornecimentos",
        ctx.cfg.prioridade_alta,
        detalhe=(
            f"{moeda(ctx.exposicao.a_vencer_90d)} a vencer em "
            f"{plural_dias(ctx.cfg.janela_a_vencer_dias)} e "
            f"{moeda(ctx.exposicao.em_atraso)} já em atraso."
        ),
    )


def _encaminhar_analise_especializada(
    ctx: ContextoDaRecomendacao,
) -> AcaoRecomendada | None:
    motivos = [veto.rotulo for veto in ctx.vetos if veto.efeito is EfeitoVeto.FORCA_D]
    if not motivos:
        return None
    return _acao(
        "encaminhar_analise_especializada",
        "Encaminhar o caso para análise jurídica especializada",
        ctx.cfg.prioridade_alta,
        detalhe=f"Gatilho eliminatório: {'; '.join(motivos)}.",
    )


def _acionar_garantia(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    extraconcursal = ctx.exposicao.valor_extraconcursal
    if extraconcursal <= NEUTRO:
        return None
    return _acao(
        "acionar_garantia",
        (
            f"Acionar as garantias extraconcursais ({moeda(extraconcursal)}), "
            "não sujeitas aos efeitos da recuperação judicial"
        ),
        ctx.cfg.prioridade_alta,
        detalhe=(
            f"{moeda(ctx.exposicao.valor_concursal)} em garantias concursais seguem "
            "sujeitos ao plano e não podem ser somados a esse valor."
        ),
    )


def _suspender_novas_operacoes(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    return _acao(
        "suspender_novas_operacoes",
        (
            "Suspender novas operações a prazo e congelar a exposição em "
            f"{moeda(ctx.exposicao.exposicao_total)}"
        ),
        ctx.cfg.prioridade_alta,
        detalhe=(
            f"{moeda(ctx.exposicao.exposicao_em_risco)} sem qualquer garantia e "
            f"{moeda(ctx.exposicao.exposicao_em_risco_em_rj)} sem proteção em cenário de RJ."
        ),
    )


def _revisar_limite(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    limite = ctx.exposicao.limite_aprovado
    if limite <= NEUTRO:
        return None
    return _acao(
        "revisar_limite",
        (
            "Revisar o limite aprovado de "
            f"{moeda(limite)} — utilização em "
            f"{percentual_de_fracao(ctx.exposicao.limite_utilizado_pct)}"
        ),
        ctx.cfg.prioridade_media,
        detalhe=(
            f"{moeda(ctx.exposicao.exposicao_total)} de exposição contra "
            f"{moeda(ctx.fatos.patrimonio_declarado)} de patrimônio declarado."
        ),
    )


def _manter_condicoes(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    return _acao(
        "manter_condicoes",
        (
            "Manter as condições comerciais vigentes para "
            f"{moeda(ctx.exposicao.exposicao_total)} de exposição"
        ),
        ctx.cfg.prioridade_baixa,
        detalhe=(
            f"Cobertura extraconcursal de "
            f"{percentual_de_fracao(ctx.exposicao.cobertura_extraconcursal)} da exposição."
        ),
    )


def _reavaliar_em(ctx: ContextoDaRecomendacao) -> AcaoRecomendada | None:
    dias = ctx.cfg.prazo_reavaliacao_por_rating[ctx.rating_final]
    return _acao(
        "reavaliar_em",
        f"Reavaliar em {plural_dias(dias)}",
        ctx.cfg.prioridade_baixa,
        detalhe=(
            f"Prazo de reavaliação da política de crédito para rating "
            f"{ctx.rating_final.value}."
        ),
    )


_Construtor = Callable[[ContextoDaRecomendacao], AcaoRecomendada | None]

#: Repertório de ações de cada recomendação, na ordem de exibição (§12).
ACOES_POR_RECOMENDACAO: dict[CodigoRecomendacao, tuple[_Construtor, ...]] = {
    CodigoRecomendacao.SUSPENDER_EXPOSICAO: (
        _suspender_novas_operacoes,
        _exigir_pagamento_a_vista,
        _acionar_garantia,
        _encaminhar_analise_especializada,
        _reduzir_limite,
        _reavaliar_em,
    ),
    CodigoRecomendacao.SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: (
        _suspender_novas_operacoes,
        _exigir_pagamento_a_vista,
        _reduzir_limite,
        _exigir_garantia_adicional,
        _converter_para_extraconcursal,
        _monitoramento_intensivo,
        _reavaliar_em,
    ),
    CodigoRecomendacao.APROVAR_COM_RESTRICOES: (
        _reduzir_limite,
        _exigir_garantia_adicional,
        _converter_para_extraconcursal,
        _reduzir_prazo,
        _monitoramento_intensivo,
        _reavaliar_em,
    ),
    CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO: (
        _monitoramento_intensivo,
        _bloquear_aumento_limite,
        _exigir_garantia_adicional,
        _reduzir_limite,
        _reavaliar_em,
    ),
    CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE: (
        _revisar_limite,
        _bloquear_aumento_limite,
        _reavaliar_em,
    ),
    CodigoRecomendacao.APROVAR: (
        _manter_condicoes,
        _reavaliar_em,
    ),
}


def montar_acoes(
    codigo: CodigoRecomendacao, ctx: ContextoDaRecomendacao
) -> list[AcaoRecomendada]:
    """Constrói as ações da recomendação, descartando as que não se aplicam."""
    construidas = [construtor(ctx) for construtor in ACOES_POR_RECOMENDACAO[codigo]]
    return [acao for acao in construidas if acao is not None]


def montar_recomendacao(
    rating_final: Rating,
    tendencia: Tendencia,
    vetos: list[VetoAtivo],
    fatos: FatosDoCliente,
    resumo: ResumoDeExposicao,
    config: ScoringConfig | None = None,
) -> Recomendacao:
    """Decisão de crédito e plano de ação — determinísticos, §12."""
    cfg = resolver_config(config)
    codigo = escolher_codigo(rating_final, tendencia, vetos, resumo, cfg)
    ctx = ContextoDaRecomendacao(
        rating_final=rating_final,
        tendencia=tendencia,
        fatos=fatos,
        resumo=resumo,
        vetos=list(vetos),
        cfg=cfg,
    )
    return Recomendacao(
        codigo=codigo,
        rotulo=cfg.rotulos_recomendacao[codigo],
        acoes=montar_acoes(codigo, ctx),
        prazo_reavaliacao_dias=cfg.prazo_reavaliacao_por_rating[rating_final],
    )
