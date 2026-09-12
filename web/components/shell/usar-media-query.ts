'use client';

/**
 * Media query como fonte externa de verdade, para o shell decidir em JS o que o CSS sozinho
 * não resolve: portar um painel para fora da sidebar deslizante, mover foco só no celular.
 *
 * `useSyncExternalStore` com snapshot de servidor `false`: no SSR ninguém sabe a largura da
 * tela, e a marcação que depende disto só existe em estados abertos por interação, então a
 * hidratação não diverge. O mesmo padrão de `components/ui/usar-movimento-reduzido.ts`.
 */

import { useCallback, useSyncExternalStore } from 'react';

/** Ponto de corte em que a sidebar volta a ser coluna fixa (`lg` do Tailwind). */
export const CONSULTA_DESKTOP = '(min-width: 1024px)';

function consultar(consulta: string): MediaQueryList | null {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null;
  return window.matchMedia(consulta);
}

export function useMediaQuery(consulta: string): boolean {
  const inscrever = useCallback(
    (aoMudar: () => void) => {
      const lista = consultar(consulta);
      if (!lista) return () => undefined;
      lista.addEventListener('change', aoMudar);
      return () => lista.removeEventListener('change', aoMudar);
    },
    [consulta],
  );
  return useSyncExternalStore(
    inscrever,
    () => consultar(consulta)?.matches ?? false,
    () => false,
  );
}
