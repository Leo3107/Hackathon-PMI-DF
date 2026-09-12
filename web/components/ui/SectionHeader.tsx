import { Info } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from './cn';
import type { TermoGlossario } from './glossario';
import { Tooltip } from './Tooltip';

export interface SectionHeaderProps {
  titulo: string;
  /** `type-eyebrow` acima do título (ex.: "DIMENSÃO 2 · 20%"). */
  sobretitulo?: string;
  /** `type-caption` abaixo do título. */
  descricao?: string;
  /** Botões/chips alinhados à direita. */
  acoes?: ReactNode;
  /** Badge de fonte ou contagem, ao lado do título. */
  meta?: ReactNode;
  /** `h2` (card) ou `h3` (subseção). Padrão 2. */
  nivel?: 2 | 3;
  /** Adiciona ícone `Info` com Tooltip do glossário ao título. */
  termo?: TermoGlossario;
  /** Divisória inferior. Padrão true dentro de `Card`. */
  divisor?: boolean;
  className?: string;
}

export function SectionHeader({
  titulo,
  sobretitulo,
  descricao,
  acoes,
  meta,
  nivel = 2,
  termo,
  divisor = true,
  className,
}: SectionHeaderProps) {
  const Titulo = nivel === 2 ? 'h2' : 'h3';

  return (
    <header
      className={cn(
        'section-header flex items-start justify-between gap-4',
        divisor && 'border-b border-line-subtle pb-3',
        className,
      )}
    >
      <div className="min-w-0">
        {sobretitulo ? <p className="type-eyebrow">{sobretitulo}</p> : null}
        <div className="flex min-w-0 items-center gap-2">
          <Titulo className={cn(nivel === 2 ? 'type-section-title' : 'type-body-strong', 'truncate')}>
            {titulo}
          </Titulo>
          {termo ? (
            <Tooltip termo={termo}>
              <button
                type="button"
                aria-label={`O que é ${titulo}`}
                className="transicao-controle inline-flex rounded-sm text-fg-tertiary hover:text-fg-secondary"
              >
                <Info size={14} strokeWidth={2} aria-hidden="true" />
              </button>
            </Tooltip>
          ) : null}
          {meta}
        </div>
        {descricao ? <p className="type-caption mt-1">{descricao}</p> : null}
      </div>
      {acoes ? <div className="flex shrink-0 items-center gap-2">{acoes}</div> : null}
    </header>
  );
}
