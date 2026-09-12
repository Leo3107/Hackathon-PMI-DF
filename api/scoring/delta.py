"""Tendência e "por que o score mudou" — `specs/02-motor-de-risco.md` §11.

    delta(fator) = impactoGlobal_t1(fator) − impactoGlobal_t0(fator)

Fator que só existe em t1 entra com `impactoGlobal_t0 = 0`, e vice-versa. Como
o score é, por construção (§3), `1000 + Σ impactoGlobalAjustado`, a soma dos
deltas reconstrói exatamente a variação do score — **invariante I6**, que este
módulo expõe em `diferencaDeFechamento` para o teste e para a UI.
"""

from __future__ import annotations

from models.avaliacao import AvaliacaoDeRisco, FatorCalculado
from models.enums import Tendencia
from models.eventos import ComparacaoDeAvaliacoes, DeltaDeFator

from .config import ScoringConfig, resolver_config
from .util import NEUTRO, arredondar

__all__ = [
    "SITUACAO_NOVO",
    "SITUACAO_REMOVIDO",
    "SITUACAO_MANTIDO",
    "fatores_da_avaliacao",
    "estimar_variacao_90d",
    "classificar_tendencia",
    "deltas_de_fatores",
    "comparar_avaliacoes",
]

#: Vocabulário de `DeltaDeFator.situacao` (spec 01).
SITUACAO_NOVO = "novo"
SITUACAO_REMOVIDO = "removido"
SITUACAO_MANTIDO = "mantido"


def fatores_da_avaliacao(avaliacao: AvaliacaoDeRisco) -> list[FatorCalculado]:
    """Todos os fatores materializados, achatando as sete dimensões."""
    return [fator for dimensao in avaliacao.dimensoes for fator in dimensao.fatores]


# ---------------------------------------------------------------------------
# Tendência
# ---------------------------------------------------------------------------


def estimar_variacao_90d(
    fatores: list[FatorCalculado], config: ScoringConfig | None = None
) -> float:
    """Variação de score atribuível aos últimos 90 dias, sem histórico.

    Os fatores de `config.FATORES_DE_JANELA_90D` são, por definição, eventos do
    trimestre — aceleração judicial, dívida ativa crescente, covenant rompido,
    pedido de RJ ou de falência, piora do atraso médio. A soma dos impactos
    deles é a melhor estimativa disponível quando só há um instante de fatos.
    Havendo dois instantes, prefira `comparar_avaliacoes`, que é exato.
    """
    cfg = resolver_config(config)
    janela = set(cfg.fatores_de_janela_90d)
    soma = sum(f.impacto_global_ajustado for f in fatores if f.id in janela)
    return arredondar(soma, cfg.casas_score)


def classificar_tendencia(
    variacao_90d: float, config: ScoringConfig | None = None
) -> Tendencia:
    """Faixas da §11, avaliadas da melhora à deterioração acelerada."""
    cfg = resolver_config(config)
    if variacao_90d >= cfg.limiar_melhorando:
        return Tendencia.MELHORANDO
    if variacao_90d <= cfg.limiar_deterioracao_acelerada:
        return Tendencia.DETERIORACAO_ACELERADA
    if variacao_90d <= cfg.limiar_deteriorando:
        return Tendencia.DETERIORANDO
    return Tendencia.ESTAVEL


# ---------------------------------------------------------------------------
# Delta fator a fator
# ---------------------------------------------------------------------------


def _situacao(anterior: FatorCalculado | None, atual: FatorCalculado | None) -> str:
    if anterior is None:
        return SITUACAO_NOVO
    if atual is None:
        return SITUACAO_REMOVIDO
    return SITUACAO_MANTIDO


def _impacto(fator: FatorCalculado | None) -> float:
    return fator.impacto_global_ajustado if fator is not None else NEUTRO


def deltas_de_fatores(
    fatores_anteriores: list[FatorCalculado],
    fatores_atuais: list[FatorCalculado],
    config: ScoringConfig | None = None,
) -> list[DeltaDeFator]:
    """Uma linha por fator presente em qualquer dos dois instantes.

    Ordenado por `|delta|` decrescente — é a ordem em que a §11 manda exibir,
    e o desempate por id mantém a saída determinística.
    """
    cfg = resolver_config(config)
    indice_anterior = {f.id: f for f in fatores_anteriores}
    indice_atual = {f.id: f for f in fatores_atuais}

    ids = list(indice_anterior) + [i for i in indice_atual if i not in indice_anterior]

    linhas: list[DeltaDeFator] = []
    for fator_id in ids:
        anterior = indice_anterior.get(fator_id)
        atual = indice_atual.get(fator_id)
        referencia = atual if atual is not None else anterior
        assert referencia is not None  # id veio de um dos dois índices
        impacto_anterior = _impacto(anterior)
        impacto_atual = _impacto(atual)
        linhas.append(
            DeltaDeFator(
                fator_id=fator_id,
                dimensao=referencia.dimensao,
                rotulo=referencia.rotulo,
                detalhe=referencia.detalhe,
                impacto_anterior=arredondar(impacto_anterior, cfg.casas_score),
                impacto_atual=arredondar(impacto_atual, cfg.casas_score),
                delta=arredondar(impacto_atual - impacto_anterior, cfg.casas_score),
                situacao=_situacao(anterior, atual),
            )
        )

    return sorted(linhas, key=lambda linha: (-abs(linha.delta), linha.fator_id))


def comparar_avaliacoes(
    anterior: AvaliacaoDeRisco,
    atual: AvaliacaoDeRisco,
    config: ScoringConfig | None = None,
) -> ComparacaoDeAvaliacoes:
    """O "por que o score mudou" da §11, com o fechamento da invariante I6."""
    cfg = resolver_config(config)
    linhas = deltas_de_fatores(
        fatores_da_avaliacao(anterior), fatores_da_avaliacao(atual), cfg
    )
    variacao = atual.score_calculado - anterior.score_calculado
    soma_dos_deltas = sum(linha.delta for linha in linhas)

    return ComparacaoDeAvaliacoes(
        cliente_id=atual.cliente_id,
        data_anterior=anterior.data_referencia,
        data_atual=atual.data_referencia,
        score_anterior=anterior.score_calculado,
        score_atual=atual.score_calculado,
        delta_score=arredondar(variacao, cfg.casas_score),
        fatores=linhas,
        diferenca_de_fechamento=arredondar(variacao - soma_dos_deltas, cfg.casas_score),
    )
