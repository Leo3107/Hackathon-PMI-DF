"""Injeção de evento simulado nos **fatos** — `00-decisoes.md` D10.

Regra de ouro do produto (D4): a simulação nunca escreve um score. Ela altera
apenas `FatosDoCliente` — o fato bruto — e devolve o objeto mutado para que
`scoring.calcular_risco` **recalcule de verdade**. O delta que aparece na tela
é a diferença entre dois cálculos reais, não um número de demonstração.

Cada tipo de evento tem uma mutação nomeada, documentada e conservadora: mexe
só nos campos que aquele evento mexeria na vida real, com magnitude compatível
com a ordem de grandeza do dataset.
"""

from __future__ import annotations

from models.enums import RiscoZarc, SituacaoRfb, TipoEventoDeRisco
from models.fatos import CovenantRompido, FatosDoCliente, RecuperacaoJudicial

from .sessao import EventoSimulado

__all__ = [
    "TIPOS_SIMULAVEIS",
    "ROTULO_DO_EVENTO",
    "aplicar_evento",
    "aplicar_eventos_simulados",
]

_VALOR_EXECUCAO = 450_000.0
_VALOR_DIVIDA_ATIVA = 380_000.0
_ACRESCIMO_ATRASO_90D = 22.0
_ACRESCIMO_ATRASO_12M = 9.0
_ACRESCIMO_PIOR_ATRASO = 28.0
_QUEDA_PONTUALIDADE = 0.12
_PIORA_PRECIPITACAO = 22.0
_PIORA_QUEBRA_SAFRA = 14.0
_PIORA_PRODUTIVIDADE = 12.0

_ESCALA_ZARC = [RiscoZarc.BAIXO, RiscoZarc.MODERADO, RiscoZarc.ALTO, RiscoZarc.CRITICO]

ROTULO_DO_EVENTO: dict[TipoEventoDeRisco, str] = {
    TipoEventoDeRisco.NOVA_EXECUCAO: "Nova execução de título",
    TipoEventoDeRisco.NOVO_PROTESTO: "Novo protesto em cartório",
    TipoEventoDeRisco.DIVIDA_ATIVA: "Inscrição em dívida ativa da União",
    TipoEventoDeRisco.PEDIDO_RJ: "Pedido de recuperação judicial",
    TipoEventoDeRisco.PEDIDO_FALENCIA: "Pedido de falência",
    TipoEventoDeRisco.EMBARGO_AMBIENTAL: "Embargo do IBAMA",
    TipoEventoDeRisco.ALTERACAO_SOCIETARIA: "Alteração societária relevante",
    TipoEventoDeRisco.COVENANT_ROMPIDO: "Covenant contratual rompido",
    TipoEventoDeRisco.MUDANCA_CLIMATICA: "Deterioração agroclimática",
    TipoEventoDeRisco.ATRASO_PAGAMENTO: "Atraso de pagamento",
    TipoEventoDeRisco.CADASTRAL: "Irregularidade cadastral na Receita Federal",
    TipoEventoDeRisco.RECALCULO: "Recálculo de monitoramento",
}


def _piorar_zarc(atual: RiscoZarc) -> RiscoZarc:
    indice = _ESCALA_ZARC.index(atual)
    return _ESCALA_ZARC[min(indice + 1, len(_ESCALA_ZARC) - 1)]


def _nova_execucao(fatos: FatosDoCliente, data: str) -> None:
    juridico = fatos.juridico
    juridico.execucoes_titulo_12m += 1
    juridico.execucoes_titulo_90d += 1
    juridico.valor_total_em_execucao += _VALOR_EXECUCAO
    juridico.credores_distintos_executando += 1
    juridico.sem_litigio_36m = False


def _novo_protesto(fatos: FatosDoCliente, data: str) -> None:
    juridico = fatos.juridico
    juridico.protestos_ativos += 1
    juridico.protestos_12m += 1
    juridico.credores_protestantes_180d += 1
    juridico.sem_litigio_36m = False


def _divida_ativa(fatos: FatosDoCliente, data: str) -> None:
    fiscal = fatos.fiscal
    fiscal.divida_ativa_pgfn += _VALOR_DIVIDA_ATIVA
    fiscal.todas_certidoes_negativas = False


def _pedido_rj(fatos: FatosDoCliente, data: str) -> None:
    juridico = fatos.juridico
    if juridico.recuperacao_judicial is None:
        juridico.recuperacao_judicial = RecuperacaoJudicial(
            dataDistribuicao=data[:10] or fatos.data_referencia,
            dataDeferimento=None,
        )
    juridico.sem_litigio_36m = False


def _pedido_falencia(fatos: FatosDoCliente, data: str) -> None:
    fatos.juridico.pedido_falencia = True
    fatos.juridico.sem_litigio_36m = False


def _embargo_ambiental(fatos: FatosDoCliente, data: str) -> None:
    ambiental = fatos.ambiental
    ambiental.embargo_ibama_vigente = True
    ambiental.auto_infracao_nao_quitado = True
    #: O caso citado nominalmente no briefing: o embargo recai sobre o imóvel
    #: dado em garantia, o que dispara veto — mas só se houver garantia real.
    if fatos.garantias:
        ambiental.embargo_sobre_imovel_em_garantia = True
        for garantia in fatos.garantias:
            if garantia.bem_embargado is not None:
                garantia.bem_embargado = True


def _alteracao_societaria(fatos: FatosDoCliente, data: str) -> None:
    cadastral = fatos.cadastral
    cadastral.alteracao_societaria_180d = True
    cadastral.saida_socio_majoritario_12m = True
    cadastral.qsa_estavel_5anos = False


def _covenant_rompido(fatos: FatosDoCliente, data: str) -> None:
    interno = fatos.interno
    sequencia = len(interno.covenants_rompidos) + 1
    interno.covenants_rompidos.append(
        CovenantRompido(
            id=f"cov-simulado-{sequencia}",
            descricao="Índice de cobertura de garantia abaixo do mínimo contratual",
            limiteContratual="1,30x",
            valorApurado="1,05x",
            dataDeteccao=data[:10] or fatos.data_referencia,
        )
    )


def _mudanca_climatica(fatos: FatosDoCliente, data: str) -> None:
    agro = fatos.agro
    agro.risco_zarc = _piorar_zarc(agro.risco_zarc)
    agro.desvio_precipitacao_pct -= _PIORA_PRECIPITACAO
    agro.quebra_safra_regional_pct += _PIORA_QUEBRA_SAFRA
    agro.produtividade_vs_media_regional_pct -= _PIORA_PRODUTIVIDADE


def _atraso_pagamento(fatos: FatosDoCliente, data: str) -> None:
    interno = fatos.interno
    interno.atraso_medio_dias_90d += _ACRESCIMO_ATRASO_90D
    interno.atraso_medio_dias_12m += _ACRESCIMO_ATRASO_12M
    interno.pior_atraso_dias_12m += _ACRESCIMO_PIOR_ATRASO
    interno.pct_titulos_pagos_em_dia_12m = max(
        0.0, interno.pct_titulos_pagos_em_dia_12m - _QUEDA_PONTUALIDADE
    )
    interno.sem_atraso_relevante_24m = False


def _cadastral(fatos: FatosDoCliente, data: str) -> None:
    fatos.cadastral.situacao_rfb = SituacaoRfb.SUSPENSA
    fatos.cadastral.cnae_compativel = False


def _recalculo(fatos: FatosDoCliente, data: str) -> None:
    """Varredura de monitoramento sem achado novo: não altera fato algum."""


_MUTACOES = {
    TipoEventoDeRisco.NOVA_EXECUCAO: _nova_execucao,
    TipoEventoDeRisco.NOVO_PROTESTO: _novo_protesto,
    TipoEventoDeRisco.DIVIDA_ATIVA: _divida_ativa,
    TipoEventoDeRisco.PEDIDO_RJ: _pedido_rj,
    TipoEventoDeRisco.PEDIDO_FALENCIA: _pedido_falencia,
    TipoEventoDeRisco.EMBARGO_AMBIENTAL: _embargo_ambiental,
    TipoEventoDeRisco.ALTERACAO_SOCIETARIA: _alteracao_societaria,
    TipoEventoDeRisco.COVENANT_ROMPIDO: _covenant_rompido,
    TipoEventoDeRisco.MUDANCA_CLIMATICA: _mudanca_climatica,
    TipoEventoDeRisco.ATRASO_PAGAMENTO: _atraso_pagamento,
    TipoEventoDeRisco.CADASTRAL: _cadastral,
    TipoEventoDeRisco.RECALCULO: _recalculo,
}

#: Tipos que o controle de demonstração oferece — todos, menos o recálculo neutro.
TIPOS_SIMULAVEIS = tuple(
    tipo for tipo in TipoEventoDeRisco if tipo is not TipoEventoDeRisco.RECALCULO
)


def aplicar_evento(fatos: FatosDoCliente, evento: EventoSimulado) -> FatosDoCliente:
    """Devolve uma **cópia** dos fatos com a mutação do evento aplicada."""
    copia = fatos.model_copy(deep=True)
    _MUTACOES[evento.tipo](copia, evento.data)
    return copia


def aplicar_eventos_simulados(
    fatos: FatosDoCliente, eventos: list[EventoSimulado]
) -> FatosDoCliente:
    """Aplica a fila de eventos na ordem de injeção. Sem eventos, devolve o original."""
    if not eventos:
        return fatos
    atual = fatos
    for evento in eventos:
        atual = aplicar_evento(atual, evento)
    return atual
