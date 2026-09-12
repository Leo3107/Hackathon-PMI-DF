"""O engine determinístico é a rede de segurança do pitch — Anexo A.

Com `LASTRO_LLM_ENABLED=false` ou sem rede, é este texto que o jurado lê. Por
isso ele é testado com o mesmo rigor do caminho do LLM: estrutura, ações,
aviso de decisão humana e **zero violações de fidelidade numérica** em todas as
personas do dataset de teste.
"""

from __future__ import annotations

import pytest
from llm.deterministic_engine import (
    SEM_ELEMENTOS,
    DeterministicNarrativeEngine,
    texto_copiloto,
    texto_parecer,
    texto_recomendacao,
    texto_score,
)
from llm.engine import ALVO_EXTENSAO
from llm.verificador import (
    TITULOS_DO_PARECER,
    contar_palavras,
    verificar_fidelidade_numerica,
)
from models.avaliacao import AVISO_DO_ANALISTA

from apoio import contexto_de

TAREFAS = {"parecer": texto_parecer, "score": texto_score, "recomendacao": texto_recomendacao}


@pytest.mark.parametrize("tarefa", list(TAREFAS))
def test_saida_nao_e_vazia(tarefa, nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, tarefa)
    assert TAREFAS[tarefa](contexto).strip()


@pytest.mark.parametrize("tarefa", list(TAREFAS))
def test_zero_violacoes_de_fidelidade(tarefa, nome_do_perfil):
    """Todo número impresso é uma string que já veio do contexto. I7 por construção."""
    contexto = contexto_de(nome_do_perfil, tarefa)
    assert verificar_fidelidade_numerica(TAREFAS[tarefa](contexto), contexto) == []


def test_parecer_tem_os_seis_titulos_na_ordem(nome_do_perfil):
    texto = texto_parecer(contexto_de(nome_do_perfil, "parecer"))
    posicoes = [texto.find(titulo) for titulo in TITULOS_DO_PARECER]
    assert all(posicao >= 0 for posicao in posicoes)
    assert posicoes == sorted(posicoes)
    assert texto.startswith(TITULOS_DO_PARECER[0])
    assert not texto.startswith("# ")


def test_parecer_fica_na_faixa_de_extensao(nome_do_perfil):
    minimo, maximo = ALVO_EXTENSAO["parecer"]
    palavras = contar_palavras(texto_parecer(contexto_de(nome_do_perfil, "parecer")))
    assert minimo <= palavras <= maximo


def test_parecer_repete_as_acoes_do_motor_na_mesma_ordem(nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, "parecer")
    texto = texto_parecer(contexto)
    esperadas = [
        f"{indice}. {acao.rotulo}"
        for indice, acao in enumerate(contexto.recomendacao.acoes, 1)
    ]
    assert all(linha in texto for linha in esperadas)
    posicoes = [texto.index(linha) for linha in esperadas]
    assert posicoes == sorted(posicoes)


def test_parecer_traz_o_aviso_de_decisao_humana(nome_do_perfil):
    """I9: nenhuma recomendação sai sem o aviso."""
    assert AVISO_DO_ANALISTA in texto_parecer(contexto_de(nome_do_perfil, "parecer"))


def test_parecer_nomeia_o_veto_quando_existe():
    texto = texto_parecer(contexto_de("veto_ambiental", "parecer"))
    assert "Embargo do IBAMA sobre imóvel oferecido em garantia" in texto
    assert "rebaixado de" in texto


def test_sem_rj_em_curso_nao_se_menciona_stay_period():
    texto = texto_parecer(contexto_de("moderado", "parecer"))
    assert "Não há Stay Period ativo." in texto
    assert "Stay Period ativo desde" not in texto


def test_com_rj_em_curso_o_stay_period_e_explicado():
    texto = texto_parecer(contexto_de("rj_com_stay_period", "parecer"))
    assert "Stay Period ativo desde" in texto
    assert "Bloqueado:" in texto and "Permitido:" in texto


def test_garantias_distinguem_extraconcursal_de_concursal(nome_do_perfil):
    texto = texto_parecer(contexto_de(nome_do_perfil, "parecer"))
    assert "cobertura extraconcursal" in texto
    assert "cobertura concursal" in texto
    assert "sobrevive a um cenário de recuperação judicial" in texto


def test_pd_e_rj_sao_apresentados_como_indicadores_distintos(nome_do_perfil):
    texto = texto_parecer(contexto_de(nome_do_perfil, "parecer"))
    assert "indicadores distintos" in texto


def test_secao_sem_conteudo_usa_a_frase_padrao():
    """Regra 6 dos prompts: nunca preencher com generalidade do setor."""
    contexto = contexto_de("excelente", "parecer")
    texto = texto_parecer(contexto)
    if not contexto.fatores_protecao:
        assert SEM_ELEMENTOS in texto


def test_score_fica_na_faixa_e_nao_usa_titulo_nem_lista(nome_do_perfil):
    texto = texto_score(contexto_de(nome_do_perfil, "score"))
    assert "##" not in texto
    assert "\n- " not in texto
    assert "**" not in texto


def test_recomendacao_cita_o_prazo_de_reavaliacao(nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, "recomendacao")
    texto = texto_recomendacao(contexto)
    assert contexto.recomendacao.reavaliar_em in texto
    assert contexto.recomendacao.rotulo in texto


def test_recomendacao_nao_repete_o_aviso_do_analista(nome_do_perfil):
    """A interface já exibe o aviso ao lado; repetir seria ruído (§3.c)."""
    assert AVISO_DO_ANALISTA not in texto_recomendacao(
        contexto_de(nome_do_perfil, "recomendacao")
    )


# ---------------------------------------------------------------------------
# Copiloto de fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("Qual a PD de 12 meses?", "PD 6m"),
        ("Como estão as garantias?", "extraconcursal"),
        ("Qual a exposição total?", "Exposição total"),
        ("Quais são as red flags?", "Fonte: motor de risco"),
        ("O que você recomenda?", "A decisão final é do analista responsável."),
    ],
)
def test_copiloto_devolve_o_bloco_pedido(pergunta, esperado):
    assert esperado in texto_copiloto(contexto_de("critico", "copiloto"), pergunta)


def test_copiloto_sem_casa_explica_a_indisponibilidade():
    resposta = texto_copiloto(
        contexto_de("moderado", "copiloto"), "fale sobre a lua", "ORCAMENTO"
    )
    assert "orçamento do modelo de linguagem atingido" in resposta
    assert "Consulte os painéis" in resposta


def test_copiloto_nao_inventa_numero(nome_do_perfil):
    contexto = contexto_de(nome_do_perfil, "copiloto")
    for pergunta in ("pd", "garantias", "exposição", "red flags", "recomendação", "score"):
        resposta = texto_copiloto(contexto, pergunta)
        assert verificar_fidelidade_numerica(resposta, contexto) == []


# ---------------------------------------------------------------------------
# Contrato do engine
# ---------------------------------------------------------------------------


def test_engine_emite_texto_e_exatamente_um_pedaco_de_uso(contexto_moderado):
    pedacos = list(DeterministicNarrativeEngine().gerar("parecer", contexto_moderado, 0.0))
    assert [p.tipo for p in pedacos].count("uso") == 1
    assert pedacos[-1].tipo == "uso"
    assert pedacos[-1].uso.entrada == 0
    assert "".join(p.texto for p in pedacos if p.tipo == "texto") == texto_parecer(
        contexto_moderado
    )


def test_engine_e_deterministico(contexto_moderado):
    """Sem relógio, sem aleatoriedade: duas chamadas dão o mesmo byte."""
    motor = DeterministicNarrativeEngine()
    primeira = [p.texto for p in motor.gerar("parecer", contexto_moderado, 0.0)]
    segunda = [p.texto for p in motor.gerar("parecer", contexto_moderado, 0.0)]
    assert primeira == segunda


def test_engine_ignora_deadline_porque_e_local(contexto_moderado):
    """O determinístico roda com `deadline=inf`; ele leva milissegundos."""
    pedacos = list(DeterministicNarrativeEngine().gerar("score", contexto_moderado, -1.0))
    assert any(p.tipo == "texto" for p in pedacos)
