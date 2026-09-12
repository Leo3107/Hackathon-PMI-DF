import { Info } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from './cn';
import type { TermoGlossario } from './glossario';
import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco, Tendencia } from './tipos-ui';
import { Tooltip } from './Tooltip';
import { TrendIndicator } from './TrendIndicator';

export interface VariacaoKpi {
  /** Já formatado pelo chamador (`formatarDelta`). */
  delta: string;
  tendencia: Tendencia | 'neutra';
  periodo?: string;
}

export interface KpiTileProps {
  rotulo: string;
  /** Já formatado por `lib/format` — o tile **não** formata. */
  valor: string;
  /** "/ 1000", "%", "meses". */
  unidade?: string;
  variacao?: VariacaoKpi;
  /** Só quando o valor é semanticamente um indicador de risco (PD, RJ, cobertura). */
  familia?: FamiliaRisco;
  termo?: TermoGlossario;
  rodape?: ReactNode;
  tamanho?: 'md' | 'sm';
  carregando?: boolean;
  aoClicar?: () => void;
  className?: string;
}

/**
 * KPI (spec §6.7). O valor é `fg-primary` por padrão; só recebe cor de risco se
 * representar um indicador com faixa definida. Exposição em R$ é sempre neutra.
 */
export function KpiTile({
  rotulo,
  valor,
  unidade,
  variacao,
  familia,
  termo,
  rodape,
  tamanho = 'md',
  carregando = false,
  aoClicar,
  className,
}: KpiTileProps) {
  const classesValor = familia ? CLASSES_RISCO[familia].texto : 'text-fg-primary';
  const Tag = aoClicar ? 'button' : 'div';

  return (
    <Tag
      {...(aoClicar ? { type: 'button' as const, onClick: aoClicar } : {})}
      className={cn(
        'kpi-tile flex w-full flex-col gap-1 rounded-md border border-line-default bg-surface-card p-3 text-left',
        aoClicar && 'transicao-controle hover:border-line-strong hover:bg-surface-hover',
        className,
      )}
    >
      <span className="type-eyebrow inline-flex items-center gap-1.5">
        {rotulo}
        {termo ? (
          <Tooltip termo={termo}>
            <span
              tabIndex={0}
              role="note"
              aria-label={`O que é ${rotulo}`}
              className="transicao-controle inline-flex rounded-sm text-fg-tertiary hover:text-fg-secondary"
            >
              <Info size={14} strokeWidth={2} aria-hidden="true" />
            </span>
          </Tooltip>
        ) : null}
      </span>

      {carregando ? (
        <span className="esqueleto h-6 w-3/5" aria-hidden="true" />
      ) : (
        <span className="flex items-baseline gap-1">
          <span className={cn(tamanho === 'sm' ? 'type-kpi-sm' : 'type-kpi', classesValor)}>
            {valor}
          </span>
          {unidade ? (
            <span className="text-[12px]/[16px] font-normal text-fg-tertiary">{unidade}</span>
          ) : null}
        </span>
      )}

      {variacao && !carregando ? (
        variacao.tendencia === 'neutra' ? (
          <span className="type-caption tnum">
            {variacao.delta}
            {variacao.periodo ? ` · ${variacao.periodo}` : ''}
          </span>
        ) : (
          <TrendIndicator
            tendencia={variacao.tendencia}
            deltaTexto={variacao.delta}
            periodo={variacao.periodo}
            tamanho="sm"
            className="mt-0.5"
          />
        )
      ) : null}

      {rodape ? <span className="type-caption">{rodape}</span> : null}
    </Tag>
  );
}
