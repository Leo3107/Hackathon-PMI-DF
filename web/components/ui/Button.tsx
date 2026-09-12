'use client';

import { LoaderCircle, type LucideIcon } from 'lucide-react';
import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react';

import { cn } from './cn';

export type VarianteBotao = 'primario' | 'secundario' | 'fantasma' | 'perigo-neutro';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  /** Padrão `secundario`. Um único `primario` por região visual. */
  variante?: VarianteBotao;
  /** `sm` = 24px · `md` = 32px de altura. */
  tamanho?: 'sm' | 'md';
  iconeEsquerda?: LucideIcon;
  iconeDireita?: LucideIcon;
  /** Troca o ícone da esquerda por um `LoaderCircle` girando e marca `aria-busy`. */
  carregando?: boolean;
  larguraTotal?: boolean;
  /** React 19 passa `ref` como prop — sem `forwardRef` legado (spec §6). */
  ref?: Ref<HTMLButtonElement>;
  children: ReactNode;
}

/**
 * `perigo-neutro` é ação destrutiva **de interface** (ex.: "Restaurar dados da
 * sessão"). Usa `fg-primary` + borda `line-strong`; nunca vermelho —
 * vermelho é risco de crédito (spec §2).
 */
const VARIANTE: Record<VarianteBotao, string> = {
  primario: cn(
    'border border-transparent bg-accent-500 text-fg-inverse shadow-card',
    'hover:bg-accent-600 hover:shadow-raised active:translate-y-0 active:shadow-card',
    'disabled:bg-line-default disabled:text-fg-disabled disabled:shadow-none disabled:hover:bg-line-default',
  ),
  secundario: cn(
    'border border-line-strong bg-surface-card text-fg-primary',
    'hover:border-line-strong hover:bg-surface-hover active:bg-surface-input',
    'disabled:border-line-default disabled:text-fg-disabled disabled:hover:bg-surface-card',
  ),
  fantasma: cn(
    'border border-transparent bg-transparent text-fg-secondary',
    'hover:bg-surface-hover hover:text-fg-primary active:bg-surface-input',
    'disabled:text-fg-disabled disabled:hover:bg-transparent',
  ),
  'perigo-neutro': cn(
    'border border-line-strong bg-surface-card text-fg-primary',
    'hover:bg-surface-hover active:bg-surface-input',
    'disabled:border-line-default disabled:text-fg-disabled disabled:hover:bg-surface-card',
  ),
};

const TAMANHO = {
  md: 'h-[var(--height-control)] px-3 text-[13px]',
  sm: 'h-[var(--height-control-sm)] px-2 text-[12px]',
} as const;

export function Button({
  variante = 'secundario',
  tamanho = 'md',
  iconeEsquerda,
  iconeDireita,
  carregando = false,
  larguraTotal = false,
  className,
  children,
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  const IconeEsquerda = iconeEsquerda;
  const IconeDireita = iconeDireita;

  return (
    <button
      type={type}
      disabled={disabled || carregando}
      aria-busy={carregando || undefined}
      className={cn(
        'transicao-controle transicao-elevacao inline-flex shrink-0 items-center justify-center gap-1.5',
        'rounded-full font-medium whitespace-nowrap',
        'hover:-translate-y-px active:translate-y-0 active:scale-[0.98]',
        TAMANHO[tamanho],
        VARIANTE[variante],
        larguraTotal && 'w-full',
        className,
      )}
      {...props}
    >
      {carregando ? (
        <LoaderCircle size={14} strokeWidth={2} className="girando shrink-0" aria-hidden="true" />
      ) : IconeEsquerda ? (
        <IconeEsquerda size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      ) : null}
      <span>{children}</span>
      {IconeDireita ? (
        <IconeDireita size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      ) : null}
    </button>
  );
}
