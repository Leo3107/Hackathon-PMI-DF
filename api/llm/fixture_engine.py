"""Engine de fixture — respostas gravadas, zero rede. `04-camada-llm.md` §6.

Usado por `pytest` e pelo E2E do Playwright. É o que permite exercitar o
protocolo de streaming inteiro, com o texto chegando em pedaços, sem gastar um
centavo do orçamento.

`chunks` preserva a fragmentação real do stream gravado; na falta dele, o texto
é fatiado em pedaços de tamanho fixo, o que basta para provar o crescimento
incremental na interface.

Fixture ausente:

- `LASTRO_LLM_FIXTURE_FALTANTE=erro` (padrão em pytest) → `FixtureAusente`, com
  o comando de gravação na mensagem;
- `LASTRO_LLM_FIXTURE_FALTANTE=deterministico` (padrão no E2E) → cai no
  template determinístico e a tela continua inteira.

Nota de nomenclatura: a spec chama este módulo `engine_fixture.py`.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Iterator, Literal

from .contexto import ContextoNarrativo
from .deterministic_engine import DeterministicNarrativeEngine
from .engine import MensagemCopiloto, PedacoNarrativa, UsoTokens

__all__ = [
    "FixtureNarrativeEngine",
    "FixtureAusente",
    "RAIZ_DAS_FIXTURES",
    "TAMANHO_DO_PEDACO",
    "gerar_slug",
    "caminho_da_fixture",
    "carregar_fixture",
]

#: `api/tests/fixtures/llm/`.
RAIZ_DAS_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "llm"

TAMANHO_DO_PEDACO = 48
_VERSAO = 1
_COMANDO = (
    "python -m llm.scripts.gravar_fixtures --clientes {cliente} --tarefas {tarefa}"
)
_RE_NAO_SLUG = re.compile(r"[^a-z0-9]+")


class FixtureAusente(FileNotFoundError):
    """Não há resposta gravada para esta tarefa/cliente/pergunta."""


def gerar_slug(texto: str) -> str:
    """`Por que o score caiu?` → `por-que-o-score-caiu`. Sem acento, sem caixa."""
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(caractere)
    )
    return _RE_NAO_SLUG.sub("-", sem_acento).strip("-")


def caminho_da_fixture(
    tarefa: str, cliente_id: str, pergunta: str | None = None, raiz: Path | None = None
) -> Path:
    base = raiz or RAIZ_DAS_FIXTURES
    if tarefa != "copiloto":
        return base / tarefa / f"{cliente_id}.json"
    return base / "copiloto" / f"{cliente_id}--{gerar_slug(pergunta or '')}.json"


def carregar_fixture(caminho: Path) -> dict:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if dados.get("versao") != _VERSAO:
        raise FixtureAusente(f"versão inesperada em {caminho}: {dados.get('versao')}")
    return dados


class FixtureNarrativeEngine:
    """`NarrativeEngine` que reproduz uma resposta gravada, pedaço a pedaço."""

    id = "fixture"

    def __init__(self, raiz: Path | None = None, modelo: str | None = None) -> None:
        self._raiz = raiz or RAIZ_DAS_FIXTURES
        self.modelo = modelo

    def gerar(
        self,
        tarefa: Literal["parecer", "score", "recomendacao"],
        contexto: ContextoNarrativo,
        deadline: float = float("inf"),
    ) -> Iterator[PedacoNarrativa]:
        yield from self._reproduzir(tarefa, contexto, None)

    def responder(
        self,
        contexto: ContextoNarrativo,
        pergunta: str,
        historico: list[MensagemCopiloto] | None = None,
        deadline: float = float("inf"),
    ) -> Iterator[PedacoNarrativa]:
        yield from self._reproduzir("copiloto", contexto, pergunta)

    # -- Interno -------------------------------------------------------------

    def _reproduzir(
        self, tarefa: str, contexto: ContextoNarrativo, pergunta: str | None
    ) -> Iterator[PedacoNarrativa]:
        caminho = caminho_da_fixture(tarefa, contexto.cliente_id, pergunta, self._raiz)
        if not caminho.exists():
            yield from self._sem_fixture(tarefa, contexto, pergunta, caminho)
            return
        dados = carregar_fixture(caminho)
        self.modelo = dados.get("modelo")
        for pedaco in self._pedacos(dados):
            yield PedacoNarrativa(tipo="texto", texto=pedaco)
        uso = dados.get("uso") or {}
        yield PedacoNarrativa(
            tipo="uso",
            uso=UsoTokens(
                entrada=int(uso.get("entrada", 0)),
                saida=int(uso.get("saida", 0)),
                raciocinio=int(uso.get("raciocinio", 0)),
            ),
        )

    @staticmethod
    def _pedacos(dados: dict) -> list[str]:
        gravados = dados.get("chunks")
        if gravados:
            return list(gravados)
        saida = dados.get("saida", "")
        return [
            saida[inicio : inicio + TAMANHO_DO_PEDACO]
            for inicio in range(0, len(saida), TAMANHO_DO_PEDACO)
        ]

    def _sem_fixture(
        self,
        tarefa: str,
        contexto: ContextoNarrativo,
        pergunta: str | None,
        caminho: Path,
    ) -> Iterator[PedacoNarrativa]:
        politica = os.environ.get("LASTRO_LLM_FIXTURE_FALTANTE", "erro").strip().lower()
        if politica != "deterministico":
            raise FixtureAusente(
                f"fixture ausente: {caminho}. Grave com: "
                + _COMANDO.format(cliente=contexto.cliente_id, tarefa=tarefa)
            )
        fallback = DeterministicNarrativeEngine()
        if tarefa == "copiloto":
            yield from fallback.responder(contexto, pergunta or "")
        else:
            yield from fallback.gerar(tarefa, contexto)  # type: ignore[arg-type]
