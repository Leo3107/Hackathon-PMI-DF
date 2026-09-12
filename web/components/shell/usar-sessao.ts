'use client';

/**
 * Ponte React para `lib/sessao.ts`.
 *
 * `useSyncExternalStore` porque o estado vive fora do React (`localStorage` + eventos) e pode
 * mudar em outra aba. O snapshot de servidor é a sessão vazia: no SSR não há `localStorage`, e
 * o primeiro paint precisa bater com o do servidor para não gerar erro de hidratação.
 */

import { useMemo, useSyncExternalStore } from 'react';

import {
  SESSAO_VAZIA,
  assinarSessao,
  lerSessao,
  sessaoParaApi,
  type EstadoDeSessao,
} from '@/lib/sessao';
import type { EstadoDeSessaoApi } from '@/types';

function assinar(aoMudar: () => void): () => void {
  return assinarSessao(aoMudar);
}

function snapshotDoServidor(): EstadoDeSessao {
  return SESSAO_VAZIA;
}

export function useSessao(): EstadoDeSessao {
  return useSyncExternalStore(assinar, lerSessao, snapshotDoServidor);
}

/**
 * Estado já recortado para o corpo das chamadas ao motor. Memoizado: este objeto costuma ser
 * dependência de `useEffect` que dispara requisição, e uma referência nova a cada render
 * geraria laço de fetch.
 */
export function useSessaoParaApi(clienteId?: string): EstadoDeSessaoApi {
  const sessao = useSessao();
  return useMemo(() => sessaoParaApi(clienteId, sessao), [clienteId, sessao]);
}
