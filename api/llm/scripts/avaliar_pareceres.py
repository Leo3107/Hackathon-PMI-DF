"""Rubrica de qualidade com juiz LLM — `04-camada-llm.md` §7.5.

⚠️  **GASTA COTA REAL** (2 chamadas por cliente: o parecer e o julgamento).
Não roda em teste nem no CI, e não foi executado na sessão em que a camada foi
escrita. Deixado pronto para quando houver saldo.

    cd api
    .venv/Scripts/python -m llm.scripts.avaliar_pareceres \\
        --clientes <10 ids> --saida .lastro/avaliacao-2026-09-12.json

Critério de aprovação (§7.2), calculado **em código**, nunca pelo juiz:

    aprovado := fidelidade == 5
             and verificador_automatico.violacoes == []
             and min(estrutura, qualidade, acionabilidade) >= 3
             and media(estrutura, qualidade, acionabilidade) >= 4,0

Meta para o pitch: ≥ 90% de aprovação numa amostra de 10 pareceres com clientes
variados — um com veto, um em RJ com Stay Period e um rating A. Qualquer
fidelidade < 5 é incidente de severidade máxima e bloqueia o release.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import fmean

from llm.contexto import serializar_contexto
from llm.ledger import LEDGER
from llm.openai_engine import OpenAINarrativeEngine
from llm.prompts import SYSTEM_JUIZ, montar_user_juiz
from llm.verificador import contar_palavras, verificar_fidelidade_numerica
from pydantic import BaseModel, Field, ValidationError
from repository import RepositorioEmMemoria

__all__ = ["NotaJuiz", "aprovado", "main"]

MAX_SAIDA_DO_JUIZ = 700
NOTA_MINIMA_POR_LENTE = 3
MEDIA_MINIMA = 4.0
FIDELIDADE_APROVADA = 5
TENTATIVAS_DO_JUIZ = 2


class NotaJuiz(BaseModel):
    """Saída do juiz (§7.3). JSON inválido duas vezes → parecer `nao_avaliado`."""

    fidelidade: int
    estrutura: int
    qualidade: int
    acionabilidade: int
    numeros_suspeitos: list[dict] = Field(default_factory=list, alias="numerosSuspeitos")
    justificativas: dict[str, str] = Field(default_factory=dict)


def aprovado(nota: NotaJuiz, violacoes: list[str]) -> bool:
    """A regra da §7.2, literal."""
    outras = (nota.estrutura, nota.qualidade, nota.acionabilidade)
    return (
        nota.fidelidade == FIDELIDADE_APROVADA
        and not violacoes
        and min(outras) >= NOTA_MINIMA_POR_LENTE
        and fmean(outras) >= MEDIA_MINIMA
    )


def _texto_de(iterador) -> str:
    return "".join(p.texto or "" for p in iterador if p.tipo == "texto")


def _julgar(engine: OpenAINarrativeEngine, user: str) -> NotaJuiz | None:
    for _ in range(TENTATIVAS_DO_JUIZ):
        bruto = _texto_de(
            engine._chamar(SYSTEM_JUIZ, user, MAX_SAIDA_DO_JUIZ, float("inf"))
        )
        try:
            return NotaJuiz.model_validate_json(bruto.strip())
        except (ValidationError, ValueError):
            continue
    return None


def main(argumentos: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--clientes", required=True)
    analisador.add_argument("--saida", default=".lastro/avaliacao.json")
    opcoes = analisador.parse_args(argumentos)

    teto = int(os.environ.get("LASTRO_EVAL_MAX_CALLS", "40"))
    clientes = [c.strip() for c in opcoes.clientes.split(",") if c.strip()]
    if len(clientes) * 2 > teto:
        raise SystemExit(f"{len(clientes) * 2} chamadas excedem LASTRO_EVAL_MAX_CALLS={teto}")

    repositorio = RepositorioEmMemoria()
    engine = OpenAINarrativeEngine()
    linhas: list[dict] = []

    for cliente_id in clientes:
        cliente = repositorio.obter_cliente(cliente_id)
        if cliente is None:
            raise SystemExit(f"cliente desconhecido: {cliente_id}")
        fatos = repositorio.obter_fatos_atuais(cliente_id)
        avaliacao = repositorio.avaliar_fatos(fatos)
        variacao = repositorio.comparacao_na_janela(cliente_id, avaliacao)
        contexto = serializar_contexto(cliente, fatos, avaliacao, variacao, "parecer")

        parecer = _texto_de(engine.gerar("parecer", contexto, float("inf")))
        violacoes = verificar_fidelidade_numerica(parecer, contexto)
        nota = _julgar(engine, montar_user_juiz(contexto.bloco, parecer, violacoes))

        linhas.append(
            {
                "clienteId": cliente_id,
                "palavras": contar_palavras(parecer),
                "violacoes": violacoes,
                "nota": nota.model_dump(by_alias=True) if nota else None,
                "aprovado": bool(nota and aprovado(nota, violacoes)),
                "naoAvaliado": nota is None,
            }
        )
        marca = "OK " if linhas[-1]["aprovado"] else "REPROVADO"
        print(f"{marca} {cliente_id} · {linhas[-1]['palavras']} palavras · {violacoes}")

    taxa = fmean([1.0 if linha["aprovado"] else 0.0 for linha in linhas]) if linhas else 0.0
    relatorio = {
        "taxaDeAprovacao": round(taxa, 3),
        "incidentesDeFidelidade": sum(1 for linha in linhas if linha["violacoes"]),
        "custoUsd": round(LEDGER.custo_acumulado, 6),
        "pareceres": linhas,
    }
    destino = Path(opcoes.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in relatorio.items() if k != "pareceres"}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - ponto de entrada manual
    sys.exit(main())
