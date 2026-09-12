"""Exposição e garantias — `specs/01-modelo-de-dados.md` + `specs/02-motor-de-risco.md` §10."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import ModeloLastro
from .enums import NaturezaGarantia, StatusParcela, TipoGarantia, TipoOperacao
from .tabelas import natureza_da_garantia, valor_atualizado_da_garantia

__all__ = ["Parcela", "Barter", "Operacao", "Garantia", "ExposicaoCalculada"]


class Parcela(ModeloLastro):
    id: str
    #: ISO date
    vencimento: str
    valor: float
    status: StatusParcela
    dias_atraso: int | None = None


class Barter(ModeloLastro):
    """Safra prometida em contrapartida. Conecta risco agro ao dinheiro exposto."""

    cultura: str
    sacas_prometidas: float
    preco_referencia_saca: float
    #: Ausente = barter sem lastro formal (penalidade D4 `barter_sem_lastro`).
    cpr_vinculada_id: str | None = None


class Operacao(ModeloLastro):
    id: str
    tipo: TipoOperacao
    #: ex.: 'Fornecimento de defensivos — safra 2025/26'
    descricao: str
    saldo_devedor: float
    #: ISO date
    data_contratacao: str
    parcelas: list[Parcela] = Field(default_factory=list)
    barter: Barter | None = None


class Garantia(ModeloLastro):
    """`natureza` e `valorAtualizado` são DERIVADOS do tipo — nunca digitados.

    Quando o dataset omite os dois campos, eles são preenchidos aqui pelas
    tabelas canônicas de `models.tabelas`. O motor os recalcula de qualquer
    forma em `scoring.exposicao.normalizar_garantias`, usando a `ScoringConfig`
    em vigor, de modo que uma sobrescrita de haircut se propaga por inteiro.
    """

    id: str
    tipo: TipoGarantia
    natureza: NaturezaGarantia = NaturezaGarantia.CONCURSAL
    descricao: str = ""
    valor_declarado: float = 0.0
    valor_atualizado: float = 0.0
    registrada: bool = True
    #: ISO date
    data_avaliacao: str = ""
    #: true quando o bem está sob embargo ambiental — aciona VETO_EMBARGO_GARANTIA.
    bem_embargado: bool | None = None

    @model_validator(mode="after")
    def _derivar_campos_calculados(self) -> "Garantia":
        if "natureza" not in self.model_fields_set:
            object.__setattr__(
                self, "natureza", natureza_da_garantia(self.tipo, self.registrada)
            )
        if "valor_atualizado" not in self.model_fields_set:
            object.__setattr__(
                self,
                "valor_atualizado",
                valor_atualizado_da_garantia(self.tipo, self.valor_declarado),
            )
        return self


class ExposicaoCalculada(ModeloLastro):
    exposicao_total: float
    limite_aprovado: float
    limite_utilizado_pct: float
    a_vencer_90d: float
    em_atraso: float
    por_tipo_operacao: dict[TipoOperacao, float]
    valor_extraconcursal: float
    valor_concursal: float
    cobertura_extraconcursal: float
    cobertura_total: float
    exposicao_protegida: float
    exposicao_em_risco: float
    #: O número que ninguém mais mostra. Ver 02 §10.
    exposicao_em_risco_em_rj: float = Field(
        alias="exposicaoEmRiscoEmRJ", serialization_alias="exposicaoEmRiscoEmRJ"
    )
