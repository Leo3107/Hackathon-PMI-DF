'use client';

/**
 * Topbar de 48px (`03-ux-e-telas.md` §1.3).
 *
 * Da esquerda para a direita: trilha · busca global · espaçador · contador de custo do LLM ·
 * simulação de evento · identidade do analista.
 */

import { usePathname } from 'next/navigation';

import { BuscaGlobal } from './BuscaGlobal';
import { CustoDoLlm } from './CustoDoLlm';
import { IdentidadeDoAnalista } from './IdentidadeDoAnalista';
import { SimularEvento } from './SimularEvento';
import { Trilha } from './Trilha';

/** Extrai o id do cliente da rota, para pré-selecionar o popover de simulação. */
function clienteDaRota(pathname: string): string | undefined {
  const m = /^\/clientes\/([^/]+)/.exec(pathname);
  return m?.[1];
}

export function BarraSuperior() {
  const pathname = usePathname();

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line-default bg-surface-card px-4">
      <Trilha />
      <BuscaGlobal />
      <CustoDoLlm />
      <SimularEvento clienteIdAtual={clienteDaRota(pathname)} />
      <IdentidadeDoAnalista />
    </header>
  );
}
