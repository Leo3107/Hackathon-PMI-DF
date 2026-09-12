'use client';

import { X } from 'lucide-react';
import { useId, useRef, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';

import { cn } from './cn';
import { IconButton } from './IconButton';
import { useFocoPreso } from './usar-foco-preso';

export interface DrawerProps {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  /** Ex.: documento mascarado + município. */
  subtitulo?: string;
  /** 520px | 720px. */
  largura?: 'padrao' | 'larga';
  /** `RatingBadge`, `TrendIndicator` ao lado do título. */
  cabecalhoExtra?: ReactNode;
  /** Barra de ações fixa no pé (Button primário à direita). */
  rodape?: ReactNode;
  children: ReactNode;
  retornarFocoPara?: RefObject<HTMLElement | null>;
  className?: string;
}

/**
 * Painel lateral (spec §6.11). Pré-visualização — a URL **não** muda ao abrir;
 * a página do cliente continua sendo a rota.
 */
export function Drawer({
  aberto,
  aoFechar,
  titulo,
  subtitulo,
  largura = 'padrao',
  cabecalhoExtra,
  rodape,
  children,
  retornarFocoPara,
  className,
}: DrawerProps) {
  const painel = useRef<HTMLDivElement>(null);
  const id = useId();
  useFocoPreso({ ativo: aberto, recipiente: painel, aoFechar, retornarFocoPara });

  // Sem estado de montagem: no servidor não há `document`, e o portal não
  // renderiza nada no lugar do componente — não há divergência de hidratação.
  if (!aberto || typeof document === 'undefined') return null;

  return createPortal(
    <div className="no-print fixed inset-0 z-50">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Fechar painel"
        onClick={aoFechar}
        className="absolute inset-0 cursor-default bg-surface-overlay"
      />
      <div
        ref={painel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-titulo`}
        tabIndex={-1}
        className={cn(
          'transicao-base absolute top-0 right-0 flex h-full flex-col rounded-l-lg',
          'border-l border-line-strong bg-surface-raised shadow-overlay outline-none',
          className,
        )}
        style={{
          width: `var(${largura === 'larga' ? '--width-drawer-wide' : '--width-drawer'})`,
          maxWidth: '100vw',
        }}
      >
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line-subtle px-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="min-w-0">
              <h2 id={`${id}-titulo`} className="type-section-title truncate">
                {titulo}
              </h2>
              {subtitulo ? <p className="type-caption truncate">{subtitulo}</p> : null}
            </div>
            {cabecalhoExtra}
          </div>
          <IconButton icone={X} rotulo="Fechar" onClick={aoFechar} />
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-5 scrollbar-thin">{children}</div>

        {rodape ? (
          <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-line-subtle px-5 py-3">
            {rodape}
          </footer>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
