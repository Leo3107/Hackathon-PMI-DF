"""Engine OpenAI — o único ponto do sistema que toca a rede do provedor.

`specs/04-camada-llm.md` §1.3. Modelo `gpt-5.4-mini` via SDK oficial, com
`stream=True`.

Fatos já verificados nesta máquina — **não gastar cota reconfirmando**:

- o parâmetro é `max_completion_tokens`; `max_tokens` é rejeitado por esta família;
- `stream=True` + `stream_options={"include_usage": True}` funciona, e o `usage`
  chega no **último** chunk, aquele em que `choices` vem vazio;
- `reasoning_tokens` vem 0;
- latência típica de 6,4 s para ~860 tokens de saída.

Nada além de `model`, `messages`, `stream`, `stream_options` e
`max_completion_tokens` é enviado: `temperature`, `top_p` e afins podem ser
rejeitados por esta família, e o efeito seria toda chamada virar 400 — a
aplicação inteira cairia no determinístico sem ninguém notar.

O cliente é **injetável**: os testes passam um duplo e nunca abrem conexão. O
`OPENAI_API_KEY` é lido só aqui, dentro do `__init__`, nunca é registrado no
ledger, nunca aparece no evento `fim` e nunca entra em fixture.

Nota de nomenclatura: a spec chama este módulo `engine_openai.py`.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator, Literal

from .contexto import ContextoNarrativo, estimar_tokens
from .engine import (
    MAX_SAIDA,
    MODELO_PADRAO,
    EngineIndisponivel,
    EngineTimeout,
    MensagemCopiloto,
    PedacoNarrativa,
    UsoTokens,
)
from .prompts import montar_system, montar_user, montar_user_copiloto

__all__ = ["OpenAINarrativeEngine", "TIMEOUT_TOTAL_S", "TIMEOUT_CONEXAO_S", "TIMEOUT_LEITURA_S"]

TIMEOUT_TOTAL_S = 25.0
TIMEOUT_CONEXAO_S = 5.0
TIMEOUT_LEITURA_S = 12.0

#: Moldura de mensagens (papéis, delimitadores) somada à estimativa de entrada.
MOLDURA_TOKENS = 200

_CODIGOS_RECUPERAVEIS = frozenset({429, 500, 502, 503, 504})


class OpenAINarrativeEngine:
    """`NarrativeEngine` sobre `chat.completions` com streaming."""

    id = "openai"

    def __init__(self, client: Any | None = None, modelo: str | None = None) -> None:
        self.modelo = modelo or os.environ.get("LASTRO_LLM_MODEL", MODELO_PADRAO)
        self._client = client if client is not None else self._abrir_cliente()

    @staticmethod
    def _abrir_cliente() -> Any:
        """Instancia o SDK. Falta de chave ou de pacote vira `EngineIndisponivel`."""
        chave = os.environ.get("OPENAI_API_KEY", "").strip()
        if not chave:
            raise EngineIndisponivel("OPENAI_API_KEY ausente", recuperavel=False)
        try:
            import httpx  # noqa: PLC0415 — importação tardia, só no caminho de rede
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as erro:  # pragma: no cover - dependência declarada
            raise EngineIndisponivel(f"SDK indisponível: {erro}", recuperavel=False) from erro
        return OpenAI(
            api_key=chave,
            timeout=httpx.Timeout(
                TIMEOUT_TOTAL_S, connect=TIMEOUT_CONEXAO_S, read=TIMEOUT_LEITURA_S
            ),
            # O retry é decisão do executor (§2.4), não do SDK: só vale a pena
            # tentar de novo se nenhum texto foi emitido e ainda há deadline.
            max_retries=0,
        )

    # -- Contrato do Protocol ------------------------------------------------

    def gerar(
        self,
        tarefa: Literal["parecer", "score", "recomendacao"],
        contexto: ContextoNarrativo,
        deadline: float,
    ) -> Iterator[PedacoNarrativa]:
        yield from self._chamar(
            montar_system(tarefa, contexto),
            montar_user(tarefa, contexto),
            MAX_SAIDA[tarefa],
            deadline,
        )

    def responder(
        self,
        contexto: ContextoNarrativo,
        pergunta: str,
        historico: list[MensagemCopiloto] | None = None,
        deadline: float = float("inf"),
    ) -> Iterator[PedacoNarrativa]:
        yield from self._chamar(
            montar_system("copiloto", contexto),
            montar_user_copiloto(contexto, pergunta, historico),
            MAX_SAIDA["copiloto"],
            deadline,
        )

    # -- Chamada -------------------------------------------------------------

    def _chamar(
        self, system: str, user: str, max_saida: int, deadline: float
    ) -> Iterator[PedacoNarrativa]:
        stream = self._abrir_stream(system, user, max_saida)
        uso: UsoTokens | None = None
        try:
            for chunk in stream:
                if time.monotonic() > deadline:
                    raise EngineTimeout("deadline da requisição ultrapassado")
                texto = _texto_do_chunk(chunk)
                if texto:
                    yield PedacoNarrativa(tipo="texto", texto=texto)
                lido = _uso_do_chunk(chunk)
                if lido is not None:
                    uso = lido
        except (EngineTimeout, EngineIndisponivel):
            raise
        except Exception as erro:  # noqa: BLE001 — contrato: só duas exceções escapam
            raise EngineIndisponivel(str(erro), recuperavel=_recuperavel(erro)) from erro
        finally:
            _fechar(stream)
        yield PedacoNarrativa(tipo="uso", uso=uso or self._estimar_uso(system, user))

    def _abrir_stream(self, system: str, user: str, max_saida: int) -> Any:
        try:
            return self._client.chat.completions.create(
                model=self.modelo,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                stream=True,
                stream_options={"include_usage": True},
                max_completion_tokens=max_saida,
            )
        except Exception as erro:  # noqa: BLE001
            raise EngineIndisponivel(str(erro), recuperavel=_recuperavel(erro)) from erro

    @staticmethod
    def _estimar_uso(system: str, user: str) -> UsoTokens:
        """Stream abortado antes do chunk de `usage`: estima e marca `estimado`."""
        return UsoTokens(
            entrada=estimar_tokens(system) + estimar_tokens(user) + MOLDURA_TOKENS,
            saida=0,
            raciocinio=0,
            estimado=True,
        )


def _texto_do_chunk(chunk: Any) -> str | None:
    escolhas = getattr(chunk, "choices", None)
    if not escolhas:
        return None
    delta = getattr(escolhas[0], "delta", None)
    return getattr(delta, "content", None) if delta is not None else None


def _uso_do_chunk(chunk: Any) -> UsoTokens | None:
    """O último chunk traz `usage` e `choices` vazio."""
    uso = getattr(chunk, "usage", None)
    if uso is None:
        return None
    detalhes = getattr(uso, "completion_tokens_details", None)
    return UsoTokens(
        entrada=getattr(uso, "prompt_tokens", 0) or 0,
        saida=getattr(uso, "completion_tokens", 0) or 0,
        raciocinio=getattr(detalhes, "reasoning_tokens", 0) or 0,
    )


def _recuperavel(erro: Exception) -> bool:
    """429, 5xx e erro de conexão valem uma segunda tentativa; 4xx não."""
    codigo = getattr(erro, "status_code", None)
    if codigo is None:
        resposta = getattr(erro, "response", None)
        codigo = getattr(resposta, "status_code", None)
    if codigo is None:
        return True
    return int(codigo) in _CODIGOS_RECUPERAVEIS


def _fechar(stream: Any) -> None:
    fechar = getattr(stream, "close", None)
    if callable(fechar):
        try:
            fechar()
        except Exception:  # noqa: BLE001, S110 — fechar não pode derrubar a resposta
            pass
