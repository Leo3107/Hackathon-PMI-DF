"""Testes da camada de modelagem: contrato de inferencia e armadilhas do dado.

Rodam sem rede e sem treinar nada pesado -- os que precisam de modelo usam os
artefatos de `src/modelos/artefatos/`, e os que precisam de ajuste treinam uma
logistica minima em memoria.

    pip install -r requirements-ml.txt -r requirements-dev.txt && pytest -q

O foco nao e "o modelo acerta" (com `alvo_sintetico` isso nao significa nada), e
sim as tres coisas que quebram silenciosamente entre o treino e a API:

1. o CSV do mock le os codigos zero-padded como string, nao como int;
2. o split nunca coloca o mesmo municipio nos dois lados;
3. o pipeline salvo pontua o dicionario de `build_features` como ele vem --
   com `None`, fora de ordem, com campo a mais e com campo a menos.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.modelos import artefatos, avaliacao, dados, esquema, preparo

pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")


# ------------------------------------------------------------------ esquema --

def test_rotulo_e_chaves_ficam_fora_das_features():
    """`perfil` e o rotulo do gerador sintetico: usar como feature e vazamento."""
    entrada = esquema.features_de_entrada()
    for proibida in ("perfil", "documento", "cnpj_basico", "municipio_ibge", "alvo_sintetico"):
        assert proibida not in entrada


def test_municipio_ibge_fica_fora_mas_e_o_grupo():
    assert esquema.GRUPO == "municipio_ibge"
    assert esquema.GRUPO in esquema.COLUNAS_EXCLUIDAS


# -------------------------------------------------------------------- dados --

@pytest.fixture(scope="module")
def mock():
    if not dados.MOCK_CSV.exists():
        pytest.skip(f"mock ausente em {dados.MOCK_CSV}")
    return dados.carregar()


def test_codigos_zero_padded_sobrevivem_a_leitura(mock):
    """`porte` '03' nao pode virar 3, senao nada casa com o que a API manda."""
    X, _, _ = mock
    for coluna in ("porte", "situacao_cadastral", "cnae_principal", "natureza_juridica"):
        valores = X[coluna].dropna().astype(str)
        assert not valores.empty
        assert valores.map(lambda v: not v.lstrip("0") or v[0] == "0" or v.isdigit()).all()
    # A prova real: existe ao menos um codigo que COMECA com zero.
    assert X["porte"].dropna().astype(str).str.startswith("0").any()
    assert X["cnae_principal"].dropna().astype(str).str.startswith("0").any()


def test_split_nao_compartilha_municipio(mock):
    """Municipio nos dois lados infla o AUC: as 12 features municipais repetem."""
    X, y, g = mock
    p = dados.separar_treino_teste(X, y, g, fracao_teste=0.2, semente=7)
    assert p.resumo()["municipios_em_comum"] == 0
    assert len(p.y_treino) + len(p.y_teste) == len(y)


def test_cv_nao_compartilha_municipio_em_nenhum_fold(mock):
    X, y, g = mock
    cv = dados.cv_agrupado(5, semente=7)
    for treino, validacao in cv.split(X, y, groups=g):
        assert not (set(g.iloc[treino]) & set(g.iloc[validacao]))
        # Estratificado: fold sem positivo tornaria o AUC indefinido.
        assert y.iloc[validacao].sum() > 0


def test_flag_booleana_aceita_bool_texto_e_numero():
    quadro = pd.DataFrame(
        {"flag_embargo_ativo": [True, False, "True", "false", "1", "0", None, np.nan]}
    )
    saida = dados.normalizar_quadro(quadro)["flag_embargo_ativo"]
    assert saida.tolist()[:6] == [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    # Ausente continua ausente: "nao sei" nao e "nao".
    assert saida.isna().tolist()[6:] == [True, True]


def test_quadro_de_registros_tolera_falta_sobra_e_desordem():
    registro = {
        "n_socios": 3,
        "documento": "12345678000190",  # chave: nao e feature
        "uf": "MT",
        "campo_inexistente": "ignorado",
    }
    quadro = dados.quadro_de_registros(registro)
    assert list(quadro.columns) == esquema.features_de_entrada()
    assert len(quadro) == 1
    assert quadro["n_socios"].iloc[0] == 3
    assert quadro["divida_ativa_total"].isna().all()


# ------------------------------------------------------------------ preparo --

def test_toda_coluna_do_esquema_chega_ao_modelo():
    """Guarda contra feature coletada e silenciosamente ignorada.

    `esquema.features_de_entrada()` le `esquema.csv` em tempo de execucao, mas
    `preparo` tem listas explicitas. Quando a coleta publicou
    `divida_ativa_corresponsavel`, a coluna entrou em `X` e o `transform` a
    descartou sem dizer nada -- feature que custa consulta e nao rende AUC.
    Este teste quebra na proxima vez, em vez de deixar passar.
    """
    ignoradas, orfas = preparo.conferir_cobertura_do_esquema()
    assert ignoradas == [], (
        f"colunas do esquema que a engenharia nao le: {ignoradas}. "
        "Ligue em ZERO_SEMANTICO ou MANTER_NAN."
    )
    assert orfas == [], f"a engenharia referencia colunas inexistentes: {orfas}"


def test_fit_avisa_quando_coluna_do_esquema_fica_de_fora(monkeypatch):
    """O aviso em `fit` e a rede de seguranca de quem nao roda os testes."""
    monkeypatch.setattr(
        preparo, "colunas_consumidas", lambda: set(esquema.features_de_entrada()) - {"uf"}
    )
    vazio = dados.quadro_de_registros({c: None for c in esquema.features_de_entrada()})
    with pytest.warns(UserWarning, match="uf"):
        preparo.EngenhariaAgro().fit(vazio)


def test_indicador_de_bloco_marca_ausencia_em_conjunto():
    """A ausencia vem em bloco; o indicador tem de ser por bloco, nao por coluna."""
    sem_clima = {c: None for c in esquema.features_de_entrada()}
    com_clima = dict(sem_clima, **{
        "precipitacao_acumulada_ciclo": 900.0,
        "precipitacao_vs_normal_climatologica": -0.1,
        "dias_secos_consecutivos_max": 12,
        "anomalia_na_fase_critica": 0.05,
    })
    quadro = dados.quadro_de_registros([sem_clima, com_clima])
    saida = preparo.EngenhariaAgro().fit(quadro).transform(quadro)
    assert saida["falta_clima"].tolist() == [1.0, 0.0]
    assert saida["n_blocos_ausentes"].tolist() == [4.0, 3.0]


def test_zero_semantico_preenche_e_nan_genuino_sobrevive():
    vazio = dados.quadro_de_registros({c: None for c in esquema.features_de_entrada()})
    saida = preparo.EngenhariaAgro().fit(vazio).transform(vazio)
    # Desvio ausente = desvio neutro = zero (mesma escolha do gerador do alvo).
    assert saida["desvio_produtividade_vs_media_5a"].iloc[0] == 0.0
    assert saida["n_protestos_ativos"].iloc[0] == 0.0
    # Capital social ausente e ignorancia de verdade: segue NaN para o imputador.
    assert math.isnan(saida["log1p_capital_social_centrado"].iloc[0])


def test_gemeas_colineares_nao_chegam_a_matriz():
    vazio = dados.quadro_de_registros({c: None for c in esquema.features_de_entrada()})
    colunas = set(preparo.EngenhariaAgro().fit(vazio).transform(vazio).columns)
    for removida in (*preparo.SUBSTITUIDAS_POR_DERIVADA, *preparo.REMOVIDAS_POR_COLINEARIDADE):
        assert removida not in colunas, f"{removida} deveria ter sido descartada"
    # O que as substitui continua la.
    assert "log1p_divida_ativa_total" in colunas
    assert "razao_divida_ajuizada" in colunas


def test_booster_recebe_nan_e_linear_nao(mock):
    X, y, _ = mock
    amostra = X.head(400)
    com_nan = preparo.construir_preprocessador(nan_nativo=True, escalar=False)
    sem_nan = preparo.construir_preprocessador(nan_nativo=False, escalar=True)
    assert np.isnan(com_nan.fit_transform(amostra, y.head(400))).sum() > 0
    assert np.isnan(sem_nan.fit_transform(amostra, y.head(400))).sum() == 0


def test_categoria_nunca_vista_nao_explode(mock):
    """CNAE novo em producao tem de cair no balde de infrequente, nao levantar."""
    X, y, _ = mock
    pre = preparo.construir_preprocessador(nan_nativo=True, escalar=False)
    pre.fit(X, y)
    novo = X.head(1).copy()
    novo.loc[novo.index[0], "cnae_principal"] = "9999999"
    novo.loc[novo.index[0], "uf"] = "ZZ"
    assert pre.transform(novo).shape[1] == pre.transform(X.head(1)).shape[1]


# --------------------------------------------------------------- avaliacao --

def test_metricas_cobrem_perda_e_metrica_pedidas():
    y = np.array([0, 0, 1, 0, 1, 0, 0, 1])
    p = np.array([0.05, 0.1, 0.9, 0.2, 0.7, 0.05, 0.3, 0.6])
    m = avaliacao.metricas(y, p)
    assert m["auc"] == pytest.approx(1.0)
    assert 0 < m["logloss"] < 1  # entropia cruzada binaria
    assert m["ks"] == pytest.approx(1.0)
    assert m["gini"] == pytest.approx(1.0)


def test_metricas_nao_explodem_em_fold_de_uma_classe():
    m = avaliacao.metricas(np.zeros(5, dtype=int), np.full(5, 0.1))
    assert math.isnan(m["auc"])
    assert math.isfinite(m["logloss"])


# -------------------------------------------------------------- inferencia --

MODELOS = ["regressao_logistica", "random_forest", "xgboost", "lightgbm"]


def _scorer(nome):
    from src.modelos.inferencia import Scorer

    try:
        return Scorer.carregar(nome)
    except (FileNotFoundError, TypeError) as exc:
        pytest.skip(f"artefato '{nome}' indisponivel: {exc}")


@pytest.mark.parametrize("nome", MODELOS)
def test_pontua_registro_totalmente_vazio(nome):
    """CNPJ cuja coleta nao achou nada ainda recebe score, nunca excecao."""
    vazio = {c: None for c in esquema.colunas_brutas() if c != esquema.ALVO}
    vazio["documento"] = "98765432000188"
    saida = _scorer(nome).pontuar(vazio)
    assert 0.0 <= saida["probabilidade_inadimplencia"] <= 1.0
    assert 0 <= saida["score_risco"] <= 1000
    assert saida["faixa_risco"] in artefatos.FAIXAS
    assert sorted(saida["fontes_ausentes"]) == sorted(esquema.BLOCOS_AUSENCIA)


@pytest.mark.parametrize("nome", MODELOS)
def test_dict_e_lista_dao_o_mesmo_score(nome):
    scorer = _scorer(nome)
    registro = {"documento": "11111111000111", "uf": "MT", "capital_social": 500000.0}
    um = scorer.pontuar(registro)
    lote = scorer.pontuar([registro, registro])
    assert isinstance(um, dict) and isinstance(lote, list) and len(lote) == 2
    assert um["probabilidade_inadimplencia"] == lote[0]["probabilidade_inadimplencia"]


@pytest.mark.parametrize("nome", MODELOS)
def test_ordem_das_chaves_nao_altera_o_score(nome):
    scorer = _scorer(nome)
    registro = {
        "documento": "22222222000122", "uf": "GO", "divida_ativa_total": 120000.0,
        "idade_empresa_meses": 90, "flag_situacao_irregular": True, "n_protestos_ativos": 2,
    }
    invertido = dict(reversed(list(registro.items())))
    assert (
        scorer.pontuar(registro)["probabilidade_inadimplencia"]
        == scorer.pontuar(invertido)["probabilidade_inadimplencia"]
    )


@pytest.mark.parametrize("nome", MODELOS)
def test_score_cresce_com_o_risco(nome):
    """Monotonia grosseira: um CNPJ ruim em todos os eixos nao pode pontuar menos."""
    scorer = _scorer(nome)
    limpo = {
        "documento": "33333333000133", "uf": "MT", "idade_empresa_meses": 360,
        "capital_social": 5_000_000.0, "divida_ativa_total": 0.0,
        "flag_situacao_irregular": False, "flag_embargo_ativo": False,
        "n_autos_infracao": 0, "n_protestos_ativos": 0,
        "n_empresas_do_socio_inaptas": 0, "desvio_produtividade_vs_media_5a": 0.10,
    }
    ruim = dict(
        limpo, documento="44444444000144", idade_empresa_meses=14, capital_social=10_000.0,
        divida_ativa_total=4_000_000.0, flag_situacao_irregular=True,
        flag_embargo_ativo=True, n_autos_infracao=9, n_protestos_ativos=6,
        n_empresas_do_socio_inaptas=4, desvio_produtividade_vs_media_5a=-0.45,
    )
    assert (
        scorer.pontuar(ruim)["probabilidade_inadimplencia"]
        > scorer.pontuar(limpo)["probabilidade_inadimplencia"]
    )


def test_faixas_sao_monotonas_na_probabilidade():
    bundle = artefatos.BundleModelo(nome="t", pipeline=None)
    bundle.calibrar_faixas(np.linspace(0, 1, 1000))
    ordem = [bundle.faixa(p) for p in (0.0, 0.5, 0.85, 0.97, 0.999)]
    assert ordem == ["BAIXO", "BAIXO", "MEDIO", "ALTO", "CRITICO"]


def test_bundle_sem_limiares_nao_inventa_faixa():
    assert artefatos.BundleModelo(nome="t", pipeline=None).faixa(0.9) == ""


def test_bundle_guarda_as_colunas_de_entrada():
    """A API reindexa por esta lista; se ela nao viajar no artefato, nada casa."""
    bundle = _scorer("regressao_logistica").bundle
    assert bundle.colunas_de_entrada == esquema.features_de_entrada()
    assert bundle.versao_libs.get("scikit-learn")


def test_scorer_padrao_carrega_uma_vez_so():
    from src.modelos.inferencia import scorer_padrao

    try:
        assert scorer_padrao() is scorer_padrao()
    except (FileNotFoundError, TypeError) as exc:
        pytest.skip(f"campeao indisponivel: {exc}")


@pytest.mark.parametrize("vazio", [None, float("nan"), np.nan, pd.NA])
def test_ausencia_vale_para_none_e_para_nan(vazio):
    """Registro vindo de DataFrame traz NaN, nao None: os dois sao 'ausente'.

    Pandas nao guarda None em coluna float, entao todo registro que passou por um
    DataFrame (CLI `--csv`, escoragem de carteira) entrega NaN. Testar so
    `is None` fazia `fontes_ausentes` voltar vazio com o bloco todo em branco.
    """
    from src.modelos.inferencia import _blocos_ausentes

    registro = {c: vazio for c in esquema.BLOCOS_AUSENCIA["protestos"]}
    assert "protestos" in _blocos_ausentes(registro)


def test_sinais_observados_leem_o_registro_cru():
    from src.modelos.inferencia import sinais_de_risco

    assert sinais_de_risco({c: None for c in esquema.colunas_brutas()}) == []
    assert sinais_de_risco({c: float("nan") for c in esquema.colunas_brutas()}) == []
    sinais = sinais_de_risco(
        {"divida_ativa_total": 1000.0, "flag_embargo_ativo": True,
         "n_protestos_ativos": 2, "anomalia_na_fase_critica": -0.40}
    )
    assert "divida ativa na PGFN" in sinais
    assert "embargo ambiental ativo" in sinais
    assert "protesto ativo em cartorio" in sinais
    assert "deficit de chuva na fase critica da cultura" in sinais
