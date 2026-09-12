"""Coleta real ligada ao fluxo de due diligence — `POST /api/due-diligence`.

**Sem rede e sem warehouse.** A porta de coleta é injetada em
`app.extensions["lastro.coleta"]` por um dublê que devolve um `Features` montado
à mão. O que se testa é o contrato da rota, não o DuckDB de outro workstream.

A pergunta que estes testes respondem é sempre a mesma: *a resposta diz de onde
veio o número, e quanto do número ela pôde apurar?*
"""

from __future__ import annotations

import pytest
from app import criar_app
from coleta.models import Features
from models.enums import DimensaoId
from routes.due_diligence import CHAVE_COLETA, ORIGEM_COLETA_REAL, ORIGEM_SIMULADO

from test_repositorio import fonte_de_teste

CNPJ_FORA_DO_DATASET = "12.345.678/0001-95"
CNPJ_INVALIDO = "12.345.678/0001-91"
SO_DIGITOS = "12345678000195"


class ColetaDublê:
    """Porta de coleta de teste: devolve o `Features` que lhe derem."""

    def __init__(self, features: Features | None) -> None:
        self.features = features
        self.consultas: list[str] = []

    def features_de(self, documento: str, cultura: str | None = None):
        self.consultas.append(documento)
        return self.features


def features_uteis() -> Features:
    """PGFN, Receita e IBAMA responderam; jurídico, agro e interno, não."""
    return Features(
        documento=SO_DIGITOS,
        cnpj_basico=SO_DIGITOS[:8],
        razao_social="Fazenda Boa Vista Agropecuária Ltda",
        uf="GO",
        municipio_ibge="5208707",
        fontes_disponiveis=["pgfn", "receita", "ibama_autos", "ibama_embargos"],
        divida_ativa_total=2_400_000.0,
        divida_ativa_ajuizada=1_100_000.0,
        n_inscricoes=7,
        delta_divida_2_trimestres=600_000.0,
        flag_divida_fgts=True,
        idade_empresa_meses=96,
        capital_social=500_000.0,
        situacao_cadastral="02",
        flag_situacao_irregular=False,
        cnae_principal="0111301",
        flag_cnae_agro=True,
        n_autos_infracao=2,
        flag_embargo_ativo=False,
    )


@pytest.fixture
def fonte_simulada():
    return fonte_de_teste()


@pytest.fixture
def documento_de_prospect(fonte_simulada):
    return fonte_simulada.prospects[0].documento


@pytest.fixture
def app_com_coleta(fonte_simulada):
    def montar(features: Features | None):
        app = criar_app(fonte=fonte_simulada, testando=True)
        dublê = ColetaDublê(features)
        app.extensions[CHAVE_COLETA] = dublê
        return app, dublê

    return montar


def _consultar(app, documento, **corpo):
    with app.test_client() as cliente:
        return cliente.post(
            "/api/due-diligence", json={"documento": documento, **corpo}
        )


# ---------------------------------------------------------------------------
# Origem — os dois caminhos
# ---------------------------------------------------------------------------


def test_documento_do_dataset_devolve_origem_simulado(app_com_coleta, documento_de_prospect):
    app, dublê = app_com_coleta(features_uteis())
    corpo = _consultar(app, documento_de_prospect).get_json()
    assert corpo["encontrado"] is True
    assert corpo["origem"] == ORIGEM_SIMULADO
    assert "cobertura" not in corpo
    assert dublê.consultas == []  # o simulado tem precedência e nem consulta


def test_documento_fora_do_dataset_devolve_origem_coleta_real(app_com_coleta):
    app, dublê = app_com_coleta(features_uteis())
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    assert corpo["encontrado"] is True
    assert corpo["origem"] == ORIGEM_COLETA_REAL
    assert dublê.consultas == [CNPJ_FORA_DO_DATASET]


def test_coleta_sem_resposta_nao_e_erro(app_com_coleta):
    app, _ = app_com_coleta(None)
    resposta = _consultar(app, CNPJ_FORA_DO_DATASET)
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert corpo["encontrado"] is False
    assert corpo["origem"] == ORIGEM_COLETA_REAL
    assert "avaliacao" not in corpo


def test_documento_invalido_continua_400(app_com_coleta):
    app, dublê = app_com_coleta(features_uteis())
    resposta = _consultar(app, CNPJ_INVALIDO)
    assert resposta.status_code == 400
    assert dublê.consultas == []


# ---------------------------------------------------------------------------
# Cegueira total não vira nota
# ---------------------------------------------------------------------------


def test_features_vazio_nao_produz_avaliacao_na_rota(app_com_coleta):
    app, _ = app_com_coleta(Features(documento=SO_DIGITOS))
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    assert corpo["encontrado"] is False
    assert "avaliacao" not in corpo
    assert corpo["cobertura"]["analisavel"] is False
    assert corpo["cobertura"]["coberturaPonderada"] == 0.0


# ---------------------------------------------------------------------------
# Cobertura na resposta
# ---------------------------------------------------------------------------


def test_resposta_real_carrega_o_relatorio_de_cobertura(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    cobertura = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()["cobertura"]
    por_dimensao = {d["dimensao"]: d for d in cobertura["dimensoes"]}

    assert cobertura["analisavel"] is True
    assert por_dimensao[DimensaoId.FISCAL.value]["status"] == "PARCIAL"
    assert por_dimensao[DimensaoId.CADASTRAL.value]["status"] == "PARCIAL"
    assert por_dimensao[DimensaoId.AMBIENTAL.value]["status"] == "PARCIAL"
    assert por_dimensao[DimensaoId.JURIDICO.value]["status"] == "CEGA"
    assert por_dimensao[DimensaoId.AGROCLIMATICO.value]["status"] == "CEGA"
    assert por_dimensao[DimensaoId.COMPORTAMENTAL.value]["status"] == "CEGA"
    assert por_dimensao[DimensaoId.GARANTIAS.value]["status"] == "CEGA"


def test_dimensao_comportamental_de_prospect_e_sempre_cega_e_diz_por_que(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    cobertura = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()["cobertura"]
    comportamental = next(
        d for d in cobertura["dimensoes"] if d["dimensao"] == DimensaoId.COMPORTAMENTAL.value
    )
    assert comportamental["pesoAplicado"] == 0.0
    assert "Krill Tech" in comportamental["justificativa"]


def test_pesos_aplicados_somam_um_e_o_score_fecha(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    soma = sum(d["pesoAplicado"] for d in corpo["cobertura"]["dimensoes"])
    assert soma == pytest.approx(1.0, abs=1e-6)
    assert abs(corpo["avaliacao"]["auditoria"]["diferenca"]) < 0.5


def test_score_real_nao_e_o_score_com_dimensao_cega_valendo_mil(app_com_coleta):
    """Quatro dimensões cegas valendo 1000 dariam quase nota máxima."""
    app, _ = app_com_coleta(features_uteis())
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    com_renormalizacao = corpo["avaliacao"]["scoreCalculado"]

    # O que o motor devolveria se cada dimensão cega valesse 1000:
    contribuicoes = {
        d["id"]: (d["score"], d["peso"]) for d in corpo["avaliacao"]["dimensoes"]
    }
    canonicos = {"comportamental": 0.22, "juridico": 0.20, "fiscal": 0.14,
                 "agroclimatico": 0.15, "cadastral": 0.10, "ambiental": 0.09,
                 "garantias": 0.10}
    sem_renormalizacao = sum(
        contribuicoes[dimensao][0] * peso for dimensao, peso in canonicos.items()
    )
    assert com_renormalizacao < sem_renormalizacao
    assert com_renormalizacao < 1000.0


def test_divida_ativa_sem_operacao_pretendida_e_declarada_nao_apurada(app_com_coleta):
    """R$ 2,4 mi de dívida ativa não pontuam sem denominador — e isso aparece.

    `divida_ativa` é razão sobre a exposição. Sem o valor da operação
    pretendida o fator não se materializa, e o relatório de cobertura é o que
    impede a tela de ler isso como "sem problema fiscal".
    """
    app, _ = app_com_coleta(features_uteis())
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    fiscal = next(
        d for d in corpo["cobertura"]["dimensoes"] if d["dimensao"] == "fiscal"
    )
    cegos = {c["fator"]: c["motivo"] for c in fiscal["fatoresCegos"]}
    assert "divida_ativa" in cegos
    assert "valorOperacaoPretendida" in cegos["divida_ativa"]
    ids = {f["id"] for d in corpo["avaliacao"]["dimensoes"] for f in d["fatores"]}
    assert "divida_ativa" not in ids


def test_com_a_operacao_pretendida_a_divida_ativa_derruba_o_rating(app_com_coleta):
    """O mesmo CNPJ, agora com denominador: a dívida ativa pesa e o rating cai."""
    app, _ = app_com_coleta(features_uteis())
    sem = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    com = _consultar(
        app, CNPJ_FORA_DO_DATASET, valorOperacaoPretendida=3_000_000.0
    ).get_json()
    ids = {f["id"] for d in com["avaliacao"]["dimensoes"] for f in d["fatores"]}
    assert "divida_ativa" in ids
    assert com["avaliacao"]["scoreCalculado"] < sem["avaliacao"]["scoreCalculado"]
    assert com["avaliacao"]["ratingFinal"] != "A"


# ---------------------------------------------------------------------------
# Estágios do pipeline refletem a cobertura, não o relógio
# ---------------------------------------------------------------------------


def test_estagios_marcam_falha_nas_dimensoes_cegas(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    estagios = {e["estagio"]: e for e in _consultar(app, CNPJ_FORA_DO_DATASET).get_json()["estagios"]}
    assert estagios["FISCAL"]["status"] == "ok"
    assert estagios["CADASTRAL"]["status"] == "ok"
    assert estagios["AMBIENTAL"]["status"] == "ok"
    assert estagios["JURIDICO"]["status"] == "falha"
    assert estagios["AGROCLIMATICO"]["status"] == "falha"
    assert estagios["INTERNO"]["status"] == "falha"
    assert estagios["SCORE"]["status"] == "ok"


def test_estagio_apurado_nomeia_a_fonte(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    estagios = {e["estagio"]: e for e in _consultar(app, CNPJ_FORA_DO_DATASET).get_json()["estagios"]}
    assert any("PGFN" in achado for achado in estagios["FISCAL"]["achados"])
    assert any("IBAMA" in achado for achado in estagios["AMBIENTAL"]["achados"])


# ---------------------------------------------------------------------------
# Valor da operação pretendida
# ---------------------------------------------------------------------------


def test_valor_pretendido_entra_como_exposicao_e_abre_garantias(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    corpo = _consultar(
        app, CNPJ_FORA_DO_DATASET, valorOperacaoPretendida=3_000_000.0
    ).get_json()
    assert corpo["avaliacao"]["exposicao"]["exposicaoTotal"] == 3_000_000.0
    garantias = next(
        d for d in corpo["cobertura"]["dimensoes"] if d["dimensao"] == DimensaoId.GARANTIAS.value
    )
    assert garantias["status"] != "CEGA"


def test_sem_valor_pretendido_a_exposicao_e_zero(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    corpo = _consultar(app, CNPJ_FORA_DO_DATASET).get_json()
    assert corpo["avaliacao"]["exposicao"]["exposicaoTotal"] == 0.0


def test_valor_pretendido_invalido_e_400(app_com_coleta):
    app, _ = app_com_coleta(features_uteis())
    resposta = _consultar(app, CNPJ_FORA_DO_DATASET, valorOperacaoPretendida=-5)
    assert resposta.status_code == 400


# ---------------------------------------------------------------------------
# Registro do Blueprint da coleta
# ---------------------------------------------------------------------------


def test_blueprint_da_coleta_registrado_sob_api_coleta(fonte_simulada):
    app = criar_app(fonte=fonte_simulada, testando=True)
    regras = {str(regra) for regra in app.url_map.iter_rules()}
    assert "/api/coleta/saude" in regras
    assert "/api/coleta/fontes" in regras
    assert any(regra.startswith("/api/coleta/features/") for regra in regras)


def test_servico_sobe_sem_warehouse(fonte_simulada):
    """Sem carga feita, a coleta degrada para 503 — a API não cai."""
    app = criar_app(fonte=fonte_simulada, testando=True)
    with app.test_client() as cliente:
        assert cliente.get("/api/saude").status_code == 200
        assert cliente.get("/api/coleta/saude").status_code in (200, 503)


def test_rotas_do_lastro_continuam_intactas(fonte_simulada):
    app = criar_app(fonte=fonte_simulada, testando=True)
    with app.test_client() as cliente:
        assert cliente.get("/api/carteira").status_code == 200
        assert cliente.get("/api/clientes").status_code == 200
