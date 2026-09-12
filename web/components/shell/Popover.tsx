'use client';

/**
 * Popover de topbar — gatilho + painel ancorado à direita.
 *
 * O catálogo do design system (`05` §6) tem `Modal`, `Drawer` e `Tooltip`, mas **não** tem
 * popover; os três slots da topbar que precisam de um (simulação de evento, identidade do
 * analista, busca global) são todos do shell. Por isso ele vive aqui, mínimo e sem dependência.
 *
 * `Esc` fecha e devolve o foco ao gatilho — é a primeira camada da ordem exigida por §1.4:
 * popover → drawer → modal.
 */

import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

import { cn } from '@/components/ui';

export interface PopoverProps {
  /** Recebe o estado para desenhar o gatilho (botão, avatar, campo). */
  gatilho: (props: {
    aberto: boolean;
    alternar: () => void;
    id: string;
    controla: string;
  }) => ReactNode;
  children: ReactNode;
  /** Largura do painel em px. Padrão 360, como pede §1.5. */
  largura?: number;
  rotulo: string;
  className?: string;
}

export function Popover({ gatilho, children, largura = 360, rotulo, className }: PopoverProps) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const gatilhoRef = useRef<HTMLElement | null>(null);
  const id = useId();

  useEffect(() => {
    if (!aberto) return;
    const aoClicar = (evento: MouseEvent) => {
      if (!caixa.current?.contains(evento.target as Node)) setAberto(false);
    };
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key !== 'Escape') return;
      evento.stopPropagation();
      setAberto(false);
      gatilhoRef.current?.focus();
    };
    document.addEventListener('mousedown', aoClicar);
    document.addEventListener('keydown', aoTeclar);
    return () => {
      document.removeEventListener('mousedown', aoClicar);
      document.removeEventListener('keydown', aoTeclar);
    };
  }, [aberto]);

  return (
    <div
      ref={caixa}
      className={cn('relative', className)}
      onFocusCapture={(e) => {
        if (e.target instanceof HTMLElement && e.target.id === `${id}-gatilho`) {
          gatilhoRef.current = e.target;
        }
      }}
    >
      {gatilho({
        aberto,
        alternar: () => setAberto((v) => !v),
        id: `${id}-gatilho`,
        controla: `${id}-painel`,
      })}
      {aberto && (
        <div
          id={`${id}-painel`}
          role="dialog"
          aria-label={rotulo}
          style={{ width: largura }}
          className={cn(
            'absolute right-0 top-[calc(100%+6px)] z-50 rounded-md border border-line-strong',
            'bg-surface-raised p-3 shadow-[var(--shadow-overlay)]',
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}
