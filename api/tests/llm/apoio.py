"""Auxiliares da suíte da camada de linguagem — `04-camada-llm.md` §6.3.

Vive fora do `conftest.py` e com nome próprio por um motivo prático: este
diretório entra no `sys.path` do pytest, e um pacote chamado `llm` aqui
sombrearia o pacote real `api/llm`. `apoio` não colide com nada.

Contém o construtor de contexto usado por todos os testes, o `Cliente` mínimo
(o pacote `api/data/` pertence a outro workstream) e o **duplo do SDK da
OpenAI**, que reproduz o formato dos chunks sem abrir um socket.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from llm.contexto import serializar_contexto
from llm.fixture_engine import RAIZ_DAS_FIXTURES
from models.cliente import Cliente
from scoring import calcular_risco
from tests import fixtures as perfis

__all__ = [
    "MENSAGEM_DA_SENTINELA",
    "CLIENTE_DA_FIXTURE",
    "RAIZ_DAS_FIXTURES",
    "montar_cliente",
    "contexto_de",
    "nomes_dos_perfis",
    "carregar_fixtures_gravadas",
    "ler_apoio",
    "chunk_de_texto",
    "chunk_de_uso",
    "StreamFalso",
    "FakeOpenAI",
    "ErroHttp",
]

MENSAGEM_DA_SENTINELA = (
    "Teste tentou instanciar openai.OpenAI — chamadas reais são proibidas em testes"
)

#: Id que casa com as fixtures gravadas em `tests/fixtures/llm/`.
CLIENTE_DA_FIXTURE = "vale-do-araguaia"


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------


def montar_cliente(cliente_id: str, **sobrescritas) -> Cliente:
    """Um `Cliente` mínimo e coerente, independente de `api/data/`."""
    campos = {
        "id": cliente_id,
        "razaoSocial": "Agropecuária Vale do Araguaia Ltda",
        "documento": "12.345.678/0001-95",
        "tipoPessoa": "PJ",
        "municipio": "Barra do Garças",
        "uf": "MT",
        "atividade": "Produtor rural — grãos",
        "cnaePrincipal": "0115-6/00",
        "culturas": ["Soja", "Milho safrinha"],
        "inicioRelacionamento": "2020-03-10",
        "estado": "EM_OBSERVACAO",
    }
    campos.update(sobrescritas)
    return Cliente(**campos)


def nomes_dos_perfis() -> list[str]:
    return [nome for nome, _ in perfis.todos_os_perfis()]


def contexto_de(
    nome_do_perfil: str, tarefa: str = "parecer", cliente_id: str | None = None
):
    """Persona de `tests/fixtures.py` → `calcular_risco` → `ContextoNarrativo`."""
    fatos = dict(perfis.todos_os_perfis())[nome_do_perfil]
    if cliente_id:
        fatos = fatos.model_copy(update={"cliente_id": cliente_id})
    avaliacao = calcular_risco(fatos)
    return serializar_contexto(
        montar_cliente(fatos.cliente_id), fatos, avaliacao, None, tarefa
    )


def ler_apoio(caminho_relativo: str) -> str:
    return (RAIZ_DAS_FIXTURES / caminho_relativo).read_text(encoding="utf-8")


def carregar_fixtures_gravadas() -> list[tuple[str, dict]]:
    arquivos = sorted(Path(RAIZ_DAS_FIXTURES).glob("*/*.json"))
    return [
        (
            f"{caminho.parent.name}/{caminho.stem}",
            json.loads(caminho.read_text(encoding="utf-8")),
        )
        for caminho in arquivos
    ]


# ---------------------------------------------------------------------------
# Duplo do SDK — nunca abre socket
# ---------------------------------------------------------------------------


def chunk_de_texto(texto: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=texto))], usage=None
    )


def chunk_de_uso(entrada: int, saida: int, raciocinio: int = 0) -> SimpleNamespace:
    """Último chunk do stream: `choices` vazio e `usage` preenchido."""
    return SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(
            prompt_tokens=entrada,
            completion_tokens=saida,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=raciocinio),
        ),
    )


class StreamFalso:
    """Iterável com `close()`, como o `Stream` do SDK. Pode morrer no meio."""

    def __init__(self, chunks, erro_no_meio=None, apos=0):
        self._chunks = list(chunks)
        self._erro = erro_no_meio
        self._apos = apos
        self.fechado = False

    def __iter__(self):
        for indice, chunk in enumerate(self._chunks):
            if self._erro is not None and indice == self._apos:
                raise self._erro
            yield chunk
        if self._erro is not None and self._apos >= len(self._chunks):
            raise self._erro

    def close(self):
        self.fechado = True


class FakeOpenAI:
    """Duplo de `openai.OpenAI` com `.chat.completions.create(**kwargs)`."""

    def __init__(self, respostas, erro_ao_criar=None):
        self._respostas = list(respostas)
        self._erro_ao_criar = erro_ao_criar
        self.chamadas: list[dict] = []
        self.streams: list[StreamFalso] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        if self._erro_ao_criar is not None:
            raise self._erro_ao_criar
        stream = self._respostas[min(len(self.chamadas) - 1, len(self._respostas) - 1)]
        self.streams.append(stream)
        return stream

    @classmethod
    def a_partir_de_texto(cls, pedacos, entrada: int = 100, saida: int = 50):
        chunks = [chunk_de_texto(p) for p in pedacos] + [chunk_de_uso(entrada, saida)]
        return cls([StreamFalso(chunks)])


class ErroHttp(Exception):
    """Erro do provedor com `status_code`, como os que o SDK levanta."""

    def __init__(self, status_code: int, mensagem: str = "falha do provedor"):
        super().__init__(mensagem)
        self.status_code = status_code
