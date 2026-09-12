import { formatarMoedaCompacta, formatarPercentual } from '@/lib/format';
import { cn } from './cn';
import { idHachura, PadraoHachura } from './hachura';
import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco } from './tipos-ui';

export interface SegmentoBarra {
  id: string;
  /** "Extraconcursal", "Concursal", "Em risco". */
  rotulo: string;
  /** Em reais. */
  valor: number;
  /** extraconcursal = `a` · concursal = `c` · em risco = `d`. */
  familia: FamiliaRisco;
  /** `hachurado` para "em risco em RJ" — o que o penhor deixa de cobrir. */
  padrao?: 'solido' | 'hachurado';
}

export interface StackedBarProps {
  segmentos: SegmentoBarra[];
  /** `exposicaoTotal` — base de 100%. */
  total: number;
  altura?: 12 | 16;
  legenda?: 'abaixo' | 'lateral' | 'nenhuma';
  /** Id do segmento a realçar (contorno `fg-primary`) — ex.: exposição em risco em RJ. */
  destaque?: string;
  formatarValor?: (valor: number) => string;
  className?: string;
  'aria-label': string;
}

/**
 * Composição da exposição (spec §6.16): protegida vs em risco. Segmentos
 * separados por 2px de `surface-card`; o padrão hachurado é o mesmo `<pattern>`
 * do veto, com a cor do segmento.
 */
export function StackedBar({
  segmentos,
  total,
  altura = 16,
  legenda = 'abaixo',
  destaque,
  formatarValor = (valor) => formatarMoedaCompacta(valor),
  className,
  'aria-label': ariaLabel,
}: StackedBarProps) {
  const base = total > 0 ? total : segmentos.reduce((soma, s) => soma + s.valor, 0) || 1;

  const descricao = segmentos
    .map((s) => `${s.rotulo}: ${formatarValor(s.valor)}, ${formatarPercentual(s.valor / base, 0)}`)
    .join('. ');

  return (
    <div className={cn('flex w-full flex-col gap-2', className)}>
      <div
        role="img"
        aria-label={`${ariaLabel}. ${descricao}`}
        className="flex w-full overflow-hidden rounded-xs bg-surface-sunken"
        style={{ height: `${altura}px`, gap: '2px' }}
      >
        {segmentos.map((segmento) => {
          const classes = CLASSES_RISCO[segmento.familia];
          const largura = Math.max(0, segmento.valor / base) * 100;
          if (largura <= 0) return null;
          return (
            <div
              key={segmento.id}
              title={`${segmento.rotulo} · ${formatarValor(segmento.valor)}`}
              className={cn(
                'relative h-full',
                segmento.padrao === 'hachurado' ? 'bg-surface-sunken' : classes.fundoSolido,
                destaque === segmento.id && 'outline outline-1 -outline-offset-1 outline-fg-primary',
              )}
              style={{ width: `${largura}%` }}
            >
              {segmento.padrao === 'hachurado' ? (
                <svg className="size-full" aria-hidden="true" focusable="false">
                  <defs>
                    <PadraoHachura familia={segmento.familia} escopo={`stacked-${segmento.id}`} />
                  </defs>
                  <rect
                    width="100%"
                    height="100%"
                    fill={`url(#${idHachura(segmento.familia, `stacked-${segmento.id}`)})`}
                  />
                </svg>
              ) : null}
            </div>
          );
        })}
      </div>

      {legenda === 'nenhuma' ? null : (
        <ul
          className={cn(
            'grid gap-x-4 gap-y-1',
            legenda === 'lateral' ? 'grid-cols-1' : 'grid-cols-3',
          )}
        >
          {segmentos.map((segmento) => {
            const classes = CLASSES_RISCO[segmento.familia];
            return (
              <li key={segmento.id} className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className={cn(
                    'inline-block size-2 shrink-0 rounded-xs',
                    classes.fundoSolido,
                    segmento.padrao === 'hachurado' && 'opacity-60',
                  )}
                />
                <span className="type-caption min-w-0 flex-1 truncate text-fg-secondary">
                  {segmento.rotulo}
                </span>
                <span className="type-caption tnum text-fg-primary">
                  {formatarValor(segmento.valor)}
                </span>
                <span className="type-caption tnum w-10 text-right">
                  {formatarPercentual(segmento.valor / base, 0)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
