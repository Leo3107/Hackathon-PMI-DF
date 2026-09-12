'use client';

/**
 * Faixa de atenção imediata da carteira (`03-ux-e-telas.md` §2.2).
 *
 * A **seleção** dos até três clientes é do motor (`ResumoCarteira.atencaoImediata`), não da
 * tela: a regra de desempate é determinística e está na spec 02. Aqui só se apresenta.
 *
 * Forma: **lista densa com hierarquia real**, não três cartões iguais. A ocorrência mais grave
 * — a primeira, já ordenada pelo motor — ocupa a linha superior com tipografia maior; as
 * demais descem como linhas compactas separadas por régua de 1px. Nenhuma caixa: a régua e o
 * filete de severidade bastam para separar.
 *
 * R2 (I8): cada linha comunica o motivo por **filete semântico + ícone + rótulo textual**,
 * nunca só por cor.
 */

import { Gavel, ShieldCheck, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';

import { CLASSES_RISCO, SEVERIDADE, cn } from '@/components/ui';
import { formatarDataHora, formatarNumero } from '@/lib/format';
import type { CartaoDeAtencao, MotivoAtencao } from '@/types';

/**
 * Ícone, rótulo e destino por motivo.
 *
 * O rótulo é escrito aqui, em caixa normal e acentuado, porque o campo `eyebrow` do motor vem
 * em caixa alta (`ALERTA CRITICA`) — versalete de faixa larga acima de cada bloco é exatamente
 * o ruído que esta tela deixou de ter. O texto do motor continua no `aria-label` e no `title`.
 */
const MOTIVO: Record<MotivoAtencao, { Icone: LucideIcon; rotulo: string; ancora: string }> = {
  VETO_ATIVO: { Icone: Gavel, rotulo: 'Veto ativo', ancora: '' },
  MAIOR_QUEDA_90D: { Icone: TrendingDown, rotulo: 'Maior queda em 90 dias', ancora: '#o-que-mudou' },
  ALERTA_CRITICO: { Icone: SEVERIDADE.CRITICA.Icone, rotulo: 'Alerta crítico', ancora: '#red-flags' },
};

export interface FaixaDeAtencaoProps {
  cartoes: CartaoDeAtencao[];
  /** ISO datetime — exibido sempre, e é a única informação quando não há ocorrência. */
  ultimaVarredura: string;
  carregando?: boolean;
}

export function FaixaDeAtencao({ cartoes, ultimaVarredura, carregando }: FaixaDeAtencaoProps) {
  if (carregando) {
    return (
      <div className="flex flex-col gap-2" aria-hidden="true">
        <div className="esqueleto h-5 w-48" />
        <div className="esqueleto h-[76px] w-full" />
        <div className="esqueleto h-12 w-full" />
        <div className="esqueleto h-12 w-full" />
      </div>
    );
  }

  if (cartoes.length === 0) {
    return (
      <section aria-label="Atenção imediata" className="flex items-center gap-2 border-y border-line-subtle py-2.5 text-fg-secondary">
        <ShieldCheck size={15} strokeWidth={2} aria-hidden="true" className="shrink-0 text-risk-a" />
        <p className="text-[13px]/[20px]">
          Nenhuma ocorrência crítica na carteira nas últimas 24h. Última varredura:{' '}
          <span className="tnum">{formatarDataHora(ultimaVarredura)}</span>.
        </p>
      </section>
    );
  }

  const visiveis = cartoes.slice(0, 3);

  return (
    <section aria-label="Atenção imediata" className="flex flex-col">
      <header className="flex items-baseline justify-between gap-4 border-b border-line-default pb-2">
        <h2 className="type-section-title">Atenção imediata</h2>
        <p className="type-caption tnum">
          {formatarNumero(visiveis.length)}{' '}
          {visiveis.length === 1 ? 'ocorrência' : 'ocorrências'} · varredura de{' '}
          {formatarDataHora(ultimaVarredura)}
        </p>
      </header>

      <ul className="flex flex-col">
        {visiveis.map((cartao, indice) => (
          <LinhaDeAtencao
            key={`${cartao.motivo}-${cartao.clienteId}`}
            cartao={cartao}
            principal={indice === 0}
          />
        ))}
      </ul>
    </section>
  );
}

function LinhaDeAtencao({ cartao, principal }: { cartao: CartaoDeAtencao; principal: boolean }) {
  const classes = CLASSES_RISCO[SEVERIDADE[cartao.severidade].familia];
  const { Icone, rotulo, ancora } = MOTIVO[cartao.motivo];
  const destino = `/clientes/${encodeURIComponent(cartao.clienteId)}${ancora}`;

  return (
    <li
      className={cn(
        'grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-6 border-b border-line-subtle border-l-2 pl-3',
        classes.bordaEsquerda,
        principal ? 'py-3' : 'py-2.5',
      )}
    >
      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="flex min-w-0 items-center gap-2">
          <Icone
            size={principal ? 15 : 13}
            strokeWidth={2}
            aria-hidden="true"
            className={cn('shrink-0', classes.texto)}
          />
          <span
            className={cn(
              'shrink-0 font-medium',
              classes.texto,
              principal ? 'text-[13px]/[20px]' : 'text-[12px]/[18px]',
            )}
            title={cartao.eyebrow}
          >
            {rotulo}
          </span>
          <span aria-hidden="true" className="shrink-0 text-line-strong">
            ·
          </span>
          <p
            className={cn(
              'truncate',
              principal ? 'text-[16px]/[22px] font-semibold' : 'text-[13px]/[18px] font-medium',
            )}
            title={cartao.razaoSocial}
          >
            {cartao.razaoSocial}
          </p>
        </div>

        <p
          className={cn(
            principal ? 'text-[13px]/[18px] text-fg-secondary' : 'type-caption',
          )}
          title={cartao.causa}
        >
          {cartao.causa}
        </p>

        <p
          className={cn(
            'tnum',
            classes.texto,
            principal ? 'text-[14px]/[20px] font-medium' : 'text-[12px]/[18px]',
          )}
          title={cartao.numero}
        >
          {cartao.numero}
        </p>
      </div>

      <Link
        href={destino}
        aria-label={`${cartao.acao} — ${cartao.razaoSocial}`}
        title={cartao.acao}
        className={cn(
          'transicao-controle max-w-[30ch] shrink-0 rounded-sm text-right font-medium text-accent-400 hover:text-accent-300',
          principal ? 'text-[13px]/[20px]' : 'text-[12px]/[18px]',
        )}
      >
        {cartao.acao} <span aria-hidden="true">&#8594;</span>
      </Link>
    </li>
  );
}
