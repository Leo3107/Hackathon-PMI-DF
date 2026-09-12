'use client';

/**
 * Barras horizontais ranqueadas — a marca escolhida por V2, V3 e V4 (`03-ux-e-telas.md` §2.4).
 *
 * Não é um primitivo novo do design system: é a composição de tela de uma barra de comprimento
 * proporcional com rótulo textual e valor escrito ao lado. Comprimento é a codificação visual
 * mais precisa para comparar magnitudes — foi por isso que a pizza de rating e o treemap de
 * exposição foram recusados em §2.5.
 *
 * Cada linha é um `<button>`: o drill-down de §2.7 exige alvo clicável e navegável por teclado.
 */

import { cn } from '@/components/ui';

export interface ItemDeBarra {
  id: string;
  rotulo: string;
  /** Nó opcional à esquerda do rótulo (ex.: `RatingBadge`). */
  marcador?: React.ReactNode;
  valor: number;
  /** Texto já formatado pelo `lib/format.ts` — a tela nunca calcula (R6). */
  valorFormatado: string;
  /** Segunda informação à direita, ex.: `5 clientes`. */
  detalhe?: string;
  /** Cor da barra: `var(--color-…)`. */
  cor: string;
  /** Parcela interna em cor semântica (V4: quanto daquela UF está em risco). */
  parcela?: { valor: number; corSemantica: string; rotulo: string } | null;
  /** Marcador textual à direita do rótulo, ex.: risco climático alto na cultura. */
  anotacao?: { simbolo: string; texto: string } | null;
}

export interface ListaDeBarrasProps {
  itens: ItemDeBarra[];
  /** Maior valor da série; define a escala comum das barras. */
  maximo?: number;
  aoClicar?: (item: ItemDeBarra) => void;
  /** Rótulo do grupo para leitores de tela. */
  rotulo: string;
  className?: string;
}

export function ListaDeBarras({
  itens,
  maximo,
  aoClicar,
  rotulo,
  className,
}: ListaDeBarrasProps) {
  const escala = maximo ?? itens.reduce((maior, item) => Math.max(maior, item.valor), 0);

  return (
    <ul aria-label={rotulo} className={cn('flex flex-col gap-2', className)}>
      {itens.map((item) => {
        const largura = escala > 0 ? Math.max(0, item.valor / escala) * 100 : 0;
        const larguraParcela =
          item.parcela && escala > 0 ? Math.max(0, item.parcela.valor / escala) * 100 : 0;

        const conteudo = (
          <>
            <span className="flex min-w-0 items-center gap-1.5">
              {item.marcador}
              <span className="truncate text-[12px]/[16px] text-fg-secondary">{item.rotulo}</span>
              {item.anotacao ? (
                <span
                  className="shrink-0 text-risk-c"
                  title={item.anotacao.texto}
                  aria-label={item.anotacao.texto}
                >
                  {item.anotacao.simbolo}
                </span>
              ) : null}
            </span>

            <span className="relative block h-2 w-full overflow-hidden rounded-xs border border-line-subtle bg-surface-sunken">
              <span
                className="absolute inset-y-0 left-0 rounded-xs"
                style={{ width: `${largura}%`, background: item.cor }}
                aria-hidden="true"
              />
              {item.parcela && larguraParcela > 0 ? (
                <span
                  className="absolute inset-y-0 left-0 rounded-xs"
                  style={{ width: `${larguraParcela}%`, background: item.parcela.corSemantica }}
                  aria-hidden="true"
                />
              ) : null}
            </span>

            <span className="flex shrink-0 items-baseline justify-end gap-2 whitespace-nowrap">
              <span className="tnum text-[12px]/[16px] font-medium text-fg-primary">
                {item.valorFormatado}
              </span>
              {item.detalhe ? (
                <span className="tnum text-[11px]/[16px] text-fg-tertiary">{item.detalhe}</span>
              ) : null}
            </span>
          </>
        );

        const descricao = [
          item.rotulo,
          item.valorFormatado,
          item.detalhe,
          item.parcela ? `${item.parcela.rotulo}` : null,
        ]
          .filter(Boolean)
          .join(' · ');

        return (
          <li key={item.id}>
            {aoClicar ? (
              <button
                type="button"
                onClick={() => aoClicar(item)}
                aria-label={descricao}
                className={cn(
                  'transicao-controle grid w-full grid-cols-[112px_1fr_auto] items-center gap-3 rounded-sm px-1 py-1 text-left',
                  'hover:bg-surface-hover',
                )}
              >
                {conteudo}
              </button>
            ) : (
              <span
                aria-label={descricao}
                className="grid w-full grid-cols-[112px_1fr_auto] items-center gap-3 px-1 py-1"
              >
                {conteudo}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
