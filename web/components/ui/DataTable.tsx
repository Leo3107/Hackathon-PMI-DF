'use client';

import { ArrowDown, ArrowUp, ArrowUpDown, Check, Info, Minus } from 'lucide-react';
import { useMemo, useRef, useState, type ReactNode } from 'react';

import { cn } from './cn';
import { EmptyState } from './EmptyState';
import type { TermoGlossario } from './glossario';
import { CLASSES_RISCO } from './risco';
import type { FamiliaRisco } from './tipos-ui';
import { Tooltip } from './Tooltip';

export interface Coluna<T> {
  id: string;
  cabecalho: string;
  celula: (linha: T) => ReactNode;
  alinhamento?: 'esquerda' | 'direita' | 'centro';
  /** Aplica `type-num` + `tnum` + alinhamento à direita. */
  numerica?: boolean;
  largura?: number | string;
  minLargura?: number;
  ordenavel?: boolean;
  /** Obrigatório quando `ordenavel` e a célula não é primitiva. */
  valorOrdenacao?: (linha: T) => number | string | null;
  fixa?: 'esquerda';
  termo?: TermoGlossario;
  /** Responsividade por corte de coluna, nunca por quebra de linha. */
  ocultarAbaixoDe?: 1280 | 1440;
}

export interface Ordenacao {
  colunaId: string;
  direcao: 'asc' | 'desc';
}

export interface SelecaoTabela {
  modo: 'unica' | 'multipla';
  selecionados: ReadonlySet<string>;
  aoMudar: (ids: Set<string>) => void;
}

export interface DataTableProps<T> {
  colunas: Coluna<T>[];
  linhas: T[];
  obterId: (linha: T) => string;
  densidade?: 'densa' | 'confortavel';
  /** Controlado. */
  ordenacao?: Ordenacao;
  /** Não controlado. */
  ordenacaoInicial?: Ordenacao;
  aoOrdenar?: (ordenacao: Ordenacao | null) => void;
  selecao?: SelecaoTabela;
  /** Realce persistente (ex.: cliente aberto no drawer). */
  linhaAtiva?: string | null;
  aoClicarLinha?: (linha: T) => void;
  /** Borda esquerda 2px na cor (ex.: rating D). */
  familiaLinha?: (linha: T) => FamiliaRisco | null;
  carregando?: boolean;
  linhasEsqueleto?: number;
  vazio?: ReactNode;
  cabecalhoFixo?: boolean;
  alturaMaxima?: number | string;
  /** Linha de totais. */
  rodape?: ReactNode;
  className?: string;
  'aria-label': string;
}

const OCULTAR: Record<1280 | 1440, string> = {
  1280: 'max-[1280px]:hidden',
  1440: 'max-[1440px]:hidden',
};

const LARGURAS_ESQUELETO = ['70%', '45%', '85%'];

function alinhamentoClasse<T>(coluna: Coluna<T>): string {
  if (coluna.numerica || coluna.alinhamento === 'direita') return 'text-right';
  if (coluna.alinhamento === 'centro') return 'text-center';
  return 'text-left';
}

function comparar(a: number | string | null, b: number | string | null): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), 'pt-BR', {
    numeric: true,
    sensitivity: 'base',
  });
}

interface CaixaProps {
  marcado: boolean;
  indeterminado?: boolean;
  rotulo: string;
  aoMudar: () => void;
}

/** Checkbox autoral: 16px, raio 2px, marcado em `accent-500`. */
function Caixa({ marcado, indeterminado = false, rotulo, aoMudar }: CaixaProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={indeterminado ? 'mixed' : marcado}
      aria-label={rotulo}
      onClick={(evento) => {
        evento.stopPropagation();
        aoMudar();
      }}
      className={cn(
        'transicao-controle inline-flex size-4 items-center justify-center rounded-xs border',
        marcado || indeterminado
          ? 'border-accent-500 bg-accent-500 text-fg-inverse'
          : 'border-line-strong bg-surface-input',
      )}
    >
      {indeterminado ? (
        <Minus size={12} strokeWidth={3} aria-hidden="true" />
      ) : marcado ? (
        <Check size={12} strokeWidth={3} aria-hidden="true" />
      ) : null}
    </button>
  );
}

/**
 * Tabela do produto (spec §6.8). Sem zebra, sem paginação.
 *
 * Teclado: as linhas clicáveis formam um anel de foco navegável por
 * `ArrowUp`/`ArrowDown`/`Home`/`End`; `Enter` e `Espaço` ativam. O cabeçalho
 * ordenável é um `<button>` com `aria-sort` no `<th>`.
 */
export function DataTable<T>({
  colunas,
  linhas,
  obterId,
  densidade = 'densa',
  ordenacao,
  ordenacaoInicial,
  aoOrdenar,
  selecao,
  linhaAtiva,
  aoClicarLinha,
  familiaLinha,
  carregando = false,
  linhasEsqueleto = 8,
  vazio,
  cabecalhoFixo = false,
  alturaMaxima,
  rodape,
  className,
  'aria-label': ariaLabel,
}: DataTableProps<T>) {
  const [ordenacaoInterna, setOrdenacaoInterna] = useState<Ordenacao | null>(
    ordenacaoInicial ?? null,
  );
  const corpo = useRef<HTMLTableSectionElement>(null);

  const ordenacaoEfetiva = ordenacao ?? ordenacaoInterna;

  const linhasOrdenadas = useMemo(() => {
    if (!ordenacaoEfetiva) return linhas;
    const coluna = colunas.find((c) => c.id === ordenacaoEfetiva.colunaId);
    if (!coluna) return linhas;
    const extrair =
      coluna.valorOrdenacao ??
      ((linha: T) => {
        const valor = (linha as Record<string, unknown>)[coluna.id];
        return typeof valor === 'number' || typeof valor === 'string' ? valor : null;
      });
    const fator = ordenacaoEfetiva.direcao === 'asc' ? 1 : -1;
    return [...linhas].sort((a, b) => fator * comparar(extrair(a), extrair(b)));
  }, [linhas, colunas, ordenacaoEfetiva]);

  function alternarOrdenacao(colunaId: string) {
    const atual = ordenacaoEfetiva;
    let proxima: Ordenacao | null;
    if (!atual || atual.colunaId !== colunaId) proxima = { colunaId, direcao: 'asc' };
    else if (atual.direcao === 'asc') proxima = { colunaId, direcao: 'desc' };
    else proxima = null;
    if (!ordenacao) setOrdenacaoInterna(proxima);
    aoOrdenar?.(proxima);
  }

  function alternarSelecao(id: string) {
    if (!selecao) return;
    if (selecao.modo === 'unica') {
      selecao.aoMudar(selecao.selecionados.has(id) ? new Set() : new Set([id]));
      return;
    }
    const proximos = new Set(selecao.selecionados);
    if (proximos.has(id)) proximos.delete(id);
    else proximos.add(id);
    selecao.aoMudar(proximos);
  }

  function navegar(evento: React.KeyboardEvent<HTMLTableRowElement>, linha: T) {
    if (!aoClicarLinha) return;
    const { key } = evento;
    if (key === 'Enter' || key === ' ') {
      evento.preventDefault();
      aoClicarLinha(linha);
      return;
    }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(key)) return;
    evento.preventDefault();
    const focaveis = Array.from(
      corpo.current?.querySelectorAll<HTMLTableRowElement>('tr[tabindex="0"]') ?? [],
    );
    const indice = focaveis.indexOf(evento.currentTarget);
    const destino =
      key === 'ArrowDown'
        ? Math.min(focaveis.length - 1, indice + 1)
        : key === 'ArrowUp'
          ? Math.max(0, indice - 1)
          : key === 'Home'
            ? 0
            : focaveis.length - 1;
    focaveis[destino]?.focus();
  }

  const alturaLinha =
    densidade === 'densa' ? 'h-[var(--height-row-dense)]' : 'h-[var(--height-row-comfortable)]';
  const padCelula = densidade === 'densa' ? 'px-3' : 'px-4';
  const totalColunas = colunas.length + (selecao?.modo === 'multipla' ? 1 : 0);

  const cabecalho = (
    <thead
      className={cn(
        'bg-surface-card',
        cabecalhoFixo && 'sticky top-0 z-10',
      )}
    >
      <tr className="h-[var(--height-table-header)] border-b border-line-strong">
        {selecao?.modo === 'multipla' ? (
          <th scope="col" className={cn('w-10', padCelula)}>
            <Caixa
              rotulo="Selecionar todas as linhas"
              marcado={
                linhasOrdenadas.length > 0 &&
                linhasOrdenadas.every((linha) => selecao.selecionados.has(obterId(linha)))
              }
              indeterminado={
                selecao.selecionados.size > 0 &&
                !linhasOrdenadas.every((linha) => selecao.selecionados.has(obterId(linha)))
              }
              aoMudar={() => {
                const todos = linhasOrdenadas.every((linha) =>
                  selecao.selecionados.has(obterId(linha)),
                );
                selecao.aoMudar(todos ? new Set() : new Set(linhasOrdenadas.map(obterId)));
              }}
            />
          </th>
        ) : null}

        {colunas.map((coluna) => {
          const ativa = ordenacaoEfetiva?.colunaId === coluna.id;
          const Icone = !ativa
            ? ArrowUpDown
            : ordenacaoEfetiva?.direcao === 'asc'
              ? ArrowUp
              : ArrowDown;
          return (
            <th
              key={coluna.id}
              scope="col"
              aria-sort={
                ativa
                  ? ordenacaoEfetiva?.direcao === 'asc'
                    ? 'ascending'
                    : 'descending'
                  : coluna.ordenavel
                    ? 'none'
                    : undefined
              }
              className={cn(
                'type-table-header whitespace-nowrap',
                padCelula,
                alinhamentoClasse(coluna),
                coluna.fixa === 'esquerda' &&
                  'sticky left-0 z-20 border-r border-line-default bg-surface-card',
                coluna.ocultarAbaixoDe && OCULTAR[coluna.ocultarAbaixoDe],
              )}
              style={{
                width: typeof coluna.largura === 'number' ? `${coluna.largura}px` : coluna.largura,
                minWidth: coluna.minLargura ? `${coluna.minLargura}px` : undefined,
              }}
            >
              <span
                className={cn(
                  'inline-flex items-center gap-1',
                  coluna.numerica || coluna.alinhamento === 'direita'
                    ? 'flex-row-reverse'
                    : 'flex-row',
                )}
              >
                {coluna.ordenavel ? (
                  <button
                    type="button"
                    onClick={() => alternarOrdenacao(coluna.id)}
                    className={cn(
                      'transicao-controle group inline-flex items-center gap-1 rounded-sm uppercase',
                      'hover:text-fg-primary',
                    )}
                  >
                    <span>{coluna.cabecalho}</span>
                    <Icone
                      size={12}
                      strokeWidth={2}
                      aria-hidden="true"
                      className={cn(
                        ativa ? 'text-accent-400' : 'text-fg-tertiary opacity-0 group-hover:opacity-100',
                      )}
                    />
                  </button>
                ) : (
                  <span>{coluna.cabecalho}</span>
                )}
                {coluna.termo ? (
                  <Tooltip termo={coluna.termo}>
                    <span
                      tabIndex={0}
                      role="note"
                      aria-label={`O que é ${coluna.cabecalho}`}
                      className="transicao-controle inline-flex rounded-sm text-fg-tertiary hover:text-fg-secondary"
                    >
                      <Info size={14} strokeWidth={2} aria-hidden="true" />
                    </span>
                  </Tooltip>
                ) : null}
              </span>
            </th>
          );
        })}
      </tr>
    </thead>
  );

  return (
    <div
      className={cn('w-full', alturaMaxima ? 'overflow-auto scrollbar-thin' : 'overflow-x-auto', className)}
      style={{
        maxHeight: typeof alturaMaxima === 'number' ? `${alturaMaxima}px` : alturaMaxima,
      }}
    >
      <table className="w-full border-collapse text-[13px]" aria-label={ariaLabel}>
        {cabecalho}

        <tbody ref={corpo}>
          {carregando
            ? Array.from({ length: linhasEsqueleto }).map((_, indiceLinha) => (
                <tr
                  key={`esqueleto-${indiceLinha}`}
                  className={cn('border-b border-line-subtle', alturaLinha)}
                >
                  {Array.from({ length: totalColunas }).map((__, indiceCelula) => (
                    <td key={indiceCelula} className={padCelula}>
                      <span
                        className="esqueleto block h-3"
                        style={{
                          width:
                            LARGURAS_ESQUELETO[(indiceLinha + indiceCelula) % LARGURAS_ESQUELETO.length],
                        }}
                        aria-hidden="true"
                      />
                    </td>
                  ))}
                </tr>
              ))
            : linhasOrdenadas.map((linha) => {
                const id = obterId(linha);
                const selecionada = selecao?.selecionados.has(id) ?? false;
                const ativa = linhaAtiva === id;
                const familia = familiaLinha?.(linha) ?? null;

                return (
                  <tr
                    key={id}
                    tabIndex={aoClicarLinha ? 0 : undefined}
                    role={aoClicarLinha ? 'button' : undefined}
                    aria-selected={selecao ? selecionada : undefined}
                    onClick={aoClicarLinha ? () => aoClicarLinha(linha) : undefined}
                    onKeyDown={(evento) => navegar(evento, linha)}
                    className={cn(
                      'transicao-controle border-b border-line-subtle',
                      alturaLinha,
                      aoClicarLinha && 'cursor-pointer',
                      ativa || selecionada
                        ? 'border-l-2 border-l-accent-400 bg-accent-tint'
                        : familia
                          ? cn('border-l-2', CLASSES_RISCO[familia].bordaEsquerda)
                          : 'border-l-2 border-l-transparent',
                      'hover:bg-surface-hover',
                    )}
                  >
                    {selecao?.modo === 'multipla' ? (
                      <td className={padCelula}>
                        <Caixa
                          rotulo={`Selecionar ${id}`}
                          marcado={selecionada}
                          aoMudar={() => alternarSelecao(id)}
                        />
                      </td>
                    ) : null}

                    {colunas.map((coluna) => (
                      <td
                        key={coluna.id}
                        className={cn(
                          padCelula,
                          alinhamentoClasse(coluna),
                          coluna.numerica && 'type-num tnum',
                          coluna.fixa === 'esquerda' &&
                            'sticky left-0 z-10 border-r border-line-default bg-surface-card',
                          coluna.ocultarAbaixoDe && OCULTAR[coluna.ocultarAbaixoDe],
                        )}
                      >
                        {coluna.celula(linha)}
                      </td>
                    ))}
                  </tr>
                );
              })}

          {!carregando && linhasOrdenadas.length === 0 ? (
            <tr>
              <td colSpan={totalColunas}>
                {vazio ?? <EmptyState compacto titulo="Nenhum registro" />}
              </td>
            </tr>
          ) : null}
        </tbody>

        {rodape ? (
          <tfoot>
            <tr className="tnum border-t border-line-strong font-semibold">
              <td colSpan={totalColunas} className={cn(padCelula, 'py-2')}>
                {rodape}
              </td>
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
