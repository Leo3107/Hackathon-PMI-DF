import { Gavel } from 'lucide-react';

import { cn } from './cn';
import { CLASSES_RISCO, RATING } from './risco';
import type { Rating } from './tipos-ui';

export interface RatingBadgeProps {
  rating: Rating;
  /** `sm` = 20px letra só · `md` = 24px letra+rótulo · `lg` = 32px letra+rótulo+ícone. */
  tamanho?: 'sm' | 'md' | 'lg';
  /** Padrão: true em `md`/`lg`, false em `sm` (que mantém `title` + `aria-label`). */
  mostrarRotulo?: boolean;
  /** Padrão `solido` em `lg`, `tint` nos demais. */
  aparencia?: 'tint' | 'solido';
  /** Se difere de `rating`, renderiza o par "calculado → final" (spec §7.7). */
  calculado?: Rating;
  className?: string;
}

const ALTURA = {
  sm: 'h-5 px-1.5 gap-1',
  md: 'h-6 px-2 gap-1.5',
  lg: 'h-8 px-3 gap-2',
} as const;

const TAMANHO_LETRA = {
  sm: 'text-[12px]',
  md: 'text-[13px]',
  lg: 'text-[16px]',
} as const;

interface SeloProps {
  rating: Rating;
  tamanho: 'sm' | 'md' | 'lg';
  mostrarRotulo: boolean;
  aparencia: 'tint' | 'solido' | 'contorno';
  className?: string;
}

/** Selo de uma única letra de rating. Nunca renderizado sem `title`. */
function Selo({ rating, tamanho, mostrarRotulo, aparencia, className }: SeloProps) {
  const apresentacao = RATING[rating];
  const classes = CLASSES_RISCO[apresentacao.familia];
  const Icone = apresentacao.Icone;

  const pele =
    aparencia === 'solido'
      ? cn('border border-transparent text-fg-inverse', classes.fundoSolido)
      : aparencia === 'contorno'
        ? cn('border bg-transparent', classes.bordaLinha, classes.texto)
        : cn('border', classes.bordaLinha, classes.fundoTint, classes.texto);

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full whitespace-nowrap',
        ALTURA[tamanho],
        pele,
        className,
      )}
      title={`Rating ${rating} — ${apresentacao.rotulo}`}
      aria-label={`Rating ${rating}, ${apresentacao.rotulo}`}
    >
      {tamanho === 'lg' ? (
        <Icone size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      ) : null}
      <span className={cn('font-bold tnum', TAMANHO_LETRA[tamanho])}>{rating}</span>
      {mostrarRotulo ? (
        <span className="text-[12px] font-medium">{apresentacao.rotulo}</span>
      ) : null}
    </span>
  );
}

/**
 * Rating do cliente (spec §6.4). Letras A–D **nunca** aparecem soltas: sempre
 * dentro deste componente, que carrega cor, rótulo e — em `lg` — ícone.
 *
 * Quando `calculado` difere de `rating`, renderiza o par
 * `[B contorno] → Gavel → [D sólido]`: o quantitativo disse uma coisa e a regra
 * de negócio impôs outra, **sem esconder nenhum dos dois** (spec §7.7).
 */
export function RatingBadge({
  rating,
  tamanho = 'md',
  mostrarRotulo,
  aparencia,
  calculado,
  className,
}: RatingBadgeProps) {
  const comRotulo = mostrarRotulo ?? tamanho !== 'sm';
  const pele = aparencia ?? (tamanho === 'lg' ? 'solido' : 'tint');

  if (calculado && calculado !== rating) {
    return (
      <span
        className={cn('inline-flex items-center gap-1.5', className)}
        aria-label={`Rating calculado ${calculado}, ${RATING[calculado].rotulo}. Rebaixado para ${rating}, ${RATING[rating].rotulo}, por regra de negócio.`}
      >
        <Selo
          rating={calculado}
          tamanho={tamanho}
          mostrarRotulo={false}
          aparencia="contorno"
        />
        <Gavel
          size={14}
          strokeWidth={2}
          className={cn('shrink-0', CLASSES_RISCO[RATING[rating].familia].texto)}
          aria-hidden="true"
        />
        <Selo rating={rating} tamanho={tamanho} mostrarRotulo={comRotulo} aparencia="solido" />
      </span>
    );
  }

  return (
    <Selo
      rating={rating}
      tamanho={tamanho}
      mostrarRotulo={comRotulo}
      aparencia={pele}
      className={className}
    />
  );
}
