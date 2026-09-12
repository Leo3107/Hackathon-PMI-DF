"""Gatilhos de veto — regras determinísticas acima do score (§8).

O veto **nunca** altera `scoreCalculado`. Ele só impõe um piso de severidade ao
`ratingFinal`, e o motivo é sempre nomeado: o analista precisa ver que o
quantitativo dizia 520 e que a regra de negócio rebaixou para D, e por quê.
"""

from __future__ import annotations

from collections.abc import Callable

from models.avaliacao import VetoAtivo
from models.enums import Rating, SituacaoRfb
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .exposicao import ResumoDeExposicao
from .score import rating_mais_severo
from .util import NEUTRO

__all__ = ["avaliar_vetos", "aplicar_vetos", "CONDICOES_DE_VETO"]


def _tem_rj(fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig) -> bool:
    return fatos.juridico.recuperacao_judicial is not None


def _tem_falencia(fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig) -> bool:
    return fatos.juridico.pedido_falencia


def _embargo_sobre_garantia(
    fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig
) -> bool:
    if not fatos.ambiental.embargo_ibama_vigente:
        return False
    return fatos.ambiental.embargo_sobre_imovel_em_garantia or any(
        garantia.bem_embargado for garantia in resumo.garantias
    )


def _cadastro_inapto(
    fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig
) -> bool:
    return fatos.cadastral.situacao_rfb is not SituacaoRfb.ATIVA


def _lista_suja(fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig) -> bool:
    return fatos.juridico.lista_suja_trabalho_escravo


def _fraude(fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig) -> bool:
    return fatos.juridico.fraude_confirmada


def _execucoes_fiscais_relevantes(
    fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig
) -> bool:
    exposicao_total = resumo.calculada.exposicao_total
    if exposicao_total <= NEUTRO:
        return False
    return (
        fatos.fiscal.valor_execucoes_fiscais
        > cfg.limiar_exec_fiscal_sobre_exposicao * exposicao_total
    )


def _cndt_relevante(
    fatos: FatosDoCliente, resumo: ResumoDeExposicao, cfg: ScoringConfig
) -> bool:
    if not fatos.fiscal.cndt_positiva:
        return False
    return (
        fatos.fiscal.valor_debito_trabalhista
        > cfg.limiar_cndt_sobre_patrimonio * fatos.patrimonio_declarado
    )


#: Predicado de cada gatilho da tabela §8. Os textos vivem em `config.REGRAS_DE_VETO`.
CONDICOES_DE_VETO: dict[
    str, Callable[[FatosDoCliente, ResumoDeExposicao, ScoringConfig], bool]
] = {
    "VETO_RJ": _tem_rj,
    "VETO_FALENCIA": _tem_falencia,
    "VETO_EMBARGO_GARANTIA": _embargo_sobre_garantia,
    "VETO_CADASTRO_INAPTO": _cadastro_inapto,
    "VETO_LISTA_SUJA": _lista_suja,
    "VETO_FRAUDE": _fraude,
    "TETO_EXEC_FISCAL": _execucoes_fiscais_relevantes,
    "TETO_CNDT": _cndt_relevante,
}


def avaliar_vetos(
    fatos: FatosDoCliente,
    resumo: ResumoDeExposicao,
    config: ScoringConfig | None = None,
) -> list[VetoAtivo]:
    """Aplica os oito gatilhos, na ordem da spec."""
    cfg = resolver_config(config)
    ativos: list[VetoAtivo] = []
    for regra in cfg.regras_de_veto:
        condicao = CONDICOES_DE_VETO[regra.id]
        if not condicao(fatos, resumo, cfg):
            continue
        ativos.append(
            VetoAtivo(
                id=regra.id,
                rotulo=regra.rotulo,
                efeito=regra.efeito,
                justificativa=regra.justificativa,
                evidencia_ids=[
                    e.id for e in fatos.evidencias if regra.id in e.fatores_relacionados
                ],
            )
        )
    return ativos


def aplicar_vetos(
    rating_calculado: Rating,
    vetos: list[VetoAtivo],
    config: ScoringConfig | None = None,
) -> Rating:
    """Resultado é o rating mais severo; `FORCA_D` prevalece sobre `TETO_C`."""
    cfg = resolver_config(config)
    candidatos = [rating_calculado]
    candidatos.extend(cfg.rating_forcado_por_efeito[veto.efeito] for veto in vetos)
    return rating_mais_severo(candidatos, cfg)
