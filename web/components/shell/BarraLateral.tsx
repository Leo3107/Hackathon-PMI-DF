'use client';

/**
 * Navegação persistente — sidebar de 240px (`03-ux-e-telas.md` §1.3).
 *
 * Dois grupos separados por divisória. **Operação** segue o dia do analista; **Documentação**
 * são superfícies de banca e ficam por último, atenuadas.
 *
 * O badge de "Alertas" traz a contagem de **não lidos**, com o número — nunca "0", que seria
 * ruído. Havendo ao menos um crítico não lido, o badge usa a cor semântica **e** o ícone de
 * alerta: nenhum estado de risco é comunicado só por cor (I8).
 *
 * O rodapé fixo tem "Restaurar dados da demonstração" (D11.3), atrás de um `Modal` de
 * confirmação — apagar a trilha de auditoria no meio do pitch por clique acidental seria caro.
 */

import { TriangleAlert } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge, Button, Modal, cn } from '@/components/ui';
import { listarAlertas } from '@/lib/api';
import { restaurarDemonstracao, sessaoParaApi, sessaoTemAlteracoes } from '@/lib/sessao';

import { GRUPO_DOCUMENTACAO, GRUPO_OPERACAO, itemAtivo, type ItemDeNavegacao } from './rotas';
import { useSessao } from './usar-sessao';

export function BarraLateral() {
  const pathname = usePathname();
  const router = useRouter();
  const sessao = useSessao();
  const [confirmando, setConfirmando] = useState(false);
  const [naoLidos, setNaoLidos] = useState(0);
  const [criticos, setCriticos] = useState(0);

  useEffect(() => {
    let vivo = true;
    listarAlertas(sessaoParaApi())
      .then((alertas) => {
        if (!vivo) return;
        const pendentes = alertas.filter(
          (a) => !a.lido && !sessao.alertasLidos.includes(a.id),
        );
        setNaoLidos(pendentes.length);
        setCriticos(pendentes.filter((a) => a.severidade === 'CRITICA').length);
      })
      .catch(() => {
        // Motor fora do ar: some o badge em vez de mostrar contagem inventada.
        if (vivo) {
          setNaoLidos(0);
          setCriticos(0);
        }
      });
    return () => {
      vivo = false;
    };
  }, [sessao]);

  function confirmarRestauracao() {
    restaurarDemonstracao();
    setConfirmando(false);
    router.refresh();
  }

  const item = (i: ItemDeNavegacao, atenuado: boolean) => {
    const ativo = itemAtivo(pathname, i.href);
    const mostrarBadge = i.contaAlertas && naoLidos > 0;
    return (
      <li key={i.href}>
        <Link
          href={i.href}
          aria-current={ativo ? 'page' : undefined}
          className={cn(
            'flex h-8 items-center gap-2 border-l-2 pl-3 pr-2',
            ativo
              ? 'border-accent-400 bg-accent-tint text-fg-primary'
              : cn(
                  'border-transparent hover:bg-surface-hover hover:text-fg-primary',
                  atenuado ? 'text-fg-tertiary' : 'text-fg-secondary',
                ),
          )}
        >
          <i.Icone aria-hidden className="size-4 shrink-0" />
          <span className="type-label min-w-0 flex-1 truncate">{i.rotulo}</span>
          {mostrarBadge &&
            (criticos > 0 ? (
              <Badge variante="severidade" severidade="CRITICA" tamanho="sm" icone={TriangleAlert}>
                {naoLidos}
              </Badge>
            ) : (
              <Badge variante="neutro" tamanho="sm" icone={null}>
                {naoLidos}
              </Badge>
            ))}
        </Link>
      </li>
    );
  };

  return (
    <nav
      aria-label="Navegação principal"
      className="flex w-60 shrink-0 flex-col border-r border-line-default bg-surface-card"
    >
      <div className="flex h-12 items-center border-b border-line-default px-3">
        <Link href="/carteira" className="type-h5 tracking-tight text-fg-primary">
          LASTRO
        </Link>
      </div>

      <ul className="py-2">{GRUPO_OPERACAO.map((i) => item(i, false))}</ul>
      <div className="mx-3 border-t border-line-subtle" />
      <ul className="py-2">{GRUPO_DOCUMENTACAO.map((i) => item(i, true))}</ul>

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
