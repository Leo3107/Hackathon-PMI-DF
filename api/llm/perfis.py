"""Matriz tarefa × seções do bloco de contexto — `specs/04-camada-llm.md` §3.5.

Cada tarefa recebe só o que precisa. O parecer e o copiloto veem tudo; a
explicação do score não vê PD, RJ, exposição, garantias, red flags nem
recomendação, porque o texto do score não fala disso — e cada seção omitida é
token que não se paga.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .engine import TarefaNarrativa

__all__ = ["Perfil", "PERFIS", "perfil_de"]


class Perfil(BaseModel):
    """Uma linha da matriz da §3.5. Imutável: é configuração, não estado."""

    model_config = ConfigDict(frozen=True)

    cliente_completo: bool
    variacao_itens: bool
    dimensoes: bool
    #: `None` = todos os fatores materializados.
    max_fatores_risco: int | None
    max_fatores_protecao: int | None
    pd_rj_stay: bool
    exposicao_garantias: bool
    red_flags: Literal["todas", "criticas_altas", "nenhuma"]
    recomendacao: bool
    evidencias: Literal["com_resumo", "sem_resumo"]


PERFIS: dict[TarefaNarrativa, Perfil] = {
    "parecer": Perfil(
        cliente_completo=True,
        variacao_itens=True,
        dimensoes=True,
        max_fatores_risco=None,
        max_fatores_protecao=None,
        pd_rj_stay=True,
        exposicao_garantias=True,
        red_flags="todas",
        recomendacao=True,
        evidencias="com_resumo",
    ),
    "score": Perfil(
        cliente_completo=False,
        variacao_itens=True,
        dimensoes=True,
        max_fatores_risco=9,
        max_fatores_protecao=3,
        pd_rj_stay=False,
        exposicao_garantias=False,
        red_flags="nenhuma",
        recomendacao=False,
        evidencias="sem_resumo",
    ),
    "recomendacao": Perfil(
        cliente_completo=False,
        variacao_itens=False,
        dimensoes=False,
        max_fatores_risco=8,
        max_fatores_protecao=2,
        pd_rj_stay=True,
        exposicao_garantias=True,
        red_flags="criticas_altas",
        recomendacao=True,
        evidencias="sem_resumo",
    ),
    "copiloto": Perfil(
        cliente_completo=True,
        variacao_itens=True,
        dimensoes=True,
        max_fatores_risco=None,
        max_fatores_protecao=None,
        pd_rj_stay=True,
        exposicao_garantias=True,
        red_flags="todas",
        recomendacao=True,
        evidencias="com_resumo",
    ),
}


def perfil_de(tarefa: TarefaNarrativa) -> Perfil:
    return PERFIS[tarefa]
