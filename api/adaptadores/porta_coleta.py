"""Fronteira de I/O com a camada de coleta. **Todo** o I/O do adaptador mora aqui.

`features_para_fatos` e `cobertura` são funções puras e continuam assim: este
módulo é o único que abre o warehouse DuckDB e chama `coleta.features`.

Três garantias, nesta ordem de importância:

1. **Tolerante.** Warehouse ausente, `duckdb` não instalado, tabela vazia — tudo
   devolve `None` em vez de levantar. O serviço sobe e a due diligence degrada
   para "documento não encontrado", nunca para erro 500.
2. **Somente leitura.** O warehouse abre `read_only=True` pelo motivo que o
   `coleta/README.md` explica: DuckDB aceita vários leitores e um só escritor,
   e o agendador de cargas pode estar rodando ao lado.
3. **Sem rede.** `permitir_rede=False`: em modo leitura o cache de clima e
   protestos não pode ser gravado, e a primeira consulta de um município sem
   cache leva 17 s — inaceitável dentro de uma requisição HTTP.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Protocol

__all__ = ["PortaDeColeta", "ColetaDuckDB", "coleta_padrao", "warehouse_disponivel"]

_log = logging.getLogger(__name__)


class PortaDeColeta(Protocol):
    """O que a rota precisa da coleta. Um dublê de teste implementa isto."""

    def features_de(self, documento: str, cultura: str | None = None) -> Any | None: ...


def caminho_do_warehouse() -> Path | None:
    try:
        from coleta import config  # noqa: PLC0415 — dependência opcional

        return Path(os.environ.get("COLETA_WAREHOUSE", str(config.WAREHOUSE_PATH)))
    except Exception:  # noqa: BLE001 — ausência da coleta não derruba a API
        return None


def warehouse_disponivel() -> bool:
    caminho = caminho_do_warehouse()
    return caminho is not None and caminho.exists()


class ColetaDuckDB:
    """Implementação real: warehouse DuckDB em somente leitura, sem rede."""

    def __init__(self, caminho: Path | None = None) -> None:
        self._caminho = caminho or caminho_do_warehouse()
        self._con = None

    def _conexao(self):
        if self._con is not None:
            return self._con
        if self._caminho is None or not self._caminho.exists():
            return None
        try:
            from coleta import warehouse  # noqa: PLC0415

            self._con = warehouse.conectar(self._caminho, read_only=True)
        except Exception as erro:  # noqa: BLE001
            _log.warning("Warehouse da coleta indisponível: %s", erro)
            return None
        return self._con

    def features_de(self, documento: str, cultura: str | None = None):
        """`Features` do documento, ou `None` se a coleta não puder responder."""
        con = self._conexao()
        if con is None:
            return None
        try:
            from coleta.features import build_features  # noqa: PLC0415
            from coleta.models import Features  # noqa: PLC0415

            bruto = build_features(
                documento, con=con.cursor(), cultura=cultura, permitir_rede=False
            )
            return Features.model_validate(bruto)
        except Exception as erro:  # noqa: BLE001 — um CNPJ não derruba a rota
            _log.warning("Falha ao montar features de %s: %s", documento, erro)
            return None


_padrao: ColetaDuckDB | None = None


def coleta_padrao() -> ColetaDuckDB:
    """Instância compartilhada pelo processo (worker único, ver `app.py`)."""
    global _padrao  # noqa: PLW0603 — cache de processo, como o repositório
    if _padrao is None:
        _padrao = ColetaDuckDB()
    return _padrao
