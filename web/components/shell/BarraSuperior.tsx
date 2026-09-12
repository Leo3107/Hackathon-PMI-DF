'use client';

/**
 * Topbar de 48px (`03-ux-e-telas.md` §1.3).
 *
 * Da esquerda para a direita: trilha · busca global · espaçador · contador de custo do LLM ·
 * identidade do analista.
 *
 * O acionador de registro de evento mora na sidebar, logo abaixo de "Clientes".
 */

import { BuscaGlobal } from './BuscaGlobal';
import { CustoDoLlm } from './CustoDoLlm';
import { IdentidadeDoAnalista } from './IdentidadeDoAnalista';
import { Trilha } from './Trilha';

export function BarraSuperior() {
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line-default bg-surface-card px-4 shadow-card">
      <Trilha />
      <BuscaGlobal />
      <CustoDoLlm />
      <IdentidadeDoAnalista />
    </header>
  );
}
