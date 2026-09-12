import { Info } from 'lucide-react';

import { formatarPercentual } from '@/lib/format';
import { cn } from './cn';
import type { TermoGlossario } from './glossario';
import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco } from './tipos-ui';
import { Tooltip } from './Tooltip';

export interface MarcaProgresso {
  valor: number;
  rotulo: string;
}

export interface ProgressBarProps {
  /** Fração 0..∞ — cobertura pode passar de 1. */
  valor: number;
  /** Padrão 1. A barra clampa visualmente no máximo e mostra o excedente por texto. */
  maximo?: number;
  rotulo: string;
  /** Padrão `formatarPercentual(valor, 0)`. */
  valorFormatado?: string;
  /** `auto`: ≥1 → a · ≥0,6 → b · ≥0,3 → c · <0,3 → d. */
  familia?: FamiliaRisco | 'auto';
  marcas?: MarcaProgresso[];
  termo?: TermoGlossario;
  altura?: 6 | 8;
  className?: string;
}

/** Faixa de cobertura → família cromática (spec §6.15). */
export function familiaDeCobertura(fracao: number): FamiliaRisco {
  if (fracao >= 1) return 'a';
  if (fracao >= 0.6) return 'b';
  if (fracao >= 0.3) return 'c';
  return 'd';
}

/**
 * Barra de cobertura (spec §6.15). Trilho `surface-sunken`, preenchimento
 * sólido na cor da família, ticks opcionais.
 */
export function ProgressBar({
  valor,
  maximo = 1,
  rotulo,
  valorFormatado,
  familia = 'auto',
  marcas,
  termo,
  altura = 8,
  className,
}: ProgressBarProps) {
  const familiaEfetiva = familia === 'auto' ? familiaDeCobertura(valor) : familia;
  const classes = CLASSES_RISCO[familiaEfetiva];
  const fracaoVisual = Math.max(0, Math.min(1, valor / maximo));
  const texto = valorFormatado ?? formatarPercentual(valor, 0);

  return (
    <div className={cn('flex w-full flex-col gap-1', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="type-label inline-flex items-center gap-1.5">
          {rotulo}
          {termo ? (
            <Tooltip termo={termo}>
              <button
                type="button"
                aria-label={`O que é ${rotulo}`}
                className="transicao-controle inline-flex rounded-sm text-fg-tertiary hover:text-fg-secondary"
              >
                <Info size={14} strokeWidth={2} aria-hidden="true" />
              </button>
            </Tooltip>
          ) : null}
        </span>
        <span className={cn('tnum text-[12px]/[16px] font-medium', classes.texto)}>{texto}</span>
      </div>

      <div
        role="meter"
        aria-label={rotulo}
        aria-valuenow={Math.round(valor * 100)}
        aria-valuemin={0}
        aria-valuemax={Math.round(maximo * 100)}
        aria-valuetext={texto}
        className="relative w-full overflow-hidden rounded-xs border border-line-subtle bg-surface-sunken"
        style={{ height: `${altura}px` }}
      >
        <div
          className={cn('h-full rounded-xs', classes.fundoSolido)}
          style={{ width: `${fracaoVisual * 100}%` }}
        />
        {marcas?.map((marca) => (
          <span
            key={marca.rotulo}
            aria-hidden="true"
            className="absolute top-0 h-full w-px bg-fg-tertiary"
            style={{ left: `${Math.max(0, Math.min(1, marca.valor / maximo)) * 100}%` }}
          />
        ))}
      </div>

      {marcas && marcas.length > 0 ? (
        <div className="relative h-4 w-full">
          {marcas.map((marca) => (
            <span
              key={marca.rotulo}
              className="type-caption tnum absolute -translate-x-1/2"
              style={{ left: `${Math.max(0, Math.min(1, marca.valor / maximo)) * 100}%` }}
            >
              {marca.rotulo}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
