'use client';

import { X, type LucideIcon } from 'lucide-react';

import { cn } from './cn';
import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco } from './tipos-ui';

export interface OpcaoChip<V extends string> {
  valor: V;
  rotulo: string;
  /** "(4)" em `tnum`, `fg-tertiary`. */
  contagem?: number;
  /** Chip de rating/severidade herda ícone e cor quando ativo. */
  familia?: FamiliaRisco;
  icone?: LucideIcon;
}

export interface FilterChipsProps<V extends string> {
  opcoes: OpcaoChip<V>[];
  selecionados: ReadonlySet<V>;
  aoMudar: (proximos: Set<V>) => void;
  modo?: 'multiplo' | 'unico';
  /** `aria-label` do grupo. */
  rotulo: string;
  /** Se presente, mostra o chip "Limpar" quando há seleção. */
  limparRotulo?: string;
  className?: string;
}

/**
 * Filtros por chip (spec §6.9). Altura 24px. `Badge` nunca é clicável — tudo
 * que filtra passa por aqui.
 */
export function FilterChips<V extends string>({
  opcoes,
  selecionados,
  aoMudar,
  modo = 'multiplo',
  rotulo,
  limparRotulo,
  className,
}: FilterChipsProps<V>) {
  function alternar(valor: V) {
    if (modo === 'unico') {
      aoMudar(selecionados.has(valor) ? new Set<V>() : new Set<V>([valor]));
      return;
    }
    const proximos = new Set(selecionados);
    if (proximos.has(valor)) proximos.delete(valor);
    else proximos.add(valor);
    aoMudar(proximos);
  }

  return (
    <div
      role="group"
      aria-label={rotulo}
      className={cn(
        'flex items-center gap-2',
        // Em mobile os nove chips quebravam em três linhas e empurravam a lista para baixo;
        // uma faixa rolável mantém a altura de 24px. Em `md+` volta a quebrar como antes.
        'flex-nowrap overflow-x-auto scrollbar-thin md:flex-wrap md:overflow-visible',
        className,
      )}
    >
      {opcoes.map((opcao) => {
        const ativo = selecionados.has(opcao.valor);
        const classes = opcao.familia ? CLASSES_RISCO[opcao.familia] : null;
        const Icone = opcao.icone;

        const pele = !ativo
          ? 'border-line-default bg-transparent text-fg-secondary hover:border-line-strong'
          : classes
            ? cn(classes.bordaLinha, classes.fundoTint, classes.texto)
            : 'border-accent-line bg-accent-tint text-accent-300';

        return (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => alternar(opcao.valor)}
            className={cn(
              'transicao-controle type-badge inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 font-medium whitespace-nowrap',
              pele,
            )}
          >
            {Icone ? <Icone size={14} strokeWidth={2} aria-hidden="true" /> : null}
            <span>{opcao.rotulo}</span>
            {opcao.contagem === undefined ? null : (
              <span className={cn('tnum', ativo ? 'opacity-80' : 'text-fg-tertiary')}>
                ({opcao.contagem})
              </span>
            )}
          </button>
        );
      })}

      {limparRotulo && selecionados.size > 0 ? (
        <button
          type="button"
          onClick={() => aoMudar(new Set<V>())}
          className={cn(
            'transicao-controle type-badge inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 font-medium whitespace-nowrap',
            'border-line-default bg-transparent text-fg-secondary hover:border-line-strong hover:text-fg-primary',
          )}
        >
          <X size={14} strokeWidth={2} aria-hidden="true" />
          <span>{limparRotulo}</span>
        </button>
      ) : null}
    </div>
  );
}
