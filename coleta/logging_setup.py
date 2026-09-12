"""Logging estruturado (JSON lines) com contagem de linhas por etapa."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "campos", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(nivel: str | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    nivel = nivel or os.environ.get("COLETA_LOG_LEVEL", "INFO")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("coleta")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(nivel.upper())
    root.propagate = False
    _CONFIGURED = True


def get_logger(nome: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"coleta.{nome}")


def log_evento(logger: logging.Logger, msg: str, **campos: Any) -> None:
    """Log de uma linha com campos estruturados anexados."""
    logger.info(msg, extra={"campos": campos})


@contextmanager
def etapa(logger: logging.Logger, nome: str, **campos: Any) -> Iterator[dict]:
    """Cronometra uma etapa e registra `linhas` no fim.

    O dicionario devolvido aceita `ctx["linhas"] = n` para que o log final
    carregue a contagem carregada.
    """
    ctx: dict[str, Any] = {"linhas": 0}
    inicio = time.monotonic()
    log_evento(logger, f"etapa.inicio: {nome}", etapa=nome, **campos)
    try:
        yield ctx
    except Exception as exc:  # noqa: BLE001 - registrado e repassado
        logger.error(
            f"etapa.erro: {nome}",
            extra={
                "campos": {
                    "etapa": nome,
                    "erro": f"{type(exc).__name__}: {exc}",
                    "duracao_s": round(time.monotonic() - inicio, 2),
                    **campos,
                }
            },
            exc_info=False,
        )
        raise
    else:
        log_evento(
            logger,
            f"etapa.fim: {nome}",
            etapa=nome,
            linhas=ctx.get("linhas", 0),
            duracao_s=round(time.monotonic() - inicio, 2),
            **campos,
        )
