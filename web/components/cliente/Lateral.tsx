'use client';

/**
 * Coluna lateral fixa da página do cliente (`03-ux-e-telas.md` §4.4).
 *
 * Quatro cards, nesta ordem: **score** (com o par calculado × final quando há veto),
 * **PD**, **risco de RJ** e **recomendação**. São as respostas de "qual o risco" e "o que fazer",
 * e por isso ficam visíveis durante toda a rolagem.
 *
 * Proibição dura implementada aqui: PD e risco de RJ **não compartilham card, eixo, barra nem
 * escala de cor**. São perguntas diferentes — "vai atrasar?" e "vai pedir recuperação judicial?"
 * — e um cliente pode pagar em dia e ainda assim pedir RJ.
 */

import { Gavel, Info, ListOrdered, Scale } from 'lucide-react';
import type { ReactNode } from 'react';

import {
  Badge,
  Button,
  CLASSES_RISCO,
  Card,
  ProgressBar,
  RATING,
  RatingBadge,
  ScoreGauge,
  StreamingText,
  Termo,
  Tooltip,
  TrendIndicator,
  type FamiliaRisco,
} from '@/components/ui';
import {
  formatarDelta,
  formatarData,
  formatarDias,
  formatarNumero,
  formatarPercentual,
  formatarProbabilidadeRJ,
  formatarScore,
} from '@/lib/format';
import { AVISO_DECISAO_HUMANA } from '@/types';
import type {
  AvaliacaoDeRisco,
  ComparacaoDeAvaliacoes,
  ProbabilidadeDeDefault,
  Recomendacao,
  RiscoRJ,
} from '@/types';

import type { Narrativa } from './dados';

/* ------------------------------------------------------------------ */
/* Card 1 — score, e o par calculado × final quando há veto            */
/* ------------------------------------------------------------------ */

export interface CardDeScoreProps {
  avaliacao: AvaliacaoDeRisco;
  variacao: ComparacaoDeAvaliacoes | null;
  aoVerEvidencia: (evidenciaId: string) => void;
}

export function CardDeScore({ avaliacao, variacao, aoVerEvidencia }: CardDeScoreProps) {
  const emVeto = avaliacao.vetosAtivos.length > 0;
  const periodo = variacao ? '90 dias' : undefined;

  return (
    <Card
      as="section"
      aria-labelledby="titulo-score"
      destaque={emVeto ? 'd' : 'nenhum'}
      className="flex flex-col items-center gap-3"
    >
      <h2 id="titulo-score" className="sr-only">
        Score de risco
      </h2>

      <ScoreGauge
        score={avaliacao.scoreCalculado}
        ratingCalculado={avaliacao.ratingCalculado}
        ratingFinal={avaliacao.ratingFinal}
        vetos={avaliacao.vetosAtivos}
        scoreAnterior={variacao?.scoreAnterior}
        periodoDelta={periodo}
        tendencia={avaliacao.tendencia}
        tamanho="lg"
      />

      {emVeto ? (
        <ParCalculadoFinal avaliacao={avaliacao} aoVerEvidencia={aoVerEvidencia} />
      ) : (
        <div className="flex flex-col items-center gap-1.5">
          <RatingBadge rating={avaliacao.ratingFinal} tamanho="lg" />
          <p className="type-caption">{RATING[avaliacao.ratingFinal].rotulo}</p>
        </div>
      )}

      <div className="flex flex-col items-center gap-1">
        <TrendIndicator
          tendencia={avaliacao.tendencia}
          delta={variacao?.deltaScore}
          periodo={periodo}
        />
        {variacao ? (
          <p className="type-caption tnum">
            {formatarScore(variacao.scoreAnterior)} em {formatarData(variacao.dataAnterior)} →{' '}
            {formatarScore(variacao.scoreAtual)} em {formatarData(variacao.dataAtual)}
          </p>
        ) : (
          <p className="type-caption">
            Sem snapshot anterior para comparar. Avaliação de{' '}
            {formatarData(avaliacao.dataReferencia)}.
          </p>
        )}
      </div>
    </Card>
  );
}

/**
 * Exigência inegociável nº 1: havendo veto, o **score calculado** e a **classificação final**
 * aparecem lado a lado, com o motivo nomeado. O calculado nunca é escondido — escondê-lo seria
 * apagar o trabalho do motor e impedir o analista de ver o tamanho da distância entre o que os
 * dados dizem e o que a regra impõe.
 */
function ParCalculadoFinal({
  avaliacao,
  aoVerEvidencia,
}: {
  avaliacao: AvaliacaoDeRisco;
  aoVerEvidencia: (evidenciaId: string) => void;
}) {
  const veto = avaliacao.vetosAtivos[0];
  const outros = avaliacao.vetosAtivos.slice(1);

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="grid grid-cols-2 gap-2" data-teste="par-veto">
        <div className="flex flex-col items-center gap-1 rounded border border-line-default bg-surface-sunken px-2 py-3">
          <p className="type-eyebrow text-fg-tertiary">Score calculado</p>
          <p className="type-score-md tnum text-fg-secondary">
            {formatarScore(avaliacao.scoreCalculado)}
          </p>
          <RatingBadge rating={avaliacao.ratingCalculado} tamanho="sm" />
          <p className="type-caption">pelo motor</p>
        </div>
        <div className="flex flex-col items-center gap-1 rounded border border-risk-d-line bg-risk-d-tint px-2 py-3">
          <p className="type-eyebrow text-fg-tertiary">Classificação final</p>
          <p className="type-score-md tnum text-fg-primary">{avaliacao.ratingFinal}</p>
          <RatingBadge rating={avaliacao.ratingFinal} tamanho="sm" aparencia="solido" />
          <p className="type-caption">por veto</p>
        </div>
      </div>

      <div className="flex flex-col gap-1 rounded border border-risk-d-line px-3 py-2">
        <p className="type-body-strong inline-flex items-start gap-1.5 text-risk-d">
          <Gavel size={14} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>VETO: {veto.rotulo}</span>
        </p>
        <p className="type-caption text-fg-secondary">{veto.justificativa}</p>
        {veto.evidenciaIds.length > 0 ? (
          <Button
            variante="fantasma"
            tamanho="sm"
            className="self-start"
            onClick={() => aoVerEvidencia(veto.evidenciaIds[0])}
          >
            Ver evidência
          </Button>
        ) : null}
        {outros.length > 0 ? (
          <ul className="type-caption flex flex-col gap-0.5 border-t border-line-subtle pt-1">
            {outros.map((extra) => (
              <li key={extra.id}>+ {extra.rotulo}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Card 2 — probabilidade de default                                   */
/* ------------------------------------------------------------------ */

/** Escala comum dos três horizontes: sem ela, a progressão 6 → 12 → 24 some. */
const ESCALA_PD = 0.6;

/**
 * Família cromática da PD. `familia="auto"` do `ProgressBar` assume "quanto maior, melhor" —
 * correto para cobertura, invertido para probabilidade de default. Os cortes acompanham as
 * faixas de rating do motor para que barra e `RatingBadge` não contem histórias diferentes.
 */
function familiaDaPd(pd: number): FamiliaRisco {
  if (pd < 0.05) return 'a';
  if (pd < 0.15) return 'b';
  if (pd < 0.3) return 'c';
  return 'd';
}

export function CardDePd({ pd }: { pd: ProbabilidadeDeDefault }) {
  const linhas: Array<{ rotulo: string; valor: number }> = [
    { rotulo: 'PD 6m', valor: pd.pd6m },
    { rotulo: 'PD 12m', valor: pd.pd12m },
    { rotulo: 'PD 24m', valor: pd.pd24m },
  ];

  return (
    <Card as="section" aria-labelledby="titulo-pd" className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="type-eyebrow text-fg-tertiary">Probabilidades</p>
        <h2 id="titulo-pd" className="type-section-title">
          <Termo sigla="PD" /> — probabilidade de default
        </h2>
      </div>

      <div className="flex flex-col gap-2">
        {linhas.map((linha) => (
          <ProgressBar
            key={linha.rotulo}
            valor={linha.valor}
            maximo={ESCALA_PD}
            familia={familiaDaPd(linha.valor)}
            rotulo={linha.rotulo}
            valorFormatado={formatarPercentual(linha.valor, 1)}
            altura={8}
          />
        ))}
      </div>

      <p className="type-caption">
        Escala comum 0–{formatarPercentual(ESCALA_PD, 0)} nos três horizontes.{' '}
        <Tooltip conteudo={pd.metodo}>
          <span tabIndex={0} className="cursor-help underline decoration-dotted">
            Como é calculada
          </span>
        </Tooltip>
        .
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Card 3 — risco de RJ, em escala própria                             */
/* ------------------------------------------------------------------ */

/** Faixas textuais do §4.4 — rótulo, nunca só cor (I8). */
function faixaDeRj(risco: RiscoRJ): { rotulo: string; familia: FamiliaRisco } {
  if (risco.eventoJaOcorrido) return { rotulo: 'OCORRIDO', familia: 'd' };
  const p = risco.probabilidade12m;
  if (p < 0.05) return { rotulo: 'BAIXO', familia: 'a' };
  if (p < 0.15) return { rotulo: 'MODERADO', familia: 'b' };
  if (p < 0.3) return { rotulo: 'ALTO', familia: 'c' };
  return { rotulo: 'CRÍTICO', familia: 'd' };
}

export function CardDeRiscoRj({ risco }: { risco: RiscoRJ }) {
  const faixa = faixaDeRj(risco);
  const classes = CLASSES_RISCO[faixa.familia];

  return (
    <Card
      as="section"
      aria-labelledby="titulo-rj"
      className="flex flex-col gap-3 border-t-2 border-t-line-strong"
    >
      <div className="flex flex-col gap-1">
        <h2 id="titulo-rj" className="type-section-title inline-flex items-center gap-2">
          <Scale size={16} strokeWidth={2} aria-hidden="true" />
          Risco de <Termo sigla="RJ" /> em 12 meses
        </h2>
        <p className="type-caption inline-flex items-center gap-1.5 text-fg-secondary">
          <Info size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          Escala própria — não comparável à <Termo sigla="PD" />
        </p>
      </div>

      {risco.elegivel ? (
        <>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className={`type-kpi tnum ${classes.texto}`}>
              {formatarProbabilidadeRJ(risco)}
            </span>
            <Badge variante="risco" familia={faixa.familia} aparencia="tint">
              {faixa.rotulo}
            </Badge>
          </div>
          <p className="type-caption tnum">
            Índice de RJ {formatarNumero(risco.rjIndex, 0)}/100
            {risco.rjIndexEfetivo !== risco.rjIndex
              ? ` · efetivo ${formatarNumero(risco.rjIndexEfetivo, 0)}/100`
              : ''}
          </p>
        </>
      ) : (
        <div className="flex flex-col gap-1 rounded border border-line-default bg-surface-sunken px-3 py-2">
          <p className="type-body-strong text-fg-primary">Não elegível a RJ</p>
          <p className="type-caption text-fg-secondary">
            {risco.motivoInelegibilidade ??
              'Sem comprovação dos requisitos da Lei 14.112/2020 para produtor rural pessoa física.'}{' '}
            Risco de RJ reduzido por inelegibilidade legal — não por saúde financeira.
          </p>
          <p className="type-caption tnum">
            Índice de RJ calculado {formatarNumero(risco.rjIndex, 0)}/100 · efetivo{' '}
            {formatarNumero(risco.rjIndexEfetivo, 0)}/100
          </p>
        </div>
      )}

      {risco.sinais.length > 0 ? (
        <ul className="flex flex-col gap-1 border-t border-line-subtle pt-2">
          {risco.sinais.map((sinal) => (
            <li
              key={sinal.rotulo}
              className="type-caption flex items-baseline justify-between gap-3 text-fg-secondary"
            >
              <span className="min-w-0">{sinal.rotulo}</span>
              <span className="tnum shrink-0 text-fg-primary">
                {formatarDelta(sinal.pontos, 'pts')}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      <p className="type-caption border-t border-line-subtle pt-2">
        Pedir recuperação judicial é decisão do devedor, não consequência de atraso. Um cliente
        adimplente com a Krill Tech pode entrar em RJ por pressão de outros credores — por isso
        este número vive fora da escala da <Termo sigla="PD" />.
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Card 4 — recomendação                                               */
/* ------------------------------------------------------------------ */

const FAMILIA_RECOMENDACAO: Record<Recomendacao['codigo'], FamiliaRisco> = {
  APROVAR: 'a',
  APROVAR_COM_MONITORAMENTO_INTENSIVO: 'b',
  APROVAR_COM_REVISAO_DE_LIMITE: 'b',
  APROVAR_COM_RESTRICOES: 'c',
  SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: 'd',
  SUSPENDER_EXPOSICAO: 'd',
};

export interface CardDeRecomendacaoProps {
  recomendacao: Recomendacao;
  narrativa: Narrativa;
}

export function CardDeRecomendacao({ recomendacao, narrativa }: CardDeRecomendacaoProps) {
  const familia = FAMILIA_RECOMENDACAO[recomendacao.codigo] ?? 'neutral';
  const classes = CLASSES_RISCO[familia];
  const acoes = [...recomendacao.acoes].sort((a, b) => a.prioridade - b.prioridade);

  return (
    <Card
      as="section"
      aria-labelledby="titulo-recomendacao"
      destaque={familia}
      className="flex flex-col gap-3"
    >
      <div className="flex flex-col gap-1">
        <p className="type-eyebrow text-fg-tertiary">Recomendação do motor</p>
        <h2
          id="titulo-recomendacao"
          className={`type-section-title inline-flex items-start gap-2 ${classes.texto}`}
        >
          <ListOrdered size={16} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden="true" />
          {recomendacao.rotulo}
        </h2>
        <p className="type-caption">
          Reavaliar em {formatarDias(recomendacao.prazoReavaliacaoDias)}.
        </p>
      </div>

      {acoes.length > 0 ? (
        <ol className="flex flex-col gap-2">
          {acoes.map((acao, indice) => (
            <li key={acao.id} className="flex gap-2">
              <span
                className="tnum type-caption mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-line-default text-fg-secondary"
                aria-hidden="true"
              >
                {indice + 1}
              </span>
              <span className="min-w-0">
                <span className="type-body block text-fg-primary">{acao.rotulo}</span>
                {acao.detalhe ? (
                  <span className="type-caption block">{acao.detalhe}</span>
                ) : null}
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      <div className="border-t border-line-subtle pt-3">
        <p className="type-eyebrow mb-1.5 text-fg-tertiary">Justificativa</p>
        <StreamingText
          texto={narrativa.texto || recomendacao.explicacao || ''}
          estado={narrativa.estado}
          origem={narrativa.origem}
          modelo={narrativa.modelo}
          linhasEsqueleto={3}
          aoTentarNovamente={narrativa.tentarNovamente}
        />
      </div>

      <AvisoDeDecisaoHumana />
    </Card>
  );
}

/**
 * Invariante I9 / regra R3. Não é dispensável, não tem botão de fechar, não é `Tooltip` e não
 * depende de rolagem dentro do card: toda superfície que recomenda algo carrega esta frase.
 */
export function AvisoDeDecisaoHumana({ children }: { children?: ReactNode }) {
  return (
    <p
      role="note"
      data-teste="aviso-decisao-humana"
      className="type-body flex items-start gap-2 rounded border border-accent-line bg-accent-tint px-3 py-2 text-fg-primary"
    >
      <Info size={14} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden="true" />
      <span>
        {AVISO_DECISAO_HUMANA}
        {children}
      </span>
    </p>
  );
}
