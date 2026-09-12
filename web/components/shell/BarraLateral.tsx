'use client';

/**
 * Navegação persistente — sidebar de 240px.
 *
 * Duas telas: Nova análise e Clientes. Sem grupos, sem badges — só as duas entradas, mais o
 * acionador de "Registrar evento" logo abaixo de "Clientes": ele não navega, mas mora na lista
 * porque é a terceira ação recorrente do analista.
 *
 * Em `lg` e acima é coluna fixa, como sempre foi. Abaixo disso, a mesma `<nav>` vira painel
 * deslizante à esquerda, com scrim, controlado pelo `Shell`: nada é duplicado, só a posição
 * muda por CSS. Fechada, fica `invisible` e fora da tela, o que a tira da ordem de tabulação
 * sem precisar de `inert`. Aberta, o foco vai ao primeiro item, o scroll do `body` trava e
 * `Esc` fecha, exceto quando a tecla nasce dentro de um diálogo aberto por cima (popover de
 * evento, modal de restauração), que tem prioridade na ordem de §1.4.
 *
 * O rodapé fixo tem "Restaurar dados da sessão", atrás de um `Modal` de confirmação —
 * apagar decisões registradas no meio do pitch por clique acidental seria caro.
 */

import { X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, useState, type RefObject } from 'react';

import { Button, Modal, cn } from '@/components/ui';
import { restaurarDemonstracao, sessaoTemAlteracoes } from '@/lib/sessao';

import { GRUPO_OPERACAO, itemAtivo, type ItemDeNavegacao } from './rotas';
import { SimularEvento } from './SimularEvento';
import { CONSULTA_DESKTOP, useMediaQuery } from './usar-media-query';
import { useSessao } from './usar-sessao';

/** Id do cliente da rota atual, para pré-selecionar o registro de evento. */
function clienteDaRota(pathname: string): string | undefined {
  const m = /^\/clientes\/([^/]+)/.exec(pathname);
  return m?.[1];
}

export interface BarraLateralProps {
  /** Id da `<nav>`, referenciado pelo `aria-controls` do botão de menu. */
  id?: string;
  /** Painel deslizante aberto (só tem efeito abaixo de `lg`). */
  aberta?: boolean;
  aoFechar?: () => void;
  /** Botão de menu da topbar, que recebe o foco de volta ao fechar. */
  retornarFocoPara?: RefObject<HTMLElement | null>;
}

export function BarraLateral({
  id,
  aberta = false,
  aoFechar,
  retornarFocoPara,
}: BarraLateralProps) {
  const pathname = usePathname();
  const router = useRouter();
  const sessao = useSessao();
  const [confirmando, setConfirmando] = useState(false);
  const desktop = useMediaQuery(CONSULTA_DESKTOP);
  const painel = useRef<HTMLElement>(null);
  const deslizanteAberta = aberta && !desktop;

  useEffect(() => {
    if (!deslizanteAberta) return;
    // O botão de menu é lido na abertura: é o mesmo elemento que estará lá ao fechar.
    const origem = retornarFocoPara?.current ?? null;
    painel.current?.querySelector<HTMLElement>('a[href], button:not([disabled])')?.focus();

    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key !== 'Escape') return;
      // Um diálogo por cima (popover, modal) fecha primeiro; a sidebar espera a próxima tecla.
      if (evento.target instanceof Element && evento.target.closest('[role="dialog"]')) return;
      aoFechar?.();
    }
    document.addEventListener('keydown', aoTeclar);

    return () => {
      document.removeEventListener('keydown', aoTeclar);
      document.body.style.overflow = overflowAnterior;
      origem?.focus();
    };
  }, [deslizanteAberta, aoFechar, retornarFocoPara]);

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
    <>
      {/* Scrim: só existe abaixo de `lg`; fecha ao toque e some do leitor de tela quando fechado. */}
      <button
        type="button"
        tabIndex={-1}
        aria-hidden={!aberta}
        aria-label="Fechar navegação"
        onClick={aoFechar}
        className={cn(
          'fixed inset-0 z-40 cursor-default bg-surface-overlay lg:hidden',
          'transition-opacity duration-[var(--duration-base)] ease-[var(--ease-standard)] motion-reduce:transition-none',
          aberta ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <nav
        id={id}
        ref={painel}
        aria-label="Navegação principal"
        className={cn(
          'flex shrink-0 flex-col border-r border-line-default bg-surface-card',
          // Abaixo de `lg`: painel fixo que desliza da esquerda.
          'fixed inset-y-0 left-0 z-50 w-[min(280px,calc(100vw-3rem))] shadow-overlay',
          'transition-[translate,visibility] duration-[var(--duration-base)] ease-[var(--ease-standard)] motion-reduce:transition-none',
          aberta ? 'visible translate-x-0' : 'invisible -translate-x-full',
          // Em `lg`+: a coluna de 240px de sempre, sem deslocamento nem sombra.
          'lg:visible lg:static lg:z-auto lg:w-60 lg:translate-none lg:shadow-none lg:transition-none',
        )}
      >
        <div className="flex h-12 items-center border-b border-line-default px-4">
          <Link
            href="/nova-analise"
            className="text-[16px] font-bold tracking-tight text-accent-600 [font-family:var(--font-display)]"
          >
            Lastro
          </Link>
          <span className="flex-1 lg:hidden" />
          <button
            type="button"
            aria-label="Fechar navegação"
            onClick={aoFechar}
            className="transicao-controle -mr-2 inline-flex size-[var(--height-control-sm)] items-center justify-center rounded-full border border-transparent text-fg-secondary hover:bg-surface-hover hover:text-fg-primary lg:hidden"
          >
            <X size={14} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>

        <ul className="flex flex-col gap-0.5 py-3">
          {GRUPO_OPERACAO.map(item)}
          {/* Não é item de navegação: sem `aria-current`, sem realce de ativo. */}
          <li>
            <SimularEvento clienteIdAtual={clienteDaRota(pathname)} />
          </li>
        </ul>

        <div className="flex-1" />

        <div className="border-t border-line-subtle p-3">
          <Button
            variante="perigo-neutro"
            tamanho="sm"
            larguraTotal
            disabled={!sessaoTemAlteracoes(sessao)}
            onClick={() => setConfirmando(true)}
          >
            Restaurar sessão
          </Button>
        </div>

        <Modal
          aberto={confirmando}
          aoFechar={() => setConfirmando(false)}
          titulo="Restaurar dados da sessão"
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
            Isto apaga decisões registradas, eventos e marcações de leitura desta sessão.
            Os dados voltam ao estado inicial.
          </p>
        </Modal>
      </nav>
    </>
  );
}
