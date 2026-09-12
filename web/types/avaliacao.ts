/**
 * Contrato de tipos do Lastro — parte 2: a saída do motor de risco.
 *
 * Transcrição literal de `specs/01-modelo-de-dados.md`. Tudo aqui é **derivado**: nunca
 * persistido no dataset, sempre recalculado por `calcular_risco()` no Flask.
 *
 * Regra de interface R6 (`03-ux-e-telas.md` §0.4): a interface **não calcula nada**. Se um
 * número não veio destes tipos, ele não existe — proibido somar, dividir ou arredondar no
 * cliente. Formatação, e só formatação, em `lib/format.ts`.
 */

import type {
  CodigoRecomendacao,
  DimensaoId,
  Evidencia,
  FonteId,
  Rating,
  Severidade,
  StatusRedFlag,
  Tendencia,
  TipoOperacao,
} from './dominio';

export interface FatorCalculado {
  id: string;
  dimensao: DimensaoId;
  /** Texto pronto para a UI, em pt-BR. */
  rotulo: string;
  /** ex.: `atraso médio subiu de 3 para 11 dias`. */
  detalhe?: string | null;
  /** Sempre positivo. */
  pontos: number;
  direcao: 'risco' | 'protecao';
  /** `peso(dimensão) × pontos × sinal`. A soma de todos reconstrói o score (invariante I2). */
  impactoGlobal: number;
  /** Após redistribuição de saturação. */
  impactoGlobalAjustado: number;
  fonte: FonteId;
  evidenciaIds: string[];
}

export interface DimensaoAvaliada {
  id: DimensaoId;
  rotulo: string;
  /** 0..1000 */
  score: number;
  /** 0..1 — a soma dos sete pesos é exatamente 1,00 (invariante I1). */
  peso: number;
  /** `score × peso`. */
  contribuicao: number;
  tendencia: Tendencia;
  fatores: FatorCalculado[];
  fontes: FonteId[];
  saturou: boolean;
}

export interface ProbabilidadeDeDefault {
  /** 0..1 */
  pd6m: number;
  /** 0..1 */
  pd12m: number;
  /** 0..1 */
  pd24m: number;
  /** Texto curto explicando a derivação, exibido em tooltip. */
  metodo: string;
}

export interface SinalRJ {
  rotulo: string;
  pontos: number;
}

export interface RiscoRJ {
  /** 0..1, ou 1 quando o evento já ocorreu. Jamais plotado na mesma escala do PD. */
  probabilidade12m: number;
  eventoJaOcorrido: boolean;
  /** 0..100 */
  rjIndex: number;
  rjIndexEfetivo: number;
  elegivel: boolean;
  /** ex.: produtor rural PF sem livro-caixa digital (Lei 14.112/2020). */
  motivoInelegibilidade?: string | null;
  sinais: SinalRJ[];
}

export interface StayPeriod {
  ativo: boolean;
  /** ISO date. */
  dataDeferimento: string;
  diasDecorridos: number;
  diasRestantes: number;
  /** O que a Krill Tech **não** pode fazer. */
  bloqueios: string[];
  /** O que segue possível (crédito extraconcursal). */
  permitido: string[];
}

export interface VetoAtivo {
  id: string;
  rotulo: string;
  efeito: 'FORCA_D' | 'TETO_C';
  justificativa: string;
  evidenciaIds: string[];
}

export interface ExposicaoCalculada {
  exposicaoTotal: number;
  limiteAprovado: number;
  limiteUtilizadoPct: number;
  aVencer90d: number;
  emAtraso: number;
  porTipoOperacao: Record<TipoOperacao, number>;
  valorExtraconcursal: number;
  valorConcursal: number;
  coberturaExtraconcursal: number;
  coberturaTotal: number;
  exposicaoProtegida: number;
  exposicaoEmRisco: number;
  /** O número que ninguém mais mostra. Ver `02` §10. */
  exposicaoEmRiscoEmRJ: number;
}

export interface RedFlag {
  id: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  /** ISO date. */
  data: string;
  fonte: FonteId;
  /** Negativo. */
  impactoEmPontos: number;
  /** Mutável na sessão do analista — ver `lib/sessao.ts`. */
  status: StatusRedFlag;
  evidenciaIds: string[];
  fatorId?: string | null;
}

export interface AcaoRecomendada {
  id: string;
  /** Já parametrizado com os números do cliente. */
  rotulo: string;
  detalhe?: string | null;
  prioridade: 1 | 2 | 3;
}

/** Texto literal e não dispensável exigido pela invariante I9 / regra R3. */
export const AVISO_DECISAO_HUMANA =
  'Decisão final sujeita à avaliação do analista responsável.' as const;

export type AvisoDecisaoHumana = typeof AVISO_DECISAO_HUMANA;

export interface Recomendacao {
  codigo: CodigoRecomendacao;
  rotulo: string;
  acoes: AcaoRecomendada[];
  prazoReavaliacaoDias: number;
  /** Preenchido pelo LLM em runtime; nunca vem do dataset. Ver `04-camada-llm.md`. */
  explicacao?: string | null;
  aviso: AvisoDecisaoHumana;
}

/** `api/models/avaliacao.py::AuditoriaDeFechamento`. */
export interface AuditoriaDeFechamento {
  somaImpactos: number;
  scoreReconstruido: number;
  /** Deve ser 0 (tolerância 0,5) para os 18 clientes. Invariante I2. */
  diferenca: number;
}

export interface AvaliacaoDeRisco {
  clienteId: string;
  /** ISO date. */
  dataReferencia: string;
  scoreCalculado: number;
  ratingCalculado: Rating;
  /** Difere de `ratingCalculado` quando há veto ativo — exibidos lado a lado (§4.2). */
  ratingFinal: Rating;
  vetosAtivos: VetoAtivo[];
  dimensoes: DimensaoAvaliada[];
  pd: ProbabilidadeDeDefault;
  riscoRJ: RiscoRJ;
  stayPeriod?: StayPeriod | null;
  exposicao: ExposicaoCalculada;
  tendencia: Tendencia;
  redFlags: RedFlag[];
  recomendacao: Recomendacao;
  evidencias: Evidencia[];
  auditoria: AuditoriaDeFechamento;
}

/**
 * Situação de um fator entre dois instantes — vocabulário de `api/scoring/delta.py`.
 * `novo` quando só existe em t1, `removido` quando só existe em t0, `mantido` nos demais.
 */
export type SituacaoDeFator = 'novo' | 'removido' | 'mantido';

/**
 * Uma linha do "por que o score mudou" (`02-motor-de-risco.md` §11).
 * Transcrição de `api/models/eventos.py::DeltaDeFator`.
 */
export interface DeltaDeFator {
  fatorId: string;
  dimensao: DimensaoId;
  rotulo: string;
  detalhe?: string | null;
  impactoAnterior: number;
  impactoAtual: number;
  delta: number;
  situacao: SituacaoDeFator;
}

/**
 * Resultado de `scoring.delta.comparar_avaliacoes` — a comparação entre dois instantes.
 * Transcrição de `api/models/eventos.py::ComparacaoDeAvaliacoes`.
 *
 * A soma dos deltas por fator reconstrói exatamente a variação do score: é o que
 * `diferencaDeFechamento` prova, e é a invariante I6.
 *
 * Nota de contrato: `ratingAnterior`, `ratingAtual` e `tendencia` **não** existem aqui. A tela
 * que precisar deles usa o `ratingFinal`/`tendencia` das duas `AvaliacaoDeRisco` que originaram
 * a comparação, em vez de duplicar derivação no cliente (R6).
 */
export interface ComparacaoDeAvaliacoes {
  clienteId: string;
  /** ISO date do snapshot de comparação. */
  dataAnterior: string;
  /** ISO date do snapshot corrente. */
  dataAtual: string;
  scoreAnterior: number;
  scoreAtual: number;
  deltaScore: number;
  /** Ordenado por `|delta|` decrescente. */
  fatores: DeltaDeFator[];
  /** `scoreAtual − scoreAnterior − Σ delta`. Deve ser 0 (tolerância 0,5). Invariante I6. */
  diferencaDeFechamento: number;
}
