"""Testes da API Flask, contra um warehouse sintetico em arquivo temporario."""
from __future__ import annotations

import pytest

from coleta import warehouse
from coleta.api import criar_app, fechar_conexao, validar_documento

# CNPJ com digito verificador valido, usado como alvo dos testes.
CNPJ = "11222333000181"


@pytest.fixture()
def app(tmp_path):
    caminho = tmp_path / "warehouse.duckdb"
    con = warehouse.conectar(caminho)
    con.execute(
        "INSERT INTO pgfn_divida (competencia, origem, documento, pf_mascarado,"
        " numero_inscricao, indicador_ajuizado, valor_consolidado) VALUES"
        f" ('2026T1','FGTS','{CNPJ}',false,'A',true,2500.0)"
    )
    con.execute(
        "INSERT INTO rf_empresas (competencia, cnpj_basico, razao_social,"
        " capital_social, porte) VALUES"
        f" ('2026-08','{CNPJ[:8]}','FAZENDA TESTE LTDA',750000.0,'03')"
    )
    con.execute(
        "INSERT INTO rf_estabelecimentos (competencia, cnpj_basico, cnpj,"
        " identificador_matriz_filial, situacao_cadastral, cnae_fiscal_principal,"
        " data_inicio_atividade, uf, municipio) VALUES"
        f" ('2026-08','{CNPJ[:8]}','{CNPJ}','1','02','0115600',"
        "  DATE '2019-03-10','GO','1234')"
    )
    warehouse.registrar_ingestao(con, "pgfn", "2026T1/FGTS", "pgfn_divida", 1)
    con.close()

    aplicacao = criar_app(
        COLETA_WAREHOUSE=str(caminho),
        COLETA_SOMENTE_LEITURA=True,
        TESTING=True,
    )
    yield aplicacao
    fechar_conexao(aplicacao)


@pytest.fixture()
def cliente(app):
    return app.test_client()


# ------------------------------------------------------------- validacao ----

@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("11.222.333/0001-81", CNPJ),
        (CNPJ, CNPJ),
        ("11222333", "11222333"),  # base de 8 digitos e aceita
    ],
)
def test_validar_documento_aceita(entrada, esperado):
    doc, erro = validar_documento(entrada)
    assert erro is None and doc == esperado


@pytest.mark.parametrize(
    "entrada,trecho_erro",
    [
        ("11222333000180", "digito verificador"),  # DV errado
        ("123", "8 digitos"),
        ("", "vazio"),
    ],
)
def test_validar_documento_rejeita(entrada, trecho_erro):
    doc, erro = validar_documento(entrada)
    assert doc is None and trecho_erro in erro


# -------------------------------------------------------------- endpoints ---

def test_saude_lista_fontes_carregadas(cliente):
    r = cliente.get("/api/v1/saude")
    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["status"] == "ok"
    assert corpo["somente_leitura"] is True
    assert corpo["consulta_ao_vivo"] is False
    assert set(corpo["fontes_carregadas"]) == {"pgfn", "receita"}


def test_fontes_mostra_ultima_carga(cliente):
    corpo = cliente.get("/api/v1/fontes").get_json()
    assert corpo["cargas"][0]["fonte"] == "pgfn"
    assert corpo["cargas"][0]["ultima_carga"] is not None


def test_features_de_um_documento(cliente):
    r = cliente.get(f"/api/v1/features/{CNPJ}")
    assert r.status_code == 200
    f = r.get_json()
    assert f["documento"] == CNPJ
    assert f["razao_social"] == "FAZENDA TESTE LTDA"
    assert f["divida_ativa_total"] == 2500.0
    assert f["flag_cnae_agro"] is True
    # Fontes nao carregadas continuam None, e nao zero.
    assert f["n_autos_infracao"] is None
    assert f["produtividade_municipal_cultura"] is None


def test_features_aceita_mascara_na_url(cliente):
    r = cliente.get("/api/v1/features/11.222.333%2F0001-81")
    assert r.status_code == 200
    assert r.get_json()["documento"] == CNPJ


def test_features_rejeita_dv_invalido(cliente):
    r = cliente.get("/api/v1/features/11222333000180")
    assert r.status_code == 400
    assert "digito verificador" in r.get_json()["detalhe"]


def test_features_rejeita_cultura_desconhecida(cliente):
    r = cliente.get(f"/api/v1/features/{CNPJ}?cultura=quinoa")
    assert r.status_code == 400


def test_features_cultura_valida_entra_no_retorno(cliente):
    f = cliente.get(f"/api/v1/features/{CNPJ}?cultura=milho").get_json()
    assert f["cultura_referencia"] == "milho"


def test_rede_ligada_em_somente_leitura_devolve_409(cliente):
    """Pedir consulta ao vivo com o banco read-only tem de falhar explicito."""
    r = cliente.get(f"/api/v1/features/{CNPJ}?rede=1")
    assert r.status_code == 409
    assert "somente leitura" in r.get_json()["detalhe"]


def test_documento_ausente_distingue_zero_de_faltante(cliente):
    """CNPJ fora da base tem de separar duas coisas diferentes.

    A PGFN esta carregada e o CNPJ nao aparece nela: a divida e zero, um fato.
    Ja o IBAMA nao foi carregado: ali nao se sabe, e o campo fica None.
    """
    f = cliente.get("/api/v1/features/11444777000161").get_json()
    assert f["divida_ativa_total"] == 0.0
    assert f["n_inscricoes"] == 0
    assert f["razao_social"] is None      # ausente do cadastro da Receita
    assert f["n_autos_infracao"] is None  # fonte nao carregada


# ------------------------------------------------------------------ lote ----

def test_lote_processa_validos_e_separa_invalidos(cliente):
    r = cliente.post(
        "/api/v1/features/lote",
        json={"documentos": [CNPJ, "11222333000180", "11444777000161"]},
    )
    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["total"] == 2
    assert len(corpo["erros"]) == 1
    assert corpo["erros"][0]["documento"] == "11222333000180"


def test_lote_sem_corpo_devolve_400(cliente):
    assert cliente.post("/api/v1/features/lote", json={}).status_code == 400


def test_lote_acima_do_limite_devolve_413(app):
    app.config["COLETA_LOTE_MAX"] = 2
    r = app.test_client().post(
        "/api/v1/features/lote", json={"documentos": [CNPJ, CNPJ, CNPJ]}
    )
    assert r.status_code == 413


def test_rota_inexistente_devolve_json(cliente):
    r = cliente.get("/api/v1/nao-existe")
    assert r.status_code == 404
    assert r.get_json()["erro"] == "rota nao encontrada"
