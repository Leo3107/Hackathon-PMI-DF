'use client';

/**
 * Faixa de atenção imediata da carteira (`03-ux-e-telas.md` §2.2).
 *
 * A **seleção** dos até três clientes é do motor (`ResumoCarteira.atencaoImediata`), não da
 * tela: a regra de desempate é determinística e está na spec 02. Aqui só se apresenta.
 *
 * R2 (I8): cada cartão comunica o motivo por **borda semântica + ícone + eyebrow textual**,
 * nunca só por cor.
 */

import { Gavel, ShieldCheck, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';

import { CLASSES_RISCO, Card, SEVERIDADE, cn } from '@/components/ui';
import { formatarDataHora } from '@/lib/format';
import type { CartaoDeAtencao, MotivoAtencao } from '@/types';

/** Ícone e destino por motivo — o rótulo textual vem do motor, em `eyebrow`. */
const MOTIVO: Record<MotivoAtencao, { Icone: LucideIcon; ancora: string }> = {
  VETO_ATIVO: { Icone: Gavel, ancora: '' },
  MAIOR_QUEDA_90D: { Icone: TrendingDown, ancora: '#o-que-mudou' },
  ALERTA_CRITICO: { Icone: SEVERIDADE.CRITICA.Icone, ancora: '#red-flags' },
};

export interface FaixaDeAtencaoProps {
  cartoes: CartaoDeAtencao[];
  /** ISO datetime — exibido quando não há ocorrência a destacar. */
  ultimaVarredura: string;
  carregando?: boolean;
}

export function FaixaDeAtencao({ cartoes, ultimaVarredura, carregando }: FaixaDeAtencaoProps) {
  if (carregando) {
    return (
      <div className="grid gap-4 md:grid-cols-3" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="esqueleto h-[132px] rounded-md" />
        ))}
      </div>
    );
  }

  if (cartoes.length === 0) {
    return (
      <div
        className={cn(
          'flex h-11 w-full items-center gap-2 rounded-md border border-line-default bg-surface-card px-4',
          'text-fg-secondary',
        )}
      >
        <ShieldCheck size={16} strokeWidth={2} aria-hidden="true" className="text-risk-a" />
        <p className="text-[13px]/[20px]">
          Nenhuma ocorrência crítica na carteira nas últimas 24h. Última varredura:{' '}
          <span className="tnum">{formatarDataHora(ultimaVarredura)}</span>.
        </p>
      </div>
    );
  }

  return (
    <section aria-label="Atenção imediata" className="grid gap-4 md:grid-cols-3">
      {cartoes.slice(0, 3).map((cartao) => (
        <CartaoDeAtencaoImediata key={`${cartao.motivo}-${cartao.clienteId}`} cartao={cartao} />
      ))}
    </section>
  );
}

function CartaoDeAtencaoImediata({ cartao }: { cartao: CartaoDeAtencao }) {
  const apresentacao = SEVERIDADE[cartao.severidade];
  const familia = apresentacao.familia;
  const classes = CLASSES_RISCO[familia];
  const { Icone, ancora } = MOTIVO[cartao.motivo];
  const destino = `/clientes/${encodeURIComponent(cartao.clienteId)}${ancora}`;

  return (
    <Card
      densidade="compacta"
      destaque={familia}
      className="flex min-h-[132px] flex-col justify-between gap-2"
    >
      <div className="flex flex-col gap-1.5">
        <span className={cn('type-eyebrow inline-flex items-center gap-1.5', classes.texto)}>
          <Icone size={14} strokeWidth={2} aria-hidden="true" />
          {cartao.eyebrow}
        </span>
        <p className="type-body-strong truncate" title={cartao.razaoSocial}>
          {cartao.razaoSocial}
        </p>
        <p className="type-caption line-clamp-2">{cartao.causa}</p>
        <p className={cn('tnum text-[13px]/[20px] font-medium', classes.texto)}>{cartao.numero}</p>
      </div>

      <Link
        href={destino}
        className="transicao-controle inline-flex w-fit items-center gap-1 rounded-sm text-[12px]/[16px] font-medium text-accent-400 hover:text-accent-300"
      >
        {cartao.acao}
        <span aria-hidden="true">→</span>
      </Link>
    </Card>
  );
}
