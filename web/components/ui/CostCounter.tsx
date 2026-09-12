'use client';

import { CircuitBoard, Coins, TriangleAlert } from 'lucide-react';

import { formatarNumero, formatarTokens } from '@/lib/format';
import { cn } from './cn';
import { Tooltip } from './Tooltip';

export interface CostCounterProps {
  tokensEntrada: number;
  tokensSaida: number;
  /** Estimado. */
  custoUsd: number;
  /** `LASTRO_LLM_BUDGET_USD`. */
  orcamentoUsd: number;
  llmAtivo: boolean;
  chamadas: number;
  /**
   * Instrumentação, não navegação: na topbar o contador fica reduzido ao ícone e ao gasto
   * acumulado, em `fg-tertiary`. A quebra completa — entrada, saída, chamadas, orçamento —
   * continua inteira no tooltip, e o orçamento volta a aparecer escrito quando passa de 80%.
   */
  compacto?: boolean;
  className?: string;
}

/**
 * Contador de custo do LLM na topbar (spec §6.24).
 *
 * O aviso de orçamento usa `TriangleAlert` **neutro**, nunca laranja: gasto de
 * API não é risco de crédito (spec §2).
 */
export function CostCounter({
  tokensEntrada,
  tokensSaida,
  custoUsd,
  orcamentoUsd,
  llmAtivo,
  chamadas,
  compacto = false,
  className,
}: CostCounterProps) {
  const total = tokensEntrada + tokensSaida;
  const fracao = orcamentoUsd > 0 ? custoUsd / orcamentoUsd : 0;
  const alerta = fracao >= 0.8;
  const estourado = fracao >= 1;

  const detalhe = (
    <span className="flex flex-col gap-0.5">
      <span>{`Entrada: ${formatarNumero(tokensEntrada)} tokens`}</span>
      <span>{`Saída: ${formatarNumero(tokensSaida)} tokens`}</span>
      <span>{`Chamadas: ${formatarNumero(chamadas)}`}</span>
      <span>{`Custo estimado: US$ ${formatarNumero(custoUsd, 2)} de US$ ${formatarNumero(orcamentoUsd, 2)}`}</span>
      {estourado ? <span>Orçamento atingido — modo determinístico.</span> : null}
    </span>
  );

  if (!llmAtivo) {
    return (
      <Tooltip conteudo="A camada de linguagem está desligada. Os números do motor continuam íntegros.">
        <span
          tabIndex={0}
          className={cn(
            'type-mono inline-flex items-center gap-1.5 rounded-sm text-[11px]/[16px]',
            compacto && 'transicao-controle text-fg-tertiary hover:text-fg-secondary',
            className,
          )}
        >
          <CircuitBoard size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          LLM desligado
        </span>
      </Tooltip>
    );
  }

  if (compacto) {
    return (
      <Tooltip conteudo={detalhe}>
        <span
          tabIndex={0}
          aria-label={`Custo do LLM: US$ ${formatarNumero(custoUsd, 2)} de US$ ${formatarNumero(orcamentoUsd, 2)}`}
          className={cn(
            'type-mono transicao-controle inline-flex items-center gap-1 rounded-sm text-[11px]/[16px]',
            alerta ? 'text-fg-secondary' : 'text-fg-tertiary hover:text-fg-secondary',
            className,
          )}
        >
          {alerta ? (
            <TriangleAlert size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          ) : (
            <Coins size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          )}
          <span className="tnum whitespace-nowrap">
            {alerta
              ? `US$ ${formatarNumero(custoUsd, 2)} / ${formatarNumero(orcamentoUsd, 2)}`
              : `US$ ${formatarNumero(custoUsd, 2)}`}
          </span>
        </span>
      </Tooltip>
    );
  }

  return (
    <Tooltip conteudo={detalhe}>
      <span
        tabIndex={0}
        className={cn(
          'type-mono inline-flex items-center gap-2 rounded-sm text-[11px]/[16px]',
          alerta && 'text-fg-primary',
          className,
        )}
      >
        {alerta ? (
          <TriangleAlert size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
        ) : (
          <Coins size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
        )}
        <span className="tnum whitespace-nowrap">
          {`US$ ${formatarNumero(custoUsd, 2)} / ${formatarNumero(orcamentoUsd, 2)} · ${formatarTokens(total)} tokens`}
        </span>
        <span
          aria-hidden="true"
          className="h-1 w-12 shrink-0 overflow-hidden rounded-xs bg-surface-sunken"
        >
          <span
            className="block h-full bg-accent-400"
            style={{ width: `${Math.max(0, Math.min(1, fracao)) * 100}%` }}
          />
        </span>
        {estourado ? (
          <span className="whitespace-nowrap">Orçamento atingido — modo determinístico</span>
        ) : null}
      </span>
    </Tooltip>
  );
}
