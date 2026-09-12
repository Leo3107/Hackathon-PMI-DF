"""Red flags derivadas automaticamente — `specs/02-motor-de-risco.md` §13.

Red flag **não é escrita à mão**: nasce do mesmo `FatorCalculado` que moveu o
score, de modo que os dois nunca divergem. `impactoEmPontos` é literalmente o
`impactoGlobalAjustado` do fator — o número que a decomposição já exibe.

As condições qualitativas da §13 ("ZARC elevado para alto", "quebra de safra
acima de 20%") viram `pontos_minimos` nas regras de `config.REGRAS_DE_RED_FLAG`:
o gatilho continua sendo uma regra declarativa, sem `if` escondido aqui.
"""

from __future__ import annotations

from models.avaliacao import FatorCalculado, RedFlag, VetoAtivo
from models.enums import Severidade
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .formatacao import numero
from .util import NEUTRO

__all__ = ["indexar_fatores", "derivar_red_flags"]

#: Separador dos ids derivados: `rf-inadimplencia_tecnica`.
_SEPARADOR_ID = "-"
_SUFIXO_QUEDA_DE_SCORE = "queda_de_score"
_SUFIXO_CERTIDAO_VENCIDA = "certidao_vencida"


def indexar_fatores(fatores: list[FatorCalculado]) -> dict[str, FatorCalculado]:
    """Fatores materializados, indexados por id — a base de toda derivação."""
    return {fator.id: fator for fator in fatores}


def _id(sufixo: str, cfg: ScoringConfig) -> str:
    return f"{cfg.prefixo_id_red_flag}{_SEPARADOR_ID}{sufixo}"


def _descricao(fator: FatorCalculado) -> str:
    return fator.detalhe or fator.rotulo


def _red_flag_de_fator(
    fator: FatorCalculado,
    severidade: Severidade,
    titulo: str,
    fatos: FatosDoCliente,
    cfg: ScoringConfig,
) -> RedFlag:
    return RedFlag(
        id=_id(fator.id, cfg),
        severidade=severidade,
        titulo=titulo,
        descricao=_descricao(fator),
        data=fatos.data_referencia,
        fonte=fator.fonte,
        impacto_em_pontos=fator.impacto_global_ajustado,
        evidencia_ids=list(fator.evidencia_ids),
        fator_id=fator.id,
    )


def _red_flags_de_fatores(
    indice: dict[str, FatorCalculado], fatos: FatosDoCliente, cfg: ScoringConfig
) -> list[RedFlag]:
    derivadas: list[RedFlag] = []
    for regra in cfg.regras_de_red_flag:
        fator = indice.get(regra.fator_id)
        if fator is None or fator.pontos < regra.pontos_minimos:
            continue
        derivadas.append(
            _red_flag_de_fator(fator, regra.severidade, regra.titulo, fatos, cfg)
        )
    return derivadas


def _red_flags_de_vetos(
    vetos: list[VetoAtivo],
    indice: dict[str, FatorCalculado],
    fatos: FatosDoCliente,
    cfg: ScoringConfig,
) -> list[RedFlag]:
    """Gatilhos que são jurídicos por natureza e não têm fator pontuado próprio."""
    ativos = {veto.id: veto for veto in vetos}
    derivadas: list[RedFlag] = []
    for regra in cfg.regras_de_red_flag_por_veto:
        veto = ativos.get(regra.veto_id)
        if veto is None:
            continue
        fator = (
            indice.get(regra.fator_relacionado)
            if regra.fator_relacionado is not None
            else None
        )
        derivadas.append(
            RedFlag(
                id=_id(regra.veto_id, cfg),
                severidade=regra.severidade,
                titulo=regra.titulo,
                descricao=veto.justificativa,
                data=fatos.data_referencia,
                fonte=regra.fonte,
                impacto_em_pontos=(
                    fator.impacto_global_ajustado if fator is not None else NEUTRO
                ),
                evidencia_ids=list(veto.evidencia_ids),
                fator_id=fator.id if fator is not None else None,
            )
        )
    return derivadas


def _red_flag_de_queda_de_score(
    variacao_90d: float, fatos: FatosDoCliente, cfg: ScoringConfig
) -> RedFlag:
    return RedFlag(
        id=_id(_SUFIXO_QUEDA_DE_SCORE, cfg),
        severidade=Severidade.ALTA,
        titulo=cfg.titulo_red_flag_queda_de_score,
        descricao=(
            f"Queda de {numero(abs(variacao_90d))} pontos de score nos últimos 90 dias, "
            "concentrada nos eventos recentes do período."
        ),
        data=fatos.data_referencia,
        fonte=cfg.fonte_red_flag_derivada,
        impacto_em_pontos=variacao_90d,
    )


def _red_flag_de_certidao(fatos: FatosDoCliente, cfg: ScoringConfig) -> RedFlag:
    return RedFlag(
        id=_id(_SUFIXO_CERTIDAO_VENCIDA, cfg),
        severidade=Severidade.MEDIA,
        titulo=cfg.titulo_red_flag_certidao_vencida,
        descricao=(
            "Não há confirmação de que todas as certidões fiscais e trabalhistas "
            "estejam negativas e vigentes na data de referência."
        ),
        data=fatos.data_referencia,
        fonte=cfg.fonte_red_flag_derivada,
        impacto_em_pontos=NEUTRO,
    )


def _ordenar(red_flags: list[RedFlag], cfg: ScoringConfig) -> list[RedFlag]:
    """Da mais severa para a menos severa; dentro da severidade, por impacto."""
    return sorted(
        red_flags,
        key=lambda flag: (
            cfg.ordem_de_severidade[flag.severidade],
            -abs(flag.impacto_em_pontos),
            flag.id,
        ),
    )


def derivar_red_flags(
    fatos: FatosDoCliente,
    fatores: list[FatorCalculado],
    vetos: list[VetoAtivo],
    variacao_90d: float = NEUTRO,
    config: ScoringConfig | None = None,
) -> list[RedFlag]:
    """Deriva a lista completa da §13 a partir dos mesmos fatores do score."""
    cfg = resolver_config(config)
    indice = indexar_fatores(fatores)

    derivadas = _red_flags_de_fatores(indice, fatos, cfg)
    derivadas.extend(_red_flags_de_vetos(vetos, indice, fatos, cfg))

    if variacao_90d <= cfg.limiar_deterioracao_acelerada:
        derivadas.append(_red_flag_de_queda_de_score(variacao_90d, fatos, cfg))
    if not fatos.fiscal.todas_certidoes_negativas:
        derivadas.append(_red_flag_de_certidao(fatos, cfg))

    return _ordenar(derivadas, cfg)
