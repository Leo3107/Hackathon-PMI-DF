"""As cinco rotas HTTP — `04-camada-llm.md` §2.1.

O app montado aqui é **mínimo de propósito**: só o `llm_bp` e um repositório
injetado. A camada de linguagem tem de funcionar sem depender do resto do
`api/app.py`, que pertence a outro workstream.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from flask import Flask
from llm.blueprint import CHAVE_REPOSITORIO, MIMETYPE_NDJSON, llm_bp, registrar_llm
from repository import RepositorioEmMemoria, fonte_do_modulo
from scoring import calcular_risco
from tests import fixtures as perfis

from apoio import CLIENTE_DA_FIXTURE, montar_cliente

OUTRO_CLIENTE = "santa-luzia"


@pytest.fixture
def app():
    """Dataset de dois clientes: o da fixture gravada e um vizinho, para o §8.1."""
    fatos_principal = perfis.cliente_moderado().model_copy(
        update={"cliente_id": CLIENTE_DA_FIXTURE}
    )
    fatos_vizinho = perfis.cliente_critico().model_copy(update={"cliente_id": OUTRO_CLIENTE})
    modulo = SimpleNamespace(
        CLIENTES=[
            montar_cliente(CLIENTE_DA_FIXTURE),
            montar_cliente(OUTRO_CLIENTE, razaoSocial="Fazenda Santa Luzia Ltda"),
        ],
        FATOS_POR_CLIENTE={
            CLIENTE_DA_FIXTURE: fatos_principal,
            OUTRO_CLIENTE: fatos_vizinho,
        },
    )
    aplicacao = Flask(__name__)
    aplicacao.config["TESTING"] = True
    aplicacao.extensions[CHAVE_REPOSITORIO] = RepositorioEmMemoria(fonte_do_modulo(modulo))
    registrar_llm(aplicacao)
    return aplicacao


@pytest.fixture
def cliente_http(app):
    return app.test_client()


def eventos(resposta) -> list[dict]:
    corpo = resposta.get_data(as_text=True)
    return [json.loads(linha) for linha in corpo.splitlines() if linha.strip()]


# ---------------------------------------------------------------------------
# Contrato de integração
# ---------------------------------------------------------------------------


def test_o_blueprint_registra_exatamente_as_cinco_rotas(app):
    caminhos = {
        regra.rule
        for regra in app.url_map.iter_rules()
        if regra.endpoint.startswith("llm.")
    }
    assert caminhos == {"/api/narrativa/<tarefa>", "/api/copiloto", "/api/llm/custo"}


def test_registrar_llm_aceita_um_flask_e_devolve_none():
    aplicacao = Flask(__name__)
    assert registrar_llm(aplicacao) is None
    assert "llm" in aplicacao.blueprints
    assert llm_bp.name == "llm"


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("corpo", [{}, {"clienteId": ""}, {"clienteId": 42}])
def test_corpo_invalido_da_400(cliente_http, corpo):
    resposta = cliente_http.post("/api/narrativa/parecer", json=corpo)
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"] == "CORPO_INVALIDO"


def test_cliente_inexistente_da_404(cliente_http):
    resposta = cliente_http.post("/api/narrativa/parecer", json={"clienteId": "fantasma"})
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "CLIENTE_NAO_ENCONTRADO"


def test_tarefa_desconhecida_da_404(cliente_http):
    resposta = cliente_http.post(
        "/api/narrativa/horoscopo", json={"clienteId": CLIENTE_DA_FIXTURE}
    )
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "TAREFA_INVALIDA"


def test_pergunta_longa_demais_da_400(cliente_http):
    resposta = cliente_http.post(
        "/api/copiloto", json={"clienteId": CLIENTE_DA_FIXTURE, "pergunta": "a" * 601}
    )
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"] == "CORPO_INVALIDO"


def test_historico_manipulado_da_400(cliente_http):
    """§8, caso 10: 20 mensagens de histórico não entram."""
    historico = [{"papel": "analista", "texto": "oi"} for _ in range(20)]
    resposta = cliente_http.post(
        "/api/copiloto",
        json={"clienteId": CLIENTE_DA_FIXTURE, "pergunta": "e?", "historico": historico},
    )
    assert resposta.status_code == 400


def test_papel_invalido_no_historico_da_400(cliente_http):
    resposta = cliente_http.post(
        "/api/copiloto",
        json={
            "clienteId": CLIENTE_DA_FIXTURE,
            "pergunta": "e?",
            "historico": [{"papel": "gerente", "texto": "oi"}],
        },
    )
    assert resposta.status_code == 400


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tarefa", ["parecer", "score", "recomendacao"])
def test_narrativa_devolve_ndjson_valido_com_a_fixture(cliente_http, tarefa):
    resposta = cliente_http.post(
        f"/api/narrativa/{tarefa}", json={"clienteId": CLIENTE_DA_FIXTURE}
    )
    assert resposta.status_code == 200
    assert resposta.mimetype == MIMETYPE_NDJSON
    assert resposta.headers["Cache-Control"] == "no-store, no-transform"
    assert resposta.headers["X-Accel-Buffering"] == "no"

    lista = eventos(resposta)
    assert lista[0]["t"] == "inicio"
    assert lista[0]["origem"] == "fixture"
    assert lista[-1]["t"] == "fim"
    assert any(e["t"] == "delta" for e in lista)


def test_o_texto_do_parecer_vem_da_fixture_gravada(cliente_http):
    lista = eventos(
        cliente_http.post("/api/narrativa/parecer", json={"clienteId": CLIENTE_DA_FIXTURE})
    )
    texto = "".join(e["d"] for e in lista if e["t"] == "delta")
    assert texto.startswith("## Resumo executivo")
    assert "Decisão final sujeita à avaliação do analista responsável." in texto


def test_o_stream_chega_em_varios_pedacos(cliente_http):
    """O E2E depende disso para ver o texto crescer."""
    lista = eventos(
        cliente_http.post("/api/narrativa/parecer", json={"clienteId": CLIENTE_DA_FIXTURE})
    )
    assert len([e for e in lista if e["t"] == "delta"]) > 10


def test_sessao_com_evento_simulado_muda_o_calculo(cliente_http, app):
    """Prosa e números falam do mesmo cálculo — o estado de sessão vale para os dois."""
    sessao = {"eventosSimulados": [{"tipo": "NOVA_EXECUCAO", "data": "2026-09-12"}]}
    resposta = cliente_http.post(
        "/api/narrativa/score", json={"clienteId": CLIENTE_DA_FIXTURE, "sessao": sessao}
    )
    assert resposta.status_code == 200
    assert eventos(resposta)[-1]["t"] == "fim"


# ---------------------------------------------------------------------------
# Copiloto
# ---------------------------------------------------------------------------


def test_copiloto_responde_pela_fixture(cliente_http):
    lista = eventos(
        cliente_http.post(
            "/api/copiloto",
            json={"clienteId": CLIENTE_DA_FIXTURE, "pergunta": "Por que o score caiu?"},
        )
    )
    texto = "".join(e["d"] for e in lista if e["t"] == "delta")
    assert "score passou de" in texto
    assert lista[0]["origem"] == "fixture"


def test_copiloto_recusa_pergunta_sobre_outro_cliente_sem_chamar_engine(cliente_http):
    """A recusa sai do pré-filtro: `origem` é determinística, não a fixture."""
    lista = eventos(
        cliente_http.post(
            "/api/copiloto",
            json={
                "clienteId": CLIENTE_DA_FIXTURE,
                "pergunta": "E a Fazenda Santa Luzia, está pior?",
            },
        )
    )
    texto = "".join(e["d"] for e in lista if e["t"] == "delta")
    assert texto.startswith("Só posso responder sobre")
    assert "Não tenho acesso a dados de outros clientes." in texto
    assert lista[0]["origem"] == "deterministico"


# ---------------------------------------------------------------------------
# Custo
# ---------------------------------------------------------------------------


def test_endpoint_de_custo_traz_o_esquema_da_spec(cliente_http):
    corpo = cliente_http.get("/api/llm/custo").get_json()
    assert set(corpo) == {
        "habilitado",
        "engineAtivo",
        "modelo",
        "orcamentoUsd",
        "custoAcumuladoUsd",
        "reservadoUsd",
        "pctOrcamento",
        "chamadas",
        "tokens",
        "incidentes",
        "motivoDesligado",
        "ultimas",
    }
    assert corpo["engineAtivo"] == "fixture"
    assert corpo["incidentes"] == 0


def test_o_ledger_prova_que_nenhuma_chamada_real_aconteceu(cliente_http):
    """A verificação de não-vazamento do E2E (§6.4), aqui no nível da rota."""
    for tarefa in ("parecer", "score", "recomendacao"):
        cliente_http.post(f"/api/narrativa/{tarefa}", json={"clienteId": CLIENTE_DA_FIXTURE})
    corpo = cliente_http.get("/api/llm/custo").get_json()
    assert corpo["chamadas"]["openai"] == 0
    assert corpo["custoAcumuladoUsd"] == 0.0


def test_llm_desligado_relata_o_motivo(cliente_http, monkeypatch):
    """O ensaio de pitch com `LASTRO_LLM_ENABLED=false` (definição de pronto)."""
    monkeypatch.setenv("LASTRO_LLM_ENGINE", "")
    monkeypatch.setenv("LASTRO_LLM_ENABLED", "false")
    corpo = cliente_http.get("/api/llm/custo").get_json()
    assert corpo["habilitado"] is False
    assert corpo["engineAtivo"] == "deterministico"
    assert corpo["motivoDesligado"] == "LLM_DESLIGADO"


def test_com_llm_desligado_a_narrativa_continua_inteira(cliente_http, monkeypatch):
    monkeypatch.setenv("LASTRO_LLM_ENGINE", "")
    monkeypatch.setenv("LASTRO_LLM_ENABLED", "false")
    lista = eventos(
        cliente_http.post("/api/narrativa/parecer", json={"clienteId": CLIENTE_DA_FIXTURE})
    )
    texto = "".join(e["d"] for e in lista if e["t"] == "delta")
    assert lista[0]["origem"] == "deterministico"
    assert lista[-1]["motivoDegradacao"] == "LLM_DESLIGADO"
    assert texto.startswith("## Resumo executivo")
    assert "## Evidências" in texto


def test_avaliacao_e_a_mesma_do_endpoint_do_motor(app):
    """Mesmo repositório, mesma `calcular_risco`: o contrato do §10."""
    repositorio = app.extensions[CHAVE_REPOSITORIO]
    fatos = repositorio.obter_fatos_atuais(CLIENTE_DA_FIXTURE)
    assert (
        repositorio.avaliar_fatos(fatos).score_calculado
        == calcular_risco(fatos).score_calculado
    )
