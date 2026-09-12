'use client';

/**
 * Tema e utilitários de gráfico da carteira.
 *
 * `05-design-system.md` §8 prevê este tema em `lib/chart-theme.ts`. Enquanto `web/lib/` é
 * território de outro workstream, ele vive aqui — a forma do objeto é a da spec, de modo que
 * mover o arquivo depois é recortar e colar.
 *
 * Regras que este módulo materializa (§8.2): grid só horizontal, eixos sem linha e sem tick,
 * nenhuma animação de série, tooltip autoral (nunca a do Recharts), legenda autoral, nenhuma
 * cor escrita inline em componente de gráfico.
 */

import type { ReactNode } from 'react';

import { cn } from '@/components/ui';

export const CHART = {
  font: 'var(--font-sans)',
  tick: { fontSize: 11, fill: 'var(--color-fg-tertiary)' },
  axisLabel: { fontSize: 11, fill: 'var(--color-fg-secondary)' },
  grid: { stroke: 'var(--color-line-subtle)', strokeWidth: 1 },
  axis: { axisLine: false, tickLine: false, tickMargin: 8 },
  cursor: { stroke: 'var(--color-line-strong)', strokeWidth: 1, strokeDasharray: '3 3' },
  series: {
    principal: 'var(--color-accent-400)',
    categoricas: [
      'var(--color-cat-1)',
      'var(--color-cat-2)',
      'var(--color-cat-3)',
      'var(--color-cat-4)',
      'var(--color-cat-5)',
      'var(--color-cat-6)',
    ],
    risco: {
      a: 'var(--color-risk-a)',
      b: 'var(--color-risk-b)',
      c: 'var(--color-risk-c)',
      d: 'var(--color-risk-d)',
      neutral: 'var(--color-risk-neutral)',
    },
  },
  bar: { radius: [0, 2, 2, 0] as [number, number, number, number], maxBarSize: 20 },
  animation: false,
  margin: { top: 8, right: 8, bottom: 0, left: 0 },
} as const;

/** Altura fixa por uso (§8.2, linha "Responsividade"). */
export const ALTURA_GRAFICO = { sparkline: 40, tile: 120, card: 240, pagina: 320 } as const;

// ---------------------------------------------------------------------------
// Tooltip autoral
// ---------------------------------------------------------------------------

export interface ItemDeTooltip {
  name?: string;
  value?: number | string;
  color?: string;
  payload?: Record<string, unknown>;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: ItemDeTooltip[];
  label?: string | number;
  formatarRotulo?: (label: string | number) => string;
  /** Obrigatório: nenhum número chega ao olho sem passar por `lib/format.ts` (R6). */
  formatarValor: (valor: number, nome: string) => string;
  extra?: (payload: Record<string, unknown>) => ReactNode;
  /** Cabeçalho fixo, quando o `label` do Recharts não serve. */
  titulo?: string;
}

/**
 * Visual idêntico ao `Tooltip` do design system (§6.13): `surface-raised`, borda `line-strong`,
 * padding 8/10, sem seta. Valores em `tnum` alinhados à direita.
 */
export function ChartTooltip({
  active,
  payload,
  label,
  formatarRotulo,
  formatarValor,
  extra,
  titulo,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const cabecalho =
    titulo ?? (label === undefined ? null : (formatarRotulo?.(label) ?? String(label)));
  const dados = payload[0]?.payload ?? {};

  return (
    <div className="pointer-events-none max-w-[280px] rounded-md border border-line-strong bg-surface-raised px-2.5 py-2 shadow-[var(--shadow-overlay)]">
      {cabecalho ? <p className="type-caption mb-1 text-fg-secondary">{cabecalho}</p> : null}
      <dl className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1">
        {payload.map((item, indice) => (
          <div key={`${item.name ?? indice}`} className="contents">
            <dt className="flex items-center gap-1.5 text-[12px]/[16px] text-fg-secondary">
              {item.color ? (
                <span
                  aria-hidden="true"
                  className="size-2 shrink-0 rounded-[1px]"
                  style={{ background: item.color }}
                />
              ) : null}
              <span>{item.name ?? ''}</span>
            </dt>
            <dd className="tnum text-right text-[12px]/[16px] font-medium text-fg-primary">
              {typeof item.value === 'number'
                ? formatarValor(item.value, item.name ?? '')
                : (item.value ?? '—')}
            </dd>
          </div>
        ))}
      </dl>
      {extra ? <div className="mt-1.5 border-t border-line-subtle pt-1.5">{extra(dados)}</div> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legenda autoral (§8.2 — a `<Legend>` do Recharts nunca é usada)
// ---------------------------------------------------------------------------

export interface ItemDeLegenda {
  cor: string;
  rotulo: string;
}

export function LegendaGrafico({
  itens,
  className,
}: {
  itens: ItemDeLegenda[];
  className?: string;
}) {
  return (
    <ul className={cn('type-caption flex flex-wrap items-center gap-x-4 gap-y-1', className)}>
      {itens.map((item) => (
        <li key={item.rotulo} className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="size-2 rounded-[1px]"
            style={{ background: item.cor }}
          />
          <span>{item.rotulo}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Moldura comum dos gráficos: fixa a altura, aplica `tabular-nums` (herdado pelos `<text>` do
 * SVG) e declara `role="img"` com descrição, como exige §10.3.
 */
export function MolduraDeGrafico({
  altura,
  descricao,
  children,
  className,
}: {
  altura: number;
  descricao: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="img"
      aria-label={descricao}
      className={cn('tnum w-full', className)}
      style={{ height: `${altura}px` }}
    >
      {children}
    </div>
  );
}
