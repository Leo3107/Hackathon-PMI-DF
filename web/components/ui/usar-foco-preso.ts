'use client';

import { useEffect, type RefObject } from 'react';

const SELETOR_FOCAVEL = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export interface OpcoesFocoPreso {
  ativo: boolean;
  recipiente: RefObject<HTMLElement | null>;
  aoFechar: () => void;
  /** Elemento que recebe o foco de volta ao fechar. */
  retornarFocoPara?: RefObject<HTMLElement | null>;
}

/**
 * Prende o foco dentro de um diálogo, fecha em `Esc` e devolve o foco ao
 * elemento de origem (spec §6.11 e §6.12).
 */
export function useFocoPreso({
  ativo,
  recipiente,
  aoFechar,
  retornarFocoPara,
}: OpcoesFocoPreso): void {
  useEffect(() => {
    if (!ativo) return;

    const origem =
      retornarFocoPara?.current ??
      (document.activeElement instanceof HTMLElement ? document.activeElement : null);

    const alvo = recipiente.current;
    const primeiro = alvo?.querySelector<HTMLElement>(SELETOR_FOCAVEL);
    (primeiro ?? alvo)?.focus();

    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === 'Escape') {
        evento.stopPropagation();
        aoFechar();
        return;
      }
      if (evento.key !== 'Tab' || !recipiente.current) return;

      const focaveis = Array.from(
        recipiente.current.querySelectorAll<HTMLElement>(SELETOR_FOCAVEL),
      ).filter((elemento) => elemento.offsetParent !== null || elemento === document.activeElement);
      if (focaveis.length === 0) {
        evento.preventDefault();
        return;
      }
      const inicio = focaveis[0];
      const fim = focaveis[focaveis.length - 1];
      if (!evento.shiftKey && document.activeElement === fim) {
        evento.preventDefault();
        inicio.focus();
      } else if (evento.shiftKey && document.activeElement === inicio) {
        evento.preventDefault();
        fim.focus();
      }
    }

    document.addEventListener('keydown', aoTeclar, true);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', aoTeclar, true);
      document.body.style.overflow = overflowAnterior;
      origem?.focus?.();
    };
  }, [ativo, recipiente, aoFechar, retornarFocoPara]);
}
