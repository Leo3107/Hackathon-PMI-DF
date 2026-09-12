"""Protocolo NDJSON, deadline e degradação em voo — `04-camada-llm.md` §2.3/§2.4.

O que se prova: a tela nunca fica com um parecer pela metade, e um número
inventado pelo modelo **não atravessa** — vira `substituir` + incidente de
severidade máxima no ledger.
"""

from __future__ import annotations

import json

import pytest
from llm import executor as modulo_executor
from llm import ledger as _ledger
from llm.engine import EngineIndisponivel, EngineTimeout, PedacoNarrativa, UsoTokens
from llm.executor import estimar_custo, executar_resposta_imediata, executar_tarefa


class EngineDeTeste:
    """Duplo de engine que emite pedaços programados e pode falhar no meio."""

    def __init__(self, textos, erro=None, apos=0, uso=None, engine_id="openai"):
        self.id = engine_id
        self.modelo = "gpt-5.4-mini" if engine_id == "openai" else None
        self._textos = list(textos)
        self._erro = erro
        self._apos = apos
        self._uso = uso or UsoTokens(entrada=100, saida=50)
        self.tentativas = 0

    def _emitir(self):
        self.tentativas += 1
        for indice, texto in enumerate(self._textos):
            if self._erro is not None and indice == self._apos:
                raise self._erro
            yield PedacoNarrativa(tipo="texto", texto=texto)
        if self._erro is not None and self._apos >= len(self._textos):
            raise self._erro
        yield PedacoNarrativa(tipo="uso", uso=self._uso)

    def gerar(self, tarefa, contexto, deadline):
        return self._emitir()

    def responder(self, contexto, pergunta, historico, deadline):
        return self._emitir()


@pytest.fixture
def fixar_engine(monkeypatch):
    def _fixar(engine, motivo=None):
        monkeypatch.setattr(
            modulo_executor, "selecionar_engine", lambda *_a, **_k: (engine, motivo)
        )
        return engine

    return _fixar


def eventos(stream) -> list[dict]:
    linhas = list(stream)
    assert all(linha.endswith("\n") for linha in linhas)
    return [json.loads(linha) for linha in linhas]


def texto_de(lista: list[dict]) -> str:
    return "".join(e["d"] for e in lista if e["t"] == "delta")


# ---------------------------------------------------------------------------
# Ordem dos eventos
# ---------------------------------------------------------------------------


def test_caminho_feliz_e_inicio_deltas_fim(contexto_moderado, fixar_engine):
    engine = fixar_engine(EngineDeTeste(["## Resumo", " executivo"]))
    lista = eventos(executar_tarefa("parecer", contexto_moderado))

    assert [e["t"] for e in lista] == ["inicio", "delta", "delta", "fim"]
    assert lista[0]["origem"] == "openai"
    assert lista[0]["modelo"] == "gpt-5.4-mini"
    assert lista[0]["clienteId"] == contexto_moderado.cliente_id
    assert lista[0]["requisicaoId"]
    assert lista[-1]["origem"] == "openai"
    assert lista[-1]["motivoDegradacao"] is None
    assert lista[-1]["uso"]["entrada"] == 100
    assert lista[-1]["acumulado"]["chamadas"] == 1
    assert engine.tentativas == 1


def test_nunca_ha_delta_depois_do_fim(contexto_moderado, fixar_engine):
    fixar_engine(EngineDeTeste(["texto"]))
    tipos = [e["t"] for e in eventos(executar_tarefa("score", contexto_moderado))]
    assert tipos[0] == "inicio"
    assert tipos[-1] in ("fim", "erro")
    assert "delta" not in tipos[tipos.index("fim") :]


# ---------------------------------------------------------------------------
# Degradação
# ---------------------------------------------------------------------------


def test_falha_antes_do_primeiro_texto_tenta_de_novo_uma_vez(
    contexto_moderado, fixar_engine, monkeypatch
):
    """§2.4: retry só quando nada foi emitido e ainda sobra deadline."""
    monkeypatch.setenv("LASTRO_LLM_TIMEOUT_MS", "60000")

    class FalhaUmaVez(EngineDeTeste):
        def _emitir(self):
            self.tentativas += 1
            if self.tentativas == 1:
                raise EngineIndisponivel("502", recuperavel=True)
            yield PedacoNarrativa(tipo="texto", texto="ok")
            yield PedacoNarrativa(tipo="uso", uso=UsoTokens(entrada=1, saida=1))

    engine = fixar_engine(FalhaUmaVez([]))
    lista = eventos(executar_tarefa("parecer", contexto_moderado))

    assert engine.tentativas == 2
    assert [e["t"] for e in lista] == ["inicio", "delta", "fim"]
    assert texto_de(lista) == "ok"


def test_falha_nao_recuperavel_nao_tenta_de_novo(contexto_moderado, fixar_engine):
    engine = fixar_engine(
        EngineDeTeste([], erro=EngineIndisponivel("400", recuperavel=False))
    )
    lista = eventos(executar_tarefa("parecer", contexto_moderado))
    assert engine.tentativas == 1
    assert any(e["t"] == "substituir" for e in lista)


def test_falha_depois_do_texto_troca_pelo_deterministico(contexto_moderado, fixar_engine):
    """Parecer pela metade não é aceitável para impressão."""
    fixar_engine(
        EngineDeTeste(["começo do texto", "resto"], erro=EngineIndisponivel(), apos=1)
    )
    lista = eventos(executar_tarefa("parecer", contexto_moderado))

    tipos = [e["t"] for e in lista]
    assert tipos[0] == "inicio" and tipos[-1] == "fim"
    assert "substituir" in tipos
    substituir = lista[tipos.index("substituir")]
    assert substituir["motivo"] == "FALHA_REDE"
    assert lista[-1]["origem"] == "deterministico"
    # o texto após o `substituir` é o parecer determinístico completo
    posterior = "".join(
        e["d"] for e in lista[tipos.index("substituir") :] if e["t"] == "delta"
    )
    assert posterior.startswith("## Resumo executivo")
    assert "Decisão final sujeita à avaliação do analista responsável." in posterior


def test_deadline_estourado_vira_timeout(contexto_moderado, fixar_engine, monkeypatch):
    monkeypatch.setenv("LASTRO_LLM_TIMEOUT_MS", "0")
    fixar_engine(EngineDeTeste(["parcial"], erro=EngineTimeout(), apos=1))
    lista = eventos(executar_tarefa("parecer", contexto_moderado))
    assert any(e["t"] == "substituir" and e["motivo"] == "TIMEOUT" for e in lista)
    assert lista[-1]["motivoDegradacao"] == "TIMEOUT"


def test_saida_vazia_do_llm_degrada(contexto_moderado, fixar_engine):
    fixar_engine(EngineDeTeste(["   ", "\n"]))
    lista = eventos(executar_tarefa("score", contexto_moderado))
    assert any(e["t"] == "substituir" and e["motivo"] == "SAIDA_VAZIA" for e in lista)


# ---------------------------------------------------------------------------
# O verificador dentro do executor — I7 ponta a ponta
# ---------------------------------------------------------------------------


def test_numero_inventado_dispara_substituir_e_incidente_maximo(
    contexto_moderado, fixar_engine
):
    fixar_engine(EngineDeTeste(["O score é 999.999 e a PD é de cerca de 42,7%."]))
    lista = eventos(executar_tarefa("parecer", contexto_moderado))

    substituir = next(e for e in lista if e["t"] == "substituir")
    assert substituir["motivo"] == "FIDELIDADE_NUMERICA"
    assert lista[-1]["origem"] == "deterministico"
    assert _ledger.LEDGER.incidentes == 1

    registro = _ledger.LEDGER.registros()[-1]
    assert registro.status == "fidelidade"
    assert registro.incidente["severidade"] == "MAXIMA"
    assert "999.999" in registro.incidente["violacoes"]


def test_saida_fiel_do_llm_atravessa_intacta(contexto_moderado, fixar_engine):
    fiel = f"O score calculado é {contexto_moderado.score}, rating {contexto_moderado.rating_final}."
    fixar_engine(EngineDeTeste([fiel]))
    lista = eventos(executar_tarefa("score", contexto_moderado))
    assert texto_de(lista) == fiel
    assert not any(e["t"] == "substituir" for e in lista)
    assert _ledger.LEDGER.incidentes == 0


def test_numero_da_pergunta_nao_gera_falso_positivo(contexto_moderado, fixar_engine):
    """§8, caso 9: o analista escreveu o número; repeti-lo não é invenção."""
    fixar_engine(EngineDeTeste(["O limite citado, R$ 4.600.000, está acima do aprovado."]))
    lista = eventos(
        executar_tarefa(
            "copiloto",
            contexto_moderado,
            pergunta="O limite de R$ 4.600.000 está alto?",
            extras_do_verificador={"4.600.000"},
        )
    )
    assert not any(e["t"] == "substituir" for e in lista)


# ---------------------------------------------------------------------------
# Engines não-OpenAI e caminho de erro
# ---------------------------------------------------------------------------


def test_engine_deterministico_nao_passa_pelo_verificador(contexto_moderado, fixar_engine):
    """Só a saída do LLM é auditada; o determinístico é a referência."""
    fixar_engine(EngineDeTeste(["texto com 999.999"], engine_id="deterministico"), "ORCAMENTO")
    lista = eventos(executar_tarefa("parecer", contexto_moderado))
    assert not any(e["t"] == "substituir" for e in lista)
    assert lista[-1]["motivoDegradacao"] == "ORCAMENTO"


def test_falha_do_deterministico_vira_evento_erro(
    contexto_moderado, fixar_engine, monkeypatch
):
    """Cenário de bug: nem a rede de segurança respondeu."""

    class Explode:
        id = "deterministico"
        modelo = None

        def __init__(self, *_a, **_k):
            pass

        def gerar(self, *_a, **_k):
            raise RuntimeError("template quebrado")
            yield  # pragma: no cover

        def responder(self, *_a, **_k):
            raise RuntimeError("template quebrado")
            yield  # pragma: no cover

    fixar_engine(EngineDeTeste([], erro=EngineIndisponivel()))
    monkeypatch.setattr(modulo_executor, "DeterministicNarrativeEngine", Explode)
    lista = eventos(executar_tarefa("parecer", contexto_moderado))

    assert lista[-1]["t"] == "erro"
    assert lista[-1]["codigo"] == "FALHA_INTERNA"


def test_resposta_imediata_respeita_o_protocolo(contexto_moderado):
    lista = eventos(
        executar_resposta_imediata("copiloto", contexto_moderado, "Recusa literal.")
    )
    assert [e["t"] for e in lista] == ["inicio", "delta", "fim"]
    assert texto_de(lista) == "Recusa literal."
    assert lista[-1]["uso"]["custoUsd"] == 0.0


# ---------------------------------------------------------------------------
# Estimativa de custo
# ---------------------------------------------------------------------------


def test_estimativa_de_custo_cresce_com_o_tamanho_do_bloco(contexto_moderado):
    parecer = estimar_custo("parecer", contexto_moderado)
    score = estimar_custo("score", contexto_moderado)
    assert parecer > score > 0
    assert parecer < 0.01  # centavos, não dólares
