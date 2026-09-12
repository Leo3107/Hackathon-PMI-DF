'use client';

/**
 * V2 · Exposição por rating e V3/V4 · Concentração por cultura e por UF
 * (`03-ux-e-telas.md` §2.4). V3 e V4 dividem um card com duas abas, para economizar altura e
 * manter a carteira legível sem rolagem em 1440×900.
 *
 * As **oito visualizações recusadas** em §2.5 — mapa coroplético, pizza de rating, gauge de
 * saúde da carteira, radar agregado, treemap, sparkline decorativo, série do score médio e
 * contador animado — não existem neste arquivo e não devem ser reintroduzidas.
 *
 * Campos que o motor ainda pode não enviar (parcela em risco por UF, marcador de ZARC por
 * cultura) são lidos de forma opcional **num único ponto**, e a barra degrada para o valor
 * simples quando ausentes.
 */

import { useState } from 'react';

import { EmptyState, RatingBadge, SectionHeader, Tooltip, cn } from '@/components/ui';
import { formatarMoedaCompacta, formatarNumero, formatarPercentual } from '@/lib/format';
import type { FatiaDeConcentracao, Rating, ResumoCarteira } from '@/types';

import { CHART } from './grafico';
import { ListaDeBarras, type ItemDeBarra } from './barras';

const RATINGS: Rating[] = ['A', 'B', 'C', 'D'];

/** Extensões opcionais do contrato: ligam sozinhas quando o Flask passar a enviá-las. */
interface FatiaComExtras extends FatiaDeConcentracao {
  exposicaoEmRisco?: number;
  /** `true` na cultura de maior ZARC médio da carteira. */
  zarcAlto?: boolean;
}

// ---------------------------------------------------------------------------
// V2 — exposição por rating
// ---------------------------------------------------------------------------

export interface ExposicaoPorRatingProps {
  porRating: ResumoCarteira['clientesPorRating'] | undefined;
  aoAbrirRating: (rating: Rating) => void;
}

export function ExposicaoPorRating({ porRating, aoAbrirRating }: ExposicaoPorRatingProps) {
  const linhas = RATINGS.map((rating) => ({
    rating,
    exposicao: porRating?.[rating]?.exposicao ?? 0,
    clientes: porRating?.[rating]?.clientes ?? 0,
  }));

  const total = linhas.reduce((soma, linha) => soma + linha.exposicao, 0);

  if (total <= 0) {
    return (
      <EmptyState
        compacto
        titulo="Sem exposição para distribuir por rating"
        descricao="Quanto do dinheiro da carteira está em cada faixa de risco — aparece assim que o motor devolver as avaliações."
      />
    );
  }

  const itens: ItemDeBarra[] = linhas.map((linha) => ({
    id: linha.rating,
    rotulo: '',
    marcador: <RatingBadge rating={linha.rating} tamanho="sm" />,
    valor: linha.exposicao,
    valorFormatado: formatarMoedaCompacta(linha.exposicao),
    detalhe: `${formatarNumero(linha.clientes)} cli.`,
    cor: CHART.series.risco[linha.rating.toLowerCase() as 'a' | 'b' | 'c' | 'd'],
  }));

  return (
    <ListaDeBarras
      rotulo="Exposição por rating"
      itens={itens}
      aoClicar={(item) => aoAbrirRating(item.id as Rating)}
    />
  );
}

// ---------------------------------------------------------------------------
// V3 e V4 — concentração
// ---------------------------------------------------------------------------

type Aba = 'cultura' | 'uf';

export interface ConcentracaoProps {
  porCultura: FatiaDeConcentracao[];
  porUf: FatiaDeConcentracao[];
  aoAbrirCultura: (cultura: string) => void;
  aoAbrirUf: (uf: string) => void;
}

const MAXIMO_LINHAS: Record<Aba, number> = { cultura: 6, uf: 7 };

export function Concentracao({
  porCultura,
  porUf,
  aoAbrirCultura,
  aoAbrirUf,
}: ConcentracaoProps) {
  const [aba, setAba] = useState<Aba>('cultura');

  const fonte = aba === 'cultura' ? porCultura : porUf;
  const limite = MAXIMO_LINHAS[aba];
  const visiveis = fonte.slice(0, limite);
  const restantes = Math.max(0, fonte.length - visiveis.length);

  const itens: ItemDeBarra[] = visiveis.map((fatiaBruta, indice) => {
    const fatia = fatiaBruta as FatiaComExtras;
    return {
      id: fatia.rotulo,
      rotulo: fatia.rotulo,
      valor: fatia.exposicao,
      valorFormatado: formatarMoedaCompacta(fatia.exposicao),
      detalhe: `${formatarPercentual(fatia.pct, 0)} · ${formatarNumero(fatia.clientes)} cli.`,
      // Rampa monocromática de azul-aço: a posição no ranking define só a luminosidade.
      // Verde, âmbar, laranja e vermelho continuam reservados a risco, e a paleta categórica
      // não pode competir com eles — o que comunica magnitude aqui é o comprimento da barra.
      cor: CHART.series.categoricas[Math.min(indice, CHART.series.categoricas.length - 1)],
      parcela:
        typeof fatia.exposicaoEmRisco === 'number' && fatia.exposicaoEmRisco > 0
          ? {
              valor: fatia.exposicaoEmRisco,
              corSemantica: CHART.series.risco.c,
              rotulo: `em risco ${formatarMoedaCompacta(fatia.exposicaoEmRisco)}`,
            }
          : null,
      anotacao: fatia.zarcAlto
        ? { simbolo: '▲', texto: 'Risco climático médio alto nesta cultura' }
        : null,
    };
  });

  const temParcela = itens.some((item) => item.parcela != null);

  return (
    <div className="flex flex-col gap-3">
      <div role="tablist" aria-label="Dimensão da concentração" className="flex items-center gap-1">
        {(['cultura', 'uf'] as Aba[]).map((valor) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={aba === valor}
            onClick={() => setAba(valor)}
            className={cn(
              'transicao-controle type-badge h-6 rounded-sm border px-2 font-medium',
              aba === valor
                ? 'border-accent-line bg-accent-tint text-accent-300'
                : 'border-line-default bg-transparent text-fg-secondary hover:border-line-strong',
            )}
          >
            {valor === 'cultura' ? 'Cultura' : 'UF'}
          </button>
        ))}
      </div>

      {itens.length === 0 ? (
        <EmptyState
          compacto
          titulo={
            aba === 'cultura'
              ? 'Sem concentração por cultura'
              : 'Sem concentração geográfica'
          }
          descricao={
            aba === 'cultura'
              ? 'Se a soja quebrar, quanto da carteira é atingido? A resposta aparece quando o motor devolver a exposição por cultura.'
              : 'Em qual UF a carteira está concentrada? A resposta aparece quando o motor devolver a exposição por UF.'
          }
        />
      ) : (
        <>
          <ListaDeBarras
            rotulo={aba === 'cultura' ? 'Exposição por cultura' : 'Exposição por UF'}
            itens={itens}
            aoClicar={(item) =>
              aba === 'cultura' ? aoAbrirCultura(item.id) : aoAbrirUf(item.id)
            }
          />
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
            {temParcela ? (
              <p className="type-caption inline-flex items-center gap-1.5">
                <span
                  aria-hidden="true"
                  className="inline-block h-2 w-3 rounded-xs bg-risk-c"
                />
                Trecho colorido no início da barra: parcela já em risco
              </p>
            ) : (
              <span />
            )}
            {restantes > 0 ? (
              <p className="type-caption">
                {aba === 'cultura'
                  ? `+${formatarNumero(restantes)} outras culturas`
                  : `+${formatarNumero(restantes)} outras UFs`}
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bloco V3/V4 com o cabeçalho e a pergunta que o gráfico responde — sem card: o que separa
// esta seção da de cima é a régua de 1px do próprio SectionHeader.
// ---------------------------------------------------------------------------

export function BlocoDeConcentracao(props: ConcentracaoProps) {
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader
        nivel={3}
        titulo="Concentração"
        descricao="Se uma cultura ou uma região quebrar, quanto da carteira é atingido?"
        acoes={
          <Tooltip conteudo="Barras ordenadas por exposição, em uma única rampa de azul: quanto mais alto no ranking, mais clara a barra. Clique para filtrar a lista de clientes.">
            <span
              tabIndex={0}
              role="note"
              aria-label="Como ler este gráfico"
              className="type-caption cursor-default rounded-sm"
            >
              ?
            </span>
          </Tooltip>
        }
      />
      <Concentracao {...props} />
    </section>
  );
}
