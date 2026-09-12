"""Modelos de resposta agregada — espelho fiel de `web/types/api.ts`.

Os tipos de `models/` cobrem o domínio; estes cobrem a **fronteira**: o que só
existe porque uma tela precisa de vários clientes de uma vez. Foram propostos
pelo workstream do frontend a partir de `03-ux-e-telas.md` §2 e são
reproduzidos aqui campo a campo, para que a serialização camelCase feche sem
adaptador do outro lado.

Todos herdam `ModeloLastro`, logo respondem a `model_dump(by_alias=True)` com
as chaves do contrato.
"""

from __future__ import annotations

from types import EllipsisType
from typing import Literal

from models.avaliacao import AvaliacaoDeRisco
from models.base import ModeloLastro
from models.cliente import Cliente
from models.enums import EstadoCliente, Rating, Severidade, Tendencia
from models.eventos import Alerta, ComparacaoDeAvaliacoes
from pydantic import Field, model_serializer
from repository.sessao import EventoSimulado

__all__ = [
    "ClienteAvaliado",
    "ProximoVencimento",
    "FatiaDeConcentracao",
    "PontoMatrizDeRisco",
    "LinhaDinheiroEmRisco",
    "CartaoDeAtencao",
    "ContagemPorRating",
    "ResumoDeAlertas",
    "ResumoDeDeterioracao",
    "ResumoCarteira",
    "ResultadoEstagio",
    "RespostaDueDiligence",
    "RespostaSimulacao",
    "RespostaSaude",
    "EstagioPipeline",
    "MotivoAtencao",
]

EstagioPipeline = Literal[
    "CADASTRAL",
    "JURIDICO",
    "FISCAL",
    "AMBIENTAL",
    "AGROCLIMATICO",
    "INTERNO",
    "SCORE",
    "RELATORIO",
]

MotivoAtencao = Literal["VETO_ATIVO", "MAIOR_QUEDA_90D", "ALERTA_CRITICO"]

#: `exposicaoEmRiscoEmRJ` mantém a sigla em caixa alta, como em `ExposicaoCalculada`.
_ALIAS_RISCO_RJ = "exposicaoEmRiscoEmRJ"


def _campo_risco_rj(padrao: float | EllipsisType = ...) -> object:
    return Field(
        padrao, alias=_ALIAS_RISCO_RJ, serialization_alias=_ALIAS_RISCO_RJ
    )


class SemNulos(ModeloLastro):
    """Base dos agregados **aninhados** cujos campos são opcionais no TypeScript.

    `?:` em TS significa "pode estar ausente", não "pode ser `null`". No nível
    superior quem cuida disso é `comum.serializar_agregado`; aqui dentro, onde
    o dicionário já está aninhado, a omissão é responsabilidade do próprio
    modelo.
    """

    @model_serializer(mode="wrap")
    def _omitir_nulos(self, serializar_padrao):
        return {
            chave: valor
            for chave, valor in serializar_padrao(self).items()
            if valor is not None
        }


class ProximoVencimento(SemNulos):
    """Coluna "Próximo vencimento" da lista (`03` §3).

    Derivada das parcelas das operações do cliente: a parcela em atraso mais
    antiga tem precedência sobre a próxima a vencer, porque é a que decide a
    ação. Exatamente um dos dois contadores é emitido.
    """

    #: ISO date
    data: str
    dias_restantes: int | None = None
    dias_atraso: int | None = None


class ClienteAvaliado(ModeloLastro):
    """Linha da lista de clientes: identidade + avaliação + variação na janela."""

    cliente: Cliente
    avaliacao: AvaliacaoDeRisco
    variacao_90d: ComparacaoDeAvaliacoes | None = None
    alertas_nao_lidos: int = 0
    proximo_vencimento: ProximoVencimento | None = None
    #: Severidade do mais grave dos alertas não lidos — dá cor e letra à pastilha.
    severidade_maxima_alerta: Severidade | None = None


class FatiaDeConcentracao(SemNulos):
    rotulo: str
    exposicao: float
    #: 0..1
    pct: float
    clientes: int
    #: Parcela desprotegida da fatia — quanto da concentração está a descoberto.
    exposicao_em_risco: float | None = None
    #: `true` quando algum cliente da fatia tem ZARC alto ou crítico (marcador ▲ de V3).
    zarc_alto: bool | None = None


class PontoMatrizDeRisco(ModeloLastro):
    cliente_id: str
    razao_social: str
    #: 0..1
    pd12m: float
    exposicao_total: float
    exposicao_em_risco_em_rj: float = _campo_risco_rj()
    rating: Rating
    tem_veto: bool


class LinhaDinheiroEmRisco(ModeloLastro):
    cliente_id: str
    razao_social: str
    uf: str
    exposicao_total: float
    exposicao_em_risco: float
    exposicao_em_risco_em_rj: float = _campo_risco_rj()
    rating: Rating
    tem_veto: bool
    tendencia: Tendencia


class CartaoDeAtencao(ModeloLastro):
    """Faixa de atenção imediata (`03` §2.2). A seleção é do motor, não da tela."""

    motivo: MotivoAtencao
    eyebrow: str
    cliente_id: str
    razao_social: str
    causa: str
    #: Número financeiro relevante, **já formatado em pt-BR** pelo servidor.
    numero: str
    acao: str
    severidade: Severidade


class ContagemPorRating(ModeloLastro):
    clientes: int = 0
    exposicao: float = 0.0


class ResumoDeAlertas(ModeloLastro):
    total: int = 0
    por_severidade: dict[Severidade, int] = Field(default_factory=dict)


class ResumoDeDeterioracao(ModeloLastro):
    clientes: int = 0
    #: Limiar em pontos usado na contagem (`03` §2.3, K7).
    limiar_pontos: float = 25.0
    aceleradas: int = 0


class ResumoCarteira(ModeloLastro):
    #: ISO date
    data_referencia: str
    #: ISO datetime da última varredura de monitoramento.
    ultima_varredura: str
    atencao_imediata: list[CartaoDeAtencao] = Field(default_factory=list)
    exposicao_total: float = 0.0
    exposicao_a_vencer_90d: float = 0.0
    exposicao_em_risco: float = 0.0
    exposicao_em_risco_em_rj: float = _campo_risco_rj(0.0)
    exposicao_critica: float = 0.0
    #: 0..1
    pct_exposicao_em_risco: float = 0.0
    #: 0..1
    pct_exposicao_critica: float = 0.0
    clientes_criticos: int = 0
    #: 0..1
    cobertura_extraconcursal: float = 0.0
    #: 0..1
    cobertura_total: float = 0.0
    total_clientes: int = 0
    clientes_por_estado: dict[EstadoCliente, int] = Field(default_factory=dict)
    clientes_por_rating: dict[Rating, ContagemPorRating] = Field(default_factory=dict)
    alertas_30d: ResumoDeAlertas = Field(default_factory=ResumoDeAlertas)
    deterioracao: ResumoDeDeterioracao = Field(default_factory=ResumoDeDeterioracao)
    concentracao_por_cultura: list[FatiaDeConcentracao] = Field(default_factory=list)
    concentracao_por_uf: list[FatiaDeConcentracao] = Field(default_factory=list)
    matriz_de_risco: list[PontoMatrizDeRisco] = Field(default_factory=list)
    dinheiro_em_risco: list[LinhaDinheiroEmRisco] = Field(default_factory=list)


class ResultadoEstagio(ModeloLastro):
    """Um estágio do pipeline de due diligence (`03` §6.4).

    `status` é `falha` apenas quando a consulta não pôde ser feita. Fonte sem
    achado é `ok` com a linha "Nenhum registro encontrado" — isso é informação,
    não falha.
    """

    estagio: EstagioPipeline
    rotulo: str
    status: Literal["ok", "falha"] = "ok"
    achados: list[str] = Field(default_factory=list)
    duracao_ms: int = 0


class RespostaDueDiligence(ModeloLastro):
    encontrado: bool
    documento: str
    cliente: Cliente | None = None
    avaliacao: AvaliacaoDeRisco | None = None
    estagios: list[ResultadoEstagio] = Field(default_factory=list)


class RespostaSimulacao(ModeloLastro):
    """D10 — o motor recalcula de verdade; nada aqui é escrito à mão."""

    cliente_id: str
    evento: EventoSimulado
    score_anterior: float
    score_atual: float
    delta_score: float
    avaliacao: AvaliacaoDeRisco
    variacao: ComparacaoDeAvaliacoes
    alerta_gerado: Alerta | None = None


class RespostaSaude(ModeloLastro):
    ok: bool
    servico: str
    versao: str | None = None
    llm_habilitado: bool | None = None
    #: ISO datetime
    data_hora: str | None = None
