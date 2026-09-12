'use client';

import { useState, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

import { formatarData, formatarDelta, formatarScore } from '@/lib/format';
import { Badge } from './Badge';
import { Button } from './Button';
import { cn } from './cn';
import { EmptyState } from './EmptyState';
import { CLASSES_RISCO, SEVERIDADE } from './risco';
import type { FonteId, Severidade } from './tipos-ui';

export interface ItemTimeline {
  id: string;
  /** ISO. */
  data: string;
  titulo: string;
  descricao?: string;
  /** Colore o marcador; ausente = neutro. */
  severidade?: Severidade;
  fonte?: FonteId;
  deltaScore?: number;
  scoreApos?: number;
  icone?: LucideIcon;
  evidenciaIds?: string[];
  /** Evento registrado nesta sessão (D10). */
  destaque?: boolean;
}

export interface TimelineProps {
  /** O componente ordena decrescente por data. */
  itens: ItemTimeline[];
  /** Eyebrow "SET 2026" separando grupos. Padrão true. */
  agruparPorMes?: boolean;
  aoSelecionarEvidencia?: (id: string) => void;
  /** Colapsa além de N com botão "Mostrar mais (12)". */
  limite?: number;
  vazio?: ReactNode;
  className?: string;
}

/** "SET 2026" a partir de um ISO, sem inventar formatador novo. */
function chaveDoMes(iso: string): string {
  const partes = formatarData(iso, 'media').split(' ');
  return `${partes[1] ?? ''} ${partes[2] ?? ''}`.trim().toUpperCase();
}

/**
 * Linha do tempo do cliente (spec §6.14): trilho vertical, marcador colorido
 * por severidade, data em coluna fixa de 88px.
 */
export function Timeline({
  itens,
  agruparPorMes = true,
  aoSelecionarEvidencia,
  limite,
  vazio,
  className,
}: TimelineProps) {
  const [expandido, setExpandido] = useState(false);

  const ordenados = [...itens].sort((a, b) => (a.data < b.data ? 1 : a.data > b.data ? -1 : 0));
  const visiveis = limite && !expandido ? ordenados.slice(0, limite) : ordenados;
  const restantes = ordenados.length - visiveis.length;

  if (ordenados.length === 0) {
    return <>{vazio ?? <EmptyState compacto titulo="Nenhum evento no período" />}</>;
  }

  // O cabeçalho de mês é decidido antes da renderização, comparando com o item
  // anterior por índice — sem variável reatribuída dentro do map.
  const meses = visiveis.map((item) => chaveDoMes(item.data));
  const comGrupo = visiveis.map((item, indice) => ({
    item,
    mes: meses[indice],
    novoMes: agruparPorMes && (indice === 0 || meses[indice - 1] !== meses[indice]),
  }));

  return (
    <div className={cn('flex flex-col', className)}>
      <ol className="relative flex flex-col">
        {comGrupo.map(({ item, mes, novoMes }) => {
          const apresentacao = item.severidade ? SEVERIDADE[item.severidade] : null;
          const classes = CLASSES_RISCO[apresentacao?.familia ?? 'neutral'];
          const critica = item.severidade === 'CRITICA';
          const Icone = item.icone;

          return (
            <li key={item.id} className="timeline-item flex flex-col">
              {novoMes ? <p className="type-eyebrow mt-3 mb-1 pl-[104px]">{mes}</p> : null}

              <div className="relative flex gap-3 py-2">
                <span className="type-caption tnum w-[88px] shrink-0 pt-0.5">
                  {formatarData(item.data, 'curta')}
                </span>

                {/* Trilho + marcador */}
                <span
                  aria-hidden="true"
                  className="absolute top-0 bottom-0 left-[96px] w-px bg-line-default"
                />
                <span
                  aria-hidden="true"
                  className={cn(
                    'absolute top-3 left-[92px] size-[10px] rounded-[5px] border-2',
                    classes.bordaLinha,
                    critica ? classes.fundoSolido : 'bg-surface-card',
                  )}
                  style={{ borderColor: classes.varCor }}
                />

                <div className="min-w-0 flex-1 pl-4">
                  <div className="flex flex-wrap items-center gap-2">
                    {Icone ? (
                      <Icone
                        size={14}
                        strokeWidth={2}
                        className={cn('shrink-0', classes.texto)}
                        aria-hidden="true"
                      />
                    ) : null}
                    <span className="type-body-strong">{item.titulo}</span>
                    {item.severidade ? (
                      <Badge variante="severidade" severidade={item.severidade} tamanho="sm" />
                    ) : null}
                    {item.fonte ? <Badge variante="fonte" fonte={item.fonte} tamanho="sm" /> : null}
                    {item.destaque ? (
                      <Badge variante="acento" tamanho="sm">
                        registrado agora
                      </Badge>
                    ) : null}
                  </div>

                  {item.descricao ? (
                    <p className="type-caption mt-0.5 text-fg-secondary">{item.descricao}</p>
                  ) : null}

                  {item.deltaScore !== undefined || item.scoreApos !== undefined ? (
                    <p className="type-caption tnum mt-0.5">
                      {item.deltaScore !== undefined ? (
                        <span
                          className={cn(
                            'font-medium',
                            item.deltaScore < 0
                              ? CLASSES_RISCO.d.texto
                              : item.deltaScore > 0
                                ? CLASSES_RISCO.a.texto
                                : CLASSES_RISCO.neutral.texto,
                          )}
                        >
                          {formatarDelta(item.deltaScore, 'pts')}
                        </span>
                      ) : null}
                      {item.scoreApos !== undefined
                        ? `${item.deltaScore !== undefined ? ' · ' : ''}score ${formatarScore(item.scoreApos)}`
                        : ''}
                    </p>
                  ) : null}

                  {item.evidenciaIds && item.evidenciaIds.length > 0 && aoSelecionarEvidencia ? (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {item.evidenciaIds.map((evidenciaId) => (
                        <button
                          key={evidenciaId}
                          type="button"
                          onClick={() => aoSelecionarEvidencia(evidenciaId)}
                          className="transicao-controle type-caption rounded-sm text-accent-400 underline underline-offset-2 hover:text-accent-300"
                        >
                          Ver evidência
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      {restantes > 0 ? (
        <div className="mt-2 pl-[104px]">
          <Button tamanho="sm" variante="fantasma" onClick={() => setExpandido(true)}>
            {`Mostrar mais (${restantes})`}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
