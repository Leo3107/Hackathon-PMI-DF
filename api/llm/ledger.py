"""Ledger de custo, reserva, disjuntor e persistência — `04-camada-llm.md` §5.

O orçamento é **dinheiro real do usuário** (HANDOFF §3: US$ 10 de saldo). Este
módulo é a defesa contra gasto silencioso, e tem quatro mecanismos:

1. **Reserva prévia.** Antes de chamar a OpenAI o executor reserva o custo
   máximo da chamada. Três blocos de prosa abrindo juntos não furam o teto
   entre eles, porque cada um vê a reserva dos outros.
2. **Teto rígido.** Atingido o orçamento, `selecionar_engine` devolve
   `ORCAMENTO` e a aplicação segue inteira no engine determinístico.
3. **Disjuntor.** Três falhas de rede/5xx em 120 s abrem o disjuntor por 60 s,
   para que o pitch não fique 25 s esperando uma API que está fora.
4. **Diário append-only.** `RegistroChamada` com `origem_final == "openai"` é
   anexado a `.lastro/ledger.jsonl`, e o total é reconstituído no boot. Um
   `restart` do Flask não pode zerar gasto que já aconteceu.

**Isto não é cache de resposta** (D4): nenhum texto gerado é gravado, e nenhuma
chamada é evitada por causa do arquivo.

O ledger é estado do processo, protegido por `threading.Lock`. O Flask roda com
**processo único** — ver o cabeçalho de `api/app.py`.

Nota de nomenclatura: a spec chama este módulo `custo.py`.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .engine import EngineId, TarefaNarrativa, UsoTokens

__all__ = [
    "RegistroChamada",
    "Reserva",
    "Ledger",
    "LEDGER",
    "custo_usd",
    "preco_entrada",
    "preco_saida",
    "orcamento",
    "reiniciar",
    "MAX_REGISTROS",
    "MAX_ULTIMAS",
    "FALHAS_PARA_ABRIR",
    "JANELA_DE_FALHAS_S",
    "DURACAO_DO_DISJUNTOR_S",
]

StatusChamada = Literal[
    "ok", "degradado", "timeout", "falha_rede", "orcamento", "fidelidade", "erro"
]

#: Últimas chamadas mantidas em memória (§5.3) e devolvidas pelo endpoint (§5.5).
MAX_REGISTROS = 500
MAX_ULTIMAS = 20

#: Disjuntor (§1.4).
FALHAS_PARA_ABRIR = 3
JANELA_DE_FALHAS_S = 120.0
DURACAO_DO_DISJUNTOR_S = 60.0

_POR_MILHAO = 1_000_000
_MS_POR_S = 1000
_PCT = 100.0

_STATUS_POR_MOTIVO: dict[str, StatusChamada] = {
    "TIMEOUT": "timeout",
    "FALHA_REDE": "falha_rede",
    "FIDELIDADE_NUMERICA": "fidelidade",
    "SAIDA_VAZIA": "degradado",
    "ORCAMENTO": "orcamento",
    "DISJUNTOR": "degradado",
    "LLM_DESLIGADO": "degradado",
    "SEM_CHAVE": "degradado",
    "FORCADO_POR_ENV": "degradado",
}


def preco_entrada() -> float:
    """US$ por 1M de tokens de entrada. Lido a cada chamada — testes sobrescrevem."""
    return float(os.environ.get("LASTRO_LLM_PRICE_IN_PER_MTOK", "0.25"))


def preco_saida() -> float:
    return float(os.environ.get("LASTRO_LLM_PRICE_OUT_PER_MTOK", "2.00"))


def orcamento() -> float:
    return float(os.environ.get("LASTRO_LLM_BUDGET_USD", "8"))


def custo_usd(uso: UsoTokens | None) -> float:
    """Custo de uma chamada.

    Os tokens de raciocínio já vêm dentro de `saida` na resposta da API — somar
    de novo dobraria o custo contabilizado.

        >>> round(custo_usd(UsoTokens(entrada=604, saida=863)), 6)
        0.001877
    """
    if uso is None:
        return 0.0
    return (uso.entrada * preco_entrada() + uso.saida * preco_saida()) / _POR_MILHAO


class RegistroChamada(BaseModel):
    """Uma linha do diário (§5.3). Nunca contém texto gerado nem a chave."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    data_hora: str
    tarefa: TarefaNarrativa
    cliente_id: str
    engine_selecionado: EngineId
    origem_final: EngineId
    modelo: str | None = None
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_raciocinio: int = 0
    estimado: bool = False
    custo_usd: float = 0.0
    duracao_ms: int = 0
    status: StatusChamada = "ok"
    motivo: str | None = None
    incidente: dict | None = None

    def uso_json(self) -> dict:
        """Campo `uso` do evento `fim` do protocolo NDJSON (§2.3)."""
        return {
            "entrada": self.tokens_entrada,
            "saida": self.tokens_saida,
            "raciocinio": self.tokens_raciocinio,
            "estimado": self.estimado,
            "custoUsd": round(self.custo_usd, 6),
        }

    def resumo_json(self) -> dict:
        """Uma linha de `ultimas` no `GET /api/llm/custo` (§5.5)."""
        return {
            "id": self.id,
            "dataHora": self.data_hora,
            "tarefa": self.tarefa,
            "clienteId": self.cliente_id,
            "origemFinal": self.origem_final,
            "tokensEntrada": self.tokens_entrada,
            "tokensSaida": self.tokens_saida,
            "custoUsd": round(self.custo_usd, 6),
            "duracaoMs": self.duracao_ms,
            "status": self.status,
            "motivo": self.motivo,
        }


class Reserva(BaseModel):
    """Valor congelado no orçamento enquanto uma chamada está em voo (§5.2)."""

    id: str
    valor_usd: float


class Ledger:
    """Diário de custo do processo. Toda mutação passa por um único lock."""

    def __init__(self, caminho: str | None = None, relogio=time.monotonic) -> None:
        self._lock = threading.RLock()
        self._relogio = relogio
        self._registros: list[RegistroChamada] = []
        self._reservas: dict[str, float] = {}
        self._custo_acumulado = 0.0
        self._tokens = {"entrada": 0, "saida": 0, "raciocinio": 0}
        self._chamadas: dict[str, int] = {
            "total": 0,
            "openai": 0,
            "deterministico": 0,
            "fixture": 0,
        }
        self._incidentes = 0
        self._falhas: list[float] = []
        self._disjuntor_ate = 0.0
        self._caminho = self._resolver_caminho(caminho)
        self._reconstituir()

    # -- Persistência --------------------------------------------------------

    @staticmethod
    def _resolver_caminho(caminho: str | None) -> Path | None:
        """Vazio (o padrão em teste) significa **só memória**, sem tocar o disco."""
        bruto = (
            caminho
            if caminho is not None
            else os.environ.get("LASTRO_LLM_LEDGER_PATH", ".lastro/ledger.jsonl")
        )
        if not bruto.strip():
            return None
        destino = Path(bruto)
        if not destino.is_absolute():
            destino = Path(__file__).resolve().parent.parent / destino
        return destino

    def _reconstituir(self) -> None:
        """Soma o `custoUsd` do `.jsonl` para o total sobreviver a um restart."""
        if self._caminho is None or not self._caminho.exists():
            return
        for linha in self._caminho.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            try:
                dados = json.loads(linha)
            except json.JSONDecodeError:  # pragma: no cover - linha truncada
                continue
            self._custo_acumulado += float(dados.get("custoUsd", 0.0))
            self._chamadas["total"] += 1
            self._chamadas["openai"] += 1
            self._tokens["entrada"] += int(dados.get("tokensEntrada", 0))
            self._tokens["saida"] += int(dados.get("tokensSaida", 0))

    def _anexar(self, registro: RegistroChamada) -> None:
        if self._caminho is None or registro.origem_final != "openai":
            return
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        with self._caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro.resumo_json(), ensure_ascii=False) + "\n")

    # -- Orçamento -----------------------------------------------------------

    @property
    def custo_acumulado(self) -> float:
        with self._lock:
            return self._custo_acumulado

    @property
    def reservado(self) -> float:
        with self._lock:
            return sum(self._reservas.values())

    def cabe_no_orcamento(self, custo_previsto_usd: float) -> bool:
        """`acumulado + reservado + previsto <= ORCAMENTO` (§5.2). Teto rígido."""
        with self._lock:
            comprometido = self._custo_acumulado + sum(self._reservas.values())
            return comprometido + custo_previsto_usd <= orcamento()

    def reservar(self, custo_previsto_usd: float, reserva_id: str = "") -> Reserva:
        with self._lock:
            identificador = reserva_id or f"r{len(self._reservas)}-{self._relogio()}"
            self._reservas[identificador] = custo_previsto_usd
            return Reserva(id=identificador, valor_usd=custo_previsto_usd)

    def liberar(self, reserva: Reserva | None) -> None:
        if reserva is None:
            return
        with self._lock:
            self._reservas.pop(reserva.id, None)

    # -- Disjuntor -----------------------------------------------------------

    def registrar_falha_rede(self) -> None:
        """3 falhas em 120 s abrem o disjuntor por 60 s."""
        with self._lock:
            agora = self._relogio()
            self._falhas = [t for t in self._falhas if agora - t <= JANELA_DE_FALHAS_S]
            self._falhas.append(agora)
            if len(self._falhas) >= FALHAS_PARA_ABRIR:
                self._disjuntor_ate = agora + DURACAO_DO_DISJUNTOR_S
                self._falhas.clear()

    def disjuntor_aberto(self) -> bool:
        with self._lock:
            return self._relogio() < self._disjuntor_ate

    # -- Incidentes ----------------------------------------------------------

    def registrar_incidente(
        self,
        requisicao_id: str,
        tipo: str,
        violacoes: Iterable[str],
        severidade: str = "MAXIMA",
    ) -> dict:
        """Um número inventado que chegaria à tela. Severidade máxima por I7.f."""
        with self._lock:
            self._incidentes += 1
        return {
            "tipo": tipo,
            "severidade": severidade,
            "requisicaoId": requisicao_id,
            "violacoes": list(violacoes),
        }

    @property
    def incidentes(self) -> int:
        with self._lock:
            return self._incidentes

    # -- Fechamento de chamada ----------------------------------------------

    def fechar(
        self,
        reserva: Reserva | None,
        requisicao_id: str,
        tarefa: TarefaNarrativa,
        cliente_id: str,
        engine_selecionado: EngineId,
        origem_final: EngineId,
        uso: UsoTokens | None,
        motivo: str | None,
        duracao_s: float,
        modelo: str | None = None,
        incidente: dict | None = None,
    ) -> RegistroChamada:
        """Substitui a reserva pelo custo real e grava a linha do diário."""
        efetivo = uso if origem_final == "openai" or engine_selecionado == "openai" else None
        registro = RegistroChamada(
            id=requisicao_id,
            data_hora=datetime.now().astimezone().isoformat(),
            tarefa=tarefa,
            cliente_id=cliente_id,
            engine_selecionado=engine_selecionado,
            origem_final=origem_final,
            modelo=modelo,
            tokens_entrada=efetivo.entrada if efetivo else 0,
            tokens_saida=efetivo.saida if efetivo else 0,
            tokens_raciocinio=efetivo.raciocinio if efetivo else 0,
            estimado=bool(efetivo and efetivo.estimado),
            custo_usd=custo_usd(efetivo),
            duracao_ms=int(duracao_s * _MS_POR_S),
            status=_STATUS_POR_MOTIVO.get(motivo or "", "ok"),
            motivo=motivo,
            incidente=incidente,
        )
        with self._lock:
            self.liberar(reserva)
            self._custo_acumulado += registro.custo_usd
            self._tokens["entrada"] += registro.tokens_entrada
            self._tokens["saida"] += registro.tokens_saida
            self._tokens["raciocinio"] += registro.tokens_raciocinio
            self._chamadas["total"] += 1
            self._chamadas[engine_selecionado] = (
                self._chamadas.get(engine_selecionado, 0) + 1
            )
            self._registros.append(registro)
            del self._registros[:-MAX_REGISTROS]
        self._anexar(registro)
        return registro

    # -- Leitura -------------------------------------------------------------

    def resumo_curto(self) -> dict:
        """Campo `acumulado` do evento `fim` (§2.3)."""
        with self._lock:
            teto = orcamento()
            return {
                "custoUsd": round(self._custo_acumulado, 6),
                "chamadas": self._chamadas["total"],
                "pctOrcamento": round(self._custo_acumulado / teto * _PCT, 2)
                if teto
                else 0.0,
            }

    def resumo(
        self,
        habilitado: bool,
        engine_ativo: EngineId,
        modelo: str | None,
        motivo_desligado: str | None,
    ) -> dict:
        """Corpo de `GET /api/llm/custo` (§5.5)."""
        with self._lock:
            teto = orcamento()
            return {
                "habilitado": habilitado,
                "engineAtivo": engine_ativo,
                "modelo": modelo,
                "orcamentoUsd": teto,
                "custoAcumuladoUsd": round(self._custo_acumulado, 6),
                "reservadoUsd": round(sum(self._reservas.values()), 6),
                "pctOrcamento": round(self._custo_acumulado / teto * _PCT, 2)
                if teto
                else 0.0,
                "chamadas": dict(self._chamadas),
                "tokens": dict(self._tokens),
                "incidentes": self._incidentes,
                "motivoDesligado": motivo_desligado,
                "ultimas": [
                    registro.resumo_json()
                    for registro in reversed(self._registros[-MAX_ULTIMAS:])
                ],
            }

    def registros(self) -> list[RegistroChamada]:
        with self._lock:
            return list(self._registros)


#: Singleton do processo. `api/app.py` documenta por que o Flask roda com um só.
LEDGER = Ledger()


def reiniciar(caminho: str | None = None, relogio=time.monotonic) -> Ledger:
    """Recria o singleton. Usado pela suíte para isolar cada teste do disco."""
    global LEDGER  # noqa: PLW0603 — o singleton é deliberado (§5.3)
    LEDGER = Ledger(caminho, relogio)
    return LEDGER
