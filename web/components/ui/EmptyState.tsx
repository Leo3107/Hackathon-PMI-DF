import { Inbox, type LucideIcon } from 'lucide-react';

import { Button } from './Button';
import { cn } from './cn';

export interface EmptyStateProps {
  icone?: LucideIcon;
  titulo: string;
  descricao?: string;
  acao?: { rotulo: string; aoClicar: () => void; icone?: LucideIcon };
  /** 160px de altura mínima (dentro de tabela) vs 320px (página inteira). */
  compacto?: boolean;
  className?: string;
}

/**
 * Estado vazio (spec §6.21). Centralizado, sem ilustração, sem emoji.
 */
export function EmptyState({
  icone: Icone = Inbox,
  titulo,
  descricao,
  acao,
  compacto = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex w-full flex-col items-center justify-center gap-3 px-4 text-center sm:px-6',
        compacto ? 'min-h-40 py-6' : 'min-h-80 py-12',
        className,
      )}
    >
      <span className="inline-flex size-14 items-center justify-center rounded-full bg-accent-tint">
        <Icone size={32} strokeWidth={1.5} className="text-accent-500" aria-hidden="true" />
      </span>
      <div className="flex min-w-0 max-w-full flex-col gap-1">
        <p className="type-section-title break-words text-fg-secondary">{titulo}</p>
        {descricao ? (
          <p className="type-caption max-w-[48ch] break-words">{descricao}</p>
        ) : null}
      </div>
      {acao ? (
        <Button
          variante="secundario"
          iconeEsquerda={acao.icone}
          onClick={acao.aoClicar}
          className="w-full sm:w-auto"
        >
          {acao.rotulo}
        </Button>
      ) : null}
    </div>
  );
}
