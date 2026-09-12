"""Exposição, garantias e coberturas — `specs/02-motor-de-risco.md` §10."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from models.enums import NaturezaGarantia, StatusParcela, TipoOperacao
from models.exposicao import ExposicaoCalculada, Garantia
from models.fatos import FatosDoCliente
from models.tabelas import natureza_da_garantia, valor_atualizado_da_garantia

from .config import ScoringConfig, resolver_config
from .util import NEUTRO, arredondar, clamp, dias_entre, para_data, razao_segura, somar_dias

__all__ = ["ResumoDeExposicao", "normalizar_garantias", "calcular_exposicao"]


@dataclass(frozen=True)
class ResumoDeExposicao:
    """`ExposicaoCalculada` mais os auxiliares que a §4 D7 e a §12 consomem."""

    calculada: ExposicaoCalculada
    garantias: list[Garantia]
    total_a_vencer: float
    prazo_medio_dias: int
    maior_garantia_concursal: Garantia | None


def normalizar_garantias(
    garantias: list[Garantia], config: ScoringConfig | None = None
) -> list[Garantia]:
    """Redeclara `natureza` e `valorAtualizado` a partir do tipo e do haircut.

    Campos derivados nunca são lidos do dataset: são recalculados aqui com a
    configuração em vigor (02 §10 e regra de separação da spec 01).
    """
    cfg = resolver_config(config)
    normalizadas: list[Garantia] = []
    for garantia in garantias:
        normalizadas.append(
            garantia.model_copy(
                update={
                    "natureza": natureza_da_garantia(
                        garantia.tipo,
                        garantia.registrada,
                        tabela=cfg.natureza_por_tipo_garantia,
                    ),
                    "valor_atualizado": valor_atualizado_da_garantia(
                        garantia.tipo,
                        garantia.valor_declarado,
                        haircuts=cfg.haircut_por_tipo_garantia,
                    ),
                }
            )
        )
    return normalizadas


def _soma_parcelas(fatos: FatosDoCliente, status: StatusParcela) -> float:
    return sum(
        parcela.valor
        for operacao in fatos.operacoes
        for parcela in operacao.parcelas
        if parcela.status is status
    )


def _a_vencer_na_janela(fatos: FatosDoCliente, data_referencia: date, janela_dias: int) -> float:
    limite = somar_dias(data_referencia, janela_dias)
    return sum(
        parcela.valor
        for operacao in fatos.operacoes
        for parcela in operacao.parcelas
        if parcela.status is StatusParcela.A_VENCER and para_data(parcela.vencimento) <= limite
    )


def _prazo_medio_dias(fatos: FatosDoCliente, data_referencia: date) -> int:
    """Prazo médio ponderado por valor das parcelas ainda a vencer."""
    peso_total = NEUTRO
    soma_ponderada = NEUTRO
    for operacao in fatos.operacoes:
        for parcela in operacao.parcelas:
            if parcela.status is not StatusParcela.A_VENCER:
                continue
            dias = dias_entre(data_referencia, para_data(parcela.vencimento))
            if dias < NEUTRO:
                continue
            peso_total += parcela.valor
            soma_ponderada += parcela.valor * dias
    if peso_total <= NEUTRO:
        return int(NEUTRO)
    return int(round(soma_ponderada / peso_total))


def _por_tipo_operacao(fatos: FatosDoCliente) -> dict[TipoOperacao, float]:
    totais: dict[TipoOperacao, float] = {tipo: NEUTRO for tipo in TipoOperacao}
    for operacao in fatos.operacoes:
        totais[operacao.tipo] = totais[operacao.tipo] + operacao.saldo_devedor
    return totais


def calcular_exposicao(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
) -> ResumoDeExposicao:
    """Aplica literalmente as fórmulas da §10."""
    cfg = resolver_config(config)
    data_ref = data_referencia if data_referencia is not None else para_data(fatos.data_referencia)

    garantias = normalizar_garantias(fatos.garantias, cfg)

    exposicao_total = sum(operacao.saldo_devedor for operacao in fatos.operacoes)
    a_vencer_90d = _a_vencer_na_janela(fatos, data_ref, cfg.janela_a_vencer_dias)
    total_a_vencer = _soma_parcelas(fatos, StatusParcela.A_VENCER)
    em_atraso = _soma_parcelas(fatos, StatusParcela.EM_ATRASO)

    valor_extraconcursal = sum(
        g.valor_atualizado for g in garantias if g.natureza is NaturezaGarantia.EXTRACONCURSAL
    )
    valor_concursal = sum(
        g.valor_atualizado for g in garantias if g.natureza is NaturezaGarantia.CONCURSAL
    )

    cobertura_extraconcursal = razao_segura(valor_extraconcursal, exposicao_total)
    cobertura_total = razao_segura(valor_extraconcursal + valor_concursal, exposicao_total)

    exposicao_protegida = min(exposicao_total, valor_extraconcursal + valor_concursal)
    exposicao_em_risco = exposicao_total - exposicao_protegida
    exposicao_em_risco_em_rj = max(NEUTRO, exposicao_total - valor_extraconcursal)

    concursais = [g for g in garantias if g.natureza is NaturezaGarantia.CONCURSAL]
    maior_concursal = (
        max(concursais, key=lambda g: g.valor_atualizado) if concursais else None
    )

    calculada = ExposicaoCalculada(
        exposicao_total=arredondar(exposicao_total, cfg.casas_moeda),
        limite_aprovado=arredondar(fatos.limite_aprovado, cfg.casas_moeda),
        limite_utilizado_pct=arredondar(
            razao_segura(exposicao_total, fatos.limite_aprovado), cfg.casas_fracao
        ),
        a_vencer_90d=arredondar(a_vencer_90d, cfg.casas_moeda),
        em_atraso=arredondar(em_atraso, cfg.casas_moeda),
        por_tipo_operacao={
            tipo: arredondar(valor, cfg.casas_moeda)
            for tipo, valor in _por_tipo_operacao(fatos).items()
        },
        valor_extraconcursal=arredondar(valor_extraconcursal, cfg.casas_moeda),
        valor_concursal=arredondar(valor_concursal, cfg.casas_moeda),
        cobertura_extraconcursal=arredondar(cobertura_extraconcursal, cfg.casas_fracao),
        cobertura_total=arredondar(cobertura_total, cfg.casas_fracao),
        exposicao_protegida=arredondar(exposicao_protegida, cfg.casas_moeda),
        exposicao_em_risco=arredondar(exposicao_em_risco, cfg.casas_moeda),
        exposicao_em_risco_em_rj=arredondar(exposicao_em_risco_em_rj, cfg.casas_moeda),
    )

    return ResumoDeExposicao(
        calculada=calculada,
        garantias=garantias,
        total_a_vencer=total_a_vencer,
        prazo_medio_dias=_prazo_medio_dias(fatos, data_ref),
        maior_garantia_concursal=maior_concursal,
    )


def cobertura_limitada(cobertura: float, config: ScoringConfig | None = None) -> float:
    """Cobertura truncada em 100% — a §4 D7 exige o teto no cálculo do descoberto."""
    cfg = resolver_config(config)
    return clamp(cobertura, NEUTRO, cfg.cobertura_maxima_no_calculo)
