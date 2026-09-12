'use client';

/**
 * Popover do shell — gatilho + painel ancorado.
 *
 * O catálogo do design system (`05` §6) tem `Modal`, `Drawer` e `Tooltip`, mas **não** tem
 * popover; os slots que precisam de um (registro de evento, identidade do analista, busca
 * global) são todos do shell. Por isso ele vive aqui, mínimo e sem dependência.
 *
 * Duas ancoragens: `inferior` (padrão, topbar — abaixo do gatilho, alinhado à direita) e
 * `lateral` (sidebar — à direita do gatilho, para o painel não sair da viewport à esquerda).
 *
 * Abaixo de `lg` a sidebar é um painel deslizante e "à direita do gatilho" cairia fora da
 * tela. Nesse caso a ancoragem `lateral` vira uma folha inferior: painel fixo no pé da tela,
 * portado para o `body`. O portal é necessário, não estético: a sidebar deslizante tem
 * `translate`, que faz de `position: fixed` uma posição relativa a ela, e não à viewport.
 *
 * `Esc` fecha e devolve o foco ao gatilho — é a primeira camada da ordem exigida por §1.4:
 * popover → drawer → modal.
 */

import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '@/components/ui';

import { CONSULTA_DESKTOP, useMediaQuery } from './usar-media-query';

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
  /** Onde o painel abre em relação ao gatilho. Padrão `inferior`. */
  ancoragem?: 'inferior' | 'lateral';
  className?: string;
}

export function Popover({
  gatilho,
  children,
  largura = 360,
  rotulo,
  ancoragem = 'inferior',
  className,
}: PopoverProps) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const painel = useRef<HTMLDivElement>(null);
  const gatilhoRef = useRef<HTMLElement | null>(null);
  const id = useId();
  const desktop = useMediaQuery(CONSULTA_DESKTOP);
  // Só existe quando aberto, por interação: no SSR nunca renderiza, então o snapshot de servidor
  // do `useMediaQuery` (`false`) não produz divergência de hidratação.
  const folhaInferior = ancoragem === 'lateral' && !desktop;

  useEffect(() => {
    if (!aberto) return;
    const aoClicar = (evento: MouseEvent) => {
      const alvo = evento.target as Node;
      if (caixa.current?.contains(alvo) || painel.current?.contains(alvo)) return;
      setAberto(false);
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

  const conteudo = aberto ? (
    <div
      ref={painel}
      id={`${id}-painel`}
      role="dialog"
      aria-label={rotulo}
      style={folhaInferior ? undefined : { width: largura }}
      className={cn(
        'rounded-md border border-line-strong bg-surface-raised p-3 shadow-[var(--shadow-overlay)]',
        folhaInferior
          ? 'fixed inset-x-4 bottom-4 z-60 max-h-[70dvh] overflow-y-auto'
          : ancoragem === 'lateral'
            ? 'absolute left-full top-0 z-50 ml-1 max-h-[calc(100vh-96px)] overflow-y-auto'
            : 'absolute right-0 top-[calc(100%+6px)] z-50',
      )}
    >
      {children}
    </div>
  ) : null;

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
      {folhaInferior && conteudo ? createPortal(conteudo, document.body) : conteudo}
    </div>
  );
}
