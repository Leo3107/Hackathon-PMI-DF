'use client';

import { X } from 'lucide-react';
import { useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from './cn';
import { IconButton } from './IconButton';
import { useFocoPreso } from './usar-foco-preso';

export interface ModalProps {
  aberto: boolean;
  aoFechar: () => void;
  titulo: string;
  descricao?: string;
  /** 400 · 560 · 760 px. */
  tamanho?: 'sm' | 'md' | 'lg';
  /** Obrigatório: pelo menos um `Button`. */
  acoes: ReactNode;
  /** Padrão true; `false` em "Registrar decisão". */
  fecharAoClicarFora?: boolean;
  children: ReactNode;
  className?: string;
}

const LARGURA = { sm: '400px', md: '560px', lg: '760px' } as const;

/**
 * Diálogo modal (spec §6.12). Um por vez; modal sobre drawer é permitido
 * (z-60 vs z-50). Uso canônico: "Registrar decisão do analista" e
 * "Simular evento de monitoramento".
 */
export function Modal({
  aberto,
  aoFechar,
  titulo,
  descricao,
  tamanho = 'md',
  acoes,
  fecharAoClicarFora = true,
  children,
  className,
}: ModalProps) {
  const caixa = useRef<HTMLDivElement>(null);
  const id = useId();
  useFocoPreso({ ativo: aberto, recipiente: caixa, aoFechar });

  // Sem estado de montagem: no servidor não há `document`, e o portal não
  // renderiza nada no lugar do componente — não há divergência de hidratação.
  if (!aberto || typeof document === 'undefined') return null;

  return createPortal(
    <div className="no-print fixed inset-0 z-60 flex items-center justify-center p-6">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Fechar diálogo"
        aria-hidden={!fecharAoClicarFora}
        onClick={fecharAoClicarFora ? aoFechar : undefined}
        disabled={!fecharAoClicarFora}
        className="absolute inset-0 cursor-default bg-surface-overlay"
      />
      <div
        ref={caixa}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-titulo`}
        aria-describedby={descricao ? `${id}-descricao` : undefined}
        tabIndex={-1}
        className={cn(
          'transicao-base relative flex max-h-full w-full flex-col rounded-lg',
          'border border-line-strong bg-surface-raised shadow-overlay outline-none',
          className,
        )}
        style={{ maxWidth: LARGURA[tamanho] }}
      >
        <header className="flex shrink-0 items-start justify-between gap-3 p-5 pb-3">
          <div className="min-w-0">
            <h2 id={`${id}-titulo`} className="type-section-title">
              {titulo}
            </h2>
            {descricao ? (
              <p id={`${id}-descricao`} className="type-caption mt-1">
                {descricao}
              </p>
            ) : null}
          </div>
          <IconButton icone={X} rotulo="Fechar" onClick={aoFechar} />
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 scrollbar-thin">{children}</div>

        <footer className="flex shrink-0 items-center justify-end gap-2 p-5 pt-3">{acoes}</footer>
      </div>
    </div>,
    document.body,
  );
}
