"""Grava fixtures com chamadas reais à OpenAI — `04-camada-llm.md` §6.2.

⚠️  **GASTA COTA REAL.** Não roda em teste, não roda no CI, e não foi executado
na sessão em que esta camada foi escrita (HANDOFF §3: orçamento de US$ 10).
Está pronto para quando houver saldo e vontade de substituir as fixtures
escritas à mão por respostas reais do modelo.

    cd api
    .venv/Scripts/python -m llm.scripts.gravar_fixtures \\
        --clientes vale-do-araguaia,<id2>,<id3> \\
        --tarefas parecer,score,recomendacao \\
        --perguntas tests/fixtures/llm/perguntas.json

Volume padrão: 3 clientes × 3 tarefas + as perguntas de 1 cliente.

Regra inegociável: **fixture com violação de fidelidade não é gravada.** O
script imprime as violações e sai com código 2. Fixtures são, por construção,
exemplos fiéis — é o que permite ao `test_verificador` usá-las como referência.

Nunca grava a chave, cabeçalho HTTP nem qualquer dado de credencial.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from llm.contexto import ContextoNarrativo, serializar_contexto
from llm.engine import MensagemCopiloto, TarefaNarrativa
from llm.fixture_engine import RAIZ_DAS_FIXTURES, caminho_da_fixture, gerar_slug
from llm.ledger import LEDGER, custo_usd
from llm.openai_engine import OpenAINarrativeEngine
from llm.prompts import montar_system, montar_user, montar_user_copiloto
from llm.verificador import verificar_fidelidade_numerica
from repository import RepositorioEmMemoria

__all__ = ["main"]

VERSAO_DA_FIXTURE = 1
SAIDA_COM_VIOLACAO = 2
_TAREFAS_PADRAO = "parecer,score,recomendacao"


def _sha(texto: str) -> str:
    return "sha256:" + hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _contexto(
    repositorio: RepositorioEmMemoria, cliente_id: str, tarefa: TarefaNarrativa
) -> ContextoNarrativo:
    cliente = repositorio.obter_cliente(cliente_id)
    if cliente is None:
        raise SystemExit(f"cliente desconhecido: {cliente_id}")
    fatos = repositorio.obter_fatos_atuais(cliente_id)
    avaliacao = repositorio.avaliar_fatos(fatos)
    variacao = repositorio.comparacao_na_janela(cliente_id, avaliacao)
    return serializar_contexto(cliente, fatos, avaliacao, variacao, tarefa)


def _gravar(
    tarefa: TarefaNarrativa,
    contexto: ContextoNarrativo,
    engine: OpenAINarrativeEngine,
    pergunta: str | None,
    slug: str | None,
    raiz: Path,
) -> int:
    system = montar_system(tarefa, contexto)
    user = (
        montar_user_copiloto(contexto, pergunta, [])
        if tarefa == "copiloto"
        else montar_user(tarefa, contexto)
    )
    inicio = datetime.now().astimezone()
    pedacos: list[str] = []
    uso = None
    iterador = (
        engine.responder(contexto, pergunta or "", [], float("inf"))
        if tarefa == "copiloto"
        else engine.gerar(tarefa, contexto, float("inf"))  # type: ignore[arg-type]
    )
    for pedaco in iterador:
        if pedaco.tipo == "texto" and pedaco.texto:
            pedacos.append(pedaco.texto)
        elif pedaco.tipo == "uso":
            uso = pedaco.uso

    saida = "".join(pedacos)
    violacoes = verificar_fidelidade_numerica(saida, contexto)
    if violacoes:
        print(f"[RECUSADA] {tarefa}/{contexto.cliente_id}: violações {violacoes}")
        return SAIDA_COM_VIOLACAO

    destino = caminho_da_fixture(tarefa, contexto.cliente_id, pergunta, raiz)
    if slug:
        destino = destino.with_name(f"{contexto.cliente_id}--{slug}.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {
                "versao": VERSAO_DA_FIXTURE,
                "tarefa": tarefa,
                "clienteId": contexto.cliente_id,
                "pergunta": pergunta,
                "modelo": engine.modelo,
                "gravadoEm": inicio.isoformat(),
                "contextoHash": _sha(contexto.bloco),
                "systemSha256": _sha(system),
                "entrada": {"system": system, "user": user},
                "saida": saida,
                "chunks": pedacos,
                "uso": uso.model_dump() if uso else {},
                "duracaoMs": int(
                    (datetime.now().astimezone() - inicio).total_seconds() * 1000
                ),
                "fidelidade": {"violacoes": []},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[ok] {destino} · US$ {custo_usd(uso):.6f}")
    return 0


def main(argumentos: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--clientes", required=True)
    analisador.add_argument("--tarefas", default=_TAREFAS_PADRAO)
    analisador.add_argument("--perguntas", default="")
    analisador.add_argument("--raiz", default=str(RAIZ_DAS_FIXTURES))
    opcoes = analisador.parse_args(argumentos)

    repositorio = RepositorioEmMemoria()
    engine = OpenAINarrativeEngine()
    raiz = Path(opcoes.raiz)
    clientes = [c.strip() for c in opcoes.clientes.split(",") if c.strip()]
    tarefas = [t.strip() for t in opcoes.tarefas.split(",") if t.strip()]

    codigo = 0
    for cliente_id in clientes:
        for tarefa in tarefas:
            contexto = _contexto(repositorio, cliente_id, tarefa)  # type: ignore[arg-type]
            codigo |= _gravar(tarefa, contexto, engine, None, None, raiz)  # type: ignore[arg-type]

    if opcoes.perguntas and clientes:
        contexto = _contexto(repositorio, clientes[0], "copiloto")
        for item in json.loads(Path(opcoes.perguntas).read_text(encoding="utf-8")):
            pergunta = item["pergunta"]
            slug = item.get("slug") or gerar_slug(pergunta)
            codigo |= _gravar("copiloto", contexto, engine, pergunta, slug, raiz)

    print(f"custo acumulado no ledger: US$ {LEDGER.custo_acumulado:.4f}")
    return codigo


if __name__ == "__main__":  # pragma: no cover - ponto de entrada manual
    sys.exit(main())
