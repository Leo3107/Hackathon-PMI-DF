"""Executor: protocolo NDJSON, deadline, degradação e ledger — §2.3 e §2.4.

Uma linha JSON por evento, terminada em `\\n`:

    inicio → delta* → [substituir → delta*] → fim | erro

Garantias do protocolo, cobertas por teste:

- `inicio` é **sempre** o primeiro evento e traz o engine selecionado;
- `fim` **ou** `erro` é sempre o último; nunca há `delta` depois deles;
- erros ocorridos **depois** do início do stream não mudam o status HTTP (já é
  200): viram `substituir` ou `erro` dentro do próprio corpo.

A degradação em voo é o que mantém a tela inteira: falha de rede, timeout,
saída vazia ou violação de fidelidade numérica trocam o texto parcial pelo
parecer determinístico completo, dentro da mesma resposta HTTP. Parecer pela
metade não é aceitável para impressão.
"""

from __future__ import annotations

import json
import os
import time
from typing import Iterable, Iterator
from uuid import uuid4

from . import ledger as _ledger
from .contexto import ContextoNarrativo, estimar_tokens
from .deterministic_engine import DeterministicNarrativeEngine
from .engine import (
    MAX_SAIDA,
    Degradar,
    EngineIndisponivel,
    EngineTimeout,
    MensagemCopiloto,
    NarrativeEngine,
    PedacoNarrativa,
    TarefaNarrativa,
    modelo_de,
    selecionar_engine,
)
from .ledger import preco_entrada, preco_saida
from .prompts import SYSTEM
from .verificador import verificar_fidelidade_numerica

__all__ = [
    "executar_tarefa",
    "executar_resposta_imediata",
    "estimar_custo",
    "linha",
    "TIMEOUT_PADRAO_MS",
    "MIN_RESTANTE_PARA_RETRY_S",
]

TIMEOUT_PADRAO_MS = 25_000
#: Só vale tentar de novo se sobrar tempo para a segunda tentativa terminar.
MIN_RESTANTE_PARA_RETRY_S = 10.0

_POR_MILHAO = 1_000_000
_MOLDURA_TOKENS = 200
_MS_POR_S = 1000


def linha(evento: dict) -> str:
    """Um evento NDJSON. `ensure_ascii=False` preserva o pt-BR sem inflar bytes."""
    return json.dumps(evento, ensure_ascii=False) + "\n"


def estimar_custo(tarefa: TarefaNarrativa, contexto: ContextoNarrativo) -> float:
    """Custo máximo da chamada, reservado antes de falar com o provedor (§5.2)."""
    entrada = (
        estimar_tokens(SYSTEM[tarefa]) + estimar_tokens(contexto.bloco) + _MOLDURA_TOKENS
    )
    saida = MAX_SAIDA[tarefa]
    return (entrada * preco_entrada() + saida * preco_saida()) / _POR_MILHAO


def _deadline() -> float:
    bruto = os.environ.get("LASTRO_LLM_TIMEOUT_MS", str(TIMEOUT_PADRAO_MS)).strip()
    try:
        milissegundos = int(bruto)
    except ValueError:  # pragma: no cover - configuração malformada
        milissegundos = TIMEOUT_PADRAO_MS
    return time.monotonic() + milissegundos / _MS_POR_S


def _iterar(
    engine: NarrativeEngine,
    tarefa: TarefaNarrativa,
    contexto: ContextoNarrativo,
    pergunta: str | None,
    historico: list[MensagemCopiloto] | None,
    deadline: float,
) -> Iterator[PedacoNarrativa]:
    if tarefa == "copiloto":
        return engine.responder(contexto, pergunta or "", historico or [], deadline)
    return engine.gerar(tarefa, contexto, deadline)


def _iterar_com_retry(
    engine: NarrativeEngine,
    tarefa: TarefaNarrativa,
    contexto: ContextoNarrativo,
    pergunta: str | None,
    historico: list[MensagemCopiloto] | None,
    deadline: float,
) -> Iterator[PedacoNarrativa]:
    """Exatamente **uma** nova tentativa, e só se nada foi emitido (§2.4)."""
    tentou_de_novo = False
    while True:
        emitiu = False
        try:
            for pedaco in _iterar(engine, tarefa, contexto, pergunta, historico, deadline):
                emitiu = emitiu or pedaco.tipo == "texto"
                yield pedaco
            return
        except EngineIndisponivel as erro:
            _ledger.LEDGER.registrar_falha_rede()
            restante = deadline - time.monotonic()
            pode_repetir = (
                not tentou_de_novo
                and not emitiu
                and erro.recuperavel
                and restante > MIN_RESTANTE_PARA_RETRY_S
            )
            if not pode_repetir:
                raise
            tentou_de_novo = True


def _motivo_da_excecao(erro: BaseException) -> str:
    if isinstance(erro, Degradar):
        return erro.codigo
    if isinstance(erro, EngineTimeout):
        return "TIMEOUT"
    return "FALHA_REDE"


def executar_tarefa(
    tarefa: TarefaNarrativa,
    contexto: ContextoNarrativo,
    *,
    pergunta: str | None = None,
    historico: list[MensagemCopiloto] | None = None,
    extras_do_verificador: Iterable[str] = (),
) -> Iterator[str]:
    """Gera o stream NDJSON de uma tarefa. Cada `yield` é uma linha completa."""
    inicio = time.monotonic()
    deadline = _deadline()
    ledger = _ledger.LEDGER
    custo_previsto = estimar_custo(tarefa, contexto)
    engine, motivo = selecionar_engine(ledger, custo_previsto)
    reserva = ledger.reservar(custo_previsto) if engine.id == "openai" else None
    requisicao_id = uuid4().hex

    yield linha(
        {
            "t": "inicio",
            "tarefa": tarefa,
            "origem": engine.id,
            "modelo": modelo_de(engine),
            "requisicaoId": requisicao_id,
            "clienteId": contexto.cliente_id,
        }
    )

    acumulado: list[str] = []
    uso = None
    origem_final = engine.id
    incidente: dict | None = None
    erro_interno: Exception | None = None

    try:
        for pedaco in _iterar_com_retry(
            engine, tarefa, contexto, pergunta, historico, deadline
        ):
            if pedaco.tipo == "texto" and pedaco.texto:
                acumulado.append(pedaco.texto)
                yield linha({"t": "delta", "d": pedaco.texto})
            elif pedaco.tipo == "uso":
                uso = pedaco.uso
        if engine.id == "openai":
            texto = "".join(acumulado)
            if not texto.strip():
                raise Degradar("SAIDA_VAZIA")
            violacoes = verificar_fidelidade_numerica(
                texto, contexto, extras=extras_do_verificador
            )
            if violacoes:
                incidente = ledger.registrar_incidente(
                    requisicao_id, "FIDELIDADE_NUMERICA", violacoes, severidade="MAXIMA"
                )
                raise Degradar("FIDELIDADE_NUMERICA", violacoes)
    except (EngineTimeout, EngineIndisponivel, Degradar) as erro:
        motivo = _motivo_da_excecao(erro)
        yield linha({"t": "substituir", "motivo": motivo})
        origem_final = "deterministico"
        try:
            for pedaco in _iterar(
                DeterministicNarrativeEngine(motivo),
                tarefa,
                contexto,
                pergunta,
                historico,
                float("inf"),
            ):
                if pedaco.tipo == "texto" and pedaco.texto:
                    yield linha({"t": "delta", "d": pedaco.texto})
        except Exception as falha:  # noqa: BLE001 — cenário de bug, coberto por teste
            erro_interno = falha

    registro = ledger.fechar(
        reserva,
        requisicao_id,
        tarefa,
        contexto.cliente_id,
        engine.id,
        origem_final,
        uso,
        motivo,
        time.monotonic() - inicio,
        modelo=modelo_de(engine),
        incidente=incidente,
    )

    if erro_interno is not None:
        yield linha(
            {"t": "erro", "codigo": "FALHA_INTERNA", "mensagem": str(erro_interno)}
        )
        return

    yield linha(
        {
            "t": "fim",
            "origem": origem_final,
            "motivoDegradacao": motivo,
            "uso": registro.uso_json(),
            "acumulado": ledger.resumo_curto(),
            "duracaoMs": registro.duracao_ms,
        }
    )


def executar_resposta_imediata(
    tarefa: TarefaNarrativa,
    contexto: ContextoNarrativo,
    texto: str,
    motivo: str = "PRE_FILTRO",
) -> Iterator[str]:
    """Recusa do pré-filtro (§8) no mesmo protocolo, sem chamar engine nenhum."""
    inicio = time.monotonic()
    requisicao_id = uuid4().hex
    yield linha(
        {
            "t": "inicio",
            "tarefa": tarefa,
            "origem": "deterministico",
            "modelo": None,
            "requisicaoId": requisicao_id,
            "clienteId": contexto.cliente_id,
        }
    )
    yield linha({"t": "delta", "d": texto})
    registro = _ledger.LEDGER.fechar(
        None,
        requisicao_id,
        tarefa,
        contexto.cliente_id,
        "deterministico",
        "deterministico",
        None,
        motivo,
        time.monotonic() - inicio,
    )
    yield linha(
        {
            "t": "fim",
            "origem": "deterministico",
            "motivoDegradacao": motivo,
            "uso": registro.uso_json(),
            "acumulado": _ledger.LEDGER.resumo_curto(),
            "duracaoMs": registro.duracao_ms,
        }
    )
