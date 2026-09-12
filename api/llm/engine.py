"""Contrato `NarrativeEngine` e seleção de engine — `specs/04-camada-llm.md` §1.2 e §1.4.

Flask é WSGI síncrono; os engines são **geradores síncronos**. Cada pedaço é um
`PedacoNarrativa`. Contrato: zero ou mais pedaços `tipo="texto"` e **exatamente
um** pedaço `tipo="uso"` por último. Só duas exceções podem escapar de um
engine — `EngineIndisponivel` e `EngineTimeout`; qualquer outra é embrulhada em
`EngineIndisponivel` pelo executor.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterator, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # pragma: no cover - só para o type checker
    from .contexto import ContextoNarrativo
    from .ledger import Ledger

__all__ = [
    "TarefaNarrativa",
    "EngineId",
    "MotivoDegradacao",
    "UsoTokens",
    "PedacoNarrativa",
    "MensagemCopiloto",
    "NarrativeEngine",
    "EngineIndisponivel",
    "EngineTimeout",
    "Degradar",
    "MAX_SAIDA",
    "ALVO_EXTENSAO",
    "LIMITE_PERGUNTA",
    "LIMITE_HISTORICO",
    "selecionar_engine",
    "diagnosticar_selecao",
    "modelo_de",
]

TarefaNarrativa = Literal["parecer", "score", "recomendacao", "copiloto"]
EngineId = Literal["openai", "deterministico", "fixture"]
MotivoDegradacao = Literal[
    "FORCADO_POR_ENV",
    "LLM_DESLIGADO",
    "SEM_CHAVE",
    "DISJUNTOR",
    "ORCAMENTO",
    "TIMEOUT",
    "FALHA_REDE",
    "FIDELIDADE_NUMERICA",
    "SAIDA_VAZIA",
]

#: Limite de `max_completion_tokens` por tarefa (§1.3). Folga de ~30% sobre o
#: alvo de extensão porque tokens de raciocínio consomem o mesmo limite.
MAX_SAIDA: dict[str, int] = {
    "parecer": 1400,
    "score": 350,
    "recomendacao": 450,
    "copiloto": 400,
}

#: Faixa de extensão pedida em cada prompt, em palavras (§3). Usada pelos
#: testes do engine determinístico e pelo script de avaliação.
ALVO_EXTENSAO: dict[str, tuple[int, int]] = {
    "parecer": (350, 550),
    "score": (80, 140),
    "recomendacao": (100, 180),
    "copiloto": (1, 150),
}

#: Pergunta do copiloto: máximo de caracteres aceitos pelo endpoint (§2.1).
LIMITE_PERGUNTA = 600
#: Histórico do copiloto: máximo de mensagens mantidas (§2.1).
LIMITE_HISTORICO = 6

#: Modelo padrão (D5). Sobrescrito por `LASTRO_LLM_MODEL`.
MODELO_PADRAO = "gpt-5.4-mini"


class UsoTokens(BaseModel):
    entrada: int = 0
    saida: int = 0
    raciocinio: int = 0
    #: True quando o stream foi abortado antes do chunk de `usage`.
    estimado: bool = False


class PedacoNarrativa(BaseModel):
    tipo: Literal["texto", "uso"]
    texto: str | None = None
    uso: UsoTokens | None = None


class MensagemCopiloto(BaseModel):
    papel: Literal["analista", "copiloto"]
    #: máx. 600 caracteres — o servidor trunca antes de montar o prompt.
    texto: str = Field(default="")


@runtime_checkable
class NarrativeEngine(Protocol):
    """Interface das três implementações (§1.3)."""

    id: EngineId

    def gerar(
        self,
        tarefa: Literal["parecer", "score", "recomendacao"],
        contexto: "ContextoNarrativo",
        deadline: float,
    ) -> Iterator[PedacoNarrativa]:  # pragma: no cover - Protocol
        ...

    def responder(
        self,
        contexto: "ContextoNarrativo",
        pergunta: str,
        historico: list[MensagemCopiloto],
        deadline: float,
    ) -> Iterator[PedacoNarrativa]:  # pragma: no cover - Protocol
        ...


class EngineIndisponivel(RuntimeError):
    """Rede, 5xx, 429 persistente, chave ausente ou qualquer falha do provedor."""

    codigo = "FALHA_REDE"

    def __init__(self, mensagem: str = "engine indisponível", *, recuperavel: bool = True):
        super().__init__(mensagem)
        #: True quando vale uma segunda tentativa (429, 5xx, erro de conexão).
        self.recuperavel = recuperavel


class EngineTimeout(TimeoutError):
    """Deadline da requisição ultrapassado durante a geração."""

    codigo = "TIMEOUT"


class Degradar(Exception):
    """Decisão do executor de descartar a saída do LLM e usar o determinístico."""

    def __init__(self, codigo: str, detalhe: list[str] | None = None):
        super().__init__(codigo)
        self.codigo = codigo
        self.detalhe = detalhe or []


def modelo_de(engine: object) -> str | None:
    """Modelo usado pelo engine, quando existir — vai no evento `inicio`."""
    return getattr(engine, "modelo", None)


def diagnosticar_selecao(
    ledger: "Ledger | None" = None,
    custo_previsto_usd: float = 0.0,
) -> tuple[EngineId, str | None]:
    """A decisão da §1.4 **sem instanciar nada** — ordem normativa.

    Variável de força → kill switch → presença de chave → disjuntor →
    orçamento. `GET /api/llm/custo` usa esta forma para relatar o estado sem
    abrir cliente HTTP nenhum.
    """
    forcado = os.environ.get("LASTRO_LLM_ENGINE", "").strip().lower()
    if forcado == "fixture":
        return "fixture", None
    if forcado == "deterministico":
        return "deterministico", "FORCADO_POR_ENV"
    if forcado == "openai":
        return "openai", None
    if os.environ.get("LASTRO_LLM_ENABLED", "true").strip().lower() != "true":
        return "deterministico", "LLM_DESLIGADO"
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        return "deterministico", "SEM_CHAVE"
    if ledger is not None and ledger.disjuntor_aberto():
        return "deterministico", "DISJUNTOR"
    if ledger is not None and not ledger.cabe_no_orcamento(custo_previsto_usd):
        return "deterministico", "ORCAMENTO"
    return "openai", None


def selecionar_engine(
    ledger: "Ledger | None" = None,
    custo_previsto_usd: float = 0.0,
) -> tuple[NarrativeEngine, str | None]:
    """Escolhe o engine. Devolve `(engine, motivo_degradacao)`.

    `motivo` é `None` apenas quando o engine escolhido é o OpenAI (ou o de
    fixture, que é modo de teste explícito). Se abrir o cliente da OpenAI
    falhar — chave inválida, SDK ausente —, cai no determinístico com
    `SEM_CHAVE` em vez de derrubar a requisição.
    """
    from .deterministic_engine import DeterministicNarrativeEngine
    from .fixture_engine import FixtureNarrativeEngine
    from .openai_engine import OpenAINarrativeEngine

    escolhido, motivo = diagnosticar_selecao(ledger, custo_previsto_usd)
    if escolhido == "fixture":
        return FixtureNarrativeEngine(), motivo
    if escolhido == "deterministico":
        return DeterministicNarrativeEngine(motivo), motivo
    try:
        return OpenAINarrativeEngine(), motivo
    except EngineIndisponivel:
        return DeterministicNarrativeEngine("SEM_CHAVE"), "SEM_CHAVE"
