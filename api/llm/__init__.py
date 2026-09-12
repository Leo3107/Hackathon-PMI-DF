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

Frase-síntese do pitch: *o modelo de risco decide e calcula; o modelo de
linguagem explica e cita. Nenhum número na tela veio de um LLM.*

**Registro no Flask** (`api/app.py`):

    from llm.blueprint import llm_bp
    app.register_blueprint(llm_bp)

ou `from llm.blueprint import registrar_llm; registrar_llm(app)`, assinatura
`(app: Flask) -> None`.

Mapa de nomes entre a spec e o código (a spec 04 antecede o código):

| Spec | Real |
|---|---|
| `api/motor/` | `api/scoring/` |
| `engine_openai.py` · `engine_deterministico.py` · `engine_fixture.py` | `openai_engine.py` · `deterministic_engine.py` · `fixture_engine.py` |
| `fidelidade.py` | `verificador.py` |
| `custo.py` | `ledger.py` |
| `routes.py` | `blueprint.py` |
| `models.py` | `pedidos.py` |
| `selecao.py` | fundido em `engine.py` |
| `prompts/*.py` | `prompts.py` (arquivo único, gerado da spec) |
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
    diagnosticar_selecao,
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
    "diagnosticar_selecao",
    "selecionar_engine",
]
