"""Protestos (fonte 7) - consulta por documento, com cache de 24h.

NAO existe API publica gratuita de protestos. O portal da CENPROT e protegido
por CAPTCHA, e este projeto nao quebra CAPTCHA nem contorna protecao
anti-bot -- isso violaria os termos de uso do servico.

O desenho aqui e uma interface de provedor com duas implementacoes:

- `CSVManualProvider`: le uma planilha preenchida a mao. E o caminho do demo.
- `ApiProvider`: stub para fornecedor homologado, com token via variavel de
  ambiente. A assinatura e o parsing ja estao prontos; so a chamada HTTP fica
  isolada num metodo.

Trocar para um fornecedor pago e mudar `COLETA_PROVEDOR_PROTESTO=api`.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import duckdb
from pydantic import BaseModel, Field

from .. import config, http
from ..logging_setup import get_logger, log_evento
from ..warehouse import normalizar_documento

log = get_logger("ondemand.protestos")


class Protesto(BaseModel):
    data: dt.date | None = None
    valor: float | None = None
    cartorio: str | None = None
    uf: str | None = None
    situacao: str | None = None


class ProtestoResult(BaseModel):
    documento: str
    provedor: str
    consultado_em: dt.datetime = Field(default_factory=dt.datetime.now)
    disponivel: bool = True
    protestos: list[Protesto] = Field(default_factory=list)

    @property
    def ativos(self) -> list[Protesto]:
        return [
            p
            for p in self.protestos
            if (p.situacao or "").strip().upper() not in {"CANCELADO", "BAIXADO", "QUITADO"}
        ]


@runtime_checkable
class ProtestoProvider(Protocol):
    nome: str

    def consultar(self, documento: str) -> ProtestoResult: ...


class CSVManualProvider:
    """Le `data/raw/protestos_manual.csv`, preenchido a mao. Para o demo.

    Colunas esperadas (separador `;`):
    documento;data_protesto;valor;cartorio;uf;situacao
    """

    nome = "csv_manual"
    COLUNAS = ("documento", "data_protesto", "valor", "cartorio", "uf", "situacao")

    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = Path(caminho or config.PROTESTO_CSV_MANUAL)

    def _linhas(self) -> list[dict]:
        if not self.caminho.exists():
            log_evento(log, "protestos.csv_ausente", caminho=str(self.caminho))
            return []
        with open(self.caminho, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    @staticmethod
    def _data(valor: str | None) -> dt.date | None:
        if not valor:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return dt.datetime.strptime(valor.strip(), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _valor(valor: str | None) -> float | None:
        if not valor:
            return None
        limpo = valor.strip().replace(".", "").replace(",", ".")
        try:
            return float(limpo)
        except ValueError:
            return None

    def consultar(self, documento: str) -> ProtestoResult:
        alvo = normalizar_documento(documento)
        linhas = self._linhas()
        if not linhas:
            # Planilha vazia (ou ausente) e "fonte nao disponivel", nao
            # "documento sem protesto".
            return ProtestoResult(
                documento=alvo or documento, provedor=self.nome, disponivel=False
            )
        protestos = [
            Protesto(
                data=self._data(linha.get("data_protesto")),
                valor=self._valor(linha.get("valor")),
                cartorio=(linha.get("cartorio") or "").strip() or None,
                uf=(linha.get("uf") or "").strip() or None,
                situacao=(linha.get("situacao") or "").strip() or None,
            )
            for linha in linhas
            if normalizar_documento(linha.get("documento")) == alvo
        ]
        return ProtestoResult(
            documento=alvo or documento, provedor=self.nome, protestos=protestos
        )


class ApiProvider:
    """Stub para fornecedor homologado de consulta de protestos.

    Toda a chamada de rede esta isolada em `_chamar_api`; o resto (parsing,
    normalizacao, cache) ja e definitivo. Integrar um fornecedor real e
    ajustar a URL e o formato de resposta em um lugar so.
    """

    nome = "api"

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or config.PROTESTO_API_BASE_URL
        self.token = token or os.environ.get(config.PROTESTO_API_TOKEN_ENV, "")

    @property
    def configurado(self) -> bool:
        return bool(self.base_url and self.token)

    def _chamar_api(self, documento: str) -> dict:
        """Unico ponto que fala com o fornecedor. Trocar aqui, nada mais."""
        return http.get_json(
            f"{self.base_url.rstrip('/')}/protestos/{documento}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _parse(payload: dict) -> list[Protesto]:
        """Parsing do formato mais comum entre fornecedores do mercado."""
        itens = payload.get("protestos") or payload.get("data") or []
        saida: list[Protesto] = []
        for item in itens:
            data = item.get("dataProtesto") or item.get("data")
            try:
                data_conv = dt.date.fromisoformat(str(data)[:10]) if data else None
            except ValueError:
                data_conv = None
            valor = item.get("valor") or item.get("valorProtestado")
            try:
                valor_conv = float(valor) if valor is not None else None
            except (TypeError, ValueError):
                valor_conv = None
            saida.append(
                Protesto(
                    data=data_conv,
                    valor=valor_conv,
                    cartorio=item.get("cartorio") or item.get("nomeCartorio"),
                    uf=item.get("uf") or item.get("estado"),
                    situacao=item.get("situacao") or item.get("status"),
                )
            )
        return saida

    def consultar(self, documento: str) -> ProtestoResult:
        alvo = normalizar_documento(documento) or documento
        if not self.configurado:
            log_evento(
                log,
                "protestos.api_nao_configurada",
                dica=(
                    f"defina PROTESTO_API_BASE_URL e {config.PROTESTO_API_TOKEN_ENV}"
                ),
            )
            return ProtestoResult(documento=alvo, provedor=self.nome, disponivel=False)
        try:
            payload = self._chamar_api(alvo)
        except Exception as exc:  # noqa: BLE001 - fonte externa nao derruba nada
            log_evento(log, "protestos.api_falhou", erro=str(exc)[:200])
            return ProtestoResult(documento=alvo, provedor=self.nome, disponivel=False)
        return ProtestoResult(
            documento=alvo, provedor=self.nome, protestos=self._parse(payload)
        )


PROVEDORES: dict[str, type] = {
    "csv_manual": CSVManualProvider,
    "api": ApiProvider,
}


def obter_provedor(nome: str | None = None) -> ProtestoProvider:
    nome = nome or config.SETTINGS.provedor_protesto
    if nome not in PROVEDORES:
        raise ValueError(
            f"provedor de protesto desconhecido: {nome} "
            f"(disponiveis: {', '.join(PROVEDORES)})"
        )
    return PROVEDORES[nome]()


# ------------------------------------------------------------------ cache ---

def consultar(
    con: duckdb.DuckDBPyConnection,
    documento: str,
    *,
    provedor: ProtestoProvider | None = None,
    ttl_horas: int | None = None,
) -> ProtestoResult:
    """Consulta com cache de 24h no warehouse."""
    provedor = provedor or obter_provedor()
    alvo = normalizar_documento(documento) or documento
    ttl = ttl_horas if ttl_horas is not None else config.PROTESTO_CACHE_TTL_HORAS

    row = con.execute(
        """
        SELECT payload_json
        FROM protesto_cache
        WHERE documento = ? AND provedor = ?
          AND consultado_em >= now() - INTERVAL (?) HOUR
        ORDER BY consultado_em DESC
        LIMIT 1
        """,
        [alvo, provedor.nome, ttl],
    ).fetchone()
    if row and row[0]:
        try:
            return ProtestoResult.model_validate_json(row[0])
        except Exception:  # noqa: BLE001 - cache corrompido e so descartado
            pass

    resultado = provedor.consultar(alvo)
    try:
        con.execute(
            "DELETE FROM protesto_cache WHERE documento = ? AND provedor = ?",
            [alvo, provedor.nome],
        )
        con.execute(
            "INSERT INTO protesto_cache "
            "(documento, provedor, consultado_em, payload_json) VALUES (?,?,?,?)",
            [alvo, provedor.nome, resultado.consultado_em, resultado.model_dump_json()],
        )
    except duckdb.Error as exc:
        # Warehouse aberto em somente leitura (a API roda assim): nao da para
        # gravar o cache, mas o resultado em si e valido -- o provedor CSV nem
        # toca a rede. Perder o cache nao pode custar a consulta.
        log_evento(log, "protestos.cache_nao_gravado", erro=str(exc)[:120])
    return resultado


def features(resultado: ProtestoResult | None) -> dict:
    """Traduz o resultado em features. Sem dado -> tudo `None`."""
    vazio = {
        "n_protestos_ativos": None,
        "valor_total_protestado": None,
        "dias_desde_protesto_mais_recente": None,
        "n_cartorios_distintos": None,
    }
    if resultado is None or not resultado.disponivel:
        return vazio

    ativos = resultado.ativos
    if not ativos:
        # Consulta bem-sucedida sem protesto e informacao: e zero, nao ausencia.
        return {
            "n_protestos_ativos": 0,
            "valor_total_protestado": 0.0,
            "dias_desde_protesto_mais_recente": None,
            "n_cartorios_distintos": 0,
        }

    datas = [p.data for p in ativos if p.data]
    valores = [p.valor for p in ativos if p.valor is not None]
    cartorios = {p.cartorio for p in ativos if p.cartorio}
    return {
        "n_protestos_ativos": len(ativos),
        "valor_total_protestado": round(sum(valores), 2) if valores else None,
        "dias_desde_protesto_mais_recente": (
            (dt.date.today() - max(datas)).days if datas else None
        ),
        "n_cartorios_distintos": len(cartorios),
    }


def exemplo_csv() -> str:
    """Cabecalho do CSV manual, usado pela CLI para criar o arquivo modelo."""
    return ";".join(CSVManualProvider.COLUNAS) + "\n"


__all__ = [
    "ApiProvider",
    "CSVManualProvider",
    "Protesto",
    "ProtestoProvider",
    "ProtestoResult",
    "consultar",
    "exemplo_csv",
    "features",
    "obter_provedor",
]
