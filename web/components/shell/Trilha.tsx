'use client';

/**
 * Trilha de navegação da topbar (`03-ux-e-telas.md` §1.3, slot 1).
 *
 * `Nova análise` · `Clientes › Fazenda Vale do Araguaia` · `… › Parecer`. Cada nível anterior é
 * link; o nível atual não é clicável e trunca com reticências.
 *
 * O último nível de `/clientes/[id]` é a razão social. Ela sai do cache compartilhado da lista
 * de clientes (`usar-clientes.ts`), e não de um contexto que a página preenche: assim a trilha
 * não depende de nenhuma outra rota chamar um hook de registro — e nenhuma página paga o custo
 * de um efeito só para dizer ao shell como se chama. Enquanto a lista não chega, o slug
 * humanizado ocupa o lugar; nunca um vazio piscando.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/components/ui';

import { rotuloDaRota } from './rotas';
import { useClientes } from './usar-clientes';

interface Nivel {
  rotulo: string;
  href?: string;
}

function humanizar(slug: string): string {
  const texto = decodeURIComponent(slug).replace(/-/g, ' ');
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function Trilha() {
  const pathname = usePathname();
  const clientes = useClientes();

  const partes = pathname.split('/').filter(Boolean);
  const raiz = rotuloDaRota(pathname);

  const niveis: Nivel[] = [];
  if (!raiz) {
    niveis.push({ rotulo: 'Lastro' });
  } else if (partes.length <= 1) {
    niveis.push({ rotulo: raiz });
  } else {
    niveis.push({ rotulo: raiz, href: `/${partes[0]}` });
    const id = partes[1];
    const nome = clientes.find((c) => c.cliente.id === id)?.cliente.razaoSocial;
    niveis.push({
      rotulo: nome ?? humanizar(id),
      href: partes.length > 2 ? `/${partes[0]}/${id}` : undefined,
    });
    if (partes.length > 2) niveis.push({ rotulo: humanizar(partes[2]) });
  }

  return (
    <nav aria-label="Trilha de navegação" className="min-w-0 flex-1">
      <ol className="flex min-w-0 items-center gap-1.5">
        {niveis.map((nivel, i) => (
          <li
            key={`${nivel.rotulo}-${i}`}
            // Abaixo de `md` só o nível atual aparece: os anteriores estão na sidebar.
            className={cn(
              'min-w-0 items-center gap-1.5',
              i < niveis.length - 1 ? 'hidden md:flex' : 'flex',
            )}
          >
            {i > 0 && (
              <span aria-hidden className="type-caption hidden text-fg-tertiary md:inline">
                ›
              </span>
            )}
            {nivel.href ? (
              <Link
                href={nivel.href}
                className="type-label truncate text-fg-secondary hover:text-fg-primary"
              >
                {nivel.rotulo}
              </Link>
            ) : (
              <span aria-current="page" className="type-label truncate text-fg-primary">
                {nivel.rotulo}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
