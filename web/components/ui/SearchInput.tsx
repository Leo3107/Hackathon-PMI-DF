'use client';

import { LoaderCircle, Search, X } from 'lucide-react';
import { useEffect, useRef } from 'react';

import { cn } from './cn';

export interface SearchInputProps {
  valor: string;
  aoMudar: (valor: string) => void;
  placeholder?: string;
  /** Ex.: "/" → exibe `<kbd>` à direita e registra o atalho global. */
  atalho?: string;
  carregando?: boolean;
  /** Botão X quando há texto. Padrão true. */
  limpavel?: boolean;
  tamanho?: 'sm' | 'md';
  autoFocus?: boolean;
  className?: string;
  'aria-label': string;
}

/**
 * Busca (spec §6.10). Foco desenha borda `accent-400` mais anel interno — sem
 * outline duplo.
 */
export function SearchInput({
  valor,
  aoMudar,
  placeholder = 'Buscar cliente, CNPJ ou município',
  atalho,
  carregando = false,
  limpavel = true,
  tamanho = 'md',
  autoFocus = false,
  className,
  'aria-label': ariaLabel,
}: SearchInputProps) {
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!atalho) return;
    function aoTeclar(evento: KeyboardEvent) {
      const alvo = evento.target as HTMLElement | null;
      const editando =
        alvo instanceof HTMLInputElement ||
        alvo instanceof HTMLTextAreaElement ||
        alvo?.isContentEditable === true;
      if (editando || evento.metaKey || evento.ctrlKey || evento.altKey) return;
      if (evento.key !== atalho) return;
      evento.preventDefault();
      campo.current?.focus();
    }
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [atalho]);

  const Icone = carregando ? LoaderCircle : Search;

  return (
    <div
      className={cn(
        'transicao-controle relative flex items-center rounded-full border border-line-default bg-surface-input',
        'focus-within:border-accent-400 focus-within:shadow-[0_0_0_1px_var(--color-accent-400)]',
        tamanho === 'sm' ? 'h-[var(--height-control-sm)]' : 'h-[var(--height-control)]',
        className,
      )}
    >
      <Icone
        size={14}
        strokeWidth={2}
        className={cn(
          'pointer-events-none absolute left-2 text-fg-tertiary',
          carregando && 'girando',
        )}
        aria-hidden="true"
      />
      <input
        ref={campo}
        type="search"
        value={valor}
        autoFocus={autoFocus}
        aria-label={ariaLabel}
        placeholder={placeholder}
        onChange={(evento) => aoMudar(evento.target.value)}
        onKeyDown={(evento) => {
          if (evento.key === 'Escape' && valor) {
            evento.stopPropagation();
            aoMudar('');
          }
        }}
        className={cn(
          'h-full w-full bg-transparent pl-8 text-[13px] text-fg-primary outline-none',
          'placeholder:text-fg-tertiary',
          '[&::-webkit-search-cancel-button]:appearance-none',
          limpavel && valor ? 'pr-8' : atalho ? 'pr-8' : 'pr-2',
        )}
      />
      {limpavel && valor ? (
        <button
          type="button"
          aria-label="Limpar busca"
          onClick={() => {
            aoMudar('');
            campo.current?.focus();
          }}
          className="transicao-controle absolute right-1.5 inline-flex rounded-sm text-fg-tertiary hover:text-fg-primary"
        >
          <X size={14} strokeWidth={2} aria-hidden="true" />
        </button>
      ) : atalho ? (
        <kbd
          aria-hidden="true"
          className="type-mono pointer-events-none absolute right-1.5 rounded-sm border border-line-default px-1 text-[11px]/[16px]"
        >
          {atalho}
        </kbd>
      ) : null}
    </div>
  );
}
