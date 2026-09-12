"""Custo, reserva, disjuntor e persistência — `04-camada-llm.md` §5.

O orçamento é dinheiro real (US$ 10 de saldo). Cada teste aqui corresponde a
uma das quatro defesas contra gasto silencioso.
"""

from __future__ import annotations

import json

import pytest
from llm.engine import UsoTokens, diagnosticar_selecao
from llm.ledger import (
    DURACAO_DO_DISJUNTOR_S,
    FALHAS_PARA_ABRIR,
    MAX_ULTIMAS,
    Ledger,
    custo_usd,
)


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


@pytest.fixture
def ledger():
    return Ledger("")


def fechar(ledger, *, reserva=None, uso=None, motivo=None, engine="openai", origem=None):
    return ledger.fechar(
        reserva,
        "req-1",
        "parecer",
        "cli-1",
        engine,
        origem or engine,
        uso,
        motivo,
        1.5,
        modelo="gpt-5.4-mini",
    )


# ---------------------------------------------------------------------------
# Preço
# ---------------------------------------------------------------------------


def test_custo_do_teste_real_de_d5():
    """604 tokens de entrada, 863 de saída — a chamada já medida nesta máquina."""
    assert round(custo_usd(UsoTokens(entrada=604, saida=863)), 6) == 0.001877


def test_tokens_de_raciocinio_nao_sao_cobrados_duas_vezes():
    """A API já os inclui em `completion_tokens`."""
    sem = custo_usd(UsoTokens(entrada=100, saida=200, raciocinio=0))
    com = custo_usd(UsoTokens(entrada=100, saida=200, raciocinio=200))
    assert sem == com


def test_uso_ausente_custa_zero():
    assert custo_usd(None) == 0.0


# ---------------------------------------------------------------------------
# Reserva e teto
# ---------------------------------------------------------------------------


def test_reserva_impede_tres_chamadas_simultaneas_de_estourar_o_teto(monkeypatch, ledger):
    """A abertura de uma página dispara três blocos ao mesmo tempo (§5.2)."""
    monkeypatch.setenv("LASTRO_LLM_BUDGET_USD", "0.01")
    previsto = 0.004
    assert ledger.cabe_no_orcamento(previsto)
    ledger.reservar(previsto, "a")
    assert ledger.cabe_no_orcamento(previsto)
    ledger.reservar(previsto, "b")
    assert not ledger.cabe_no_orcamento(previsto)


def test_fechar_troca_a_reserva_pelo_custo_real(ledger):
    reserva = ledger.reservar(0.05, "r")
    assert ledger.reservado == 0.05
    fechar(ledger, reserva=reserva, uso=UsoTokens(entrada=604, saida=863))
    assert ledger.reservado == 0.0
    assert round(ledger.custo_acumulado, 6) == 0.001877


def test_teto_atingido_seleciona_o_deterministico_com_motivo_orcamento(
    monkeypatch, ledger
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-falso")
    monkeypatch.setenv("LASTRO_LLM_ENGINE", "")
    monkeypatch.setenv("LASTRO_LLM_BUDGET_USD", "0.001")
    assert diagnosticar_selecao(ledger, 0.0) == ("openai", None)
    fechar(ledger, uso=UsoTokens(entrada=604, saida=863))
    assert diagnosticar_selecao(ledger, 0.0) == ("deterministico", "ORCAMENTO")


# ---------------------------------------------------------------------------
# Disjuntor
# ---------------------------------------------------------------------------


def test_disjuntor_abre_apos_tres_falhas_e_fecha_depois_de_60s(monkeypatch):
    relogio = RelogioFalso()
    ledger = Ledger("", relogio)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-falso")
    monkeypatch.setenv("LASTRO_LLM_ENGINE", "")

    for _ in range(FALHAS_PARA_ABRIR - 1):
        ledger.registrar_falha_rede()
    assert not ledger.disjuntor_aberto()

    ledger.registrar_falha_rede()
    assert ledger.disjuntor_aberto()
    assert diagnosticar_selecao(ledger, 0.0) == ("deterministico", "DISJUNTOR")

    relogio.avancar(DURACAO_DO_DISJUNTOR_S + 1)
    assert not ledger.disjuntor_aberto()
    assert diagnosticar_selecao(ledger, 0.0) == ("openai", None)


def test_falhas_fora_da_janela_nao_somam():
    relogio = RelogioFalso()
    ledger = Ledger("", relogio)
    for _ in range(FALHAS_PARA_ABRIR - 1):
        ledger.registrar_falha_rede()
    relogio.avancar(200.0)
    ledger.registrar_falha_rede()
    assert not ledger.disjuntor_aberto()


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def test_persistencia_reconstitui_o_total_depois_de_um_restart(tmp_path):
    caminho = tmp_path / "ledger.jsonl"
    primeiro = Ledger(str(caminho))
    fechar(primeiro, uso=UsoTokens(entrada=604, saida=863))
    fechar(primeiro, uso=UsoTokens(entrada=604, saida=863))

    linhas = caminho.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2
    assert "saida" not in json.loads(linhas[0])  # nenhum texto gerado é gravado

    segundo = Ledger(str(caminho))
    assert round(segundo.custo_acumulado, 6) == round(primeiro.custo_acumulado, 6)


def test_chamada_deterministica_nao_entra_no_diario(tmp_path):
    """O `.jsonl` é o gasto real; o determinístico não gasta nada."""
    caminho = tmp_path / "ledger.jsonl"
    ledger = Ledger(str(caminho))
    fechar(ledger, engine="deterministico", motivo="ORCAMENTO")
    assert not caminho.exists()


def test_caminho_vazio_nao_toca_o_disco(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ledger = Ledger("")
    fechar(ledger, uso=UsoTokens(entrada=10, saida=10))
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def test_resumo_tem_o_esquema_do_endpoint_de_custo(ledger):
    fechar(ledger, uso=UsoTokens(entrada=604, saida=863))
    resumo = ledger.resumo(True, "openai", "gpt-5.4-mini", None)
    esperadas = {
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
    assert set(resumo) == esperadas
    assert resumo["chamadas"]["openai"] == 1
    assert resumo["tokens"]["entrada"] == 604
    assert resumo["ultimas"][0]["status"] == "ok"


def test_ultimas_traz_no_maximo_vinte_mais_recentes(ledger):
    for _ in range(MAX_ULTIMAS + 5):
        fechar(ledger, uso=UsoTokens(entrada=1, saida=1))
    assert len(ledger.resumo(True, "openai", None, None)["ultimas"]) == MAX_ULTIMAS


def test_incidente_de_fidelidade_e_contado(ledger):
    ledger.registrar_incidente("req", "FIDELIDADE_NUMERICA", ["999"], "MAXIMA")
    assert ledger.incidentes == 1
    assert ledger.resumo(True, "openai", None, None)["incidentes"] == 1


def test_status_derivado_do_motivo(ledger):
    assert fechar(ledger, motivo="TIMEOUT").status == "timeout"
    assert fechar(ledger, motivo="FIDELIDADE_NUMERICA").status == "fidelidade"
    assert fechar(ledger, motivo=None).status == "ok"
