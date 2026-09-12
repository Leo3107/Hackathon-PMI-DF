'use client';

import { Gavel } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { formatarScore } from '@/lib/format';
import { cn } from './cn';
import {
  anguloDoScore,
  comprimentoArco,
  dashOffset,
  GAUGE,
  pathArco,
  pontoNoArco,
  ancoraTexto,
} from './gauge-geometry';
import { idHachura, PadraoHachura } from './hachura';
import { RatingBadge } from './RatingBadge';
import { CLASSES_RISCO, FAIXAS_RATING, RATING, TENDENCIA } from './risco';
import type { Rating, Tendencia, VetoAtivo } from './tipos-ui';
import { TrendIndicator } from './TrendIndicator';
import { useReducedMotion } from './usar-movimento-reduzido';

export interface ScoreGaugeProps {
  /** `scoreCalculado`, 0..1000. Nunca escondido, nem em modo veto. */
  score: number;
  ratingCalculado: Rating;
  ratingFinal: Rating;
  /** `length > 0` → modo veto (spec §7.7). */
  vetos?: VetoAtivo[];
  /** Marcador fantasma + arco de delta (spec §7.5). */
  scoreAnterior?: number;
  periodoDelta?: string;
  tendencia?: Tendencia;
  /** 120 · 200 · 280 px de largura. */
  tamanho?: 'sm' | 'md' | 'lg';
  /** Padrão true; respeita `prefers-reduced-motion`. */
  animar?: boolean;
  rotulo?: string;
  className?: string;
}

const LARGURA = { sm: 120, md: 200, lg: 280 } as const;
const CLASSE_NUMERO = {
  sm: 'type-score-sm',
  md: 'type-score-md',
  lg: 'type-score-xl',
} as const;

const RAIO_ORBITA = GAUGE.r + 14;
const COMPRIMENTO = comprimentoArco();

/** Posição vertical, em % da altura do viewBox (172), de cada camada do centro. */
const Y = {
  numero: (92 / 172) * 100,
  denominador: (118 / 172) * 100,
  badge: (131 / 172) * 100,
  rodape: (157 / 172) * 100,
} as const;

function Ticks() {
  const marcas = [400, 600, 750];
  return (
    <g aria-hidden="true">
      {marcas.map((marca) => {
        const angulo = anguloDoScore(marca);
        const interno = pontoNoArco(angulo, GAUGE.r - 10);
        const externo = pontoNoArco(angulo, GAUGE.r + 10);
        const rotulo = pontoNoArco(angulo, GAUGE.r + 18);
        return (
          <g key={marca}>
            <line
              x1={interno.x}
              y1={interno.y}
              x2={externo.x}
              y2={externo.y}
              stroke="var(--color-fg-tertiary)"
              strokeWidth={1.5}
            />
            <text
              x={rotulo.x}
              y={rotulo.y}
              fontSize={9}
              fontWeight={500}
              fill="var(--color-fg-tertiary)"
              textAnchor={ancoraTexto(angulo)}
              dominantBaseline="middle"
              style={{ fontVariantNumeric: 'tabular-nums lining-nums' }}
            >
              {marca}
            </text>
          </g>
        );
      })}
      {[0, 1000].map((extremo) => {
        const angulo = anguloDoScore(extremo);
        const ponto = pontoNoArco(angulo, GAUGE.r + 18);
        return (
          <text
            key={extremo}
            x={ponto.x}
            y={ponto.y}
            fontSize={9}
            fontWeight={500}
            fill="var(--color-fg-tertiary)"
            textAnchor={ancoraTexto(angulo)}
            dominantBaseline="middle"
            style={{ fontVariantNumeric: 'tabular-nums lining-nums' }}
          >
            {extremo}
          </text>
        );
      })}
    </g>
  );
}

/**
 * Gauge de score (spec §7). SVG autoral, sem biblioteca.
 *
 * O número central **nunca** é colorido: a cor está no arco, no badge e no
 * ícone — três canais bastam, e o número em cor faria o analista ler "vermelho"
 * antes de ler "604".
 *
 * Em modo veto, o preenchimento vira hachura na cor do rating **calculado**, um
 * anel externo mostra o rating **final** e o par de badges exibe os dois lado a
 * lado. O score calculado nunca é escondido.
 */
export function ScoreGauge({
  score,
  ratingCalculado,
  ratingFinal,
  vetos,
  scoreAnterior,
  periodoDelta,
  tendencia,
  tamanho = 'md',
  animar = true,
  rotulo = 'Score de risco',
  className,
}: ScoreGaugeProps) {
  const reduzido = useReducedMotion();
  const [animado, setAnimado] = useState(() => (animar ? 0 : score));
  const ultimo = useRef(animar ? 0 : score);

  useEffect(() => {
    if (!animar || reduzido) {
      ultimo.current = score;
      return;
    }
    const de = ultimo.current;
    const inicio = performance.now();
    const duracao = 600;
    let quadro = 0;
    const passo = (agora: number) => {
      const t = Math.min(1, (agora - inicio) / duracao);
      // Aproximação de --ease-gauge: desacelera longo, sem overshoot.
      const eased = 1 - Math.pow(1 - t, 3);
      const valor = Math.round(de + (score - de) * eased);
      setAnimado(valor);
      ultimo.current = valor;
      if (t < 1) quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [score, animar, reduzido]);

  // Sem animação (ou com movimento reduzido) o valor é derivado, não estado.
  const exibido = !animar || reduzido ? score : animado;

  const emVeto = Boolean(vetos && vetos.length > 0);
  const classesCalculado = CLASSES_RISCO[RATING[ratingCalculado].familia];
  const classesFinal = CLASSES_RISCO[RATING[ratingFinal].familia];
  const largura = LARGURA[tamanho];

  const delta =
    scoreAnterior === undefined ? undefined : Math.round(score - scoreAnterior);
  const temDelta = delta !== undefined && Math.abs(delta) >= 1;

  const familiaDelta = tendencia
    ? TENDENCIA[tendencia].familia
    : temDelta && Math.abs(delta ?? 0) < 25
      ? 'neutral'
      : (delta ?? 0) < 0
        ? 'c'
        : 'a';

  const anguloCursor = anguloDoScore(exibido);
  const pontaDelta = temDelta ? pontoNoArco(anguloDoScore(score), RAIO_ORBITA) : null;

  const vetoPrincipal = emVeto ? vetos![0] : null;
  const rotuloVeto = vetoPrincipal
    ? `Veto · ${vetoPrincipal.rotulo}${vetos!.length > 1 ? ` +${vetos!.length - 1}` : ''}`
    : null;

  const descricao = emVeto
    ? `Score calculado ${formatarScore(score)} de 1000, rating calculado ${ratingCalculado}. ` +
      `Classificação final ${ratingFinal} por regra de negócio: ${vetoPrincipal?.rotulo}. ` +
      `${RATING[ratingFinal].rotulo}.`
    : [
        `${rotulo} ${formatarScore(score)} de 1000`,
        `rating ${ratingFinal}`,
        RATING[ratingFinal].rotulo,
        temDelta
          ? `variação de ${delta! < 0 ? 'menos ' : 'mais '}${Math.abs(delta!)} pontos${periodoDelta ? ` em ${periodoDelta}` : ''}`
          : null,
        tendencia ? TENDENCIA[tendencia].rotulo : null,
      ]
        .filter(Boolean)
        .join(', ');

  return (
    <div
      role="img"
      aria-label={descricao}
      className={cn('score-gauge relative shrink-0', className)}
      style={{ width: `${largura}px` }}
    >
      <svg
        viewBox="0 0 200 172"
        width={largura}
        height={(largura * 172) / 200}
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          {emVeto ? (
            <PadraoHachura familia={RATING[ratingCalculado].familia} escopo="gauge" />
          ) : null}
        </defs>

        {/* Trilho */}
        <path
          d={pathArco(0, 1000)}
          fill="none"
          stroke="var(--color-line-subtle)"
          strokeWidth={14}
          strokeLinecap="butt"
        />
        <path
          d={pathArco(0, 1000)}
          fill="none"
          stroke="var(--color-surface-sunken)"
          strokeWidth={12}
          strokeLinecap="butt"
        />

        {/* Faixas de rating */}
        {FAIXAS_RATING.map((faixa) => (
          <path
            key={faixa.rating}
            d={pathArco(faixa.de, faixa.ate === 1000 ? 1000 : faixa.ate + 1)}
            fill="none"
            stroke={CLASSES_RISCO[faixa.familia].varCor}
            strokeWidth={12}
            strokeLinecap="butt"
            opacity={0.28}
          >
            <title>{`Faixa ${faixa.rating} · ${faixa.de}–${faixa.ate} · ${RATING[faixa.rating].rotulo}`}</title>
          </path>
        ))}

        <Ticks />

        {/* Preenchimento até o score */}
        <path
          d={pathArco(0, 1000)}
          fill="none"
          stroke={
            emVeto
              ? `url(#${idHachura(RATING[ratingCalculado].familia, 'gauge')})`
              : classesCalculado.varCor
          }
          strokeWidth={12}
          strokeLinecap="butt"
          strokeDasharray={`${COMPRIMENTO} ${COMPRIMENTO}`}
          strokeDashoffset={dashOffset(exibido)}
        />

        {/* Anel externo do rating final — só em modo veto */}
        {emVeto ? (
          <path
            d={pathArco(0, 1000, RAIO_ORBITA)}
            fill="none"
            stroke={classesFinal.varCor}
            strokeWidth={3}
            strokeLinecap="butt"
          >
            <title>{`Classificação final ${ratingFinal} por regra de negócio`}</title>
          </path>
        ) : null}

        {/* Arco de delta e marcador fantasma — suprimidos em modo veto */}
        {!emVeto && temDelta && scoreAnterior !== undefined ? (
          <g>
            <path
              d={pathArco(scoreAnterior, score, RAIO_ORBITA)}
              fill="none"
              stroke={CLASSES_RISCO[familiaDelta].varCor}
              strokeWidth={2}
              strokeDasharray="3 3"
            />
            <circle
              cx={pontoNoArco(anguloDoScore(scoreAnterior), RAIO_ORBITA).x}
              cy={pontoNoArco(anguloDoScore(scoreAnterior), RAIO_ORBITA).y}
              r={3}
              fill="none"
              stroke="var(--color-fg-tertiary)"
              strokeWidth={1.5}
            />
            {pontaDelta ? (
              <polygon
                points="-2.5,-2 2.5,-2 0,2.5"
                fill={CLASSES_RISCO[familiaDelta].varCor}
                transform={`translate(${pontaDelta.x} ${pontaDelta.y}) rotate(${anguloDoScore(score) + (delta! < 0 ? 90 : -90)})`}
              />
            ) : null}
          </g>
        ) : null}

        {/* Cursor */}
        <rect
          x={GAUGE.cx - 3}
          y={GAUGE.cy - (GAUGE.r + 9)}
          width={6}
          height={18}
          rx={3}
          fill="var(--color-fg-primary)"
          stroke="var(--color-surface-card)"
          strokeWidth={2}
          transform={`rotate(${anguloCursor} ${GAUGE.cx} ${GAUGE.cy})`}
        />
      </svg>

      {/* Centro tipográfico — HTML sobreposto, para que a escala do viewBox não
          distorça a tipografia do design system. */}
      <div className="pointer-events-none absolute inset-0">
        <span
          className={cn(
            'absolute left-1/2 -translate-x-1/2 -translate-y-1/2 text-fg-primary',
            CLASSE_NUMERO[tamanho],
          )}
          style={{ top: `${Y.numero}%` }}
        >
          {formatarScore(exibido)}
        </span>

        {tamanho === 'sm' ? null : (
          <span
            className="tnum absolute left-1/2 -translate-x-1/2 -translate-y-1/2 text-[11px]/[16px] font-normal text-fg-tertiary"
            style={{ top: `${Y.denominador}%` }}
          >
            / 1000
          </span>
        )}

        {tamanho === 'sm' ? null : (
          <span
            className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2"
            style={{ top: `${Y.badge}%` }}
          >
            <RatingBadge
              rating={ratingFinal}
              calculado={emVeto ? ratingCalculado : undefined}
              tamanho="md"
              mostrarRotulo={!emVeto}
            />
          </span>
        )}

        {tamanho === 'sm' ? null : emVeto ? (
          <span
            className={cn(
              'absolute left-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1 whitespace-nowrap',
              'text-[11px]/[16px] font-semibold text-fg-primary',
            )}
            style={{ top: `${Y.rodape}%` }}
          >
            <Gavel
              size={12}
              strokeWidth={2}
              className={cn('shrink-0', classesFinal.texto)}
              aria-hidden="true"
            />
            {rotuloVeto}
          </span>
        ) : tendencia ? (
          <span
            className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap"
            style={{ top: `${Y.rodape}%` }}
          >
            <TrendIndicator
              tendencia={tendencia}
              delta={temDelta ? delta : undefined}
              periodo={periodoDelta}
              tamanho="sm"
            />
          </span>
        ) : null}
      </div>

      {tamanho === 'sm' ? (
        <div className="mt-1 flex justify-center">
          <RatingBadge
            rating={ratingFinal}
            calculado={emVeto ? ratingCalculado : undefined}
            tamanho="sm"
          />
        </div>
      ) : null}
    </div>
  );
}
