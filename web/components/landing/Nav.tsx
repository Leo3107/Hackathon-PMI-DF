import Link from 'next/link';

import { CTA_PRIMARIO } from './botoes';

/**
 * Nav mínima: wordmark à esquerda, "Entrar" à direita. Uma linha em qualquer largura.
 *
 * Não há autenticação: "Entrar" leva direto à carteira em `/clientes`, já "logado". O rótulo é
 * o mesmo do CTA principal do hero de propósito: uma intenção, um rótulo.
 */
export function Nav() {
  return (
    <header className="mx-auto flex h-[64px] w-full max-w-[1152px] items-center justify-between px-4 sm:h-[72px] sm:px-6">
      <Link
        href="/"
        className="rounded-sm font-display text-[24px] font-bold tracking-tight text-fg-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-400"
        aria-label="Lastro, página inicial"
      >
        Lastro
      </Link>
      <Link href="/clientes" className={`${CTA_PRIMARIO} h-[40px] px-5 text-[14px]`}>
        Entrar
      </Link>
    </header>
  );
}
