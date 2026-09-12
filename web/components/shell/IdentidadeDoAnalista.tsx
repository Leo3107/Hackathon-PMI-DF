'use client';

/**
 * Identidade do analista na topbar (`03-ux-e-telas.md` §1.3, slot 6 · D11.1).
 *
 * Avatar de iniciais + nome. O popover diz, sem rodeios, que este é um perfil de demonstração e
 * que o produto não tem autenticação nesta versão. **Sem "sair", sem troca de usuário**: um
 * gate de login atrasaria o jurado sem agregar nada, e fingir autenticação seria pior.
 */

import { Popover } from './Popover';
import { PERSONA } from './persona';

export function IdentidadeDoAnalista() {
  return (
    <Popover
      rotulo="Identidade do analista"
      largura={280}
      gatilho={({ aberto, alternar, id, controla }) => (
        <button
          id={id}
          type="button"
          aria-expanded={aberto}
          aria-controls={controla}
          onClick={alternar}
          className="flex h-7 items-center gap-2 rounded px-1.5 text-fg-secondary hover:bg-surface-hover hover:text-fg-primary"
        >
          <span
            aria-hidden
            className="grid size-6 place-items-center rounded-full bg-accent-tint type-caption text-accent-300"
          >
            {PERSONA.iniciais}
          </span>
          <span className="type-label hidden sm:inline">{PERSONA.nome}</span>
        </button>
      )}
    >
      <p className="type-subtitle text-fg-primary">{PERSONA.nome}</p>
      <p className="type-caption text-fg-secondary">
        {PERSONA.cargo} · {PERSONA.empresa}
      </p>
      <p className="type-caption mt-2 border-t border-line-subtle pt-2 text-fg-tertiary">
        {PERSONA.aviso}
      </p>
    </Popover>
  );
}
