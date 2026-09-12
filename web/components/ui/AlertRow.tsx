'use client';

import { ArrowRight, ChevronRight } from 'lucide-react';

import { formatarData, formatarDataRelativa } from '@/lib/format';
import { Badge } from './Badge';
import { cn } from './cn';
import { SEVERIDADE } from './risco';
import type { Alerta } from './tipos-ui';

export interface AlertRowProps {
  alerta: Alerta;
  aoAbrirCliente: (clienteId: string) => void;
  aoMarcarLido?: (id: string) => void;
  /** Dropdown da topbar. */
  compacto?: boolean;
  selecionado?: boolean;
  /**
   * Data de referência para a data relativa. Os formatadores são puros e
   * jamais leem o relógio do sistema (spec §11); sem referência, a data é
   * exibida em formato absoluto.
   */
  referencia?: string;
  className?: string;
}

/**
 * Linha da central de alertas (spec §6.17). A linha inteira é clicável.
 * Severidade CRÍTICA usa badge sólido; as demais, `tint`.
 */
export function AlertRow({
  alerta,
  aoAbrirCliente,
  aoMarcarLido,
  compacto = false,
  selecionado = false,
  referencia,
  className,
}: AlertRowProps) {
  const apresentacao = SEVERIDADE[alerta.severidade];
  const data = referencia
    ? formatarDataRelativa(alerta.data, referencia)
    : formatarData(alerta.data, 'curta');

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${apresentacao.rotulo}: ${alerta.titulo} — ${alerta.clienteNome}`}
      onClick={() => {
        aoMarcarLido?.(alerta.id);
        aoAbrirCliente(alerta.clienteId);
      }}
      onKeyDown={(evento) => {
        if (evento.key !== 'Enter' && evento.key !== ' ') return;
        evento.preventDefault();
        aoMarcarLido?.(alerta.id);
        aoAbrirCliente(alerta.clienteId);
      }}
      className={cn(
        'transicao-controle flex w-full cursor-pointer items-start gap-3 border-b border-line-subtle',
        compacto ? 'px-3 py-2' : 'min-h-14 px-4 py-3',
        alerta.lido ? 'border-l-2 border-l-transparent' : 'border-l-2 border-l-accent-400',
        selecionado ? 'bg-accent-tint' : 'hover:bg-surface-hover',
        className,
      )}
    >
      <Badge
        variante="severidade"
        severidade={alerta.severidade}
        tamanho="sm"
        aparencia={alerta.severidade === 'CRITICA' ? 'solido' : 'tint'}
        className="mt-0.5"
      />

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'type-body-strong truncate',
            alerta.lido ? 'text-fg-secondary' : 'text-fg-primary',
          )}
        >
          {alerta.titulo}
        </p>
        <p className="type-caption truncate text-fg-secondary">{alerta.clienteNome}</p>

        {compacto ? null : (
          <div className="mt-1 flex flex-col gap-0.5">
            <p className="type-caption">{alerta.impacto}</p>
            <p className="type-caption inline-flex items-center gap-1.5 text-fg-secondary">
              <ArrowRight size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" />
              {alerta.acaoRecomendada}
            </p>
          </div>
        )}
      </div>

      <span className="type-caption tnum shrink-0 whitespace-nowrap">{data}</span>
      <ChevronRight
        size={16}
        strokeWidth={2}
        className="mt-0.5 shrink-0 text-fg-tertiary"
        aria-hidden="true"
      />
    </div>
  );
}
