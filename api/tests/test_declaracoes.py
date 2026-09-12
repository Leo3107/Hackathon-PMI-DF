"""Declaração de operação do analista e semeadura de demonstração — Tarefa 3.

Usa o dataset real (`api/data/`, Tarefa 2) porque a mecânica só existe para
CNPJs com `Features` — o stub de `tests/fixtures.py` (motor puro) nunca tem
`fonte.features_por_cliente`, e por isso não é afetado por nada aqui (ver
`test_repositorio.py`, que continua verde).
"""

from __future__ import annotations

import pytest
from app import criar_app
from models.enums import TipoGarantia
from repository import DeclaracaoDeOperacao, GarantiaDeclarada, RepositorioEmMemoria
from repository.declaracoes import RepositorioDeDeclaracoes, normalizar_documento
from repository.memoria import QUANTIDADE_POR_PERFIL_DEMO

import data


# ---------------------------------------------------------------------------
# `RepositorioDeDeclaracoes` isolado
# ---------------------------------------------------------------------------


def test_declarar_e_obter():
    repo = RepositorioDeDeclaracoes()
    declaracao = DeclaracaoDeOperacao(
        documento="12.345.678/0001-90", valor_operacao=500_000.0, prazo_meses=12
    )
    repo.declarar(declaracao)
    assert repo.obter("12345678000190") == declaracao
    assert len(repo) == 1


def test_normalizar_documento_ignora_pontuacao():
    assert normalizar_documento("12.345.678/0001-90") == "12345678000190"


def test_remover_documento_nao_declarado_devolve_falso():
    repo = RepositorioDeDeclaracoes()
    assert repo.remover("00000000000000") is False


def test_limpar_apenas_demonstracao_preserva_declaracao_real():
    repo = RepositorioDeDeclaracoes()
    repo.declarar(
        DeclaracaoDeOperacao(documento="1" * 14, valor_operacao=1.0, prazo_meses=1, demonstracao=True)
    )
    repo.declarar(
        DeclaracaoDeOperacao(documento="2" * 14, valor_operacao=2.0, prazo_meses=2, demonstracao=False)
    )
    removidos = repo.limpar(apenas_demonstracao=True)
    assert removidos == 1
    assert repo.obter("1" * 14) is None
    assert repo.obter("2" * 14) is not None


def test_garantias_do_motor_derivam_natureza_e_valor_atualizado():
    declaracao = DeclaracaoDeOperacao(
        documento="1" * 14,
        valor_operacao=100_000.0,
        prazo_meses=6,
        garantias=(GarantiaDeclarada(tipo=TipoGarantia.CPR_FINANCEIRA, valor=80_000.0),),
    )
    garantias = declaracao.garantias_do_motor("2026-09-12")
    assert len(garantias) == 1
    assert garantias[0].valor_declarado == 80_000.0
    assert garantias[0].valor_atualizado < garantias[0].valor_declarado  # haircut aplicado


# ---------------------------------------------------------------------------
# `RepositorioEmMemoria` com o dataset real — a carteira nasce vazia
# ---------------------------------------------------------------------------


@pytest.fixture
def repo() -> RepositorioEmMemoria:
    return RepositorioEmMemoria()


def test_carteira_nasce_vazia_sem_declaracao(repo):
    assert repo.listar_clientes() == []


def test_declarar_operacao_poe_o_documento_na_carteira(repo):
    documento = next(iter(data.FEATURES_POR_CLIENTE))
    repo.declaracoes.declarar(
        DeclaracaoDeOperacao(documento=documento, valor_operacao=200_000.0, prazo_meses=12)
    )
    ids = {cliente.id for cliente in repo.listar_clientes()}
    assert documento in ids


def test_documento_sem_declaracao_continua_consultavel_fora_da_carteira(repo):
    documento = next(iter(data.FEATURES_POR_CLIENTE))
    assert repo.obter_cliente(documento) is not None
    assert documento not in {c.id for c in repo.listar_clientes()}


def test_declaracao_abre_a_dimensao_de_garantias(repo):
    from models.enums import DimensaoId

    documento = next(iter(data.FEATURES_POR_CLIENTE))
    sem = repo.avaliar(documento)
    repo.declaracoes.declarar(
        DeclaracaoDeOperacao(
            documento=documento,
            valor_operacao=300_000.0,
            prazo_meses=12,
            garantias=(GarantiaDeclarada(tipo=TipoGarantia.CPR_FINANCEIRA, valor=200_000.0),),
        )
    )
    com = repo.avaliar(documento)
    garantias_dim = next(d for d in com.dimensoes if d.id is DimensaoId.GARANTIAS)
    assert garantias_dim.peso > 0.0
    assert com.exposicao.exposicao_total > sem.exposicao.exposicao_total


def test_semear_carteira_de_demonstracao_declara_cerca_de_20_documentos(repo):
    semeados = repo.semear_carteira_de_demonstracao()
    assert 15 <= len(semeados) <= 25
    assert len(repo.listar_clientes()) == len(semeados)
    perfis = {data.PERFIL_POR_CLIENTE[doc] for doc in semeados}
    assert perfis == set(QUANTIDADE_POR_PERFIL_DEMO)


def test_limpar_declaracoes_de_demonstracao_esvazia_a_carteira(repo):
    repo.semear_carteira_de_demonstracao()
    assert repo.listar_clientes() != []
    repo.limpar_declaracoes_de_demonstracao()
    assert repo.listar_clientes() == []


def test_semeadura_e_deterministica():
    repo_a = RepositorioEmMemoria()
    repo_b = RepositorioEmMemoria()
    assert sorted(repo_a.semear_carteira_de_demonstracao()) == sorted(
        repo_b.semear_carteira_de_demonstracao()
    )


# ---------------------------------------------------------------------------
# Rotas `/api/carteira/semear` e a inversa
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    return criar_app(testando=True)


@pytest.fixture
def client(app):
    return app.test_client()


def test_rota_semear_declara_e_avisa_que_e_demonstracao(client):
    resposta = client.post("/api/carteira/semear")
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["semeado"] is True
    assert "DEMONSTRA" in corpo["aviso"].upper()
    assert corpo["totalDeclarado"] == len(corpo["documentos"])
    assert corpo["totalDeclarado"] > 0


def test_carteira_responde_com_clientes_depois_de_semear(client):
    client.post("/api/carteira/semear")
    resposta = client.post("/api/carteira")
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["totalClientes"] > 0
    assert corpo["exposicaoTotal"] > 0


def test_rota_limpar_semeadura_esvazia_a_carteira_de_novo(client):
    client.post("/api/carteira/semear")
    resposta = client.post("/api/carteira/semear/limpar")
    assert resposta.status_code == 200
    assert resposta.get_json()["limpo"] is True

    carteira = client.post("/api/carteira").get_json()
    assert carteira["totalClientes"] == 0
