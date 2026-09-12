import type { HTMLAttributes, ReactNode } from 'react';

import { cn } from './cn';
import type { FamiliaRisco } from './tipos-ui';

export type DestaqueCard = 'nenhum' | 'acento' | FamiliaRisco;

export interface CardProps extends Omit<HTMLAttributes<HTMLElement>, 'children'> {
  children: ReactNode;
  /** `padrao` = 16px · `compacta` = 12px. */
  densidade?: 'padrao' | 'compacta';
  /** Card que contém apenas `DataTable`: a tabela toca as bordas. */
  semPadding?: boolean;
  /** Hover `surface-hover` + borda `line-strong`; usado como link/botão. */
  interativo?: boolean;
  /** Borda esquerda 2px na cor (ex.: card de veto = `d`). */
  destaque?: DestaqueCard;
  as?: 'div' | 'section' | 'article';
  className?: string;
}

const DESTAQUE: Record<DestaqueCard, string> = {
  nenhum: '',
  acento: 'border-l-2 border-l-accent-400',
  a: 'border-l-2 border-l-risk-a',
  b: 'border-l-2 border-l-risk-b',
  c: 'border-l-2 border-l-risk-c',
  d: 'border-l-2 border-l-risk-d',
  neutral: 'border-l-2 border-l-risk-neutral',
};

/**
 * Superfície padrão (spec §6.1): bg `surface-card`, borda 1px `line-default`,
 * raio `radius-md`, **sem sombra** — sombra só em elementos flutuantes.
 * Cards não se aninham: dentro de um card, agrupamento é por `SectionHeader`
 * e divisórias.
 */
export function Card({
  children,
  densidade = 'padrao',
  semPadding = false,
  interativo = false,
  destaque = 'nenhum',
  as: Tag = 'div',
  className,
  ...props
}: CardProps) {
  return (
    <Tag
      className={cn(
        'card rounded-md border border-line-default bg-surface-card',
        semPadding ? 'p-0' : densidade === 'compacta' ? 'p-3' : 'p-4',
        interativo &&
          'transicao-controle cursor-pointer hover:border-line-strong hover:bg-surface-hover',
        DESTAQUE[destaque],
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}
