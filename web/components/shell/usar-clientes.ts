'use client';

/**
 * Cache de sessão da lista de clientes avaliados.
 *
 * Três peças do shell precisam da mesma lista: a busca global, o select de simulação de evento e
 * a trilha (que resolve `/clientes/<slug>` para a razão social). Três `fetch` independentes
 * seriam três viagens ao motor para o mesmo dado, na abertura da app — justamente o momento em
 * que a carteira já está carregando.
 *
 * O store é um `useSyncExternalStore` module-level: a primeira assinatura dispara a carga, as
 * seguintes reaproveitam. Falha de rede não lança — a lista fica vazia e a faixa global de
 * §9.4 é quem explica por quê.
 */

import { useCallback, useSyncExternalStore } from 'react';

import { listarClientes } from '@/lib/api';
import { sessaoParaApi } from '@/lib/sessao';
import type { ClienteAvaliado } from '@/types';

const VAZIO: ClienteAvaliado[] = [];

let cache: ClienteAvaliado[] = VAZIO;
let carregando = false;
const ouvintes = new Set<() => void>();

function notificar(): void {
  for (const ouvinte of ouvintes) ouvinte();
}

function garantirCarga(): void {
  if (carregando) return;
  carregando = true;
  listarClientes(sessaoParaApi())
    .then((lista) => {
      cache = lista;
      notificar();
    })
    .catch(() => {
      carregando = false; // Permite nova tentativa quando o motor voltar.
    });
}

/** Invalida o cache após uma mutação que muda o cálculo (novo evento, desfazer). */
export function recarregarClientes(): void {
  carregando = false;
  garantirCarga();
}

export function useClientes(): ClienteAvaliado[] {
  const assinar = useCallback((aoMudar: () => void) => {
    ouvintes.add(aoMudar);
    garantirCarga();
    return () => {
      ouvintes.delete(aoMudar);
    };
  }, []);
  return useSyncExternalStore(
    assinar,
    () => cache,
    () => VAZIO,
  );
}

/** Razão social de um cliente já carregado, ou `null` enquanto a lista não chegou. */
export function useRazaoSocial(clienteId: string | undefined): string | null {
  const lista = useClientes();
  if (!clienteId) return null;
  return lista.find((c) => c.cliente.id === clienteId)?.cliente.razaoSocial ?? null;
}
