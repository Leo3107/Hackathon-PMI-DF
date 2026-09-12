"""Cliente HTTP compartilhado: rate limit por host, backoff e download resumivel."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from . import config
from .logging_setup import get_logger, log_evento

log = get_logger("http")


class RateLimiter:
    """Token bucket simples, uma instancia por host."""

    def __init__(self, req_por_segundo: float) -> None:
        self._intervalo = 1.0 / req_por_segundo
        self._lock = threading.Lock()
        self._proximo = 0.0

    def acquire(self) -> None:
        with self._lock:
            agora = time.monotonic()
            espera = self._proximo - agora
            if espera > 0:
                time.sleep(espera)
                agora = time.monotonic()
            self._proximo = max(agora, self._proximo) + self._intervalo


_limiters: dict[str, RateLimiter] = {}
_limiters_lock = threading.Lock()


def _limiter_para(url: str) -> RateLimiter:
    host = urlparse(url).netloc
    with _limiters_lock:
        if host not in _limiters:
            _limiters[host] = RateLimiter(config.MAX_REQUESTS_PER_SECOND_PER_HOST)
        return _limiters[host]


_client: httpx.Client | None = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=config.HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": config.USER_AGENT},
        )
    return _client


class HttpErro(RuntimeError):
    pass


def _deve_repetir(status: int) -> bool:
    return status == 429 or 500 <= status < 600


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    content: bytes | None = None,
    stream: bool = False,
) -> httpx.Response:
    """Requisicao com rate limit e backoff exponencial em 429/5xx."""
    ultima_excecao: Exception | None = None
    for tentativa in range(config.HTTP_MAX_RETRIES):
        _limiter_para(url).acquire()
        try:
            if stream:
                req = client().build_request(
                    method, url, headers=headers, params=params, content=content
                )
                resp = client().send(req, stream=True, auth=auth or httpx.USE_CLIENT_DEFAULT)
            else:
                resp = client().request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    auth=auth,
                    content=content,
                )
        except httpx.HTTPError as exc:
            ultima_excecao = exc
            espera = config.HTTP_BACKOFF_BASE_SECONDS ** (tentativa + 1)
            log_evento(
                log, "http.retry", url=url, motivo=str(exc), espera_s=round(espera, 1)
            )
            time.sleep(espera)
            continue

        if _deve_repetir(resp.status_code):
            retry_after = resp.headers.get("Retry-After")
            espera = (
                float(retry_after)
                if retry_after and retry_after.isdigit()
                else config.HTTP_BACKOFF_BASE_SECONDS ** (tentativa + 1)
            )
            if stream:
                resp.close()
            log_evento(
                log,
                "http.retry",
                url=url,
                status=resp.status_code,
                espera_s=round(espera, 1),
            )
            time.sleep(espera)
            ultima_excecao = HttpErro(f"{resp.status_code} em {url}")
            continue
        return resp

    raise HttpErro(f"falhou apos {config.HTTP_MAX_RETRIES} tentativas: {url}") from (
        ultima_excecao
    )


def get_json(url: str, **kwargs: Any) -> Any:
    resp = request("GET", url, **kwargs)
    resp.raise_for_status()
    return resp.json()


def tamanho_remoto(url: str, auth: tuple[str, str] | None = None) -> int | None:
    """Content-Length via HEAD, ou None quando o servidor nao informa."""
    try:
        resp = request("HEAD", url, auth=auth)
    except HttpErro:
        return None
    if resp.status_code >= 400:
        return None
    valor = resp.headers.get("Content-Length")
    return int(valor) if valor and valor.isdigit() else None


def baixar(
    url: str,
    destino: Path,
    *,
    auth: tuple[str, str] | None = None,
    forcar: bool = False,
) -> Path:
    """Baixa `url` para `destino` de forma resumivel e cacheada.

    - Se o arquivo ja existe com o mesmo tamanho do remoto, nao rebaixa.
    - Se existe parcial, tenta continuar via Range; se o servidor nao aceitar,
      recomeca do zero.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    esperado = tamanho_remoto(url, auth=auth)

    if destino.exists() and not forcar:
        atual = destino.stat().st_size
        if esperado is not None and atual == esperado:
            log_evento(log, "download.cache_hit", url=url, bytes=atual)
            return destino
        if esperado is None and atual > 0:
            log_evento(log, "download.cache_sem_tamanho", url=url, bytes=atual)
            return destino

    parcial = destino.with_suffix(destino.suffix + ".part")
    ja_baixado = parcial.stat().st_size if parcial.exists() and not forcar else 0
    if forcar and parcial.exists():
        parcial.unlink()
        ja_baixado = 0

    headers: dict[str, str] = {}
    modo = "wb"
    if ja_baixado and esperado and ja_baixado < esperado:
        headers["Range"] = f"bytes={ja_baixado}-"
        modo = "ab"
    elif ja_baixado:
        parcial.unlink()
        ja_baixado = 0

    inicio = time.monotonic()
    resp = request("GET", url, headers=headers, auth=auth, stream=True)
    try:
        if resp.status_code == 416:  # o servidor diz que ja temos tudo
            parcial.replace(destino)
            return destino
        if headers.get("Range") and resp.status_code != 206:
            # Servidor ignorou o Range: recomeca do zero.
            modo = "wb"
            ja_baixado = 0
        resp.raise_for_status()
        with open(parcial, modo) as fh:
            for bloco in resp.iter_bytes(chunk_size=1 << 20):
                fh.write(bloco)
    finally:
        resp.close()

    total = parcial.stat().st_size
    if esperado is not None and total != esperado:
        raise HttpErro(
            f"tamanho inesperado em {url}: baixado {total}, esperado {esperado}"
        )
    parcial.replace(destino)
    log_evento(
        log,
        "download.ok",
        url=url,
        bytes=total,
        retomado_de=ja_baixado,
        duracao_s=round(time.monotonic() - inicio, 1),
    )
    return destino


def paginar_odata(
    url: str, *, page_size: int, filtro: str | None = None, select: str | None = None
) -> Iterable[list[dict]]:
    """Itera paginas de um endpoint OData usando $top/$skip."""
    skip = 0
    while True:
        params: dict[str, Any] = {
            "$top": page_size,
            "$skip": skip,
            "$format": "json",
        }
        if filtro:
            params["$filter"] = filtro
        if select:
            params["$select"] = select
        payload = get_json(url, params=params)
        valores = payload.get("value", [])
        if not valores:
            return
        yield valores
        if len(valores) < page_size:
            return
        skip += page_size
