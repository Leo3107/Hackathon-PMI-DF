"""Engine OpenAI **sem tocar a rede** — `04-camada-llm.md` §1.3 e §6.3.

Todo teste aqui injeta um `FakeOpenAI`. A sentinela do `conftest` garante que,
mesmo por engano, ninguém instancie `openai.OpenAI` de verdade: o teste falha
com `AssertionError` em vez de gastar cota.
"""

from __future__ import annotations

import time

import pytest
from llm.engine import EngineIndisponivel, EngineTimeout
from llm.openai_engine import OpenAINarrativeEngine
from llm.prompts import SYSTEM_PARECER

from apoio import (
    MENSAGEM_DA_SENTINELA,
    ErroHttp,
    FakeOpenAI,
    StreamFalso,
    chunk_de_texto,
    chunk_de_uso,
)


def textos(pedacos):
    return "".join(p.texto for p in pedacos if p.tipo == "texto")


def uso(pedacos):
    return next(p.uso for p in pedacos if p.tipo == "uso")


# ---------------------------------------------------------------------------
# A sentinela
# ---------------------------------------------------------------------------


def test_instanciar_o_cliente_real_falha_o_teste(monkeypatch):
    """Prova de que nenhum teste desta suíte consegue gastar cota."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-nao-usar")
    with pytest.raises(AssertionError, match=MENSAGEM_DA_SENTINELA):
        OpenAINarrativeEngine()


def test_sem_chave_o_engine_recusa_antes_de_qualquer_socket():
    with pytest.raises(EngineIndisponivel):
        OpenAINarrativeEngine()


# ---------------------------------------------------------------------------
# Parâmetros da chamada
# ---------------------------------------------------------------------------


def test_envia_max_completion_tokens_e_nunca_max_tokens(contexto_moderado):
    """`max_tokens` é rejeitado por esta família — 400 em toda chamada."""
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    engine = OpenAINarrativeEngine(client=cliente)
    list(engine.gerar("parecer", contexto_moderado, float("inf")))

    enviado = cliente.chamadas[0]
    assert enviado["max_completion_tokens"] == 1400
    assert "max_tokens" not in enviado


def test_nao_envia_temperature_nem_top_p(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    list(OpenAINarrativeEngine(client=cliente).gerar("score", contexto_moderado, float("inf")))
    assert set(cliente.chamadas[0]) == {
        "model",
        "messages",
        "stream",
        "stream_options",
        "max_completion_tokens",
    }


def test_pede_o_usage_no_stream(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    list(OpenAINarrativeEngine(client=cliente).gerar("score", contexto_moderado, float("inf")))
    assert cliente.chamadas[0]["stream"] is True
    assert cliente.chamadas[0]["stream_options"] == {"include_usage": True}


def test_monta_system_e_user_com_o_bloco_do_contexto(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    list(OpenAINarrativeEngine(client=cliente).gerar("parecer", contexto_moderado, float("inf")))
    mensagens = cliente.chamadas[0]["messages"]
    assert mensagens[0]["role"] == "system"
    assert mensagens[0]["content"] == SYSTEM_PARECER
    assert contexto_moderado.bloco in mensagens[1]["content"]
    assert "<<<CONTEXTO>>>" in mensagens[1]["content"]


def test_copiloto_nomeia_o_cliente_no_system(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    list(
        OpenAINarrativeEngine(client=cliente).responder(
            contexto_moderado, "Qual o score?", [], float("inf")
        )
    )
    system = cliente.chamadas[0]["messages"][0]["content"]
    assert contexto_moderado.razao_social in system
    assert "{{RAZAO_SOCIAL}}" not in system


def test_modelo_vem_do_ambiente(contexto_moderado, monkeypatch):
    monkeypatch.setenv("LASTRO_LLM_MODEL", "modelo-de-teste")
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    engine = OpenAINarrativeEngine(client=cliente)
    list(engine.gerar("score", contexto_moderado, float("inf")))
    assert engine.modelo == "modelo-de-teste"
    assert cliente.chamadas[0]["model"] == "modelo-de-teste"


# ---------------------------------------------------------------------------
# Leitura do stream
# ---------------------------------------------------------------------------


def test_concatena_os_deltas_e_le_o_usage_do_ultimo_chunk(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["## Resumo", " executivo"], entrada=604, saida=863)
    pedacos = list(
        OpenAINarrativeEngine(client=cliente).gerar("parecer", contexto_moderado, float("inf"))
    )
    assert textos(pedacos) == "## Resumo executivo"
    assert pedacos[-1].tipo == "uso"
    assert uso(pedacos).entrada == 604
    assert uso(pedacos).saida == 863
    assert uso(pedacos).raciocinio == 0
    assert uso(pedacos).estimado is False


def test_chunk_sem_conteudo_nao_vira_pedaco(contexto_moderado):
    chunks = [chunk_de_texto(None), chunk_de_texto("a"), chunk_de_uso(1, 1)]
    cliente = FakeOpenAI([StreamFalso(chunks)])
    pedacos = list(
        OpenAINarrativeEngine(client=cliente).gerar("score", contexto_moderado, float("inf"))
    )
    assert textos(pedacos) == "a"


def test_stream_sem_usage_produz_estimativa_marcada(contexto_moderado):
    cliente = FakeOpenAI([StreamFalso([chunk_de_texto("texto")])])
    pedacos = list(
        OpenAINarrativeEngine(client=cliente).gerar("score", contexto_moderado, float("inf"))
    )
    assert uso(pedacos).estimado is True
    assert uso(pedacos).entrada > 0


def test_o_stream_e_sempre_fechado(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["ok"])
    list(OpenAINarrativeEngine(client=cliente).gerar("score", contexto_moderado, float("inf")))
    assert cliente.streams[0].fechado is True


def test_o_stream_e_fechado_mesmo_com_erro(contexto_moderado):
    cliente = FakeOpenAI([StreamFalso([chunk_de_texto("a")], erro_no_meio=ErroHttp(500), apos=1)])
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineIndisponivel):
        list(engine.gerar("score", contexto_moderado, float("inf")))
    assert cliente.streams[0].fechado is True


# ---------------------------------------------------------------------------
# Deadline e falhas
# ---------------------------------------------------------------------------


def test_deadline_ultrapassado_interrompe_no_proximo_chunk(contexto_moderado):
    cliente = FakeOpenAI.a_partir_de_texto(["a", "b", "c"])
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineTimeout):
        list(engine.gerar("parecer", contexto_moderado, time.monotonic() - 1))


@pytest.mark.parametrize(("codigo", "recuperavel"), [(429, True), (503, True), (400, False)])
def test_erro_http_vira_engine_indisponivel_com_recuperabilidade(
    contexto_moderado, codigo, recuperavel
):
    cliente = FakeOpenAI([], erro_ao_criar=ErroHttp(codigo))
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineIndisponivel) as capturado:
        list(engine.gerar("score", contexto_moderado, float("inf")))
    assert capturado.value.recuperavel is recuperavel


def test_erro_de_conexao_sem_status_e_tratado_como_recuperavel(contexto_moderado):
    cliente = FakeOpenAI([], erro_ao_criar=ConnectionError("sem rota para o host"))
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineIndisponivel) as capturado:
        list(engine.gerar("score", contexto_moderado, float("inf")))
    assert capturado.value.recuperavel is True


def test_stream_que_morre_no_meio_vira_engine_indisponivel(contexto_moderado):
    cliente = FakeOpenAI(
        [StreamFalso([chunk_de_texto("come"), chunk_de_texto("ço")], erro_no_meio=ErroHttp(502), apos=1)]
    )
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineIndisponivel):
        list(engine.gerar("parecer", contexto_moderado, float("inf")))


def test_nenhuma_outra_excecao_escapa_do_engine(contexto_moderado):
    """Contrato da §1.2: só `EngineIndisponivel` e `EngineTimeout` saem daqui."""
    cliente = FakeOpenAI([], erro_ao_criar=ValueError("erro interno do SDK"))
    engine = OpenAINarrativeEngine(client=cliente)
    with pytest.raises(EngineIndisponivel):
        list(engine.gerar("score", contexto_moderado, float("inf")))
