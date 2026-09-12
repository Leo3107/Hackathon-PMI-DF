'use client';

/**
 * Coluna principal, parte analítica (`03-ux-e-telas.md` §4.5, §4.6 e §4.7).
 *
 * Quatro blocos, na ordem em que o analista pergunta: **o que mudou** → **por que este score**
 * → **decomposição por dimensão** → **red flags**. Todos renderizam apenas números que o motor
 * mandou; nenhum deles espera o LLM para aparecer.
 */

import { AlertOctagon, ChevronDown, Flag, ListTree, TrendingDown } from 'lucide-react';
import { useMemo, useState } from 'react';

import {
  Badge,
  Button,
  CLASSES_RISCO,
  Card,
  EmptyState,
  FactorBar,
  FilterChips,
  NOME_DIMENSAO,
  NOME_CURTO_FONTE,
  ProgressBar,
  SEVERIDADE,
  SectionHeader,
  StreamingText,
  Tooltip,
  TrendIndicator,
  type FatorExibido,
} from '@/components/ui';
import { definirStatusRedFlag } from '@/lib/sessao';
import {
  formatarData,
  formatarDelta,
  formatarNumero,
  formatarPercentual,
  formatarScore,
} from '@/lib/format';
import type {
  AuditoriaDeFechamento,
  AvaliacaoDeRisco,
  ComparacaoDeAvaliacoes,
  DimensaoAvaliada,
  FatorCalculado,
  RedFlag,
  StatusRedFlag,
} from '@/types';

import type { Narrativa } from './dados';

/* ------------------------------------------------------------------ */
/* Bloco 4 — o que mudou                                               */
/* ------------------------------------------------------------------ */

export interface BlocoOQueMudouProps {
  variacao: ComparacaoDeAvaliacoes;
  aoSelecionarFator: (fatorId: string) => void;
}

/**
 * Formato literal exigido pela `02-motor-de-risco.md` §11: a lista de deltas por fator e, em
 * seguida, a **linha de fechamento**, que materializa a invariante I6. A linha é obrigatória e
 * visível: é ela que prova que a soma dos deltas reconstrói a variação do score, e não uma
 * aproximação simpática.
 */
export function BlocoOQueMudou({ variacao, aoSelecionarFator }: BlocoOQueMudouProps) {
  const fecha = Math.abs(variacao.diferencaDeFechamento) <= 0.5;

  return (
    <Card id="mudou" as="section" aria-labelledby="titulo-mudou" className="scroll-mt-[88px]">
      <SectionHeader
        nivel={2}
        titulo="O que mudou"
        sobretitulo={`${formatarData(variacao.dataAnterior)} → ${formatarData(variacao.dataAtual)}`}
        descricao="Comparação com o snapshot anterior publicado pelo motor."
      />
      <h2 id="titulo-mudou" className="sr-only">
        O que mudou no score
      </h2>

      <p className="type-kpi tnum mt-3 flex flex-wrap items-baseline gap-x-3 text-fg-primary">
        <span>{formatarScore(variacao.scoreAnterior)}</span>
        <span aria-hidden="true" className="text-fg-tertiary">
          →
        </span>
        <span>{formatarScore(variacao.scoreAtual)}</span>
        <span className="type-body-strong">
          <TrendIndicator
            tendencia={variacao.deltaScore < 0 ? 'deteriorando' : 'melhorando'}
            delta={variacao.deltaScore}
          />
        </span>
      </p>

      <div className="mt-3">
        <FactorBar
          fatores={variacao.fatores.map(
            (delta): FatorExibido => ({
              id: delta.fatorId,
              rotulo: delta.rotulo,
              detalhe: delta.detalhe ?? undefined,
              direcao: delta.delta < 0 ? 'risco' : 'protecao',
              dimensao: delta.dimensao,
              impacto: delta.delta,
            }),
          )}
          modo="delta"
          mostrarDimensao
          limite={8}
          somaEsperada={variacao.deltaScore}
          aoSelecionar={aoSelecionarFator}
        />
      </div>

      <p
        className={`type-caption tnum mt-2 border-t border-line-subtle pt-2 ${
          fecha ? '' : CLASSES_RISCO.d.texto
        }`}
        data-teste="fechamento-delta"
      >
        Σ dos deltas = {formatarDelta(variacao.deltaScore, 'pts')} · variação do score ={' '}
        {formatarDelta(variacao.scoreAtual - variacao.scoreAnterior, 'pts')} · diferença{' '}
        {formatarNumero(variacao.diferencaDeFechamento, 1)}{' '}
        {fecha ? '✓ fecha' : '✗ não fecha — não utilize este parecer'}
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Bloco 5 — por que este score                                        */
/* ------------------------------------------------------------------ */

function paraExibicao(fator: FatorCalculado): FatorExibido {
  return {
    id: fator.id,
    rotulo: fator.rotulo,
    detalhe: fator.detalhe ?? undefined,
    direcao: fator.direcao,
    dimensao: fator.dimensao,
    impacto: fator.impactoGlobalAjustado,
  };
}

export interface BlocoPorQueProps {
  avaliacao: AvaliacaoDeRisco;
  narrativa: Narrativa;
  aoSelecionarFator: (fatorId: string) => void;
  fatorDestacado: string | null;
}

export function BlocoPorQue({
  avaliacao,
  narrativa,
  aoSelecionarFator,
  fatorDestacado,
}: BlocoPorQueProps) {
  const { risco, protecao } = useMemo(() => {
    const todos = avaliacao.dimensoes.flatMap((d) => d.fatores).map(paraExibicao);
    return {
      risco: todos.filter((f) => f.direcao === 'risco'),
      protecao: todos.filter((f) => f.direcao === 'protecao'),
    };
  }, [avaliacao]);

  return (
    <Card id="por-que" as="section" aria-labelledby="titulo-por-que" className="scroll-mt-[88px]">
      <SectionHeader
        nivel={2}
        titulo="Por que este score"
        descricao="Contribuição de cada fator, já ponderada pelo peso da dimensão. As barras e os números são do motor; o parágrafo ao pé é prosa."
      />
      <h2 id="titulo-por-que" className="sr-only">
        Por que este score
      </h2>

      <div className="mt-3 grid gap-4 xl:grid-cols-2">
        <section aria-label="Fatores de risco" className="flex flex-col gap-2">
          <h3 className="type-eyebrow inline-flex items-center gap-1.5 text-risk-c">
            <TrendingDown size={12} strokeWidth={2.5} aria-hidden="true" />
            Fatores de risco ({risco.length})
          </h3>
          {risco.length === 0 ? (
            <p className="type-caption">Nenhum fator de risco registrado nesta varredura.</p>
          ) : (
            <FactorBar
              fatores={risco}
              modo="contribuicao"
              limite={6}
              mostrarDimensao
              selecionado={fatorDestacado}
              aoSelecionar={aoSelecionarFator}
            />
          )}
        </section>

        <section aria-label="Fatores de proteção" className="flex flex-col gap-2">
          <h3 className="type-eyebrow inline-flex items-center gap-1.5 text-risk-a">
            <Flag size={12} strokeWidth={2.5} aria-hidden="true" />
            Fatores de proteção ({protecao.length})
          </h3>
          {protecao.length === 0 ? (
            <p className="type-caption">
              Nenhum fator de proteção: não há garantia, histórico ou certidão que compense o
              risco apurado.
            </p>
          ) : (
            <FactorBar
              fatores={protecao}
              modo="contribuicao"
              limite={4}
              mostrarDimensao
              selecionado={fatorDestacado}
              aoSelecionar={aoSelecionarFator}
            />
          )}
        </section>
      </div>

      <div className="mt-4 border-t border-line-subtle pt-3">
        <p className="type-eyebrow mb-1.5 text-fg-tertiary">ANÁLISE</p>
        <StreamingText
          texto={narrativa.texto}
          estado={narrativa.estado}
          origem={narrativa.origem}
          modelo={narrativa.modelo}
          aoTentarNovamente={narrativa.tentarNovamente}
        />
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Bloco 6 — decomposição por dimensão                                 */
/* ------------------------------------------------------------------ */

export interface BlocoDimensoesProps {
  dimensoes: DimensaoAvaliada[];
  auditoria: AuditoriaDeFechamento;
  scoreExibido: number;
  aoSelecionarFator: (fatorId: string) => void;
}

export function BlocoDimensoes({
  dimensoes,
  auditoria,
  scoreExibido,
  aoSelecionarFator,
}: BlocoDimensoesProps) {
  const [aberta, setAberta] = useState<string | null>(null);
  const ordenadas = useMemo(() => [...dimensoes].sort((a, b) => b.peso - a.peso), [dimensoes]);
  const fecha = Math.abs(auditoria.diferenca) <= 0.5;

  return (
    <Card
      id="dimensoes"
      as="section"
      aria-labelledby="titulo-dimensoes"
      className="scroll-mt-[88px]"
    >
      <SectionHeader
        nivel={2}
        titulo="Decomposição por dimensão"
        descricao="Sete dimensões, em ordem de peso decrescente. Os pesos somam exatamente 1,00."
        meta={<ListTree size={14} strokeWidth={2} aria-hidden="true" />}
      />
      <h2 id="titulo-dimensoes" className="sr-only">
        Decomposição por dimensão
      </h2>

      <ul className="mt-3 flex flex-col divide-y divide-line-subtle">
        {ordenadas.map((dimensao) => {
          const expandida = aberta === dimensao.id;
          return (
            <li key={dimensao.id} className="py-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setAberta(expandida ? null : dimensao.id)}
                  aria-expanded={expandida}
                  className="transicao-controle flex shrink-0 items-center gap-1 rounded px-1 py-0.5 text-fg-secondary hover:bg-surface-hover"
                >
                  <ChevronDown
                    size={14}
                    strokeWidth={2}
                    className={expandida ? 'rotate-180' : ''}
                    aria-hidden="true"
                  />
                  <span className="type-body-strong">{NOME_DIMENSAO[dimensao.id]}</span>
                  <span className="type-caption tnum">{formatarPercentual(dimensao.peso, 0)}</span>
                </button>

                <div className="min-w-0 flex-1">
                  <ProgressBar
                    valor={dimensao.score}
                    maximo={1000}
                    familia="auto"
                    rotulo={`Score da dimensão ${dimensao.rotulo}`}
                    valorFormatado={formatarScore(dimensao.score)}
                    altura={6}
                  />
                </div>

                <span className="shrink-0">
                  <TrendIndicator tendencia={dimensao.tendencia} tamanho="sm" rotuloCurto />
                </span>

                {dimensao.saturou ? (
                  <Tooltip conteudo="Dimensão saturada: o excedente foi redistribuído. O impacto real é maior que o exibido nesta barra.">
                    <span tabIndex={0} className="shrink-0 rounded-sm text-risk-c">
                      <AlertOctagon size={14} strokeWidth={2} aria-label="Dimensão saturada" />
                    </span>
                  </Tooltip>
                ) : null}
              </div>

              {expandida ? (
                <div className="mt-2 ml-6 flex flex-col gap-2 border-l border-line-subtle pl-3">
                  <p className="type-caption tnum">
                    Contribuição para o score: {formatarNumero(dimensao.contribuicao, 1)} ={' '}
                    {formatarScore(dimensao.score)} × {formatarPercentual(dimensao.peso, 0)}
                  </p>
                  {dimensao.fatores.length === 0 ? (
                    <p className="type-caption">Nenhum fator acionado nesta dimensão.</p>
                  ) : (
                    <FactorBar
                      fatores={dimensao.fatores.map(paraExibicao)}
                      modo="contribuicao"
                      aoSelecionar={aoSelecionarFator}
                    />
                  )}
                  {dimensao.fontes.length > 0 ? (
                    <p className="type-caption flex flex-wrap items-center gap-1">
                      <span>Fontes:</span>
                      {dimensao.fontes.map((fonte) => (
                        <Badge key={fonte} variante="fonte" fonte={fonte} tamanho="sm" />
                      ))}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      <p
        className={`type-caption tnum mt-2 border-t border-line-subtle pt-2 ${
          fecha ? '' : CLASSES_RISCO.d.texto
        }`}
        data-teste="fechamento-score"
      >
        {fecha ? (
          <>
            Σ contribuições = {formatarNumero(auditoria.somaImpactos, 1)} · score exibido ={' '}
            {formatarScore(scoreExibido)} · diferença {formatarNumero(auditoria.diferenca, 1)} ✓
          </>
        ) : (
          <>
            Inconsistência de fechamento detectada (diferença{' '}
            {formatarNumero(auditoria.diferenca, 1)}). Não utilize este parecer.
          </>
        )}
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Bloco 7 — red flags                                                 */
/* ------------------------------------------------------------------ */

const ORDEM_SEVERIDADE: Record<RedFlag['severidade'], number> = {
  CRITICA: 0,
  ALTA: 1,
  MEDIA: 2,
  BAIXA: 3,
};

type FiltroStatus = 'todas' | StatusRedFlag;

export interface BlocoRedFlagsProps {
  redFlags: RedFlag[];
  dataReferencia: string;
  aoVerEvidencia: (evidenciaId: string) => void;
  aoSelecionarFator: (fatorId: string) => void;
}

export function BlocoRedFlags({
  redFlags,
  dataReferencia,
  aoVerEvidencia,
  aoSelecionarFator,
}: BlocoRedFlagsProps) {
  const [filtro, setFiltro] = useState<ReadonlySet<FiltroStatus>>(new Set(['todas']));
  const escolhido = [...filtro][0] ?? 'todas';

  const ordenadas = useMemo(
    () =>
      [...redFlags].sort(
        (a, b) =>
          ORDEM_SEVERIDADE[a.severidade] - ORDEM_SEVERIDADE[b.severidade] ||
          b.data.localeCompare(a.data),
      ),
    [redFlags],
  );
  const visiveis =
    escolhido === 'todas' ? ordenadas : ordenadas.filter((f) => f.status === escolhido);

  const contar = (status: StatusRedFlag) => redFlags.filter((f) => f.status === status).length;

  return (
    <Card
      id="red-flags"
      as="section"
      aria-labelledby="titulo-red-flags"
      className="scroll-mt-[88px]"
    >
      <SectionHeader
        nivel={2}
        titulo={`Red flags (${redFlags.length})`}
        descricao="Ocorrências que o motor destacou nesta varredura, por severidade."
        acoes={
          <FilterChips<FiltroStatus>
            rotulo="Filtrar red flags por status"
            modo="unico"
            opcoes={[
              { valor: 'todas', rotulo: 'Todas', contagem: redFlags.length },
              { valor: 'nova', rotulo: 'Novas', contagem: contar('nova') },
              { valor: 'analisada', rotulo: 'Analisadas', contagem: contar('analisada') },
              { valor: 'resolvida', rotulo: 'Resolvidas', contagem: contar('resolvida') },
            ]}
            selecionados={filtro}
            aoMudar={(proximos) => setFiltro(proximos.size === 0 ? new Set(['todas']) : proximos)}
          />
        }
      />
      <h2 id="titulo-red-flags" className="sr-only">
        Red flags
      </h2>

      {visiveis.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            compacto
            titulo={
              redFlags.length === 0
                ? 'Nenhuma red flag ativa'
                : 'Nenhuma red flag neste filtro'
            }
            descricao={
              redFlags.length === 0
                ? `A varredura de ${formatarData(dataReferencia)} não encontrou ocorrências.`
                : 'Troque o filtro de status para ver as demais ocorrências.'
            }
          />
        </div>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {visiveis.map((flag) => (
            <LinhaRedFlag
              key={flag.id}
              flag={flag}
              aoVerEvidencia={aoVerEvidencia}
              aoSelecionarFator={aoSelecionarFator}
            />
          ))}
        </ul>
      )}

      <p className="type-caption mt-2 border-t border-line-subtle pt-2">
        Marcar como analisada não altera o cálculo; é registro de triagem.
      </p>
    </Card>
  );
}

function LinhaRedFlag({
  flag,
  aoVerEvidencia,
  aoSelecionarFator,
}: {
  flag: RedFlag;
  aoVerEvidencia: (evidenciaId: string) => void;
  aoSelecionarFator: (fatorId: string) => void;
}) {
  const apresentacao = SEVERIDADE[flag.severidade];
  const classes = CLASSES_RISCO[apresentacao.familia];
  const Icone = apresentacao.Icone;

  return (
    <li
      className={`flex flex-col gap-1 rounded border border-line-default border-l-2 ${classes.bordaEsquerda} bg-surface-sunken px-3 py-2`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`type-eyebrow inline-flex items-center gap-1 ${classes.texto}`}>
          <Icone size={13} strokeWidth={2.5} aria-hidden="true" />
          {apresentacao.rotulo.toUpperCase()}
        </span>
        <span className="type-body-strong min-w-0 text-fg-primary">{flag.titulo}</span>
        <span className="tnum type-body-strong ml-auto shrink-0 text-fg-primary">
          {formatarDelta(flag.impactoEmPontos, 'pts')}
        </span>
      </div>

      <p className="type-body text-fg-secondary">{flag.descricao}</p>

      <div className="type-caption flex flex-wrap items-center gap-2">
        <Badge variante="fonte" fonte={flag.fonte} tamanho="sm">
          {NOME_CURTO_FONTE[flag.fonte]}
        </Badge>
        <span>{formatarData(flag.data)}</span>
        <Badge variante="status" status={flag.status} tamanho="sm" />
        <span className="ml-auto flex flex-wrap items-center gap-1">
          {flag.fatorId ? (
            <Button
              variante="fantasma"
              tamanho="sm"
              onClick={() => aoSelecionarFator(flag.fatorId as string)}
            >
              Ver fator
            </Button>
          ) : null}
          {flag.evidenciaIds.length > 0 ? (
            <Button
              variante="fantasma"
              tamanho="sm"
              onClick={() => aoVerEvidencia(flag.evidenciaIds[0])}
            >
              Ver evidência
            </Button>
          ) : null}
          {flag.status !== 'analisada' ? (
            <Button
              variante="fantasma"
              tamanho="sm"
              onClick={() => definirStatusRedFlag(flag.id, 'analisada')}
            >
              Marcar analisada
            </Button>
          ) : null}
          {flag.status !== 'resolvida' ? (
            <Button
              variante="fantasma"
              tamanho="sm"
              onClick={() => definirStatusRedFlag(flag.id, 'resolvida')}
            >
              Marcar resolvida
            </Button>
          ) : null}
        </span>
      </div>
    </li>
  );
}
