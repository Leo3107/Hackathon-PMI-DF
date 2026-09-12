'use client';

/**
 * Linha do tempo (`03-ux-e-telas.md` §5).
 *
 * Objetivo declarado na spec: **tornar a deterioração impossível de não ver** — não listar
 * eventos. Daí a construção em duas camadas sobre o mesmo eixo X: a série do score em cima, os
 * marcadores de evento embaixo, ligados por linha-guia.
 *
 * A linha é em **degraus**, não curva suave: o score não varia continuamente entre varreduras;
 * ele muda quando um fato novo entra. Interpolar inventaria valores que o motor nunca calculou.
 */

import { Clock } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';

import {
  Badge,
  Button,
  CLASSES_RISCO,
  Card,
  Drawer,
  EmptyState,
  FAIXAS_RATING,
  RATING,
  RatingBadge,
  SEVERIDADE,
  SectionHeader,
  Timeline,
  ratingDoScore,
  type ItemTimeline,
} from '@/components/ui';
import { formatarData, formatarDelta, formatarScore } from '@/lib/format';
import type { AvaliacaoDeRisco, EventoDeRisco, Severidade } from '@/types';

import { serieDeScore, type PontoDaSerie } from './dados';

type Janela = '90d' | '6m' | '12m';

const DIAS_DA_JANELA: Record<Janela, number> = { '90d': 90, '6m': 183, '12m': 365 };

const ROTULO_JANELA: Record<Janela, string> = {
  '90d': '90 dias',
  '6m': '6 meses',
  '12m': '12 meses',
};

const LARGURA = 800;
const ALTURA_SERIE = 160;
const MARGEM_ESQ = 34;
const MARGEM_DIR = 26;
const TOPO = 10;

function paraDia(iso: string): number {
  return Math.floor(new Date(`${iso.slice(0, 10)}T00:00:00Z`).getTime() / 86_400_000);
}

function y(score: number): number {
  return TOPO + (1 - Math.min(1000, Math.max(0, score)) / 1000) * (ALTURA_SERIE - TOPO * 2);
}

/** Marcador por severidade: forma distinta, nunca só cor (I8). */
function caminhoDoMarcador(severidade: Severidade, cx: number, cy: number): string {
  const r = 5;
  switch (severidade) {
    case 'CRITICA': // losango
      return `M ${cx} ${cy - r} L ${cx + r} ${cy} L ${cx} ${cy + r} L ${cx - r} ${cy} Z`;
    case 'ALTA': // triângulo
      return `M ${cx} ${cy - r} L ${cx + r} ${cy + r} L ${cx - r} ${cy + r} Z`;
    case 'MEDIA': // quadrado
      return `M ${cx - r} ${cy - r} H ${cx + r} V ${cy + r} H ${cx - r} Z`;
    default: // círculo aproximado por dois arcos
      return `M ${cx - r} ${cy} a ${r} ${r} 0 1 0 ${r * 2} 0 a ${r} ${r} 0 1 0 ${-r * 2} 0`;
  }
}

export interface BlocoLinhaDoTempoProps {
  avaliacao: AvaliacaoDeRisco;
  eventos: EventoDeRisco[];
  aoVerEvidencia: (evidenciaId: string) => void;
}

export function BlocoLinhaDoTempo({
  avaliacao,
  eventos,
  aoVerEvidencia,
}: BlocoLinhaDoTempoProps) {
  const [janela, setJanela] = useState<Janela>('12m');
  const [focado, setFocado] = useState(0);
  const [comparando, setComparando] = useState<PontoDaSerie | null>(null);
  const [eventoDestacado, setEventoDestacado] = useState<string | null>(null);
  const grafico = useRef<SVGSVGElement>(null);

  const todosOsPontos = useMemo(
    () => serieDeScore(eventos, avaliacao),
    [eventos, avaliacao],
  );

  const fim = paraDia(avaliacao.dataReferencia);
  const inicio = fim - DIAS_DA_JANELA[janela];
  const pontos = todosOsPontos.filter((p) => paraDia(p.data) >= inicio);
  const eventosNaJanela = eventos.filter((e) => paraDia(e.data) >= inicio);

  const x = (iso: string): number => {
    const t = (paraDia(iso) - inicio) / Math.max(1, fim - inicio);
    return MARGEM_ESQ + Math.min(1, Math.max(0, t)) * (LARGURA - MARGEM_ESQ - MARGEM_DIR);
  };

  const itens: ItemTimeline[] = eventosNaJanela.map((evento) => ({
    id: evento.id,
    data: evento.data,
    titulo: evento.titulo,
    descricao: evento.descricao,
    severidade: evento.severidade,
    fonte: evento.fonte,
    deltaScore: evento.deltaScore,
    scoreApos: evento.scoreApos,
    evidenciaIds: evento.evidenciaIds,
    destaque: evento.id === eventoDestacado,
  }));

  const primeiro = pontos[0];
  const ultimo = pontos.at(-1);
  const descricaoDaSerie =
    primeiro && ultimo
      ? `Score de ${formatarScore(primeiro.score)} em ${formatarData(primeiro.data, 'mesAno')} ` +
        `para ${formatarScore(ultimo.score)} em ${formatarData(ultimo.data, 'mesAno')}, ` +
        `variação de ${formatarDelta(ultimo.score - primeiro.score, 'pts')}, ` +
        `faixa ${ratingDoScore(primeiro.score)} para faixa ${ratingDoScore(ultimo.score)}.`
      : 'Série de score indisponível.';

  return (
    <Card id="timeline" as="section" aria-labelledby="titulo-timeline" className="scroll-mt-[88px]">
      <SectionHeader
        nivel={2}
        titulo="Linha do tempo"
        descricao="A série do score e os eventos que a moveram, no mesmo eixo."
        meta={<Clock size={14} strokeWidth={2} aria-hidden="true" />}
        acoes={
          <div className="flex gap-1" role="group" aria-label="Janela da linha do tempo">
            {(Object.keys(ROTULO_JANELA) as Janela[]).map((opcao) => (
              <Button
                key={opcao}
                tamanho="sm"
                variante={janela === opcao ? 'secundario' : 'fantasma'}
                aria-pressed={janela === opcao}
                onClick={() => {
                  setJanela(opcao);
                  setFocado(0);
                }}
              >
                {ROTULO_JANELA[opcao]}
              </Button>
            ))}
          </div>
        }
      />
      <h2 id="titulo-timeline" className="sr-only">
        Linha do tempo
      </h2>

      {pontos.length < 2 ? (
        <div className="mt-3">
          <EmptyState
            compacto
            titulo="Histórico insuficiente para série temporal"
            descricao={`Este cliente tem ${pontos.length} ponto de score registrado (${formatarData(
              avaliacao.dataReferencia,
            )}). A série aparece a partir de dois pontos; os eventos, quando houver, seguem listados abaixo.`}
          />
        </div>
      ) : (
        <svg
          ref={grafico}
          role="img"
          aria-label={descricaoDaSerie}
          tabIndex={0}
          viewBox={`0 0 ${LARGURA} ${ALTURA_SERIE + 46}`}
          className="mt-3 w-full rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-400"
          onKeyDown={(evento) => {
            if (evento.key === 'ArrowRight') {
              evento.preventDefault();
              setFocado((i) => Math.min(pontos.length - 1, i + 1));
            } else if (evento.key === 'ArrowLeft') {
              evento.preventDefault();
              setFocado((i) => Math.max(0, i - 1));
            } else if (evento.key === 'Enter' || evento.key === ' ') {
              evento.preventDefault();
              setComparando(pontos[focado] ?? null);
            }
          }}
        >
          {/* Faixas de rating ao fundo, rotuladas à direita */}
          {FAIXAS_RATING.map((faixa) => {
            const topo = y(faixa.ate);
            const base = y(faixa.de);
            return (
              <g key={faixa.rating}>
                <rect
                  x={MARGEM_ESQ}
                  y={topo}
                  width={LARGURA - MARGEM_ESQ - MARGEM_DIR}
                  height={Math.max(1, base - topo)}
                  fill={CLASSES_RISCO[faixa.familia].varCor}
                  opacity={0.07}
                />
                <text
                  x={LARGURA - MARGEM_DIR + 5}
                  y={(topo + base) / 2}
                  fontSize={10}
                  fontWeight={600}
                  dominantBaseline="middle"
                  fill={CLASSES_RISCO[faixa.familia].varCor}
                >
                  {faixa.rating}
                </text>
              </g>
            );
          })}

          {/* Eixo Y mínimo: 0, 500, 1000 */}
          {[0, 500, 1000].map((marca) => (
            <text
              key={marca}
              x={MARGEM_ESQ - 6}
              y={y(marca)}
              fontSize={9}
              textAnchor="end"
              dominantBaseline="middle"
              fill="var(--color-fg-tertiary)"
              style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              {marca}
            </text>
          ))}

          {/* Série em degraus */}
          <path
            d={pontos
              .map((ponto, indice) => {
                const px = x(ponto.data);
                const py = y(ponto.score);
                if (indice === 0) return `M ${px} ${py}`;
                const anterior = pontos[indice - 1];
                return `L ${px} ${y(anterior.score)} L ${px} ${py}`;
              })
              .join(' ')}
            fill="none"
            stroke="var(--color-accent-400, var(--color-fg-primary))"
            strokeWidth={2}
          />

          {pontos.map((ponto, indice) => (
            <g key={ponto.data}>
              <circle
                cx={x(ponto.data)}
                cy={y(ponto.score)}
                r={indice === focado ? 5.5 : 3.5}
                fill="var(--color-surface-page)"
                stroke={CLASSES_RISCO[RATING[ratingDoScore(ponto.score)].familia].varCor}
                strokeWidth={2}
                onClick={() => {
                  setFocado(indice);
                  setComparando(ponto);
                }}
                style={{ cursor: 'pointer' }}
              >
                <title>{`${formatarData(ponto.data)} · score ${formatarScore(ponto.score)} · rating ${ratingDoScore(
                  ponto.score,
                )} · ${ponto.eventos.length} evento(s) nesta data`}</title>
              </circle>
            </g>
          ))}

          {/* Camada inferior: marcadores de evento e linha-guia */}
          {eventosNaJanela.map((evento) => {
            const px = x(evento.data);
            const cy = ALTURA_SERIE + 22;
            const familia = SEVERIDADE[evento.severidade].familia;
            return (
              <g
                key={evento.id}
                onClick={() => setEventoDestacado(evento.id)}
                style={{ cursor: 'pointer' }}
              >
                <line
                  x1={px}
                  y1={y(evento.scoreApos)}
                  x2={px}
                  y2={cy - 7}
                  stroke="var(--color-line-strong)"
                  strokeWidth={1}
                  strokeDasharray="2 3"
                />
                <path
                  d={caminhoDoMarcador(evento.severidade, px, cy)}
                  fill={CLASSES_RISCO[familia].varTint}
                  stroke={CLASSES_RISCO[familia].varCor}
                  strokeWidth={1.5}
                >
                  <title>{`${formatarData(evento.data)} · ${SEVERIDADE[evento.severidade].rotulo} · ${evento.titulo} · ${formatarDelta(
                    evento.deltaScore,
                    'pts',
                  )}`}</title>
                </path>
              </g>
            );
          })}

          {/* Eixo X: primeira e última data da janela */}
          <text
            x={MARGEM_ESQ}
            y={ALTURA_SERIE + 42}
            fontSize={9}
            fill="var(--color-fg-tertiary)"
          >
            {formatarData(pontos[0].data)}
          </text>
          <text
            x={LARGURA - MARGEM_DIR}
            y={ALTURA_SERIE + 42}
            fontSize={9}
            textAnchor="end"
            fill="var(--color-fg-tertiary)"
          >
            {formatarData(avaliacao.dataReferencia)}
          </text>
        </svg>
      )}

      <p className="type-caption mt-1">
        Linha em degraus: o score muda quando um fato novo entra, não continuamente. Setas ←/→
        percorrem os pontos; Enter compara com hoje.
      </p>

      <div className="mt-3 border-t border-line-subtle pt-3">
        <Timeline
          itens={itens}
          limite={8}
          aoSelecionarEvidencia={aoVerEvidencia}
          vazio={
            <EmptyState
              compacto
              titulo="Nenhum evento nesta janela"
              descricao={`Nenhum evento de risco foi registrado nos últimos ${ROTULO_JANELA[janela]}. Amplie a janela para ver o histórico anterior.`}
            />
          }
        />
      </div>

      <DrawerDeComparacao
        ponto={comparando}
        avaliacao={avaliacao}
        aoFechar={() => setComparando(null)}
        aoVerEvidencia={aoVerEvidencia}
      />
    </Card>
  );
}

/**
 * "Comparar com hoje". A decomposição de deltas por fator entre um snapshot antigo e o atual
 * depende de uma rota de comparação que o motor ainda não publica; enquanto isso, o drawer
 * mostra os dois números que **existem** — score e rating dos dois instantes e os eventos
 * daquela data — em vez de inventar a diferença por fator.
 */
function DrawerDeComparacao({
  ponto,
  avaliacao,
  aoFechar,
  aoVerEvidencia,
}: {
  ponto: PontoDaSerie | null;
  avaliacao: AvaliacaoDeRisco;
  aoFechar: () => void;
  aoVerEvidencia: (evidenciaId: string) => void;
}) {
  const rating = ponto ? ratingDoScore(ponto.score) : 'A';

  return (
    <Drawer
      aberto={ponto !== null}
      aoFechar={aoFechar}
      titulo="Comparar com hoje"
      subtitulo={ponto ? `${formatarData(ponto.data)} × ${formatarData(avaliacao.dataReferencia)}` : ''}
    >
      {ponto ? (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col items-start gap-1 rounded border border-line-default p-3">
              <p className="type-eyebrow text-fg-tertiary">{formatarData(ponto.data)}</p>
              <p className="type-score-md tnum text-fg-primary">{formatarScore(ponto.score)}</p>
              <RatingBadge rating={rating} tamanho="md" />
            </div>
            <div className="flex flex-col items-start gap-1 rounded border border-accent-line p-3">
              <p className="type-eyebrow text-fg-tertiary">
                Hoje · {formatarData(avaliacao.dataReferencia)}
              </p>
              <p className="type-score-md tnum text-fg-primary">
                {formatarScore(avaliacao.scoreCalculado)}
              </p>
              <RatingBadge
                rating={avaliacao.ratingFinal}
                calculado={avaliacao.ratingCalculado}
                tamanho="md"
              />
            </div>
          </div>

          <section className="flex flex-col gap-2">
            <h3 className="type-eyebrow text-fg-secondary">
              Eventos em {formatarData(ponto.data)}
            </h3>
            {ponto.eventos.length === 0 ? (
              <p className="type-caption">
                Nenhum evento nesta data — o ponto é a varredura corrente do motor.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {ponto.eventos.map((evento) => (
                  <li
                    key={evento.id}
                    className="flex flex-col gap-1 rounded border border-line-default p-2"
                  >
                    <p className="type-body-strong text-fg-primary">{evento.titulo}</p>
                    <p className="type-caption">{evento.descricao}</p>
                    <p className="type-caption flex flex-wrap items-center gap-2">
                      <Badge variante="severidade" severidade={evento.severidade} tamanho="sm" />
                      <span className="tnum">{formatarDelta(evento.deltaScore, 'pts')}</span>
                      {evento.evidenciaIds.length > 0 ? (
                        <Button
                          variante="fantasma"
                          tamanho="sm"
                          onClick={() => {
                            aoVerEvidencia(evento.evidenciaIds[0]);
                            aoFechar();
                          }}
                        >
                          Ver evidência
                        </Button>
                      ) : null}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <p className="type-caption border-t border-line-subtle pt-2">
            A decomposição de deltas por fator entre dois snapshots é produzida pelo motor
            (`comparar_avaliacoes`) e aparece no bloco &quot;O que mudou&quot; assim que a rota de
            comparação por período estiver publicada.
          </p>
        </div>
      ) : null}
    </Drawer>
  );
}
