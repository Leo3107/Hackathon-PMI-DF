'use client';

/**
 * Navegação persistente — sidebar de 240px.
 *
 * Duas telas: Nova análise e Clientes. Sem grupos, sem badges — só as duas entradas.
 *
 * O rodapé fixo tem "Restaurar dados da demonstração", atrás de um `Modal` de confirmação —
 * apagar decisões registradas no meio do pitch por clique acidental seria caro.
 */

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button, Modal, cn } from '@/components/ui';
import { restaurarDemonstracao, sessaoTemAlteracoes } from '@/lib/sessao';

import { GRUPO_OPERACAO, itemAtivo, type ItemDeNavegacao } from './rotas';
import { useSessao } from './usar-sessao';

export function BarraLateral() {
  const pathname = usePathname();
  const router = useRouter();
  const sessao = useSessao();
  const [confirmando, setConfirmando] = useState(false);

  function confirmarRestauracao() {
    restaurarDemonstracao();
    setConfirmando(false);
    router.refresh();
  }

  const item = (i: ItemDeNavegacao) => {
    const ativo = itemAtivo(pathname, i.href);
    return (
      <li key={i.href}>
        <Link
          href={i.href}
          aria-current={ativo ? 'page' : undefined}
          className={cn(
            'transicao-controle mx-2 flex h-9 items-center gap-2 rounded-md px-3',
            ativo
              ? 'bg-accent-tint font-medium text-accent-600'
              : 'text-fg-secondary hover:bg-surface-hover hover:text-fg-primary',
          )}
        >
          <i.Icone aria-hidden className="size-4 shrink-0" />
          <span className="type-label min-w-0 flex-1 truncate text-current">{i.rotulo}</span>
        </Link>
      </li>
    );
  };

  return (
    <nav
      aria-label="Navegação principal"
      className="flex w-60 shrink-0 flex-col border-r border-line-default bg-surface-card"
    >
      <div className="flex h-12 items-center border-b border-line-default px-4">
        <Link
          href="/nova-analise"
          className="text-[16px] font-bold tracking-tight text-accent-600 [font-family:var(--font-display)]"
        >
          Lastro
        </Link>
      </div>

      <ul className="flex flex-col gap-0.5 py-3">{GRUPO_OPERACAO.map(item)}</ul>

      <div className="flex-1" />

      <div className="border-t border-line-subtle p-3">
        <Button
          variante="perigo-neutro"
          tamanho="sm"
          larguraTotal
          disabled={!sessaoTemAlteracoes(sessao)}
          onClick={() => setConfirmando(true)}
        >
          Restaurar demonstração
        </Button>
      </div>

      <Modal
        aberto={confirmando}
        aoFechar={() => setConfirmando(false)}
        titulo="Restaurar dados da demonstração"
        tamanho="sm"
        acoes={
          <>
            <Button variante="secundario" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
            <Button variante="primario" onClick={confirmarRestauracao}>
              Restaurar
            </Button>
          </>
        }
      >
        <p className="type-body text-fg-secondary">
          Isto apaga decisões registradas, eventos simulados e marcações de leitura desta sessão.
          Os dados voltam ao estado inicial.
        </p>
      </Modal>
    </nav>
  );
}
