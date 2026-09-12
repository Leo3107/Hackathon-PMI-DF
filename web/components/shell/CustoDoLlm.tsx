'use client';

/**
 * Fonte de dados do contador de custo do LLM (`04-camada-llm.md` §5.6 · §1.3 slot 4).
 *
 * **Não é um primitivo.** O visual é `CostCounter`, do design system, que é presentacional e
 * recebe tudo por prop. O que falta a ele — e o que este arquivo faz — é buscar o ledger em
 * `GET /api/llm/custo`, manter a revalidação viva e traduzir `motivoDesligado` em rótulo. Toda
 * marcação sai de `components/ui`.
 *
 * É a **defesa visível contra gasto silencioso**: sem cache (D5), cada abertura de bloco de
 * prosa é uma chamada nova, e o orçamento de US$ 10 precisa estar à vista o tempo todo.
 *
 * Revalida: na montagem, a cada 20s, e imediatamente ao receber `lastro:llm:uso`, disparado no
 * evento `fim` de todo stream.
 *
 * Todos os estados têm **rótulo textual**, nunca só cor (I8): `LLM ativo`, `LLM desligado`,
 * `Orçamento atingido — modo determinístico`, `Sem chave`, `Disjuntor aberto`,
 * `Motor indisponível`.
 */

import { useCallback, useEffect, useState } from 'react';

import { CostCounter } from '@/components/ui';
import { EVENTO_USO_LLM, obterCustoLlm } from '@/lib/api';
import type { MotivoLlmDesligado, RespostaCusto } from '@/types';

const INTERVALO_MS = 20_000;

const ROTULO_DESLIGADO: Record<MotivoLlmDesligado, string> = {
  LLM_DESLIGADO: 'LLM desligado (env)',
  SEM_CHAVE: 'Sem chave',
  ORCAMENTO: 'Orçamento atingido — narrativa determinística',
  DISJUNTOR: 'Disjuntor aberto',
  FORCADO_POR_ENV: 'LLM desligado (env)',
};

export function CustoDoLlm() {
  const [custo, setCusto] = useState<RespostaCusto | null>(null);
  const [indisponivel, setIndisponivel] = useState(false);

  const atualizar = useCallback(async () => {
    try {
      setCusto(await obterCustoLlm());
      setIndisponivel(false);
    } catch {
      // O ledger é indicador, não conteúdo: falha dele nunca derruba nem alarma a tela.
      setIndisponivel(true);
    }
  }, []);

  useEffect(() => {
    // A primeira leitura sai por `setTimeout(0)`, e não no corpo do efeito: manter a montagem
    // livre de setState síncrono evita render em cascata na abertura da app.
    const inicial = window.setTimeout(() => void atualizar(), 0);
    const periodico = window.setInterval(() => void atualizar(), INTERVALO_MS);
    const aoUsar = () => void atualizar();
    window.addEventListener(EVENTO_USO_LLM, aoUsar);
    return () => {
      window.clearTimeout(inicial);
      window.clearInterval(periodico);
      window.removeEventListener(EVENTO_USO_LLM, aoUsar);
    };
  }, [atualizar]);

  if (indisponivel || !custo) {
    return (
      <span className="type-mono whitespace-nowrap text-fg-tertiary" title="Ledger de custo do LLM">
        {indisponivel ? 'LLM · motor indisponível' : 'LLM · —'}
      </span>
    );
  }

  const rotuloEstado = custo.motivoDesligado
    ? ROTULO_DESLIGADO[custo.motivoDesligado]
    : 'LLM ativo';

  return (
    <span className="flex items-center gap-2">
      <CostCounter
        tokensEntrada={custo.tokens.entrada}
        tokensSaida={custo.tokens.saida}
        custoUsd={custo.custoAcumuladoUsd}
        orcamentoUsd={custo.orcamentoUsd}
        llmAtivo={custo.habilitado && custo.motivoDesligado === null}
        chamadas={custo.chamadas.total}
      />
      <span className="sr-only">{rotuloEstado}</span>
    </span>
  );
}
