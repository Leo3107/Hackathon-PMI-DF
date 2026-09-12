import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from './cn';
import { CLASSES_RISCO, NATUREZA_GARANTIA, SEVERIDADE } from './risco';
import {
  NOME_CURTO_FONTE,
  type FamiliaRisco,
  type FonteId,
  type NaturezaGarantia,
  type Severidade,
  type StatusRedFlag,
} from './tipos-ui';

export type AparenciaBadge = 'tint' | 'solido' | 'contorno';

export type VarianteBadge =
  | { variante: 'neutro' }
  | { variante: 'acento' }
  /** Uso interno de `RatingBadge` e dos compostos de risco. */
  | { variante: 'risco'; familia: FamiliaRisco }
  | { variante: 'severidade'; severidade: Severidade }
  | { variante: 'natureza'; natureza: NaturezaGarantia }
  | { variante: 'status'; status: StatusRedFlag }
  | { variante: 'fonte'; fonte: FonteId };

export type BadgeProps = VarianteBadge & {
  /** Sobrescreve o rótulo padrão da variante. */
  children?: ReactNode;
  /** `null` suprime o ícone padrão (só em `neutro`, `acento` e `fonte`). */
  icone?: LucideIcon | null;
  /** `sm` = 16px · `md` = 20px de altura. */
  tamanho?: 'sm' | 'md';
  aparencia?: AparenciaBadge;
  titulo?: string;
  className?: string;
};

const STATUS: Record<StatusRedFlag, { rotulo: string; tracejado: boolean; acento: boolean }> = {
  nova: { rotulo: 'Nova', tracejado: false, acento: true },
  analisada: { rotulo: 'Analisada', tracejado: false, acento: false },
  resolvida: { rotulo: 'Resolvida', tracejado: true, acento: false },
};

interface Resolvido {
  familia: FamiliaRisco | null;
  rotulo: string;
  Icone: LucideIcon | null;
  acento: boolean;
  tracejado: boolean;
}

function resolver(props: BadgeProps): Resolvido {
  const vazio: Resolvido = {
    familia: null,
    rotulo: '',
    Icone: null,
    acento: false,
    tracejado: false,
  };

  switch (props.variante) {
    case 'severidade': {
      const apresentacao = SEVERIDADE[props.severidade];
      return { ...vazio, familia: apresentacao.familia, rotulo: apresentacao.rotulo, Icone: apresentacao.Icone };
    }
    case 'natureza': {
      const apresentacao = NATUREZA_GARANTIA[props.natureza];
      return { ...vazio, familia: apresentacao.familia, rotulo: apresentacao.rotulo, Icone: apresentacao.Icone };
    }
    case 'risco':
      return { ...vazio, familia: props.familia };
    case 'status': {
      const status = STATUS[props.status];
      return {
        ...vazio,
        familia: status.acento ? null : 'neutral',
        rotulo: status.rotulo,
        acento: status.acento,
        tracejado: status.tracejado,
      };
    }
    case 'fonte':
      return { ...vazio, familia: 'neutral', rotulo: NOME_CURTO_FONTE[props.fonte] };
    case 'acento':
      return { ...vazio, acento: true };
    case 'neutro':
    default:
      return { ...vazio, familia: 'neutral' };
  }
}

const TAMANHO = {
  sm: 'h-4 gap-1 px-2',
  md: 'h-5 gap-1 px-2',
} as const;

/**
 * Selo não clicável (spec §6.3). Para filtro, use `FilterChips`.
 *
 * `tint`: bg `-tint`, texto e ícone na cor, borda `-line`.
 * `solido`: bg na cor, texto `fg-inverse` (só `RatingBadge` e severidade
 * CRÍTICA em `AlertRow`). `contorno`: transparente, borda `-line`, texto na cor
 * (usado para "rating calculado" ao lado do "final" no veto).
 */
export function Badge(props: BadgeProps) {
  const {
    children,
    icone,
    tamanho = 'md',
    aparencia = 'tint',
    titulo,
    className,
  } = props;

  const resolvido = resolver(props);
  const Icone = icone === null ? null : (icone ?? resolvido.Icone);
  const conteudo = children ?? resolvido.rotulo;

  const classesFamilia = resolvido.familia ? CLASSES_RISCO[resolvido.familia] : null;

  const aparenciaClasses = resolvido.acento
    ? aparencia === 'solido'
      ? 'border border-accent-500 bg-accent-500 text-fg-inverse'
      : aparencia === 'contorno'
        ? 'border border-accent-line bg-transparent text-accent-300'
        : 'border border-accent-line bg-accent-tint text-accent-300'
    : classesFamilia
      ? aparencia === 'solido'
        ? cn('border border-transparent text-fg-inverse', classesFamilia.fundoSolido)
        : aparencia === 'contorno'
          ? cn('border bg-transparent', classesFamilia.bordaLinha, classesFamilia.texto)
          : cn('border', classesFamilia.bordaLinha, classesFamilia.fundoTint, classesFamilia.texto)
      : 'border border-line-default bg-surface-card text-fg-secondary';

  return (
    <span
      className={cn(
        'type-badge inline-flex shrink-0 items-center rounded-full whitespace-nowrap',
        TAMANHO[tamanho],
        aparenciaClasses,
        resolvido.tracejado && 'border-dashed',
        className,
      )}
      title={titulo}
      aria-label={titulo}
    >
      {Icone ? <Icone size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" /> : null}
      {conteudo ? <span>{conteudo}</span> : null}
    </span>
  );
}
