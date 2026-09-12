'use client';

import { ChevronDown, ChevronUp, Link2Off } from 'lucide-react';

import { formatarData, formatarDelta } from '@/lib/format';
import { Badge } from './Badge';
import { Card } from './Card';
import { cn } from './cn';
import { CLASSES_RISCO, ICONE_EVIDENCIA } from './risco';
import type { Evidencia } from './tipos-ui';

export interface FatorRelacionado {
  id: string;
  rotulo: string;
  impacto: number;
}

export interface EvidenceCardProps {
  evidencia: Evidencia;
  /** Resolvidos pelo chamador. */
  fatoresRelacionados?: FatorRelacionado[];
  aoClicarFator?: (fatorId: string) => void;
  expandida?: boolean;
  aoAlternar?: () => void;
  className?: string;
}

/**
 * Cartão de evidência (spec §6.18). O selo `simulado` é **obrigatório** (D11.6)
 * e a URL fictícia nunca é clicável.
 */
export function EvidenceCard({
  evidencia,
  fatoresRelacionados,
  aoClicarFator,
  expandida = false,
  aoAlternar,
  className,
}: EvidenceCardProps) {
  const Icone = ICONE_EVIDENCIA[evidencia.tipo];

  return (
    <Card densidade="compacta" className={cn('evidence-card flex flex-col gap-2', className)}>
      <div className="flex items-start gap-2">
        <Icone size={16} strokeWidth={2} className="mt-0.5 shrink-0 text-fg-secondary" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="type-body-strong">{evidencia.titulo}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <Badge variante="fonte" fonte={evidencia.fonte} tamanho="sm" />
            <Badge variante="simulado" tamanho="sm" />
          </div>
        </div>
        {aoAlternar ? (
          <button
            type="button"
            aria-expanded={expandida}
            onClick={aoAlternar}
            aria-label={expandida ? 'Recolher evidência' : 'Expandir evidência'}
            className="transicao-controle inline-flex shrink-0 rounded-sm text-fg-tertiary hover:text-fg-primary"
          >
            {expandida ? (
              <ChevronUp size={16} strokeWidth={2} aria-hidden="true" />
            ) : (
              <ChevronDown size={16} strokeWidth={2} aria-hidden="true" />
            )}
          </button>
        ) : null}
      </div>

      <p className="type-caption tnum">
        {`Consulta em ${formatarData(evidencia.dataConsulta, 'curta')}`}
        {evidencia.dataDocumento
          ? ` · Documento de ${formatarData(evidencia.dataDocumento, 'curta')}`
          : ''}
      </p>

      <p className="type-body text-fg-secondary">{evidencia.resumo}</p>

      {expandida ? (
        <div className="flex flex-col gap-2 border-t border-line-subtle pt-2">
          {evidencia.urlFicticia ? (
            <p className="type-mono inline-flex items-center gap-1.5 break-all">
              <Link2Off size={14} strokeWidth={2} className="shrink-0" aria-hidden="true" />
              {evidencia.urlFicticia}
            </p>
          ) : null}

          {fatoresRelacionados && fatoresRelacionados.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {fatoresRelacionados.map((fator) => {
                const classes =
                  fator.impacto < 0
                    ? CLASSES_RISCO.d
                    : fator.impacto > 0
                      ? CLASSES_RISCO.a
                      : CLASSES_RISCO.neutral;
                return (
                  <button
                    key={fator.id}
                    type="button"
                    disabled={!aoClicarFator}
                    onClick={() => aoClicarFator?.(fator.id)}
                    className={cn(
                      'transicao-controle type-badge inline-flex h-6 items-center gap-1 rounded-sm border px-2 font-medium',
                      'border-line-default bg-transparent text-fg-secondary',
                      aoClicarFator && 'hover:border-line-strong hover:text-fg-primary',
                    )}
                  >
                    <span>{fator.rotulo}</span>
                    <span className={cn('tnum', classes.texto)}>{formatarDelta(fator.impacto)}</span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
