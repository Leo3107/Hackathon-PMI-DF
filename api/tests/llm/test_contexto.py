"""Serialização do contexto — `04-camada-llm.md` §4 e matriz de perfis §3.5.

O que se prova aqui: **nenhum número cru chega ao modelo**. Tudo que sai do
serializador é string pt-BR já formatada, de modo que copiar seja a única
operação possível — e o verificador possa comparar strings exatas.
"""

from __future__ import annotations

import pytest
from llm.contexto import (
    fmt_booleano,
    fmt_data,
    fmt_decimal,
    fmt_impacto,
    fmt_inteiro,
    fmt_moeda,
    fmt_percentual_de_fracao,
    fmt_percentual_direto,
    fmt_peso,
    serializar_contexto,
)
from llm.perfis import PERFIS
from llm.verificador import extrair_numeros
from scoring import calcular_risco, comparar_avaliacoes
from tests import fixtures as perfis_de_teste

from apoio import contexto_de, montar_cliente

#: Teto por cliente no perfil `parecer` (§4.3).
TETO_DE_TOKENS_DO_PARECER = 3200

TAREFAS = ("parecer", "score", "recomendacao", "copiloto")


# ---------------------------------------------------------------------------
# Formatadores — a tabela normativa da §4.2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("funcao", "entrada", "esperado"),
    [
        (fmt_moeda, 1_200_000.0, "R$ 1.200.000"),
        (fmt_moeda, 0.0, "R$ 0"),
        (fmt_percentual_de_fracao, 0.1712, "17,1%"),
        (fmt_percentual_de_fracao, 0.5, "50,0%"),
        (fmt_percentual_direto, 25.0, "25%"),
        (fmt_percentual_direto, 91.3, "91,3%"),
        (fmt_inteiro, 604.0, "604"),
        (fmt_impacto, -26.4, "-26,4"),
        (fmt_impacto, 15.0, "+15,0"),
        (fmt_decimal, 107.64, "107,6"),
        (fmt_peso, 0.22, "22%"),
        (fmt_data, "2026-08-20", "20/08/2026"),
        (fmt_booleano, True, "sim"),
        (fmt_booleano, False, "nao"),
    ],
)
def test_formatadores_seguem_a_tabela_normativa(funcao, entrada, esperado):
    assert funcao(entrada) == esperado


def test_moeda_nao_leva_centavos():
    """`R$ 1.200.000,00` seria um número diferente para o verificador."""
    assert "," not in fmt_moeda(1_234_567.89)


# ---------------------------------------------------------------------------
# Formato literal do bloco (§4.3)
# ---------------------------------------------------------------------------


def test_o_bloco_abre_com_o_cabecalho_de_dados_simulados(contexto_moderado):
    primeira = contexto_moderado.bloco.splitlines()[0]
    assert primeira.startswith("LASTRO · CONTEXTO DE AVALIAÇÃO · dados simulados")
    assert primeira.endswith("12/09/2026")


def test_secoes_usam_o_formato_de_colchetes_e_pipes(contexto_moderado):
    linhas = contexto_moderado.bloco.splitlines()
    for marcador in ("[CLIENTE]", "[SCORE]", "[FATORES]", "[PD]", "[EXPOSICAO]"):
        assert any(linha.startswith(marcador) for linha in linhas), marcador


def test_nao_ha_json_nem_tabela_markdown_no_bloco(contexto_moderado):
    """JSON e tabela custam token sem informar nada a mais (§4.3)."""
    assert "|---" not in contexto_moderado.bloco
    assert '": ' not in contexto_moderado.bloco


def test_fatores_de_risco_vem_antes_dos_de_protecao_e_por_impacto(contexto_moderado):
    impactos = [
        abs(float(f.impacto.replace(".", "").replace(",", ".")))
        for f in contexto_moderado.fatores_risco
    ]
    assert impactos == sorted(impactos, reverse=True)
    assert all(f.impacto.startswith("-") for f in contexto_moderado.fatores_risco)
    assert all(f.impacto.startswith("+") for f in contexto_moderado.fatores_protecao)


def test_sem_rj_em_curso_o_stay_period_e_nao_aplicavel(contexto_moderado):
    assert "[STAY_PERIOD] nao_aplicavel" in contexto_moderado.bloco


def test_com_rj_em_curso_o_stay_period_traz_bloqueios_e_permitidos():
    contexto = contexto_de("rj_com_stay_period")
    linha = next(
        linha for linha in contexto.bloco.splitlines() if linha.startswith("[STAY_PERIOD]")
    )
    assert "ativo=sim" in linha
    assert "bloqueado:" in linha
    assert "permitido:" in linha


def test_veto_e_nomeado_na_linha_de_score():
    contexto = contexto_de("veto_ambiental")
    linha = next(
        linha for linha in contexto.bloco.splitlines() if linha.startswith("[SCORE]")
    )
    assert "vetos: VETO_EMBARGO_GARANTIA" in linha
    assert "força D" in linha


def test_sem_veto_a_linha_de_score_diz_nenhum(contexto_moderado):
    assert "vetos=nenhum" in contexto_moderado.bloco


def test_variacao_entra_quando_ha_snapshot_anterior():
    serie = dict(perfis_de_teste.todas_as_series())["em_deterioracao"]
    anterior, atual = calcular_risco(serie[0]), calcular_risco(serie[-1])
    variacao = comparar_avaliacoes(anterior, atual)
    contexto = serializar_contexto(
        montar_cliente(atual.cliente_id), serie[-1], atual, variacao, "parecer"
    )
    assert "[VARIACAO_90D]" in contexto.bloco
    assert contexto.variacao is not None
    assert "referencia anterior" in contexto.bloco


# ---------------------------------------------------------------------------
# Matriz de perfis (§3.5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tarefa", TAREFAS)
def test_perfil_inclui_e_omite_as_secoes_da_matriz(tarefa, nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, tarefa)
    perfil = PERFIS[tarefa]
    bloco = contexto.bloco

    assert ("[DIMENSOES]" in bloco) == perfil.dimensoes
    assert ("[PD]" in bloco) == perfil.pd_rj_stay
    assert ("[RJ]" in bloco) == perfil.pd_rj_stay
    assert ("[EXPOSICAO]" in bloco) == perfil.exposicao_garantias
    assert ("[GARANTIAS]" in bloco) == perfil.exposicao_garantias
    assert ("[RECOMENDACAO]" in bloco) == perfil.recomendacao
    assert ("[RED_FLAGS]" in bloco) == (perfil.red_flags != "nenhuma")


@pytest.mark.parametrize("tarefa", TAREFAS)
def test_perfil_respeita_o_teto_de_fatores(tarefa, nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, tarefa)
    perfil = PERFIS[tarefa]
    if perfil.max_fatores_risco is not None:
        assert len(contexto.fatores_risco) <= perfil.max_fatores_risco
    if perfil.max_fatores_protecao is not None:
        assert len(contexto.fatores_protecao) <= perfil.max_fatores_protecao


def test_perfil_recomendacao_so_traz_red_flags_graves():
    contexto = contexto_de("critico", "recomendacao")
    assert all(r.severidade in ("CRITICA", "ALTA") for r in contexto.red_flags)


def test_perfil_score_nao_fala_de_dinheiro():
    """O texto do score não menciona exposição nem garantias — nem o contexto."""
    contexto = contexto_de("moderado", "score")
    assert "[EXPOSICAO]" not in contexto.bloco
    assert "[GARANTIAS]" not in contexto.bloco
    assert "[RECOMENDACAO]" not in contexto.bloco


def test_cliente_reduzido_omite_documento_e_culturas():
    reduzido = contexto_de("moderado", "score")
    completo = contexto_de("moderado", "parecer")
    linha_reduzida = next(
        linha for linha in reduzido.bloco.splitlines() if linha.startswith("[CLIENTE]")
    )
    linha_completa = next(
        linha for linha in completo.bloco.splitlines() if linha.startswith("[CLIENTE]")
    )
    assert "CNPJ" not in linha_reduzida
    assert "CNPJ" in linha_completa
    assert "culturas:" in linha_completa


# ---------------------------------------------------------------------------
# Tamanho e números permitidos
# ---------------------------------------------------------------------------


def test_bloco_do_parecer_cabe_no_teto_de_tokens(nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, "parecer")
    assert contexto.tokens_estimados < TETO_DE_TOKENS_DO_PARECER


def test_numeros_permitidos_saem_do_proprio_bloco(contexto_moderado):
    assert contexto_moderado.numeros_permitidos == frozenset(
        extrair_numeros(contexto_moderado.bloco)
    )
    assert contexto_moderado.score in contexto_moderado.numeros_permitidos


def test_todo_campo_estruturado_e_string_ja_formatada(contexto_moderado):
    """Se um float vazasse para cá, o modelo teria de converter — e converter é calcular."""
    assert isinstance(contexto_moderado.score, str)
    assert isinstance(contexto_moderado.pd.m12, str)
    assert contexto_moderado.pd.m12.endswith("%")
    assert contexto_moderado.exposicao.total.startswith("R$ ")
    assert all("," in d.contribuicao for d in contexto_moderado.dimensoes)


def test_contexto_e_imutavel(contexto_moderado):
    with pytest.raises(Exception):
        contexto_moderado.score = "999"
