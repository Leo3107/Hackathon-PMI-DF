"""Montagem do dicionario de features por documento.

Regra que vale para o arquivo inteiro: nenhuma funcao aqui levanta excecao por
dado ausente. Cada bloco de fonte roda isolado; se a fonte nao foi carregada,
ou a consulta falha, os campos daquele bloco ficam `None` e a montagem segue.
E por isso que `features --documento` funciona com apenas PGFN e Receita no
warehouse.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

import duckdb

from . import config, warehouse
from .bulk import clima as clima_mod
from .bulk import ibge_sidra
from .logging_setup import get_logger, log_evento
from .models import Features
from .ondemand import protestos as protestos_mod

log = get_logger("features")


# --------------------------------------------------------------- helpers ----

def _seguro(nome_fonte: str, fn: Callable[[], dict]) -> dict:
    """Executa o bloco de uma fonte; falha vira log, nunca excecao."""
    try:
        return fn() or {}
    except Exception as exc:  # noqa: BLE001 - isolamento por fonte e requisito
        log_evento(
            log, "features.fonte_falhou", fonte=nome_fonte, erro=f"{type(exc).__name__}: {exc}"
        )
        return {}


def _uma(con: duckdb.DuckDBPyConnection, sql: str, params: list) -> tuple | None:
    try:
        return con.execute(sql, params).fetchone()
    except duckdb.Error as exc:
        log_evento(log, "features.sql_falhou", erro=str(exc)[:200])
        return None


def _ultima_competencia(con: duckdb.DuckDBPyConnection, tabela: str) -> str | None:
    row = _uma(con, f"SELECT max(competencia) FROM {tabela}", [])
    return row[0] if row and row[0] else None


def _competencias_pgfn(con: duckdb.DuckDBPyConnection, limite: int = 2) -> list[str]:
    """Competencias mais recentes, ordenadas do mais novo para o mais antigo.

    A ordenacao alfabetica de '2026T2' funciona dentro do mesmo seculo, que e
    o horizonte desta base.
    """
    try:
        rows = con.execute(
            "SELECT DISTINCT competencia FROM pgfn_divida "
            "ORDER BY competencia DESC LIMIT ?",
            [limite],
        ).fetchall()
    except duckdb.Error:
        return []
    return [r[0] for r in rows]


def _filtro_documento(documento: str) -> tuple[str, list]:
    """CNPJ completo casa exato; base de 8 digitos casa por prefixo."""
    if len(documento) == 14:
        return "documento = ?", [documento]
    return "documento LIKE ?", [documento + "%"]


# ------------------------------------------------------------- fonte 1 ------

def _features_pgfn(con: duckdb.DuckDBPyConnection, documento: str) -> dict:
    competencias = _competencias_pgfn(con, limite=2)
    if not competencias:
        return {}
    atual = competencias[0]
    cond, params = _filtro_documento(documento)

    row = _uma(
        con,
        f"""
        SELECT
            coalesce(sum(valor_consolidado), 0),
            coalesce(sum(CASE WHEN indicador_ajuizado THEN valor_consolidado END), 0),
            count(DISTINCT numero_inscricao),
            bool_or(origem = 'PREV'),
            bool_or(origem = 'FGTS')
        FROM pgfn_divida
        WHERE competencia = ? AND {cond}
        """,
        [atual, *params],
    )
    if row is None:
        return {}

    total, ajuizada, n_inscricoes, tem_prev, tem_fgts = row
    saida: dict[str, Any] = {
        "divida_ativa_total": float(total or 0.0),
        "divida_ativa_ajuizada": float(ajuizada or 0.0),
        "n_inscricoes": int(n_inscricoes or 0),
        "flag_divida_previdenciaria": bool(tem_prev),
        "flag_divida_fgts": bool(tem_fgts),
    }

    if len(competencias) > 1:
        anterior = _uma(
            con,
            f"""
            SELECT coalesce(sum(valor_consolidado), 0)
            FROM pgfn_divida WHERE competencia = ? AND {cond}
            """,
            [competencias[1], *params],
        )
        if anterior is not None:
            saida["delta_divida_2_trimestres"] = round(
                float(total or 0.0) - float(anterior[0] or 0.0), 2
            )
    return saida


# ------------------------------------------------------------- fonte 2 ------

def _features_receita(
    con: duckdb.DuckDBPyConnection, documento: str, cnpj_basico: str | None
) -> dict:
    competencia = _ultima_competencia(con, "rf_estabelecimentos")
    if not competencia or not cnpj_basico:
        return {}

    # O estabelecimento de referencia e o proprio CNPJ, quando informado
    # completo; caso contrario, a matriz.
    if len(documento) == 14:
        cond_est, par_est = "cnpj = ?", [documento]
    else:
        cond_est, par_est = (
            "cnpj_basico = ? AND identificador_matriz_filial = '1'",
            [cnpj_basico],
        )

    est = _uma(
        con,
        f"""
        SELECT situacao_cadastral, cnae_fiscal_principal, data_inicio_atividade,
               uf, municipio
        FROM rf_estabelecimentos
        WHERE competencia = ? AND {cond_est}
        LIMIT 1
        """,
        [competencia, *par_est],
    )
    if est is None:
        return {}

    saida: dict[str, Any] = {}
    if est[0] is not None or est[1] is not None:
        situacao, cnae, inicio, uf, municipio_rf = est
        saida["situacao_cadastral"] = situacao
        saida["flag_situacao_irregular"] = (
            situacao != config.RF_SITUACAO_ATIVA if situacao else None
        )
        saida["cnae_principal"] = cnae
        saida["flag_cnae_agro"] = (
            (cnae or "").zfill(7)[:2] in config.CNAE_DIVISOES_AGRO if cnae else None
        )
        saida["uf"] = uf
        if inicio:
            hoje = dt.date.today()
            saida["idade_empresa_meses"] = (
                (hoje.year - inicio.year) * 12 + hoje.month - inicio.month
            )
        saida["_municipio_rf"] = municipio_rf

    emp = _uma(
        con,
        "SELECT razao_social, capital_social, porte, natureza_juridica "
        "FROM rf_empresas WHERE competencia = ? AND cnpj_basico = ? LIMIT 1",
        [competencia, cnpj_basico],
    )
    if emp:
        saida["razao_social"] = emp[0]
        saida["capital_social"] = float(emp[1]) if emp[1] is not None else None
        saida["porte"] = emp[2]
        saida["natureza_juridica"] = emp[3]

    filiais = _uma(
        con,
        "SELECT count(*) FROM rf_estabelecimentos "
        "WHERE competencia = ? AND cnpj_basico = ? "
        "  AND identificador_matriz_filial = '2'",
        [competencia, cnpj_basico],
    )
    if filiais:
        saida["n_filiais"] = int(filiais[0])

    socios = _uma(
        con,
        "SELECT count(DISTINCT socio_id) FROM socio_empresa "
        "WHERE competencia = ? AND cnpj_basico = ?",
        [competencia, cnpj_basico],
    )
    if socios:
        saida["n_socios"] = int(socios[0])
    return saida


def _features_grafo_societario(
    con: duckdb.DuckDBPyConnection, cnpj_basico: str | None
) -> dict:
    """As tres features que dependem de sair do CNPJ e andar pelo grafo.

    Um socio com cinco empresas inaptas e um sinal que nenhum cadastro do
    proprio CNPJ mostra.
    """
    competencia = _ultima_competencia(con, "socio_empresa")
    if not competencia or not cnpj_basico:
        return {}

    base_cte = """
    WITH meus_socios AS (
        SELECT DISTINCT socio_id
        FROM socio_empresa
        WHERE competencia = ? AND cnpj_basico = ?
    ),
    empresas_ligadas AS (
        SELECT DISTINCT se.cnpj_basico
        FROM socio_empresa se
        JOIN meus_socios ms USING (socio_id)
        WHERE se.competencia = ? AND se.cnpj_basico <> ?
    )
    """
    params = [competencia, cnpj_basico, competencia, cnpj_basico]

    row = _uma(con, base_cte + "SELECT count(*) FROM empresas_ligadas", params)
    if row is None:
        return {}
    saida: dict[str, Any] = {"n_empresas_do_socio": int(row[0])}

    comp_pgfn = _competencias_pgfn(con, limite=1)
    if comp_pgfn:
        row = _uma(
            con,
            base_cte
            + """
            SELECT count(DISTINCT e.cnpj_basico)
            FROM empresas_ligadas e
            WHERE EXISTS (
                SELECT 1 FROM pgfn_divida p
                WHERE p.competencia = ?
                  AND p.documento IS NOT NULL
                  AND substr(p.documento, 1, 8) = e.cnpj_basico
            )
            """,
            [*params, comp_pgfn[0]],
        )
        if row is not None:
            saida["n_empresas_do_socio_com_divida_ativa"] = int(row[0])

    comp_rf = _ultima_competencia(con, "rf_estabelecimentos")
    if comp_rf:
        row = _uma(
            con,
            base_cte
            + """
            SELECT count(DISTINCT e.cnpj_basico)
            FROM empresas_ligadas e
            JOIN rf_estabelecimentos est
              ON est.cnpj_basico = e.cnpj_basico
            WHERE est.competencia = ?
              AND est.identificador_matriz_filial = '1'
              AND est.situacao_cadastral = ?
            """,
            [*params, comp_rf, config.RF_SITUACAO_INAPTA],
        )
        if row is not None:
            saida["n_empresas_do_socio_inaptas"] = int(row[0])
    return saida


# ------------------------------------------------------------- fonte 3 ------

def _features_ibama(con: duckdb.DuckDBPyConnection, documento: str) -> dict:
    saida: dict[str, Any] = {}
    cond, params = _filtro_documento(documento)

    # Tabela vazia significa "fonte nao carregada", nao "zero autuacoes".
    if warehouse.tem_dados(con, "ibama_autos"):
        autos = _uma(
            con,
            f"""
            SELECT count(*), coalesce(sum(valor_auto), 0)
            FROM ibama_autos
            WHERE {cond} AND coalesce(upper(sit_cancelado), 'N') <> 'S'
            """,
            params,
        )
        if autos is not None:
            saida["n_autos_infracao"] = int(autos[0])
            saida["valor_multas_ambientais"] = float(autos[1] or 0.0)

    if not warehouse.tem_dados(con, "ibama_embargos"):
        return saida

    embargos = _uma(
        con,
        f"""
        SELECT count(*), coalesce(sum(area_embargada_ha), 0)
        FROM ibama_embargos
        WHERE {cond}
          AND coalesce(upper(sit_cancelado), 'N') <> 'S'
          AND data_desembargo IS NULL
          AND coalesce(upper(sit_desembargo), '') NOT IN ('S', 'SIM', 'DESEMBARGADO')
        """,
        params,
    )
    if embargos is not None:
        saida["flag_embargo_ativo"] = int(embargos[0]) > 0
        saida["area_embargada_ha"] = float(embargos[1] or 0.0)
    return saida


# ------------------------------------------------------------- fonte 4 ------

def _features_bcb(con: duckdb.DuckDBPyConnection, cod_ibge: str | None) -> dict:
    if not cod_ibge:
        return {}
    row = _uma(
        con,
        """
        WITH ultimo AS (
            SELECT max(ano) AS ano FROM bcb_mdcr WHERE cod_ibge = ?
        )
        SELECT
            coalesce(sum(vl_custeio + vl_investimento
                         + vl_comercializacao + vl_industrializacao), 0),
            coalesce(sum(qtd_custeio + qtd_investimento
                         + qtd_comercializacao + qtd_industrializacao), 0),
            coalesce(sum(vl_custeio + vl_investimento), 0),
            coalesce(sum(area_custeio + area_investimento), 0)
        FROM bcb_mdcr, ultimo
        WHERE bcb_mdcr.cod_ibge = ? AND bcb_mdcr.ano = ultimo.ano
        """,
        [cod_ibge, cod_ibge],
    )
    if row is None or not row[1]:
        return {}

    volume, n_contratos, vl_area, area = row
    saida: dict[str, Any] = {
        "volume_credito_rural_municipio": round(float(volume), 2),
        "n_contratos_municipio": int(n_contratos),
        "ticket_medio_municipio": (
            round(float(volume) / int(n_contratos), 2) if n_contratos else None
        ),
        "credito_por_hectare_municipio": (
            round(float(vl_area) / float(area), 2) if area else None
        ),
    }
    # A MDCR nao publica acionamentos de Proagro -- apenas `cdTipoSeguro`, que
    # e cobertura contratada, nao sinistro. Sem proxy honesto, fica None.
    saida["acionamentos_proagro_municipio"] = None
    return saida


# ------------------------------------------------------------- fonte 5 ------

def _features_producao(
    con: duckdb.DuckDBPyConnection, cod_ibge: str | None, cultura: str
) -> dict:
    if not cod_ibge:
        return {}
    row = _uma(
        con,
        """
        SELECT max(ano) FROM ibge_producao
        WHERE cod_ibge = ? AND cultura = ? AND variavel = 'rendimento_medio_kg_ha'
        """,
        [cod_ibge, cultura],
    )
    if row is None or row[0] is None:
        return {}
    ano = int(row[0])

    valores = _uma(
        con,
        """
        SELECT
            max(CASE WHEN variavel = 'rendimento_medio_kg_ha' AND ano = ?
                     THEN valor END),
            max(CASE WHEN variavel = 'area_plantada_ha' AND ano = ? THEN valor END),
            avg(CASE WHEN variavel = 'rendimento_medio_kg_ha'
                      AND ano BETWEEN ? AND ? THEN valor END)
        FROM ibge_producao
        WHERE cod_ibge = ? AND cultura = ?
        """,
        [ano, ano, ano - 5, ano - 1, cod_ibge, cultura],
    )
    if valores is None:
        return {}

    produtividade, area, media_5a = valores
    saida: dict[str, Any] = {
        "produtividade_municipal_cultura": (
            float(produtividade) if produtividade is not None else None
        ),
        "area_plantada_municipio_cultura": float(area) if area is not None else None,
    }
    if produtividade is not None and media_5a:
        # Desvio relativo: e o que indica quebra de safra, nao o kg/ha absoluto.
        saida["desvio_produtividade_vs_media_5a"] = round(
            (float(produtividade) - float(media_5a)) / float(media_5a), 4
        )
    return saida


# ------------------------------------------------------------- fonte 6 ------

def janela_safra(
    cultura: str, referencia: dt.date | None = None
) -> tuple[dt.date, dt.date] | None:
    """Janela da safra mais recente ja semeada, nao o ano civil."""
    cal = config.CALENDARIO_CULTURAS.get(cultura)
    if not cal:
        return None
    referencia = referencia or dt.date.today()

    mes_s, dia_s = cal.semeadura_mes_dia
    mes_c, dia_c = cal.colheita_mes_dia
    ano_semeadura = referencia.year
    if (referencia.month, referencia.day) < (mes_s, dia_s):
        ano_semeadura -= 1
    inicio = dt.date(ano_semeadura, mes_s, dia_s)
    # Colheita antes da semeadura no calendario significa virada de ano.
    ano_colheita = ano_semeadura + (1 if (mes_c, dia_c) <= (mes_s, dia_s) else 0)
    return inicio, dt.date(ano_colheita, mes_c, dia_c)


def _janela_fase_critica(
    cultura: str, inicio: dt.date
) -> tuple[dt.date, dt.date] | None:
    cal = config.CALENDARIO_CULTURAS.get(cultura)
    if not cal:
        return None
    d0, d1 = cal.fase_critica_offset
    return inicio + dt.timedelta(days=d0), inicio + dt.timedelta(days=d1)


def _chuva_acumulada(
    con: duckdb.DuckDBPyConnection, ponto: str, inicio: dt.date, fim: dt.date
) -> float | None:
    row = _uma(
        con,
        "SELECT sum(precipitacao_mm) FROM clima_diario "
        "WHERE ponto_id = ? AND data BETWEEN ? AND ?",
        [ponto, inicio, fim],
    )
    return float(row[0]) if row and row[0] is not None else None


def _normal_da_janela(
    con: duckdb.DuckDBPyConnection,
    ponto: str,
    mes_dia_inicio: tuple[int, int],
    dias: int,
) -> float | None:
    """Media, em 1991-2020, da chuva acumulada na mesma janela do calendario."""
    mes, dia = mes_dia_inicio
    acumulados: list[float] = []
    for ano in range(config.NORMAL_CLIMATOLOGICA_INICIO, config.NORMAL_CLIMATOLOGICA_FIM + 1):
        try:
            ini = dt.date(ano, mes, dia)
        except ValueError:
            continue
        valor = _chuva_acumulada(con, ponto, ini, ini + dt.timedelta(days=dias))
        if valor is not None:
            acumulados.append(valor)
    if len(acumulados) < 10:  # amostra curta demais para virar "normal"
        return None
    return sum(acumulados) / len(acumulados)


def _dias_secos_consecutivos(
    con: duckdb.DuckDBPyConnection, ponto: str, inicio: dt.date, fim: dt.date
) -> int | None:
    try:
        rows = con.execute(
            "SELECT data, precipitacao_mm FROM clima_diario "
            "WHERE ponto_id = ? AND data BETWEEN ? AND ? ORDER BY data",
            [ponto, inicio, fim],
        ).fetchall()
    except duckdb.Error:
        return None
    if not rows:
        return None
    maior = atual = 0
    for _, chuva in rows:
        if chuva is None or float(chuva) < config.DIAS_SEM_CHUVA_LIMIAR_MM:
            atual += 1
            maior = max(maior, atual)
        else:
            atual = 0
    return maior


def _features_clima(
    con: duckdb.DuckDBPyConnection,
    cod_ibge: str | None,
    cultura: str,
    *,
    permitir_rede: bool,
) -> dict:
    if not cod_ibge:
        return {}
    janela = janela_safra(cultura)
    if not janela:
        return {}
    inicio, fim = janela

    ponto_coords = ibge_sidra.centroide(con, cod_ibge) if permitir_rede else None
    if ponto_coords is None:
        row = _uma(
            con,
            "SELECT latitude, longitude FROM municipio_centroide WHERE cod_ibge = ?",
            [cod_ibge],
        )
        if not row:
            return {}
        ponto_coords = (float(row[0]), float(row[1]))

    lat, lon = ponto_coords
    provedor = clima_mod.obter_provedor()
    ponto = clima_mod.ponto_id(lat, lon, provedor.nome)

    if permitir_rede:
        clima_mod.garantir_serie(con, lat, lon, inicio, min(fim, dt.date.today()),
                                 provedor=provedor)
        clima_mod.garantir_normal_climatologica(con, lat, lon, provedor=provedor)

    saida: dict[str, Any] = {}
    acumulado = _chuva_acumulada(con, ponto, inicio, fim)
    if acumulado is None:
        return saida
    saida["precipitacao_acumulada_ciclo"] = round(acumulado, 1)
    saida["dias_secos_consecutivos_max"] = _dias_secos_consecutivos(
        con, ponto, inicio, fim
    )

    dias_ciclo = (fim - inicio).days
    normal = _normal_da_janela(con, ponto, (inicio.month, inicio.day), dias_ciclo)
    if normal:
        # Anomalia relativa, nao milimetro absoluto: e o que tem poder preditivo.
        saida["precipitacao_vs_normal_climatologica"] = round(
            (acumulado - normal) / normal, 4
        )

    fase = _janela_fase_critica(cultura, inicio)
    if fase:
        fase_ini, fase_fim = fase
        chuva_fase = _chuva_acumulada(con, ponto, fase_ini, fase_fim)
        normal_fase = _normal_da_janela(
            con, ponto, (fase_ini.month, fase_ini.day), (fase_fim - fase_ini).days
        )
        if chuva_fase is not None and normal_fase:
            saida["anomalia_na_fase_critica"] = round(
                (chuva_fase - normal_fase) / normal_fase, 4
            )
    return saida


# ------------------------------------------------------------- fonte 7 ------

def _features_protestos(
    con: duckdb.DuckDBPyConnection, documento: str, *, permitir_rede: bool
) -> dict:
    provedor = protestos_mod.obter_provedor()
    if isinstance(provedor, protestos_mod.ApiProvider) and not permitir_rede:
        return protestos_mod.features(None)
    resultado = protestos_mod.consultar(con, documento, provedor=provedor)
    return protestos_mod.features(resultado)


# ------------------------------------------------------------- montagem -----

def _fontes_disponiveis(con: duckdb.DuckDBPyConnection) -> list[str]:
    mapa = {
        "pgfn": "pgfn_divida",
        "receita": "rf_estabelecimentos",
        "grafo_societario": "socio_empresa",
        "ibama_autos": "ibama_autos",
        "ibama_embargos": "ibama_embargos",
        "bcb_mdcr": "bcb_mdcr",
        "ibge_producao": "ibge_producao",
        "clima": "clima_diario",
    }
    return [nome for nome, tabela in mapa.items() if warehouse.tem_dados(con, tabela)]


def build_features(
    documento: str,
    *,
    con: duckdb.DuckDBPyConnection | None = None,
    cultura: str | None = None,
    permitir_rede: bool = True,
) -> dict:
    """Monta o dicionario de features de um documento.

    `documento` aceita CNPJ com ou sem mascara, completo (14 digitos) ou apenas
    a base (8 digitos). Campos sem dado voltam como `None`.
    """
    doc = warehouse.normalizar_documento(documento) or ""
    cultura = cultura or config.SETTINGS.cultura_padrao
    fechar = con is None
    con = con or warehouse.conectar()

    try:
        cnpj_basico = doc[:8] if len(doc) >= 8 else None
        dados: dict[str, Any] = {
            "documento": doc or documento,
            "cnpj_basico": cnpj_basico,
            "cultura_referencia": cultura,
            "fontes_disponiveis": _seguro(
                "inventario", lambda: {"v": _fontes_disponiveis(con)}
            ).get("v", []),
        }

        dados.update(_seguro("pgfn", lambda: _features_pgfn(con, doc)))
        receita = _seguro("receita", lambda: _features_receita(con, doc, cnpj_basico))
        municipio_rf = receita.pop("_municipio_rf", None)
        dados.update(receita)
        dados.update(
            _seguro("grafo_societario", lambda: _features_grafo_societario(con, cnpj_basico))
        )
        dados.update(_seguro("ibama", lambda: _features_ibama(con, doc)))

        cod_ibge = _seguro(
            "municipio",
            lambda: {
                "v": ibge_sidra.mapear_municipio_rf(con, municipio_rf, dados.get("uf"))
            },
        ).get("v")
        dados["municipio_ibge"] = cod_ibge

        dados.update(_seguro("bcb_mdcr", lambda: _features_bcb(con, cod_ibge)))
        dados.update(
            _seguro("ibge_producao", lambda: _features_producao(con, cod_ibge, cultura))
        )
        dados.update(
            _seguro(
                "clima",
                lambda: _features_clima(
                    con, cod_ibge, cultura, permitir_rede=permitir_rede
                ),
            )
        )
        dados.update(
            _seguro(
                "protestos",
                lambda: _features_protestos(con, doc, permitir_rede=permitir_rede),
            )
        )

        return Features(**dados).to_dict()
    finally:
        if fechar:
            con.close()


__all__ = ["build_features", "janela_safra"]
