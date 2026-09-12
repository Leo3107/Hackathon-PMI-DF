"""`/api/clientes*` — lista, ficha, avaliação, histórico, eventos e simulação.

As rotas que **recalculam risco** (`/api/clientes`, `/avaliacao`, `/eventos`,
`/simular-evento`) aceitam `POST` com o `EstadoDeSessao` no corpo (D3). As que
devolvem fato puro (`/api/clientes/<id>`, `/historico`) são `GET`: não há o que
a sessão pudesse mudar nelas.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from flask import Blueprint
from models.enums import Severidade, TipoEventoDeRisco
from models.eventos import Alerta
from repository import PERIODOS_VALIDOS, ClienteNaoEncontrado, EventoSimulado
from repository.simulacao import ROTULO_DO_EVENTO
from scoring import comparar_avaliacoes
from scoring.formatacao import numero

from .agregados import RespostaSimulacao
from .comum import (
    corpo_da_requisicao,
    lista_serializada,
    repositorio,
    resposta,
    serializar,
    serializar_agregado,
    sessao_da_requisicao,
)
from .erros import CodigoErro, ErroApi
from .servico_carteira import avaliar_carteira

clientes_bp = Blueprint("clientes", __name__)

#: Severidade do alerta gerado pela simulação ao vivo (D10).
_SEVERIDADE_DO_EVENTO: dict[TipoEventoDeRisco, Severidade] = {
    TipoEventoDeRisco.PEDIDO_RJ: Severidade.CRITICA,
    TipoEventoDeRisco.PEDIDO_FALENCIA: Severidade.CRITICA,
    TipoEventoDeRisco.EMBARGO_AMBIENTAL: Severidade.CRITICA,
    TipoEventoDeRisco.NOVA_EXECUCAO: Severidade.ALTA,
    TipoEventoDeRisco.DIVIDA_ATIVA: Severidade.ALTA,
    TipoEventoDeRisco.COVENANT_ROMPIDO: Severidade.ALTA,
    TipoEventoDeRisco.NOVO_PROTESTO: Severidade.ALTA,
    TipoEventoDeRisco.ATRASO_PAGAMENTO: Severidade.MEDIA,
    TipoEventoDeRisco.MUDANCA_CLIMATICA: Severidade.MEDIA,
    TipoEventoDeRisco.ALTERACAO_SOCIETARIA: Severidade.MEDIA,
    TipoEventoDeRisco.CADASTRAL: Severidade.MEDIA,
    TipoEventoDeRisco.RECALCULO: Severidade.BAIXA,
}

_ACAO_PADRAO = "Abrir o cliente e revisar a recomendação recalculada."

#: Janela padrão do seletor de "O que mudou" (`03` §4).
PERIODO_PADRAO = "90d"


def _exigir_cliente(cliente_id: str):
    cliente = repositorio().obter_cliente(cliente_id)
    if cliente is None:
        raise ErroApi(
            CodigoErro.CLIENTE_NAO_ENCONTRADO,
            HTTPStatus.NOT_FOUND,
            f"Nenhum cliente com id `{cliente_id}` no conjunto de dados simulado.",
        )
    return cliente


@clientes_bp.post("/api/clientes")
@clientes_bp.get("/api/clientes")
def listar_clientes():
    """Lista avaliada — `ClienteAvaliado[]`, uma linha por cliente da carteira."""
    linhas = avaliar_carteira(repositorio(), sessao_da_requisicao())
    return resposta([serializar_agregado(linha) for linha in linhas])


@clientes_bp.get("/api/clientes/<cliente_id>")
def obter_cliente(cliente_id: str):
    return resposta(serializar(_exigir_cliente(cliente_id)))


@clientes_bp.post("/api/clientes/<cliente_id>/avaliacao")
@clientes_bp.get("/api/clientes/<cliente_id>/avaliacao")
def obter_avaliacao(cliente_id: str):
    _exigir_cliente(cliente_id)
    sessao = sessao_da_requisicao()
    return resposta(serializar(repositorio().avaliar(cliente_id, sessao)))


@clientes_bp.post("/api/clientes/<cliente_id>/comparacao")
@clientes_bp.get("/api/clientes/<cliente_id>/comparacao")
def obter_comparacao(cliente_id: str):
    """"O que mudou" — `ComparacaoDeAvaliacoes` entre um período e hoje.

    Corpo: `{periodo, sessao}`, com `periodo` em `30d · 90d · 12m · inicio`
    (padrão `90d`). O snapshot daquele instante é **recalculado** pelo motor e
    comparado com a avaliação corrente; a soma dos deltas por fator reconstrói
    exatamente a variação do score (invariante I6), e é isso que abre o
    `712 → 604` linha a linha.
    """
    _exigir_cliente(cliente_id)
    repo = repositorio()
    sessao = sessao_da_requisicao()
    periodo = _periodo_do_corpo()
    atual = repo.avaliar(cliente_id, sessao)
    return resposta(serializar(repo.comparacao_por_periodo(cliente_id, atual, periodo)))


@clientes_bp.get("/api/clientes/<cliente_id>/historico")
def obter_historico(cliente_id: str):
    _exigir_cliente(cliente_id)
    return resposta(lista_serializada(repositorio().obter_historico(cliente_id)))


@clientes_bp.post("/api/clientes/<cliente_id>/eventos")
@clientes_bp.get("/api/clientes/<cliente_id>/eventos")
def obter_eventos(cliente_id: str):
    """Eventos do dataset com `scoreApos` e `deltaScore` recalculados (spec 06 §3)."""
    _exigir_cliente(cliente_id)
    sessao_da_requisicao()  # valida o corpo mesmo quando não altera o histórico
    return resposta(lista_serializada(repositorio().obter_eventos(cliente_id)))


@clientes_bp.post("/api/clientes/<cliente_id>/simular-evento")
def simular_evento(cliente_id: str):
    """D10 — injeta o evento nos **fatos** e devolve o recálculo real do motor."""
    cliente = _exigir_cliente(cliente_id)
    repo = repositorio()
    sessao = sessao_da_requisicao()
    tipo = _tipo_do_corpo()

    try:
        fatos = repo.obter_fatos_atuais(cliente_id)
    except ClienteNaoEncontrado as erro:
        raise ErroApi(
            CodigoErro.CLIENTE_NAO_ENCONTRADO,
            HTTPStatus.NOT_FOUND,
            f"Sem fatos para o cliente `{cliente_id}`.",
        ) from erro

    evento = EventoSimulado(tipo=tipo, data=datetime.now().astimezone().isoformat())
    anterior = repo.avaliar_fatos(fatos, sessao)
    sessao_com_evento = sessao.model_copy(
        update={"eventos_simulados": [*sessao.eventos_simulados, evento]}
    )
    atual = repo.avaliar_fatos(fatos, sessao_com_evento)
    variacao = comparar_avaliacoes(anterior, atual)

    simulacao = RespostaSimulacao(
        clienteId=cliente_id,
        evento=evento,
        scoreAnterior=anterior.score_calculado,
        scoreAtual=atual.score_calculado,
        deltaScore=variacao.delta_score,
        avaliacao=atual,
        variacao=variacao,
        alertaGerado=_alerta_da_simulacao(cliente, evento, variacao.delta_score),
    )
    return resposta(serializar_agregado(simulacao))


def _periodo_do_corpo() -> str:
    bruto = corpo_da_requisicao().get("periodo", PERIODO_PADRAO)
    if bruto not in PERIODOS_VALIDOS:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            f"`periodo` deve ser um de {', '.join(PERIODOS_VALIDOS)}.",
        )
    return bruto


def _tipo_do_corpo() -> TipoEventoDeRisco:
    bruto = corpo_da_requisicao().get("tipo")
    if not isinstance(bruto, str):
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "`tipo` é obrigatório e deve ser um `TipoEventoDeRisco`.",
        )
    try:
        return TipoEventoDeRisco(bruto)
    except ValueError as erro:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            f"`{bruto}` não é um tipo de evento conhecido.",
        ) from erro


def _alerta_da_simulacao(cliente, evento: EventoSimulado, delta: float) -> Alerta:
    """O alerta que entra na central durante a demonstração ao vivo."""
    rotulo = ROTULO_DO_EVENTO[evento.tipo]
    sinal = "+" if delta > 0 else ""
    return Alerta(
        id=f"alerta-simulado-{cliente.id}-{evento.tipo.value.lower()}",
        clienteId=cliente.id,
        clienteNome=cliente.razao_social,
        data=evento.data[:10],
        severidade=_SEVERIDADE_DO_EVENTO[evento.tipo],
        titulo=f"{rotulo} — evento de monitoramento simulado",
        descricao=(
            f"Evento injetado pelo controle de demonstração e processado pelo motor "
            f"determinístico, que recalculou a avaliação de {cliente.razao_social}."
        ),
        impacto=f"Variação de score: {sinal}{numero(delta, 1)} pontos",
        acaoRecomendada=_ACAO_PADRAO,
        lido=False,
    )
