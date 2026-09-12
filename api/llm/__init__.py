"""Camada de linguagem natural do Lastro — `specs/04-camada-llm.md`.

Fronteira única entre o motor determinístico e o modelo de linguagem.
A invariante I7 ("o LLM nunca produz, altera ou recalcula um número") é
garantida por três mecanismos, todos neste pacote:

1. `contexto.serializar_contexto` — o modelo só vê números **já formatados**
   em pt-BR; copiar é a única operação possível.
2. `verificador.verificar_fidelidade_numerica` — toda saída do engine OpenAI é
   conferida contra o conjunto de números do contexto; divergência descarta o
   texto e dispara o evento `substituir`.
3. `deterministic_engine.DeterministicNarrativeEngine` — rede de segurança sem
   rede e sem custo, com a mesma estrutura de saída.

Para registrar as rotas no Flask, ver `llm.blueprint` (nome a importar:
``from llm.blueprint import llm_bp``).
"""

from __future__ import annotations

from .engine import (
    EngineId,
    EngineIndisponivel,
    EngineTimeout,
    MensagemCopiloto,
    NarrativeEngine,
    PedacoNarrativa,
    TarefaNarrativa,
    UsoTokens,
    selecionar_engine,
)

__all__ = [
    "EngineId",
    "EngineIndisponivel",
    "EngineTimeout",
    "MensagemCopiloto",
    "NarrativeEngine",
    "PedacoNarrativa",
    "TarefaNarrativa",
    "UsoTokens",
    "selecionar_engine",
]
