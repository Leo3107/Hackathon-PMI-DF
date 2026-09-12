'use client';

import { Sigma, TriangleAlert } from 'lucide-react';
import { useState } from 'react';

import { formatarDelta } from '@/lib/format';
import { Button } from './Button';
import { cn } from './cn';
import { CLASSES_RISCO } from './risco';
import { NOME_DIMENSAO, type FatorExibido } from './tipos-ui';

export interface FactorBarProps {
  fatores: FatorExibido[];
  /** Muda o cabeçalho e o tratamento do zero. */
  modo: 'contribuicao' | 'delta';
  /** Padrão: `max(|impacto|)` arredondado para cima em múltiplo de 10. */
  escalaMaxima?: number;
  /** Exibe os N maiores por `|impacto|`, com botão "Mostrar todos (23)". */
  limite?: number;
  aoSelecionar?: (fatorId: string) => void;
  selecionado?: string | null;
  mostrarDimensao?: boolean;
  /** Renderiza o rodapé de conferência "Σ = −108 · fecha com score" (I2/I6). */
  somaEsperada?: number;
  className?: string;
}

function escalaPadrao(fatores: FatorExibido[]): number {
  const maximo = fatores.reduce((acumulado, fator) => Math.max(acumulado, Math.abs(fator.impacto)), 0);
  return Math.max(10, Math.ceil(maximo / 10) * 10);
}

/**
 * Barra divergente de fatores (spec §6.19). Eixo zero central; impacto negativo
 * cresce para a esquerda em `risk-d`, positivo para a direita em `risk-a`.
 *
 * O uso de verde/vermelho aqui é semântico — proteção contra risco — e é o
 * único caso em que a cor de risco descreve um fator e não um cliente.
 */
export function FactorBar({
  fatores,
  modo,
  escalaMaxima,
  limite,
  aoSelecionar,
  selecionado,
  mostrarDimensao = false,
  somaEsperada,
  className,
}: FactorBarProps) {
  const [expandido, setExpandido] = useState(false);

  const ordenados = [...fatores].sort((a, b) => Math.abs(b.impacto) - Math.abs(a.impacto));
  const visiveis = limite && !expandido ? ordenados.slice(0, limite) : ordenados;
  const restantes = ordenados.length - visiveis.length;
  const escala = escalaMaxima ?? escalaPadrao(ordenados);

  const soma = ordenados.reduce((acumulado, fator) => acumulado + fator.impacto, 0);
  const fecha = somaEsperada === undefined || Math.abs(soma - somaEsperada) <= 0.5;

  return (
    <div className={cn('flex w-full flex-col gap-1', className)}>
      <div className="flex items-center justify-between gap-2 pb-1">
        <span className="type-label">Fator</span>
        <span className="type-label">
          {modo === 'contribuicao' ? 'Impacto no score' : 'Variação no período'}
        </span>
      </div>

      <ul className="flex flex-col">
        {visiveis.map((fator) => {
          const negativo = fator.impacto < 0;
          const classes = negativo
            ? CLASSES_RISCO.d
            : fator.impacto > 0
              ? CLASSES_RISCO.a
              : CLASSES_RISCO.neutral;
          const largura = (Math.min(Math.abs(fator.impacto), escala) / escala) * 50;
          const ativo = selecionado === fator.id;
          const Tag = aoSelecionar ? 'button' : 'div';

          return (
            <li key={fator.id}>
              <Tag
                {...(aoSelecionar
                  ? { type: 'button' as const, onClick: () => aoSelecionar(fator.id) }
                  : {})}
                aria-pressed={aoSelecionar ? ativo : undefined}
                className={cn(
                  'flex h-7 w-full items-center gap-3 rounded-sm text-left',
                  aoSelecionar && 'transicao-controle hover:bg-surface-hover',
                )}
              >
                <span className="flex w-[40%] min-w-0 flex-col justify-center">
                  <span className="flex min-w-0 items-baseline gap-1.5">
                    {mostrarDimensao && fator.dimensao ? (
                      <span className="type-eyebrow shrink-0">{NOME_DIMENSAO[fator.dimensao]}</span>
                    ) : null}
                    <span className="type-body truncate" title={fator.rotulo}>
                      {fator.rotulo}
                    </span>
                  </span>
                  {fator.detalhe ? (
                    <span className="type-caption truncate" title={fator.detalhe}>
                      {fator.detalhe}
                    </span>
                  ) : null}
                </span>

                <span className="relative h-full w-[60%]">
                  <span
                    aria-hidden="true"
                    className="absolute top-0 bottom-0 left-1/2 w-px bg-line-strong"
                  />
                  <span
                    className={cn(
                      'absolute top-1/2 h-2 -translate-y-1/2 rounded-xs',
                      classes.fundoSolido,
                      ativo && 'outline outline-1 outline-offset-0 outline-fg-primary',
                    )}
                    style={
                      negativo
                        ? { right: '50%', width: `${largura}%` }
                        : { left: '50%', width: `${largura}%` }
                    }
                  />
                  <span
                    className={cn(
                      'tnum absolute top-1/2 -translate-y-1/2 text-[12px]/[16px] font-medium',
                      classes.texto,
                    )}
                    style={
                      negativo
                        ? { right: `calc(50% + ${largura}% + 6px)` }
                        : { left: `calc(50% + ${largura}% + 6px)` }
                    }
                  >
                    {formatarDelta(fator.impacto)}
                  </span>
                </span>
              </Tag>
            </li>
          );
        })}
      </ul>

      {restantes > 0 ? (
        <div>
          <Button tamanho="sm" variante="fantasma" onClick={() => setExpandido(true)}>
            {`Mostrar todos (${ordenados.length})`}
          </Button>
        </div>
      ) : null}

      {somaEsperada === undefined ? null : (
        <p
          className={cn(
            'type-label tnum mt-1 inline-flex items-center gap-1.5 border-t border-line-subtle pt-2',
            fecha ? '' : 'text-fg-primary',
          )}
        >
          {fecha ? (
            <Sigma size={14} strokeWidth={2} aria-hidden="true" />
          ) : (
            <TriangleAlert size={14} strokeWidth={2} aria-hidden="true" />
          )}
          {`Σ = ${formatarDelta(Math.round(soma))} · ${fecha ? 'fecha com o score' : 'não fecha'}`}
        </p>
      )}
    </div>
  );
}
