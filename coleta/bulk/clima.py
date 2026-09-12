"""Clima (fonte 6) - NASA POWER com INMET como alternativa.

NASA POWER e o padrao: API aberta, sem chave, em grade, o que resolve a
esparsidade da rede do INMET no Cerrado e no MATOPIBA. O INMET fica atras da
mesma interface para o caso de se exigir fonte oficial brasileira.

O que fica no warehouse e a serie diaria bruta (`clima_diario`); as features
derivadas -- anomalia contra a normal climatologica, veranico, deficit na fase
critica -- sao calculadas em `features.py` sobre a janela da safra, nunca sobre
o ano civil.
"""
from __future__ import annotations

import datetime as dt
from typing import Protocol, runtime_checkable

import duckdb

from .. import config, http
from ..logging_setup import etapa, get_logger, log_evento
from ..warehouse import registrar_ingestao

log = get_logger("bulk.clima")

FONTE = "clima"

# (data, precipitacao_mm, t_max, t_min)
Serie = list[tuple[dt.date, float | None, float | None, float | None]]


@runtime_checkable
class ProvedorClima(Protocol):
    nome: str

    def series_diarias(
        self, latitude: float, longitude: float, inicio: dt.date, fim: dt.date
    ) -> Serie: ...


class NasaPowerProvider:
    """Grade global de reanalise, resolucao ~0.5 grau, sem chave de acesso."""

    nome = "nasa_power"

    def series_diarias(
        self, latitude: float, longitude: float, inicio: dt.date, fim: dt.date
    ) -> Serie:
        payload = http.get_json(
            config.NASA_POWER_URL,
            params={
                "parameters": config.NASA_POWER_PARAMETROS,
                "community": "AG",
                "latitude": round(latitude, 4),
                "longitude": round(longitude, 4),
                "start": inicio.strftime("%Y%m%d"),
                "end": fim.strftime("%Y%m%d"),
                "format": "JSON",
            },
        )
        parametros = payload.get("properties", {}).get("parameter", {})
        prec = parametros.get("PRECTOTCORR", {})
        tmax = parametros.get("T2M_MAX", {})
        tmin = parametros.get("T2M_MIN", {})

        def limpar(valor) -> float | None:
            if valor is None:
                return None
            valor = float(valor)
            # POWER usa -999 como ausencia de dado.
            return None if valor <= config.NASA_POWER_FILL_VALUE + 1 else valor

        saida: Serie = []
        for chave in sorted(prec.keys() | tmax.keys() | tmin.keys()):
            try:
                data = dt.datetime.strptime(chave, "%Y%m%d").date()
            except ValueError:
                continue
            saida.append(
                (data, limpar(prec.get(chave)), limpar(tmax.get(chave)),
                 limpar(tmin.get(chave)))
            )
        return saida


class InmetProvider:
    """Alternativa oficial brasileira.

    Usa a API de estacoes automaticas (dados recentes). Para historico longo o
    INMET exige o BDMEP, que nao tem endpoint publico estavel -- nesse caso a
    serie volta vazia e as features de clima ficam `None`, em vez de inventar
    numero.
    """

    nome = "inmet"

    def __init__(self) -> None:
        self._estacoes: list[dict] | None = None

    def _carregar_estacoes(self) -> list[dict]:
        if self._estacoes is None:
            try:
                self._estacoes = http.get_json(config.INMET_ESTACOES_URL)
            except Exception as exc:  # noqa: BLE001
                log_evento(log, "inmet.estacoes_falhou", erro=str(exc)[:200])
                self._estacoes = []
        return self._estacoes

    def estacao_mais_proxima(
        self, latitude: float, longitude: float
    ) -> dict | None:
        melhor, menor = None, float("inf")
        for est in self._carregar_estacoes():
            try:
                lat = float(est["VL_LATITUDE"])
                lon = float(est["VL_LONGITUDE"])
            except (KeyError, TypeError, ValueError):
                continue
            # Distancia euclidiana em graus basta para escolher a estacao.
            d = (lat - latitude) ** 2 + (lon - longitude) ** 2
            if d < menor:
                melhor, menor = est, d
        return melhor

    def series_diarias(
        self, latitude: float, longitude: float, inicio: dt.date, fim: dt.date
    ) -> Serie:
        est = self.estacao_mais_proxima(latitude, longitude)
        if not est:
            return []
        codigo = est.get("CD_ESTACAO")
        url = (
            f"{config.INMET_DIARIO_URL}/{inicio:%Y-%m-%d}/{fim:%Y-%m-%d}/{codigo}"
        )
        try:
            registros = http.get_json(url)
        except Exception as exc:  # noqa: BLE001
            log_evento(log, "inmet.serie_falhou", estacao=codigo, erro=str(exc)[:200])
            return []

        def num(valor) -> float | None:
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None

        saida: Serie = []
        for r in registros or []:
            try:
                data = dt.datetime.strptime(r["DT_MEDICAO"], "%Y-%m-%d").date()
            except (KeyError, TypeError, ValueError):
                continue
            saida.append(
                (data, num(r.get("CHUVA")), num(r.get("TEMP_MAX")),
                 num(r.get("TEMP_MIN")))
            )
        return saida


PROVEDORES: dict[str, type] = {
    "nasa_power": NasaPowerProvider,
    "inmet": InmetProvider,
}


def obter_provedor(nome: str | None = None) -> ProvedorClima:
    nome = nome or config.SETTINGS.provedor_clima
    if nome not in PROVEDORES:
        raise ValueError(
            f"provedor de clima desconhecido: {nome} "
            f"(disponiveis: {', '.join(PROVEDORES)})"
        )
    return PROVEDORES[nome]()


def ponto_id(latitude: float, longitude: float, provedor: str) -> str:
    """Arredondar para 2 casas (~1 km) evita cache duplicado por ruido."""
    return f"{provedor}:{latitude:.2f},{longitude:.2f}"


def garantir_serie(
    con: duckdb.DuckDBPyConnection,
    latitude: float,
    longitude: float,
    inicio: dt.date,
    fim: dt.date,
    *,
    provedor: ProvedorClima | None = None,
) -> int:
    """Garante a serie diaria do ponto no intervalo pedido. Idempotente."""
    provedor = provedor or obter_provedor()
    pid = ponto_id(latitude, longitude, provedor.nome)

    row = con.execute(
        "SELECT min(data), max(data) FROM clima_diario WHERE ponto_id = ?", [pid]
    ).fetchone()
    if row and row[0] and row[0] <= inicio and row[1] >= fim:
        return 0

    serie = provedor.series_diarias(latitude, longitude, inicio, fim)
    if not serie:
        return 0

    con.execute(
        "DELETE FROM clima_diario WHERE ponto_id = ? AND data BETWEEN ? AND ?",
        [pid, inicio, fim],
    )
    con.executemany(
        "INSERT INTO clima_diario "
        "(ponto_id, provedor, latitude, longitude, data, precipitacao_mm, "
        " t_max, t_min) VALUES (?,?,?,?,?,?,?,?)",
        [
            (pid, provedor.nome, latitude, longitude, data, prec, tmax, tmin)
            for data, prec, tmax, tmin in serie
        ],
    )
    log_evento(log, "clima.serie", ponto=pid, dias=len(serie))
    return len(serie)


def garantir_normal_climatologica(
    con: duckdb.DuckDBPyConnection,
    latitude: float,
    longitude: float,
    *,
    provedor: ProvedorClima | None = None,
) -> int:
    """Baixa 1991-2020 de uma vez; e o que da sentido a palavra 'anomalia'."""
    return garantir_serie(
        con,
        latitude,
        longitude,
        dt.date(config.NORMAL_CLIMATOLOGICA_INICIO, 1, 1),
        dt.date(config.NORMAL_CLIMATOLOGICA_FIM, 12, 31),
        provedor=provedor,
    )


def municipios_prioritarios(
    con: duckdb.DuckDBPyConnection, limite: int, cultura: str
) -> list[str]:
    """Municipios com maior area plantada da cultura -- onde o clima importa."""
    try:
        rows = con.execute(
            """
            SELECT cod_ibge
            FROM ibge_producao
            WHERE cultura = ? AND variavel = 'area_plantada_ha'
            GROUP BY cod_ibge
            ORDER BY max(valor) DESC NULLS LAST
            LIMIT ?
            """,
            [cultura, limite],
        ).fetchall()
    except duckdb.Error:
        return []
    return [r[0] for r in rows if r[0]]


def executar(
    con: duckdb.DuckDBPyConnection,
    *,
    municipios: tuple[str, ...] | None = None,
    limite: int = 50,
    cultura: str | None = None,
    provedor: str | None = None,
) -> int:
    """Pre-aquece o cache de clima para um conjunto limitado de municipios.

    A consulta por documento tambem busca sob demanda; este passo existe para
    que a demo nao dependa de rede na hora de montar as features.
    """
    cultura = cultura or config.SETTINGS.cultura_padrao
    prov = obter_provedor(provedor)
    from . import ibge_sidra  # import tardio: evita ciclo na importacao do pacote

    alvos = list(municipios or municipios_prioritarios(con, limite, cultura))
    if not alvos:
        log_evento(log, "clima.sem_municipios", cultura=cultura)
        return 0

    total = 0
    for cod_ibge in alvos:
        with etapa(log, "clima.municipio", cod_ibge=cod_ibge) as ctx:
            ponto = ibge_sidra.centroide(con, cod_ibge)
            if not ponto:
                ctx["linhas"] = 0
                continue
            lat, lon = ponto
            dias = garantir_normal_climatologica(con, lat, lon, provedor=prov)
            dias += garantir_serie(
                con,
                lat,
                lon,
                dt.date(dt.date.today().year - 2, 1, 1),
                dt.date.today(),
                provedor=prov,
            )
            ctx["linhas"] = dias
            total += dias
    registrar_ingestao(con, FONTE, prov.nome, "clima_diario", total)
    return total
