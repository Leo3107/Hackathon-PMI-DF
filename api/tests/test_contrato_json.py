"""Contrato de saída — `specs/01-modelo-de-dados.md` e §14 da spec do motor.

O JSON devolvido pelo Flask tem de bater campo a campo com o contrato
TypeScript: `snake_case` só dentro do Python, `camelCase` na fronteira. Um
campo com nome errado aqui quebra a tela sem quebrar teste nenhum do motor —
por isso este arquivo existe.
"""

from __future__ import annotations

import json

import pytest

from scoring import calcular_risco, comparar_avaliacoes

from fixtures import PERFIS, cliente_em_rj_com_stay_period, serie_em_deterioracao

_CHAVES_DA_AVALIACAO = {
    "clienteId",
    "dataReferencia",
    "scoreCalculado",
    "ratingCalculado",
    "ratingFinal",
    "vetosAtivos",
    "dimensoes",
    "pd",
    "riscoRJ",
    "stayPeriod",
    "exposicao",
    "tendencia",
    "redFlags",
    "recomendacao",
    "evidencias",
    "auditoria",
}


def _json(nome: str) -> dict:
    return calcular_risco(PERFIS[nome]()).json_do_contrato()


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_chaves_de_primeiro_nivel(nome):
    assert set(_json(nome)) == _CHAVES_DA_AVALIACAO


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_json_e_serializavel(nome):
    texto = json.dumps(_json(nome), ensure_ascii=False)
    assert json.loads(texto)["clienteId"]


def test_chaves_aninhadas_do_contrato():
    dados = _json("em_deterioracao")

    assert set(dados["pd"]) == {"pd6m", "pd12m", "pd24m", "metodo"}
    assert set(dados["auditoria"]) == {"somaImpactos", "scoreReconstruido", "diferenca"}
    assert {
        "probabilidade12m",
        "eventoJaOcorrido",
        "rjIndex",
        "rjIndexEfetivo",
        "elegivel",
        "motivoInelegibilidade",
        "sinais",
    } == set(dados["riscoRJ"])

    exposicao = dados["exposicao"]
    assert {
        "exposicaoTotal",
        "limiteAprovado",
        "limiteUtilizadoPct",
        "aVencer90d",
        "emAtraso",
        "porTipoOperacao",
        "valorExtraconcursal",
        "valorConcursal",
        "coberturaExtraconcursal",
        "coberturaTotal",
        "exposicaoProtegida",
        "exposicaoEmRisco",
        "exposicaoEmRiscoEmRJ",
    } == set(exposicao)

    dimensao = dados["dimensoes"][0]
    assert {
        "id",
        "rotulo",
        "score",
        "peso",
        "contribuicao",
        "tendencia",
        "fatores",
        "fontes",
        "saturou",
    } == set(dimensao)

    fator = next(f for d in dados["dimensoes"] for f in d["fatores"])
    assert {
        "id",
        "dimensao",
        "rotulo",
        "detalhe",
        "pontos",
        "direcao",
        "impactoGlobal",
        "impactoGlobalAjustado",
        "fonte",
        "evidenciaIds",
    } == set(fator)

    red_flag = dados["redFlags"][0]
    assert {
        "id",
        "severidade",
        "titulo",
        "descricao",
        "data",
        "fonte",
        "impactoEmPontos",
        "status",
        "evidenciaIds",
        "fatorId",
    } == set(red_flag)

    recomendacao = dados["recomendacao"]
    assert {"codigo", "rotulo", "acoes", "prazoReavaliacaoDias", "explicacao", "aviso"} == set(
        recomendacao
    )
    assert set(recomendacao["acoes"][0]) == {"id", "rotulo", "detalhe", "prioridade"}
    #: o LLM preenche `explicacao` em runtime; o motor nunca escreve prosa
    assert recomendacao["explicacao"] is None


def test_stay_period_no_contrato():
    dados = calcular_risco(cliente_em_rj_com_stay_period()).json_do_contrato()
    assert set(dados["stayPeriod"]) == {
        "ativo",
        "dataDeferimento",
        "diasDecorridos",
        "diasRestantes",
        "bloqueios",
        "permitido",
    }
    assert set(dados["vetosAtivos"][0]) == {
        "id",
        "rotulo",
        "efeito",
        "justificativa",
        "evidenciaIds",
    }


def test_comparacao_no_contrato():
    serie = serie_em_deterioracao()
    comparacao = comparar_avaliacoes(
        calcular_risco(serie[-2]), calcular_risco(serie[-1])
    ).json_do_contrato()
    assert set(comparacao) == {
        "clienteId",
        "dataAnterior",
        "dataAtual",
        "scoreAnterior",
        "scoreAtual",
        "deltaScore",
        "fatores",
        "diferencaDeFechamento",
    }
    assert set(comparacao["fatores"][0]) == {
        "fatorId",
        "dimensao",
        "rotulo",
        "detalhe",
        "impactoAnterior",
        "impactoAtual",
        "delta",
        "situacao",
    }


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_nenhuma_chave_em_snake_case_vaza_para_o_json(nome):
    def visitar(no):
        if isinstance(no, dict):
            for chave, valor in no.items():
                #: chaves que são valores de enum (`VENDA_A_PRAZO`) são dado, não campo
                if not chave.isupper():
                    assert "_" not in chave, chave
                visitar(valor)
        elif isinstance(no, list):
            for item in no:
                visitar(item)

    visitar(_json(nome))
