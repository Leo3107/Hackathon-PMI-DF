'use client';

import type { LucideIcon } from 'lucide-react';
import type { ButtonHTMLAttributes, Ref } from 'react';

import { cn } from './cn';
import { Tooltip } from './Tooltip';

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icone: LucideIcon;
  /** Obrigatório: vira `aria-label` **e** Tooltip. Ícone nunca vai sozinho. */
  rotulo: string;
  variante?: 'secundario' | 'fantasma';
  tamanho?: 'sm' | 'md';
  /** React 19 passa `ref` como prop — sem `forwardRef` legado (spec §6). */
  ref?: Ref<HTMLButtonElement>;
}

const VARIANTE = {
  secundario: cn(
    'border border-line-strong bg-surface-card text-fg-primary',
    'hover:bg-surface-hover active:bg-surface-input',
    'disabled:border-line-default disabled:text-fg-disabled',
  ),
  fantasma: cn(
    'border border-transparent bg-transparent text-fg-secondary',
    'hover:bg-surface-hover hover:text-fg-primary active:bg-surface-input',
    'disabled:text-fg-disabled',
  ),
} as const;

const TAMANHO = {
  md: 'size-[var(--height-control)]',
  sm: 'size-[var(--height-control-sm)]',
} as const;

export function IconButton({
  icone: Icone,
  rotulo,
  variante = 'fantasma',
  tamanho = 'md',
  className,
  type = 'button',
  ...props
}: IconButtonProps) {
  return (
    <Tooltip conteudo={rotulo}>
      <button
        type={type}
        aria-label={rotulo}
        className={cn(
          'transicao-controle inline-flex shrink-0 items-center justify-center rounded-full',
          TAMANHO[tamanho],
          VARIANTE[variante],
          className,
        )}
        {...props}
      >
        <Icone size={tamanho === 'sm' ? 14 : 16} strokeWidth={2} aria-hidden="true" />
      </button>
    </Tooltip>
  );
}
