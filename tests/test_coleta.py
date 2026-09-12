"""Testes sem rede: normalizacao, SQL de carga e montagem de features.

Rodam contra um DuckDB em memoria e CSVs sinteticos com os layouts reais.

    pip install -r requirements-dev.txt && pytest -q
"""
from __future__ import annotations

import datetime as dt

import duckdb
import pytest

from coleta import config, warehouse
from coleta.bulk import pgfn
from coleta.bulk._common import colunas_varchar, read_csv_sql
from coleta.features import build_features, janela_safra
from coleta.ondemand import protestos


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    """Warehouse limpo por teste -- INCLUSIVE o cache de competencias.

    `features._cache_competencia` e de modulo e sobrevive entre testes, mas
    cada teste recebe um DuckDB em memoria novo. Sem a limpeza, o segundo teste
    herda a competencia semeada pelo primeiro, nenhuma linha casa e features
    como `delta_divida_2_trimestres` voltam None -- falhando so na suite
    inteira e passando quando rodadas isoladas, que e o jeito mais caro de
    descobrir o problema.

    Em producao o cache e correto como esta: um processo serve um warehouse so,
    e o TTL de 300s cobre a troca de competencia entre cargas.
    """
    import coleta.features as _features

    _features.limpar_cache_competencias()
    c = duckdb.connect(":memory:")
    warehouse.criar_schema(c)
    yield c
    c.close()
    _features.limpar_cache_competencias()


# ------------------------------------------------------------ normalizacao --

@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("84.461.748/0001-81", "84461748000181"),
        ("84461748000181", "84461748000181"),
        ("XXX735.623XX", "735623"),
        ("", None),
        (None, None),
    ],
)
def test_normalizar_documento(entrada, esperado):
    assert warehouse.normalizar_documento(entrada) == esperado


# -------------------------------------------------------------- carga PGFN --

def _csv_pgfn(tmp_path, origem: str) -> str:
    """CSV sintetico no layout real da origem, inclusive a mascara de CPF."""
    colunas = config.PGFN_ORIGENS[origem]["colunas"]
    linhas = [";".join(colunas)]
    base = {
        "CPF_CNPJ": "84.461.748/0001-81",
        "TIPO_PESSOA": "Pessoa juridica",
        "TIPO_DEVEDOR": "PRINCIPAL",
        "NOME_DEVEDOR": "FAZENDA TESTE LTDA",
        "UF_DEVEDOR": "GO",
        "UNIDADE_RESPONSAVEL": "GOIAS",
        "ENTIDADE_RESPONSAVEL": "PGFN",
        "UNIDADE_INSCRICAO": "GOIAS",
        "NUMERO_INSCRICAO": "123456",
        "TIPO_SITUACAO_INSCRICAO": "Em cobranca",
        "SITUACAO_INSCRICAO": "ATIVA AJUIZADA",
        "RECEITA_PRINCIPAL": "Receita teste",
        "TIPO_CREDITO": "Credito teste",
        "DATA_INSCRICAO": "30/11/1999",
        "INDICADOR_AJUIZADO": "SIM",
        "VALOR_CONSOLIDADO": "1500.50",
    }
    linhas.append(";".join(base[c] for c in colunas))
    # Pessoa fisica com CPF mascarado: nao pode virar documento utilizavel.
    pf = dict(base, CPF_CNPJ="XXX735.623XX", TIPO_PESSOA="Pessoa fisica",
              INDICADOR_AJUIZADO="NAO", VALOR_CONSOLIDADO="10.00",
              NUMERO_INSCRICAO="999")
    linhas.append(";".join(pf[c] for c in colunas))

    caminho = tmp_path / f"pgfn_{origem}.csv"
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return str(caminho)


@pytest.mark.parametrize("origem", ["SIDA", "FGTS", "PREV"])
def test_carga_pgfn_normaliza_cada_layout(con, tmp_path, origem):
    leitura = read_csv_sql(
        _csv_pgfn(tmp_path, origem),
        colunas_varchar(config.PGFN_ORIGENS[origem]["colunas"]),
        encoding="utf-8",
        header=True,
    )
    con.execute(
        "INSERT INTO pgfn_divida BY NAME "
        + pgfn._select_normalizado(leitura, origem, "2026T1")
    )

    pj = con.execute(
        "SELECT documento, pf_mascarado, indicador_ajuizado, valor_consolidado,"
        "       data_inscricao, receita_principal"
        " FROM pgfn_divida WHERE NOT pf_mascarado"
    ).fetchone()
    assert pj[0] == "84461748000181"  # mascara removida
    assert pj[1] is False
    assert pj[2] is True
    assert pj[3] == pytest.approx(1500.50)  # ponto decimal, nao virgula
    assert pj[4] == dt.date(1999, 11, 30)
    assert pj[5] is not None

    pf = con.execute(
        "SELECT documento, pf_mascarado, cpf_cnpj_raw FROM pgfn_divida"
        " WHERE pf_mascarado"
    ).fetchone()
    assert pf[0] is None, "CPF mascarado nao pode virar chave de join"
    assert pf[1] is True
    assert pf[2] == "XXX735.623XX", "o valor original deve ser preservado"


def test_carga_pgfn_e_idempotente(con, tmp_path):
    leitura = read_csv_sql(
        _csv_pgfn(tmp_path, "FGTS"),
        colunas_varchar(config.PGFN_ORIGENS["FGTS"]["colunas"]),
        encoding="utf-8",
        header=True,
    )
    select = pgfn._select_normalizado(leitura, "FGTS", "2026T1")
    for _ in range(2):
        warehouse.apagar_particao(
            con, "pgfn_divida", competencia="2026T1", origem="FGTS"
        )
        con.execute("INSERT INTO pgfn_divida BY NAME " + select)
    assert warehouse.contar(con, "pgfn_divida") == 2


# ---------------------------------------------------------------- features --

def _semear(con) -> None:
    con.execute(
        "INSERT INTO pgfn_divida (competencia, origem, documento, pf_mascarado,"
        " numero_inscricao, indicador_ajuizado, valor_consolidado, tipo_devedor)"
        " VALUES"
        " ('2026T1','FGTS','11111111000191',false,'A',true,1000.0,'PRINCIPAL'),"
        " ('2025T4','FGTS','11111111000191',false,'A',true,400.0,'PRINCIPAL'),"
        " ('2026T1','PREV','22222222000110',false,'B',false,50.0,'Principal'),"
        # Avalista de uma divida alheia de 9 milhoes: nao e divida propria.
        " ('2026T1','SIDA','11111111000191',false,'C',false,9000000.0,"
        "  'CORRESPONSAVEL')"
    )
    con.execute(
        "INSERT INTO rf_empresas (competencia, cnpj_basico, razao_social,"
        " natureza_juridica, capital_social, porte) VALUES"
        " ('2026-08','11111111','FAZENDA TESTE LTDA','2062',500000.0,'03')"
    )
    con.execute(
        "INSERT INTO rf_estabelecimentos (competencia, cnpj_basico, cnpj,"
        " identificador_matriz_filial, situacao_cadastral, cnae_fiscal_principal,"
        " data_inicio_atividade, uf, municipio) VALUES"
        " ('2026-08','11111111','11111111000191','1','02','0115600',"
        "  DATE '2020-01-15','GO','1234'),"
        " ('2026-08','11111111','11111111000272','2','02','0115600',"
        "  DATE '2021-01-15','GO','1234'),"
        " ('2026-08','22222222','22222222000110','1','04','4711302',"
        "  DATE '2015-01-15','GO','1234')"
    )
    con.execute(
        "INSERT INTO socio_empresa (competencia, socio_id, socio_tipo,"
        " socio_nome, cnpj_basico) VALUES"
        " ('2026-08','PF:***111**|MARIA','PF','MARIA','11111111'),"
        " ('2026-08','PF:***111**|MARIA','PF','MARIA','22222222')"
    )


def test_build_features_so_com_pgfn_e_receita(con):
    _semear(con)
    f = build_features("11.111.111/0001-91", con=con, permitir_rede=False)

    assert f["documento"] == "11111111000191"
    assert f["divida_ativa_total"] == pytest.approx(1000.0)
    assert f["divida_ativa_corresponsavel"] == pytest.approx(9_000_000.0)
    assert f["divida_ativa_ajuizada"] == pytest.approx(1000.0)
    assert f["delta_divida_2_trimestres"] == pytest.approx(600.0)
    assert f["flag_divida_fgts"] is True
    assert f["flag_divida_previdenciaria"] is False

    assert f["capital_social"] == pytest.approx(500000.0)
    assert f["flag_cnae_agro"] is True
    assert f["flag_situacao_irregular"] is False
    assert f["n_filiais"] == 1
    assert f["n_socios"] == 1

    # Grafo: a socia tambem esta em 22222222, que esta inapta.
    assert f["n_empresas_do_socio"] == 1
    assert f["n_empresas_do_socio_inaptas"] == 1
    assert f["n_empresas_do_socio_com_divida_ativa"] == 1

    # Fontes ausentes viram None, nao zero, e nada estoura.
    for campo in (
        "n_autos_infracao",
        "flag_embargo_ativo",
        "volume_credito_rural_municipio",
        "produtividade_municipal_cultura",
        "precipitacao_acumulada_ciclo",
        "n_protestos_ativos",
    ):
        assert f[campo] is None, campo


def test_build_features_documento_inexistente_nao_estoura(con):
    f = build_features("99999999000199", con=con, permitir_rede=False)
    assert f["documento"] == "99999999000199"
    assert f["capital_social"] is None


# ------------------------------------------------------------- calendario ---

def test_janela_safra_soja_cruza_o_ano():
    inicio, fim = janela_safra("soja", referencia=dt.date(2026, 1, 10))
    assert inicio == dt.date(2025, 10, 15)
    assert fim == dt.date(2026, 3, 15)


def test_janela_safra_antes_da_semeadura_usa_ciclo_anterior():
    inicio, _ = janela_safra("soja", referencia=dt.date(2026, 9, 1))
    assert inicio == dt.date(2025, 10, 15)


def test_janela_safra_cultura_desconhecida():
    assert janela_safra("quinoa") is None


# -------------------------------------------------------------- protestos ---

def test_protestos_csv_manual(tmp_path):
    csv = tmp_path / "protestos.csv"
    csv.write_text(
        "documento;data_protesto;valor;cartorio;uf;situacao\n"
        "11.111.111/0001-91;01/03/2026;1.234,56;1o Tabelionato;GO;ATIVO\n"
        "11111111000191;15/02/2026;500,00;2o Tabelionato;GO;CANCELADO\n"
        "99999999000199;01/01/2026;10,00;3o Tabelionato;SP;ATIVO\n",
        encoding="utf-8",
    )
    resultado = protestos.CSVManualProvider(csv).consultar("11111111000191")
    assert len(resultado.protestos) == 2
    assert len(resultado.ativos) == 1, "protesto cancelado nao conta como ativo"

    f = protestos.features(resultado)
    assert f["n_protestos_ativos"] == 1
    assert f["valor_total_protestado"] == pytest.approx(1234.56)
    assert f["n_cartorios_distintos"] == 1


def test_protestos_csv_vazio_e_indisponivel_nao_zero(tmp_path):
    csv = tmp_path / "vazio.csv"
    csv.write_text("documento;data_protesto;valor;cartorio;uf;situacao\n", "utf-8")
    f = protestos.features(protestos.CSVManualProvider(csv).consultar("11111111000191"))
    assert f["n_protestos_ativos"] is None


def test_protestos_api_sem_token_nao_estoura():
    provider = protestos.ApiProvider(base_url="", token="")
    resultado = provider.consultar("11111111000191")
    assert resultado.disponivel is False
    assert protestos.features(resultado)["n_protestos_ativos"] is None


# ------------------------------------------------- regressao: nomes de coluna --

def test_apagar_particao_com_chave_chamada_tabela(con):
    """`rf_dominio` tem uma COLUNA chamada `tabela`.

    Sem parametro posicional-apenas, `apagar_particao(con, "rf_dominio",
    tabela="Cnaes")` colide com o proprio parametro `tabela` e estoura. Foi o
    que derrubou a carga da Receita inteira na primeira execucao real.
    """
    con.execute(
        "INSERT INTO rf_dominio VALUES ('2026-08','Cnaes','1','a'),"
        " ('2026-08','Motivos','2','b')"
    )
    removidas = warehouse.apagar_particao(
        con, "rf_dominio", competencia="2026-08", tabela="Cnaes"
    )
    assert removidas == 1
    assert warehouse.contar(con, "rf_dominio", tabela="Motivos") == 1
    assert warehouse.contar(con, "rf_dominio") == 1


def test_corresponsabilidade_nao_entra_na_divida_propria(con):
    """A PGFN repete a inscricao por devedor, com o valor cheio em cada linha.

    Somar tudo faria uma avalista de R$ 9 milhoes parecer devedora de
    R$ 9 milhoes -- e inflaria o estoque nacional de R$ 2,9 tri para R$ 6,8 tri.
    """
    _semear(con)
    f = build_features("11111111000191", con=con, permitir_rede=False)

    assert f["divida_ativa_total"] == pytest.approx(1000.0)
    assert f["divida_ativa_corresponsavel"] == pytest.approx(9_000_000.0)
    # n_inscricoes e o delta tambem olham so o que e divida propria.
    assert f["n_inscricoes"] == 1
    assert f["delta_divida_2_trimestres"] == pytest.approx(600.0)
    # A inscricao de corresponsabilidade e SIDA, mas as flags sao do principal.
    assert f["flag_divida_fgts"] is True


def test_competencia_e_cacheada_entre_chamadas(con):
    """Descobrir a competencia custa um scan da tabela inteira.

    Sem cache isso rodava 7x por documento; com 96 milhoes de linhas na PGFN
    virou o gargalo da montagem em lote.
    """
    from coleta import features as mod

    _semear(con)
    mod.limpar_cache_competencias()

    chamadas = {"n": 0}
    original = mod._uma

    def espiao(c, sql, params):
        if "max(competencia)" in sql:
            chamadas["n"] += 1
        return original(c, sql, params)

    mod._uma = espiao
    try:
        for _ in range(5):
            build_features("11111111000191", con=con, permitir_rede=False)
    finally:
        mod._uma = original

    # Uma vez por tabela consultada, nao uma vez por chamada.
    assert chamadas["n"] <= 2, f"scan repetido {chamadas['n']} vezes"

    mod.limpar_cache_competencias()
    assert not mod._cache_competencia
