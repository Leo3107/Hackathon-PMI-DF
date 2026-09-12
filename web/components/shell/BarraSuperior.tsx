'use client';

/**
 * Topbar de 48px (`03-ux-e-telas.md` §1.3).
 *
 * Da esquerda para a direita: trilha · busca global · espaçador · contador de custo do LLM ·
 * identidade do analista.
 *
 * Abaixo de `lg` entra, antes da trilha, o botão de menu que abre a sidebar deslizante.
 * Abaixo de `md` o contador de custo sai (o `sr-only` dele também: é indicador, não conteúdo),
 * a trilha mostra só o nível atual e a busca vira ícone que expande sobre a barra inteira.
 * A barra nunca cresce: tudo cabe em 48px, em qualquer largura.
 *
 * O acionador de registro de evento mora na sidebar, logo abaixo de "Clientes".
 */

import { Menu } from 'lucide-react';
import type { RefObject } from 'react';

import { BuscaGlobal } from './BuscaGlobal';
import { CustoDoLlm } from './CustoDoLlm';
import { IdentidadeDoAnalista } from './IdentidadeDoAnalista';
import { Trilha } from './Trilha';

export interface BarraSuperiorProps {
  menuAberto?: boolean;
  aoAbrirMenu?: () => void;
  /** Id da `<nav>` da sidebar, para o `aria-controls` do botão de menu. */
  idNavegacao?: string;
  /** Recebe o foco de volta quando a sidebar deslizante fecha. */
  refBotaoMenu?: RefObject<HTMLButtonElement | null>;
}

export function BarraSuperior({
  menuAberto = false,
  aoAbrirMenu,
  idNavegacao,
  refBotaoMenu,
}: BarraSuperiorProps) {
  return (
    <header className="relative flex h-12 shrink-0 items-center gap-3 border-b border-line-default bg-surface-card px-4 shadow-card">
      <button
        ref={refBotaoMenu}
        type="button"
        aria-label="Abrir navegação"
        aria-expanded={menuAberto}
        aria-controls={idNavegacao}
        onClick={aoAbrirMenu}
        className="transicao-controle -ml-1.5 inline-flex size-[var(--height-control-sm)] shrink-0 items-center justify-center rounded-full border border-transparent text-fg-secondary hover:bg-surface-hover hover:text-fg-primary lg:hidden"
      >
        <Menu size={16} strokeWidth={2} aria-hidden="true" />
      </button>
      <Trilha />
      <BuscaGlobal />
      <div className="hidden md:contents">
        <CustoDoLlm />
      </div>
      <IdentidadeDoAnalista />
    </header>
  );
}
