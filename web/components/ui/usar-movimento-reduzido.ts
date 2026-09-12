'use client';

import { useSyncExternalStore } from 'react';

const CONSULTA = '(prefers-reduced-motion: reduce)';

function consulta(): MediaQueryList | null {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null;
  return window.matchMedia(CONSULTA);
}

function inscrever(aoMudar: () => void): () => void {
  const lista = consulta();
  if (!lista) return () => undefined;
  lista.addEventListener('change', aoMudar);
  return () => lista.removeEventListener('change', aoMudar);
}

function obterCliente(): boolean {
  return consulta()?.matches ?? false;
}

function obterServidor(): boolean {
  return false;
}

/**
 * `prefers-reduced-motion: reduce` (spec §9.4).
 *
 * Desliga a contagem do gauge e o stagger do pipeline. Assinado por
 * `useSyncExternalStore`: o `matchMedia` é a fonte externa da verdade e não há
 * `setState` dentro de efeito.
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(inscrever, obterCliente, obterServidor);
}
