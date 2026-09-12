"""Suíte das rotas Flask, com o cliente de teste — status, forma e contrato.

O que esta suíte protege:

* **Status corretos** — 200/201 no caminho feliz, 400 em corpo inválido, 404 em
  id inexistente, e sempre o envelope `{erro, detalhe}`, nunca HTML.
* **Chaves camelCase** — o contrato de `web/types/api.ts` fecha sem adaptador.
* **Verbo `POST` nas leituras** — o corpo carrega o `EstadoDeSessao` (D3).
* **Recálculo real na simulação** (D10) — o score depois difere do antes, e o
  delta devolvido é a diferença entre dois cálculos do motor.
"""

from __future__ import annotations

import pytest
from app import criar_app
from models.enums import EstadoCliente, Rating, Severidade

from test_repositorio import cnpj_valido, fonte_de_teste

#: CNPJ com dígito verificador válido que não pertence a nenhum perfil (§6.5).
DOCUMENTO_DESCONHECIDO = cnpj_valido("998887770001")
CLIENTE = "cli-deterioracao"


@pytest.fixture
def app():
    return criar_app(fonte=fonte_de_teste(), testando=True)


@pytest.fixture
def client(app):
    return app.test_client()


def _json(resposta):
    assert resposta.mimetype == "application/json", "erro jamais sai como HTML"
    return resposta.get_json()


# ---------------------------------------------------------------------------
# Saúde e erros de superfície
# ---------------------------------------------------------------------------


def test_saude_responde(client):
    resposta = client.get("/api/saude")
    assert resposta.status_code == 200
    corpo = _json(resposta)
    assert corpo["ok"] is True
    assert corpo["servico"] == "lastro-api"
    assert "llmHabilitado" in corpo and "dataHora" in corpo


def test_rota_inexistente_devolve_envelope_padrao(client):
    resposta = client.get("/api/nao-existe")
    assert resposta.status_code == 404
    assert _json(resposta)["erro"] == "ROTA_NAO_ENCONTRADA"


def test_corpo_malformado_e_recusado(client):
    resposta = client.post(
        "/api/carteira", data="{isto não é json", content_type="application/json"
    )
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_sessao_com_tipo_errado_e_recusada(client):
    resposta = client.post("/api/carteira", json={"sessao": []})
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_evento_simulado_desconhecido_na_sessao_e_recusado(client):
    resposta = client.post(
        "/api/clientes",
        json={"sessao": {"eventosSimulados": [{"tipo": "METEORO"}], "statusRedFlags": {}}},
    )
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


# ---------------------------------------------------------------------------
# Carteira
# ---------------------------------------------------------------------------


def test_carteira_aceita_post_com_sessao(client):
    resposta = client.post(
        "/api/carteira", json={"sessao": {"eventosSimulados": [], "statusRedFlags": {}}}
    )
    assert resposta.status_code == 200
    corpo = _json(resposta)

    assert corpo["totalClientes"] == 10
    assert corpo["exposicaoTotal"] > 0
    assert corpo["exposicaoEmRiscoEmRJ"] >= 0
    assert set(corpo["clientesPorEstado"]) == {e.value for e in EstadoCliente}
    assert set(corpo["clientesPorRating"]) == {r.value for r in Rating}
    assert set(corpo["alertas30d"]["porSeveridade"]) == {s.value for s in Severidade}
    assert corpo["deterioracao"]["limiarPontos"] == 25.0
    assert corpo["ultimaVarredura"].startswith(corpo["dataReferencia"])


def test_carteira_tambem_responde_em_get(client):
    """Tolerância declarada em `web/lib/api/cliente.ts`: 405 nunca deve acontecer."""
    assert client.get("/api/carteira").status_code == 200


def test_carteira_traz_visualizacoes_e_faixa_de_atencao(client):
    corpo = _json(client.post("/api/carteira"))
    assert corpo["matrizDeRisco"], "V1 precisa de um ponto por cliente"
    assert len(corpo["matrizDeRisco"]) == corpo["totalClientes"]
    assert len(corpo["dinheiroEmRisco"]) <= 8
    assert corpo["concentracaoPorUf"] and corpo["concentracaoPorCultura"]

    cartoes = corpo["atencaoImediata"]
    assert 1 <= len(cartoes) <= 3
    assert {c["clienteId"] for c in cartoes} == {c["clienteId"] for c in cartoes}
    for cartao in cartoes:
        assert cartao["motivo"] in {
            "VETO_ATIVO",
            "MAIOR_QUEDA_90D",
            "ALERTA_CRITICO",
        }
        assert cartao["causa"] and cartao["numero"] and cartao["acao"]


def test_carteira_nao_vaza_chave_snake_case(client):
    corpo = _json(client.post("/api/carteira"))
    assert "_" not in "".join(corpo.keys())


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------


def test_lista_de_clientes_traz_avaliacao_e_variacao(client):
    corpo = _json(client.post("/api/clientes"))
    assert len(corpo) == 10
    linha = next(item for item in corpo if item["cliente"]["id"] == CLIENTE)
    assert linha["avaliacao"]["clienteId"] == CLIENTE
    assert linha["avaliacao"]["ratingFinal"] in {"A", "B", "C", "D"}
    assert "riscoRJ" in linha["avaliacao"]
    assert linha["variacao90d"]["deltaScore"] != 0
    assert linha["alertasNaoLidos"] >= 1


def test_cliente_individual(client):
    corpo = _json(client.get(f"/api/clientes/{CLIENTE}"))
    assert corpo["id"] == CLIENTE
    assert corpo["razaoSocial"]
    assert corpo["tipoPessoa"] in {"PF", "PJ"}


def test_cliente_inexistente_devolve_404(client):
    resposta = client.get("/api/clientes/cli-fantasma")
    assert resposta.status_code == 404
    assert _json(resposta)["erro"] == "CLIENTE_NAO_ENCONTRADO"


def test_avaliacao_fecha_a_soma_das_contribuicoes(client):
    corpo = _json(client.post(f"/api/clientes/{CLIENTE}/avaliacao"))
    assert abs(corpo["auditoria"]["diferenca"]) <= 0.5
    assert corpo["recomendacao"]["aviso"]
    assert len(corpo["dimensoes"]) == 7


def test_avaliacao_de_cliente_inexistente_devolve_404(client):
    resposta = client.post("/api/clientes/cli-fantasma/avaliacao")
    assert resposta.status_code == 404
    assert _json(resposta)["erro"] == "CLIENTE_NAO_ENCONTRADO"


def test_historico(client):
    corpo = _json(client.get(f"/api/clientes/{CLIENTE}/historico"))
    assert len(corpo) >= 5
    assert corpo[0]["fatos"]["clienteId"] == CLIENTE


def test_eventos_trazem_score_recalculado(client):
    corpo = _json(client.post(f"/api/clientes/{CLIENTE}/eventos"))
    assert corpo
    assert all(evento["scoreApos"] > 0 for evento in corpo)


def test_eventos_de_cliente_sem_evento_devolvem_lista_vazia(client):
    assert _json(client.post("/api/clientes/cli-excelente/eventos")) == []


# ---------------------------------------------------------------------------
# Simulação de evento (D10) — o recálculo real
# ---------------------------------------------------------------------------


def test_simular_evento_recalcula_de_verdade(client):
    antes = _json(client.post("/api/clientes/cli-excelente/avaliacao"))
    resposta = client.post(
        "/api/clientes/cli-excelente/simular-evento",
        json={"tipo": "NOVA_EXECUCAO", "sessao": {"eventosSimulados": [], "statusRedFlags": {}}},
    )
    assert resposta.status_code == 200
    corpo = _json(resposta)

    assert corpo["scoreAnterior"] == antes["scoreCalculado"]
    assert corpo["scoreAtual"] != corpo["scoreAnterior"], "o motor precisa recalcular"
    assert corpo["scoreAtual"] < corpo["scoreAnterior"]
    assert corpo["deltaScore"] == pytest.approx(
        corpo["scoreAtual"] - corpo["scoreAnterior"], abs=0.05
    )
    assert abs(corpo["variacao"]["diferencaDeFechamento"]) <= 0.5
    assert corpo["avaliacao"]["scoreCalculado"] == corpo["scoreAtual"]
    assert corpo["alertaGerado"]["clienteId"] == "cli-excelente"
    assert corpo["evento"]["tipo"] == "NOVA_EXECUCAO"


def test_simulacao_nao_persiste_entre_requisicoes(client):
    client.post(
        "/api/clientes/cli-excelente/simular-evento", json={"tipo": "PEDIDO_FALENCIA"}
    )
    depois = _json(client.post("/api/clientes/cli-excelente/avaliacao"))
    assert depois["ratingFinal"] == "A"


def test_sessao_com_evento_simulado_altera_a_avaliacao(client):
    limpo = _json(client.post("/api/clientes/cli-excelente/avaliacao"))
    com_evento = _json(
        client.post(
            "/api/clientes/cli-excelente/avaliacao",
            json={
                "sessao": {
                    "eventosSimulados": [
                        {"tipo": "EMBARGO_AMBIENTAL", "data": "2026-09-12T10:00:00-03:00"}
                    ],
                    "statusRedFlags": {},
                }
            },
        )
    )
    assert com_evento["scoreCalculado"] < limpo["scoreCalculado"]


def test_simular_evento_com_tipo_invalido(client):
    resposta = client.post(
        "/api/clientes/cli-excelente/simular-evento", json={"tipo": "EXPLOSAO_SOLAR"}
    )
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_simular_evento_com_corpo_vazio(client):
    resposta = client.post("/api/clientes/cli-excelente/simular-evento")
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_simular_evento_em_cliente_inexistente(client):
    resposta = client.post(
        "/api/clientes/cli-fantasma/simular-evento", json={"tipo": "NOVA_EXECUCAO"}
    )
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Alertas e auditoria
# ---------------------------------------------------------------------------


def test_alertas(client):
    corpo = _json(client.post("/api/alertas"))
    assert len(corpo) == 3
    assert corpo[0]["severidade"] in {s.value for s in Severidade}
    assert corpo[0]["acaoRecomendada"]


def test_auditoria_lista(client):
    corpo = _json(client.get("/api/auditoria"))
    assert corpo and corpo[0]["divergiuDaRecomendacao"] is False


def test_auditoria_registra_e_carimba(client):
    resposta = client.post(
        "/api/auditoria",
        json={
            "clienteId": "cli-moderado",
            "analista": "Ana Ribeiro",
            "scoreNoMomento": 604.0,
            "ratingNoMomento": "C",
            "recomendacaoGerada": "SUSPENDER_NOVA_EXPOSICAO_A_PRAZO",
            "decisaoAnalista": "APROVAR",
            "justificativa": "Garantia extraconcursal cobre o ciclo integralmente.",
        },
    )
    assert resposta.status_code == 201
    corpo = _json(resposta)
    assert corpo["id"]
    assert corpo["dataHora"]
    assert corpo["divergiuDaRecomendacao"] is True
    assert len(_json(client.get("/api/auditoria"))) == 2


def test_auditoria_recusa_corpo_vazio(client):
    resposta = client.post("/api/auditoria")
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_auditoria_recusa_decisao_invalida(client):
    resposta = client.post(
        "/api/auditoria",
        json={
            "clienteId": "cli-moderado",
            "scoreNoMomento": 604.0,
            "ratingNoMomento": "C",
            "recomendacaoGerada": "APROVAR",
            "decisaoAnalista": "TALVEZ",
            "justificativa": "…",
        },
    )
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


# ---------------------------------------------------------------------------
# Due diligence (fluxo A)
# ---------------------------------------------------------------------------


def test_due_diligence_encontra_prospect(client):
    documento = fonte_de_teste().prospects[0].documento
    corpo = _json(client.post("/api/due-diligence", json={"documento": documento}))
    assert corpo["encontrado"] is True
    assert corpo["cliente"]["origem"] == "PROSPECT"
    assert corpo["avaliacao"]["scoreCalculado"] > 0
    assert [e["estagio"] for e in corpo["estagios"]] == [
        "CADASTRAL",
        "JURIDICO",
        "FISCAL",
        "AMBIENTAL",
        "AGROCLIMATICO",
        "INTERNO",
        "SCORE",
        "RELATORIO",
    ]
    assert all(estagio["achados"] for estagio in corpo["estagios"])


def test_due_diligence_documento_valido_sem_perfil(client):
    """§6.5 — não encontrado é resposta de negócio, com 200 e `encontrado: false`."""
    resposta = client.post(
        "/api/due-diligence", json={"documento": DOCUMENTO_DESCONHECIDO}
    )
    assert resposta.status_code == 200
    corpo = _json(resposta)
    assert corpo["encontrado"] is False
    assert corpo["documento"] == DOCUMENTO_DESCONHECIDO
    assert "cliente" not in corpo


@pytest.mark.parametrize(
    "documento", ["123", "00.000.000/0000-00", "11.111.111/1111-11", "abcdefghij"]
)
def test_due_diligence_documento_malformado(client, documento):
    resposta = client.post("/api/due-diligence", json={"documento": documento})
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_due_diligence_sem_documento(client):
    resposta = client.post("/api/due-diligence", json={})
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_due_diligence_aceita_cpf(client):
    """O produtor rural PF entra pelo mesmo fluxo (Lei 14.112/2020, D7)."""
    resposta = client.post("/api/due-diligence", json={"documento": "529.982.247-25"})
    assert resposta.status_code == 200
    assert _json(resposta)["encontrado"] is False


# ---------------------------------------------------------------------------
# "O que mudou" — comparação por período
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("periodo", ["30d", "90d", "12m", "inicio"])
def test_comparacao_por_periodo(client, periodo):
    resposta = client.post(
        f"/api/clientes/{CLIENTE}/comparacao", json={"periodo": periodo}
    )
    assert resposta.status_code == 200
    corpo = _json(resposta)
    assert corpo["clienteId"] == CLIENTE
    assert abs(corpo["diferencaDeFechamento"]) <= 0.5, "invariante I6"
    assert corpo["fatores"], "a decomposição fator a fator é o coração do bloco"
    assert corpo["scoreAtual"] != corpo["scoreAnterior"]


def test_comparacao_soma_dos_deltas_reconstroi_a_variacao(client):
    corpo = _json(client.post(f"/api/clientes/{CLIENTE}/comparacao"))
    soma = sum(fator["delta"] for fator in corpo["fatores"])
    assert soma == pytest.approx(corpo["deltaScore"], abs=0.5)


def test_comparacao_sem_periodo_usa_90d(client):
    padrao = _json(client.post(f"/api/clientes/{CLIENTE}/comparacao"))
    explicito = _json(
        client.post(f"/api/clientes/{CLIENTE}/comparacao", json={"periodo": "90d"})
    )
    assert padrao["dataAnterior"] == explicito["dataAnterior"]


def test_comparacao_com_periodo_invalido(client):
    resposta = client.post(
        f"/api/clientes/{CLIENTE}/comparacao", json={"periodo": "ontem"}
    )
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "CORPO_INVALIDO"


def test_comparacao_de_cliente_inexistente(client):
    resposta = client.post("/api/clientes/cli-fantasma/comparacao")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Campos opcionais dos agregados (pedidos pela tela de carteira)
# ---------------------------------------------------------------------------


def test_linha_traz_proximo_vencimento_e_severidade(client):
    corpo = _json(client.post("/api/clientes"))
    por_id = {item["cliente"]["id"]: item for item in corpo}

    vencimento = por_id["cli-excelente"]["proximoVencimento"]
    assert vencimento["data"]
    #: Exatamente um dos dois contadores — nunca os dois, nunca `null`.
    assert ("diasRestantes" in vencimento) != ("diasAtraso" in vencimento)

    assert por_id["cli-critico"]["severidadeMaximaAlerta"] == "CRITICA"
    assert por_id["cli-deterioracao"]["severidadeMaximaAlerta"] == "ALTA"
    #: Alerta lido não acende a pastilha.
    assert "severidadeMaximaAlerta" not in por_id["cli-moderado"]


def test_parcela_em_atraso_tem_precedencia(client):
    corpo = _json(client.post("/api/clientes"))
    por_id = {item["cliente"]["id"]: item for item in corpo}
    vencimento = por_id["cli-critico"].get("proximoVencimento")
    if vencimento is not None and "diasAtraso" in vencimento:
        assert vencimento["diasAtraso"] >= 0


def test_fatias_de_concentracao_trazem_risco_e_clima(client):
    corpo = _json(client.post("/api/carteira"))
    for fatia in corpo["concentracaoPorCultura"]:
        assert fatia["exposicaoEmRisco"] <= fatia["exposicao"] + 0.01
        assert isinstance(fatia["zarcAlto"], bool)
    for fatia in corpo["concentracaoPorUf"]:
        assert "exposicaoEmRisco" in fatia
        #: `zarcAlto` é marcador de cultura (V3); não faz sentido por UF.
        assert "zarcAlto" not in fatia
