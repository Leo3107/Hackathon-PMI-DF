'use client';

/**
 * V1 · Matriz de risco da carteira (`03-ux-e-telas.md` §2.4).
 *
 * Pergunta: *"quais clientes combinam alta probabilidade de calote com muito dinheiro
 * desprotegido?"*. Dispersão de `pd12m` (x) contra `exposicaoEmRiscoEmRJ` (y), raio ∝ √
 * exposição total, cor pelo rating — e **a letra do rating impressa dentro do ponto**, porque
 * nenhum estado de risco pode ser comunicado só por cor (I8/R2). Ponto com veto ganha anel
 * tracejado.
 *
 * Drill-down: clique no ponto → `/clientes/[id]`.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as TooltipRecharts,
  XAxis,
  YAxis,
} from 'recharts';

import { CLASSES_RISCO, RATING, RatingBadge, cn } from '@/components/ui';
import { formatarMoeda, formatarMoedaCompacta, formatarPercentual } from '@/lib/format';
import type { PontoMatrizDeRisco, Rating } from '@/types';

import { ALTURA_GRAFICO, CHART, ChartTooltip, LegendaGrafico, MolduraDeGrafico } from './grafico';

const RAIO_MINIMO = 6;
const RAIO_MAXIMO = 18;

function raio(exposicaoTotal: number, maiorExposicao: number): number {
  if (maiorExposicao <= 0) return RAIO_MINIMO;
  const fracao = Math.sqrt(Math.max(0, exposicaoTotal) / maiorExposicao);
  return RAIO_MINIMO + fracao * (RAIO_MAXIMO - RAIO_MINIMO);
}

/** Domínio do eixo X fixo em 0–60%, como a spec determina, para comparabilidade entre sessões. */
const TICKS_PD = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6];

interface PontoPlotado extends PontoMatrizDeRisco {
  r: number;
}

export interface MatrizDeRiscoProps {
  pontos: PontoMatrizDeRisco[];
}

export function MatrizDeRisco({ pontos }: MatrizDeRiscoProps) {
  const router = useRouter();
  const maior = pontos.reduce((maximo, p) => Math.max(maximo, p.exposicaoTotal), 0);
  const dados: PontoPlotado[] = pontos.map((p) => ({ ...p, r: raio(p.exposicaoTotal, maior) }));

  const descricao = `Dispersão de ${dados.length} clientes: probabilidade de inadimplência em 12 meses no eixo horizontal, exposição em risco em cenário de recuperação judicial no eixo vertical. O tamanho do ponto é proporcional à exposição total e a letra dentro do ponto é o rating.`;

  return (
    <div className="flex flex-col gap-3">
      <MolduraDeGrafico altura={ALTURA_GRAFICO.pagina} descricao={descricao}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke={CHART.grid.stroke} strokeWidth={CHART.grid.strokeWidth} />
            <XAxis
              type="number"
              dataKey="pd12m"
              domain={[0, 0.6]}
              ticks={TICKS_PD}
              tickFormatter={(valor: number) => formatarPercentual(valor, 0)}
              axisLine={false}
              tickLine={false}
              tickMargin={8}
              tick={CHART.tick}
              name="PD 12m"
            />
            <YAxis
              type="number"
              dataKey="exposicaoEmRiscoEmRJ"
              tickFormatter={(valor: number) => formatarMoedaCompacta(valor, { prefixo: false })}
              axisLine={false}
              tickLine={false}
              tickMargin={8}
              tick={CHART.tick}
              width={52}
              name="Em risco em RJ"
            />
            <TooltipRecharts
              cursor={CHART.cursor}
              isAnimationActive={false}
              content={(props) => (
                <ChartTooltip
                  active={props.active}
                  titulo={tituloDoPonto(props.payload)}
                  payload={linhasDoPonto(props.payload)}
                  formatarValor={(valor, nome) =>
                    nome === 'PD 12m' ? formatarPercentual(valor, 1) : formatarMoeda(valor, { casas: 0 })
                  }
                  extra={(dado) => <ExtraDoTooltip dado={dado} />}
                />
              )}
            />
            <Scatter
              data={dados}
              isAnimationActive={false}
              shape={(props: unknown) => <PontoDeRating {...(props as PropsDoPonto)} />}
              onClick={(dado: unknown) => {
                // O Recharts ora entrega o nó (com `payload` aninhado), ora o próprio dado.
                const bruto = dado as { payload?: PontoPlotado; clienteId?: string } | undefined;
                const id = bruto?.payload?.clienteId ?? bruto?.clienteId;
                if (id) router.push(`/clientes/${encodeURIComponent(id)}`);
              }}
              className="cursor-pointer"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </MolduraDeGrafico>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <LegendaGrafico
          itens={(['A', 'B', 'C', 'D'] as Rating[]).map((rating) => ({
            cor: CHART.series.risco[RATING[rating].familia as 'a' | 'b' | 'c' | 'd'],
            rotulo: `${rating} · ${RATING[rating].rotulo}`,
          }))}
        />
        <p className="type-caption">Tamanho do ponto = exposição total · anel tracejado = veto ativo</p>
      </div>

      {/* Equivalente acessível e navegável por teclado do gráfico (§10.3). */}
      <ul className="sr-only">
        {dados.map((ponto) => (
          <li key={ponto.clienteId}>
            <Link
              href={`/clientes/${encodeURIComponent(ponto.clienteId)}`}
              className="focus:not-sr-only focus:absolute focus:z-50 focus:rounded focus:bg-surface-raised focus:px-2 focus:py-1"
            >
              {ponto.razaoSocial}: rating {ponto.rating}, PD 12 meses{' '}
              {formatarPercentual(ponto.pd12m, 1)}, exposição em risco em recuperação judicial{' '}
              {formatarMoeda(ponto.exposicaoEmRiscoEmRJ, { casas: 0 })}
              {ponto.temVeto ? ', com veto ativo' : ''}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface PropsDoPonto {
  cx?: number;
  cy?: number;
  payload?: PontoPlotado;
}

/** Círculo com a letra do rating dentro — a redundância de canal exigida por §10.4. */
function PontoDeRating({ cx, cy, payload }: PropsDoPonto) {
  if (cx === undefined || cy === undefined || !payload) return <g />;
  const familia = RATING[payload.rating].familia as 'a' | 'b' | 'c' | 'd';
  const cor = CHART.series.risco[familia];
  const r = payload.r;

  return (
    <g>
      {payload.temVeto ? (
        <circle
          cx={cx}
          cy={cy}
          r={r + 3}
          fill="none"
          stroke={cor}
          strokeWidth={1}
          strokeDasharray="3 2"
        />
      ) : null}
      <circle cx={cx} cy={cy} r={r} fill={cor} fillOpacity={0.28} stroke={cor} strokeWidth={1.5} />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={Math.max(9, Math.min(12, r))}
        fontWeight={600}
        fill={cor}
      >
        {payload.rating}
      </text>
    </g>
  );
}

type PayloadRecharts = ReadonlyArray<{ payload?: unknown }> | undefined;

function pontoDoPayload(payload: PayloadRecharts): PontoPlotado | null {
  const bruto = payload?.[0]?.payload;
  return bruto && typeof bruto === 'object' ? (bruto as PontoPlotado) : null;
}

function tituloDoPonto(payload: PayloadRecharts): string | undefined {
  return pontoDoPayload(payload)?.razaoSocial;
}

function linhasDoPonto(payload: PayloadRecharts) {
  const ponto = pontoDoPayload(payload);
  if (!ponto) return [];
  return [
    { name: 'PD 12m', value: ponto.pd12m, payload: ponto as unknown as Record<string, unknown> },
    { name: 'Em risco em RJ', value: ponto.exposicaoEmRiscoEmRJ },
    { name: 'Exposição total', value: ponto.exposicaoTotal },
  ];
}

function ExtraDoTooltip({ dado }: { dado: Record<string, unknown> }) {
  const rating = dado.rating as Rating | undefined;
  const temVeto = Boolean(dado.temVeto);
  if (!rating) return null;
  return (
    <div className="flex items-center gap-2">
      <RatingBadge rating={rating} tamanho="sm" />
      {temVeto ? (
        <span className={cn('type-badge', CLASSES_RISCO.d.texto)}>Veto ativo</span>
      ) : null}
    </div>
  );
}
