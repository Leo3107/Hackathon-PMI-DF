"""`RepositorioEmMemoria` — a implementação de `RepositorioLastro` sobre `data/`.

Sem banco, sem I/O em requisição (D3). O dataset é carregado uma vez na
importação da fonte e vive no processo. As decisões do analista registradas
via `POST /api/auditoria` ficam numa lista de processo **apenas para devolver
a trilha durante a sessão** — a persistência real é o `localStorage` do
navegador (D11.3).

Este módulo também concentra o que a spec 06 §3 chama de "preenchido em runtime
pela camada de serviço": `EventoDeRisco.scoreApos` e `EventoDeRisco.deltaScore`
são recalculados a partir dos snapshots, nunca lidos do dataset.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from models.avaliacao import AvaliacaoDeRisco
from models.cliente import Cliente
from models.enums import (
    CodigoRecomendacao,
    DecisaoAnalista,
    Rating,
    TipoEventoDeRisco,
)
from models.eventos import (
    Alerta,
    ComparacaoDeAvaliacoes,
    EventoDeRisco,
    RegistroAuditoria,
    SnapshotHistorico,
)
from models.base import ModeloLastro
from models.fatos import FatosDoCliente
from pydantic import Field
from scoring import calcular_risco, comparar_avaliacoes
from scoring.util import para_data

from .base import ClienteNaoEncontrado, RepositorioLastro
from .fonte import FonteDeDados, carregar_fonte
from .sessao import SESSAO_VAZIA, EstadoDeSessao, EventoSimulado
from .simulacao import aplicar_eventos_simulados

__all__ = [
    "RepositorioEmMemoria",
    "NovoRegistroAuditoria",
    "DECISOES_ALINHADAS",
    "JANELA_COMPARACAO_DIAS",
    "PERIODOS_DE_COMPARACAO",
    "PERIODOS_VALIDOS",
    "PERIODO_INICIO",
    "divergiu_da_recomendacao",
]

#: `03-ux-e-telas.md` §8.3 — regra de interface, não de risco.
DECISOES_ALINHADAS: dict[CodigoRecomendacao, frozenset[DecisaoAnalista]] = {
    CodigoRecomendacao.APROVAR: frozenset({DecisaoAnalista.APROVAR}),
    CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO: frozenset(
        {DecisaoAnalista.APROVAR, DecisaoAnalista.APROVAR_COM_RESTRICOES}
    ),
    CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE: frozenset(
        {DecisaoAnalista.APROVAR_COM_RESTRICOES}
    ),
    CodigoRecomendacao.APROVAR_COM_RESTRICOES: frozenset(
        {DecisaoAnalista.APROVAR_COM_RESTRICOES}
    ),
    CodigoRecomendacao.SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: frozenset(
        {DecisaoAnalista.SUSPENDER, DecisaoAnalista.REVISAR}
    ),
    CodigoRecomendacao.SUSPENDER_EXPOSICAO: frozenset(
        {DecisaoAnalista.SUSPENDER, DecisaoAnalista.RECUSAR}
    ),
}

#: Janela do "o que mudou" da carteira e da lista (`03` §2.3, K7).
JANELA_COMPARACAO_DIAS = 90

#: Períodos do seletor do bloco "O que mudou" da página do cliente (`03` §4).
PERIODO_INICIO = "inicio"
PERIODOS_DE_COMPARACAO: dict[str, int] = {"30d": 30, "90d": 90, "12m": 365}
PERIODOS_VALIDOS = (*PERIODOS_DE_COMPARACAO, PERIODO_INICIO)


def divergiu_da_recomendacao(
    recomendacao: CodigoRecomendacao, decisao: DecisaoAnalista
) -> bool:
    return decisao not in DECISOES_ALINHADAS.get(recomendacao, frozenset())


class NovoRegistroAuditoria(ModeloLastro):
    """Corpo de `POST /api/auditoria` (`NovoRegistroAuditoria` de `web/types`).

    `dataHora` e `divergiuDaRecomendacao` são aceitos mas **recalculados** pelo
    servidor: quem carimba a trilha é o motor, não a tela (R6).
    """

    cliente_id: str
    cliente_nome: str = ""
    analista: str = ""
    data_hora: str | None = None
    score_no_momento: float
    rating_no_momento: Rating
    recomendacao_gerada: CodigoRecomendacao
    decisao_analista: DecisaoAnalista
    justificativa: str = Field(min_length=1)


class RepositorioEmMemoria(RepositorioLastro):
    def __init__(self, fonte: FonteDeDados | None = None) -> None:
        self.fonte = fonte if fonte is not None else carregar_fonte()
        self._decisoes: list[RegistroAuditoria] = []
        self._cache_snapshot: dict[tuple[str, str], AvaliacaoDeRisco] = {}

    # -- Interface da spec 01 ------------------------------------------------

    def listar_clientes(self) -> list[Cliente]:
        return list(self.fonte.clientes)

    def obter_cliente(self, cliente_id: str) -> Cliente | None:
        return self.fonte.por_id(cliente_id)

    def obter_fatos_atuais(self, cliente_id: str) -> FatosDoCliente:
        fatos = self.fonte.fatos_por_cliente.get(cliente_id)
        if fatos is None:
            raise ClienteNaoEncontrado(cliente_id)
        return fatos

    def obter_historico(self, cliente_id: str) -> list[SnapshotHistorico]:
        self._exigir_cliente(cliente_id)
        return list(self.fonte.snapshots_por_cliente.get(cliente_id, []))

    def obter_eventos(self, cliente_id: str) -> list[EventoDeRisco]:
        """Eventos do dataset com `scoreApos` e `deltaScore` **recalculados**."""
        self._exigir_cliente(cliente_id)
        trilha = self._trilha_de_scores(cliente_id)
        eventos: list[EventoDeRisco] = []
        for bruto in self.fonte.eventos_por_cliente.get(cliente_id, []):
            score_apos, delta = self._score_na_data(trilha, bruto.data)
            eventos.append(
                bruto.model_copy(update={"score_apos": score_apos, "delta_score": delta})
            )
        return sorted(eventos, key=lambda evento: evento.data, reverse=True)

    def listar_alertas(self) -> list[Alerta]:
        return sorted(self.fonte.alertas, key=lambda a: a.data, reverse=True)

    def listar_auditoria(self) -> list[RegistroAuditoria]:
        todos = [*self.fonte.registros_auditoria, *self._decisoes]
        return sorted(todos, key=lambda r: r.data_hora, reverse=True)

    def registrar_decisao(self, dados: dict) -> RegistroAuditoria:
        """Carimba id, data-hora e divergência. Não persiste em disco (D3)."""
        novo = NovoRegistroAuditoria.model_validate(dados)
        cliente = self.obter_cliente(novo.cliente_id)
        if cliente is None and not novo.cliente_nome:
            raise ClienteNaoEncontrado(novo.cliente_id)
        registro = RegistroAuditoria(
            id=f"aud-{len(self._decisoes) + 1:03d}-{novo.cliente_id}",
            clienteId=novo.cliente_id,
            clienteNome=novo.cliente_nome
            or (cliente.razao_social if cliente else novo.cliente_id),
            analista=novo.analista or "Analista de crédito — Krill Tech",
            dataHora=novo.data_hora or datetime.now().astimezone().isoformat(),
            scoreNoMomento=novo.score_no_momento,
            ratingNoMomento=novo.rating_no_momento,
            recomendacaoGerada=novo.recomendacao_gerada,
            decisaoAnalista=novo.decisao_analista,
            justificativa=novo.justificativa,
            divergiuDaRecomendacao=divergiu_da_recomendacao(
                novo.recomendacao_gerada, novo.decisao_analista
            ),
        )
        self._decisoes.append(registro)
        return registro

    def consultar_documento(self, documento: str) -> Cliente | None:
        return self.fonte.por_documento(documento)

    def simular_evento(
        self, cliente_id: str, tipo: TipoEventoDeRisco
    ) -> FatosDoCliente:
        fatos = self.obter_fatos_atuais(cliente_id)
        evento = EventoSimulado(tipo=tipo, data=datetime.now().astimezone().isoformat())
        return aplicar_eventos_simulados(fatos, [evento])

    # -- Camada de serviço: fato → avaliação ---------------------------------

    def avaliar_fatos(
        self, fatos: FatosDoCliente, sessao: EstadoDeSessao = SESSAO_VAZIA
    ) -> AvaliacaoDeRisco:
        """Aplica a sessão e roda o motor. Único caminho para produzir um score."""
        mutados = aplicar_eventos_simulados(fatos, sessao.eventos_simulados)
        avaliacao = calcular_risco(mutados)
        if sessao.status_red_flags:
            for red_flag in avaliacao.red_flags:
                status = sessao.status_red_flags.get(red_flag.id)
                if status is not None:
                    red_flag.status = status
        return avaliacao

    def avaliar(
        self, cliente_id: str, sessao: EstadoDeSessao = SESSAO_VAZIA
    ) -> AvaliacaoDeRisco:
        return self.avaliar_fatos(self.obter_fatos_atuais(cliente_id), sessao)

    def avaliar_snapshot(self, snapshot: SnapshotHistorico) -> AvaliacaoDeRisco:
        """Avaliação de um instante histórico, memoizada — o dataset é imutável."""
        chave = (snapshot.fatos.cliente_id, snapshot.data)
        em_cache = self._cache_snapshot.get(chave)
        if em_cache is None:
            em_cache = calcular_risco(snapshot.fatos, data_referencia=snapshot.data)
            self._cache_snapshot[chave] = em_cache
        return em_cache

    def comparacao_na_janela(
        self,
        cliente_id: str,
        avaliacao_atual: AvaliacaoDeRisco,
        dias: int = JANELA_COMPARACAO_DIAS,
    ) -> ComparacaoDeAvaliacoes | None:
        """Compara o agora com o snapshot mais próximo de `dias` atrás."""
        anterior = self._snapshot_em(cliente_id, avaliacao_atual.data_referencia, dias)
        if anterior is None:
            return None
        return comparar_avaliacoes(self.avaliar_snapshot(anterior), avaliacao_atual)

    def comparacao_por_periodo(
        self,
        cliente_id: str,
        avaliacao_atual: AvaliacaoDeRisco,
        periodo: str = "90d",
    ) -> ComparacaoDeAvaliacoes:
        """Decomposição fator a fator entre um instante passado e o de agora.

        É o "o que mudou" do bloco de decomposição — o `712 → 604` aberto linha
        a linha. Sem história suficiente, compara o presente consigo mesmo: os
        deltas saem zerados, que é a leitura correta de "não há com o que
        comparar", e a tela não quebra.
        """
        anterior = self._snapshot_do_periodo(
            cliente_id, avaliacao_atual.data_referencia, periodo
        )
        if anterior is None:
            return comparar_avaliacoes(avaliacao_atual, avaliacao_atual)
        return comparar_avaliacoes(self.avaliar_snapshot(anterior), avaliacao_atual)

    def _snapshot_do_periodo(
        self, cliente_id: str, data_referencia: str, periodo: str
    ) -> SnapshotHistorico | None:
        if periodo == PERIODO_INICIO:
            anteriores = [
                snapshot
                for snapshot in self.fonte.snapshots_por_cliente.get(cliente_id, [])
                if snapshot.data < data_referencia
            ]
            return min(anteriores, key=lambda s: s.data) if anteriores else None
        return self._snapshot_em(
            cliente_id, data_referencia, PERIODOS_DE_COMPARACAO[periodo]
        )

    def alertas_do_cliente(self, cliente_id: str) -> list[Alerta]:
        return [a for a in self.fonte.alertas if a.cliente_id == cliente_id]

    # -- Auxiliares privados -------------------------------------------------

    def _exigir_cliente(self, cliente_id: str) -> Cliente:
        cliente = self.obter_cliente(cliente_id)
        if cliente is None:
            raise ClienteNaoEncontrado(cliente_id)
        return cliente

    def _snapshot_em(
        self, cliente_id: str, data_referencia: str, dias: int
    ) -> SnapshotHistorico | None:
        historico = self.fonte.snapshots_por_cliente.get(cliente_id, [])
        if len(historico) < 2:
            return None
        alvo: date = para_data(data_referencia) - timedelta(days=dias)
        anteriores = [s for s in historico if para_data(s.data) <= alvo]
        if anteriores:
            return max(anteriores, key=lambda s: s.data)
        #: Série curta demais: usa o snapshot mais antigo, que ainda é passado.
        mais_antigo = min(historico, key=lambda s: s.data)
        if para_data(mais_antigo.data) >= para_data(data_referencia):
            return None
        return mais_antigo

    def _trilha_de_scores(self, cliente_id: str) -> list[tuple[str, float]]:
        historico = sorted(
            self.fonte.snapshots_por_cliente.get(cliente_id, []),
            key=lambda s: s.data,
        )
        return [
            (snapshot.data, self.avaliar_snapshot(snapshot).score_calculado)
            for snapshot in historico
        ]

    @staticmethod
    def _score_na_data(
        trilha: list[tuple[str, float]], data_evento: str
    ) -> tuple[float, float]:
        """Score do primeiro snapshot em ou após o evento, e a variação que o trouxe."""
        if not trilha:
            return 0.0, 0.0
        indice = next(
            (i for i, (data, _) in enumerate(trilha) if data >= data_evento),
            len(trilha) - 1,
        )
        score_apos = trilha[indice][1]
        anterior = trilha[indice - 1][1] if indice > 0 else score_apos
        return round(score_apos, 1), round(score_apos - anterior, 1)

