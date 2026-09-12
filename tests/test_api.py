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
        " numero_inscricao, indicador_ajuizado, valor_consolidado, tipo_devedor)"
        " VALUES"
        f" ('2026T1','FGTS','{CNPJ}',false,'A',true,2500.0,'PRINCIPAL')"
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


# ----------------------------------------------------------------- scoring --
#
# Os testes abaixo dependem de um campeao publicado em
# `src/modelos/artefatos/`. Quando nao ha (checkout limpo, CI sem o passo de
# treino), o contrato que vale e o 503 com texto acionavel -- e isso tambem e
# testado, em `test_score_sem_modelo_responde_503`.

pytest.importorskip("sklearn", reason="scoring exige requirements-ml.txt")


def _tem_campeao() -> bool:
    from src.modelos import artefatos

    return artefatos.nome_do_campeao() is not None


precisa_campeao = pytest.mark.skipif(
    not _tem_campeao(),
    reason="sem campeao publicado; rode treinar_todos --promover-melhor",
)


@precisa_campeao
def test_score_devolve_probabilidade_e_faixa(cliente):
    corpo = cliente.get(f"/api/v1/score/{CNPJ}").get_json()

    assert corpo["documento"] == CNPJ
    assert 0.0 <= corpo["probabilidade_inadimplencia"] <= 1.0
    # O score e a probabilidade em 0..1000, monotono e coerente com ela.
    assert corpo["score_risco"] == round(corpo["probabilidade_inadimplencia"] * 1000)
    assert corpo["faixa_risco"] in ("BAIXO", "MEDIO", "ALTO", "CRITICO")
    # O CNPJ da fixture tem divida ativa na PGFN: o sinal tem de aparecer.
    assert "divida ativa na PGFN" in corpo["sinais_observados"]
    # E as fontes que a fixture nao semeia tem de ser declaradas ausentes, para
    # o analista saber que o score foi dado sem elas.
    assert set(corpo["fontes_ausentes"]) >= {"bcb", "ibge", "clima"}


@precisa_campeao
def test_score_nao_satura_com_capital_social_zero(cliente, app):
    """Regressao do bug que colava o score em 1,000.

    91% das matrizes agro declaram capital social <= R$ 1. Com a razao
    divida/capital crua, o logit saturava e QUALQUER microempresa com divida
    virava CRITICO -- metade da carteira. Aqui o CNPJ tem R$ 2.500 de divida e
    capital zerado; o score tem de continuar dentro do intervalo aberto.
    """
    con = warehouse.conectar(app.config["COLETA_WAREHOUSE"])
    con.execute("UPDATE rf_empresas SET capital_social = 0.0")
    con.close()
    fechar_conexao(app)

    corpo = cliente.get(f"/api/v1/score/{CNPJ}").get_json()
    assert corpo["probabilidade_inadimplencia"] < 1.0
    assert corpo["score_risco"] < 1000


@precisa_campeao
def test_score_explicar_traz_contribuicoes(cliente):
    """O campeao e linear, entao a decomposicao coeficiente x valor e exata."""
    sem = cliente.get(f"/api/v1/score/{CNPJ}").get_json()
    com = cliente.get(f"/api/v1/score/{CNPJ}?explicar=1&features=1").get_json()

    assert "contribuicoes" not in sem
    assert com["contribuicoes"] and isinstance(com["contribuicoes"], dict)
    # `features=1` devolve o dicionario que alimentou o modelo, para auditoria.
    assert com["features"]["documento"] == CNPJ
    # Explicar nao pode mudar o numero.
    assert com["score_risco"] == sem["score_risco"]


@precisa_campeao
def test_score_lote_ordena_por_risco_e_isola_invalido(cliente):
    resposta = cliente.post(
        "/api/v1/score/lote",
        json={"documentos": [CNPJ, "11222333000180", "84461748000181"]},
    )
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["total"] == 2  # o do DV errado nao entra
    assert len(corpo["erros"]) == 1
    assert "digito verificador" in corpo["erros"][0]["detalhe"]
    # Carteira: o pior risco vem primeiro, que e o que o analista abre.
    scores = [s["score_risco"] for s in corpo["scores"]]
    assert scores == sorted(scores, reverse=True)


@precisa_campeao
def test_score_rejeita_documento_invalido_antes_de_carregar_modelo(cliente):
    resposta = cliente.get("/api/v1/score/123")
    assert resposta.status_code == 400
    assert "documento invalido" in resposta.get_json()["erro"]


@precisa_campeao
def test_modelo_expoe_metricas_e_avisa_sobre_alvo_sintetico(cliente):
    corpo = cliente.get("/api/v1/modelo").get_json()

    assert corpo["nome"] and corpo["metricas"]
    assert corpo["n_colunas_de_entrada"] > 0
    # O alvo sintetico tem de viajar junto com o numero, nao so no README.
    if corpo["alvo"] == "alvo_sintetico":
        assert "sintetico" in corpo["aviso_alvo"]


def test_score_sem_modelo_responde_503(app, tmp_path):
    """Sem artefato publicado a API de features continua de pe.

    O 503 tem de dizer o comando que resolve: um 500 generico aqui manda o
    time procurar bug no lugar errado.
    """
    from coleta import api_score

    vazio = tmp_path / "sem_artefatos"
    vazio.mkdir()
    with app.app_context():
        original = api_score._scorer
        api_score._scorer = lambda nome=None: (_ for _ in ()).throw(
            RuntimeError("modelo indisponivel. Treine e promova um campeao com ...")
        )
        try:
            resposta = app.test_client().get(f"/api/v1/score/{CNPJ}")
        finally:
            api_score._scorer = original

    assert resposta.status_code == 503
    assert "campeao" in resposta.get_json()["erro"]


def test_saude_declara_o_modelo_carregado(cliente):
    """Instancia que serve feature mas nao serve score nao esta inteira."""
    corpo = cliente.get("/api/v1/saude").get_json()
    assert "modelo" in corpo
