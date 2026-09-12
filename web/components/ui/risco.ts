import {
  Building2,
  ChevronsDown,
  CircleAlert,
  ClipboardList,
  Database,
  FileCheck,
  Gavel,
  Hourglass,
  Info,
  LineChart,
  Lock,
  LockOpen,
  MoveRight,
  Newspaper,
  OctagonAlert,
  Scale,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';

import type {
  FamiliaRisco,
  NaturezaGarantia,
  Rating,
  Severidade,
  Tendencia,
  TipoEvidencia,
} from './tipos-ui';

/**
 * Redundância de canal — trio obrigatório (spec §3).
 *
 * Nenhum estado de risco é comunicado só por cor. Cada estado tem
 * **cor + rótulo textual + ícone `lucide-react`** fixos, centralizados aqui e
 * consumidos por `Badge`, `RatingBadge`, `TrendIndicator`, `AlertRow`,
 * `ScoreGauge` e pelos gráficos.
 */
export interface ApresentacaoRisco {
  /** Resolve para `--color-risk-{familia}`, `-tint`, `-line`. */
  familia: FamiliaRisco;
  /** Texto SEMPRE renderizado (visually-hidden apenas em ícone isolado com aria-label). */
  rotulo: string;
  /** Para células estreitas. */
  rotuloCurto: string;
  Icone: LucideIcon;
}

export const RATING: Record<Rating, ApresentacaoRisco> = {
  A: { familia: 'a', rotulo: 'Baixo risco', rotuloCurto: 'A', Icone: ShieldCheck },
  B: { familia: 'b', rotulo: 'Risco moderado', rotuloCurto: 'B', Icone: Shield },
  C: { familia: 'c', rotulo: 'Risco elevado', rotuloCurto: 'C', Icone: ShieldAlert },
  D: { familia: 'd', rotulo: 'Risco crítico · Alerta de RJ', rotuloCurto: 'D', Icone: ShieldX },
};

export const SEVERIDADE: Record<Severidade, ApresentacaoRisco> = {
  CRITICA: { familia: 'd', rotulo: 'Crítica', rotuloCurto: 'CRÍT.', Icone: OctagonAlert },
  ALTA: { familia: 'c', rotulo: 'Alta', rotuloCurto: 'ALTA', Icone: TriangleAlert },
  MEDIA: { familia: 'b', rotulo: 'Média', rotuloCurto: 'MÉDIA', Icone: CircleAlert },
  BAIXA: { familia: 'neutral', rotulo: 'Baixa', rotuloCurto: 'BAIXA', Icone: Info },
};

export const TENDENCIA: Record<Tendencia, ApresentacaoRisco> = {
  melhorando: { familia: 'a', rotulo: 'Melhorando', rotuloCurto: 'Melhor.', Icone: TrendingUp },
  estavel: { familia: 'neutral', rotulo: 'Estável', rotuloCurto: 'Estável', Icone: MoveRight },
  deteriorando: { familia: 'c', rotulo: 'Deteriorando', rotuloCurto: 'Deter.', Icone: TrendingDown },
  deterioracao_acelerada: {
    familia: 'd',
    rotulo: 'Deterioração acelerada',
    rotuloCurto: 'Acelerada',
    Icone: ChevronsDown,
  },
};

/**
 * Conceitos jurídicos com ícone fixo. Extraconcursal usa verde porque é
 * **proteção que sobrevive à RJ**; concursal usa laranja porque **entra no
 * plano com deságio**. Semântica de risco legítima (motor §10), não decoração.
 */
export const JURIDICO = {
  veto: { familia: 'd' as FamiliaRisco, rotulo: 'Veto', Icone: Gavel },
  tetoC: { familia: 'c' as FamiliaRisco, rotulo: 'Teto C', Icone: Gavel },
  stayPeriod: { familia: 'd' as FamiliaRisco, rotulo: 'Stay Period', Icone: Hourglass },
  extraconcursal: { familia: 'a' as FamiliaRisco, rotulo: 'Extraconcursal', Icone: Lock },
  concursal: { familia: 'c' as FamiliaRisco, rotulo: 'Concursal', Icone: LockOpen },
} as const;

export const NATUREZA_GARANTIA: Record<NaturezaGarantia, ApresentacaoRisco> = {
  EXTRACONCURSAL: {
    familia: 'a',
    rotulo: 'Extraconcursal',
    rotuloCurto: 'Extra.',
    Icone: Lock,
  },
  CONCURSAL: { familia: 'c', rotulo: 'Concursal', rotuloCurto: 'Conc.', Icone: LockOpen },
};

/** Ícone por tipo de evidência (spec §6.18). */
export const ICONE_EVIDENCIA: Record<TipoEvidencia, LucideIcon> = {
  CERTIDAO: FileCheck,
  PROCESSO: Scale,
  PUBLICACAO: Newspaper,
  CADASTRO: Building2,
  LAUDO: ClipboardList,
  SERIE_HISTORICA: LineChart,
  INTERNO: Database,
};

/**
 * Classes Tailwind por família.
 *
 * Escritas por extenso (nunca interpoladas) porque o scanner do Tailwind v4 lê
 * o código-fonte como texto: `text-risk-${familia}` jamais seria gerado.
 */
export interface ClassesRisco {
  texto: string;
  fundoTint: string;
  fundoSolido: string;
  bordaLinha: string;
  bordaEsquerda: string;
  /** Referência CSS para atributos de apresentação SVG. */
  varCor: string;
  varTint: string;
  varLinha: string;
}

export const CLASSES_RISCO: Record<FamiliaRisco, ClassesRisco> = {
  a: {
    texto: 'text-risk-a',
    fundoTint: 'bg-risk-a-tint',
    fundoSolido: 'bg-risk-a',
    bordaLinha: 'border-risk-a-line',
    bordaEsquerda: 'border-l-risk-a',
    varCor: 'var(--color-risk-a)',
    varTint: 'var(--color-risk-a-tint)',
    varLinha: 'var(--color-risk-a-line)',
  },
  b: {
    texto: 'text-risk-b',
    fundoTint: 'bg-risk-b-tint',
    fundoSolido: 'bg-risk-b',
    bordaLinha: 'border-risk-b-line',
    bordaEsquerda: 'border-l-risk-b',
    varCor: 'var(--color-risk-b)',
    varTint: 'var(--color-risk-b-tint)',
    varLinha: 'var(--color-risk-b-line)',
  },
  c: {
    texto: 'text-risk-c',
    fundoTint: 'bg-risk-c-tint',
    fundoSolido: 'bg-risk-c',
    bordaLinha: 'border-risk-c-line',
    bordaEsquerda: 'border-l-risk-c',
    varCor: 'var(--color-risk-c)',
    varTint: 'var(--color-risk-c-tint)',
    varLinha: 'var(--color-risk-c-line)',
  },
  d: {
    texto: 'text-risk-d',
    fundoTint: 'bg-risk-d-tint',
    fundoSolido: 'bg-risk-d',
    bordaLinha: 'border-risk-d-line',
    bordaEsquerda: 'border-l-risk-d',
    varCor: 'var(--color-risk-d)',
    varTint: 'var(--color-risk-d-tint)',
    varLinha: 'var(--color-risk-d-line)',
  },
  neutral: {
    texto: 'text-risk-neutral',
    fundoTint: 'bg-risk-neutral-tint',
    fundoSolido: 'bg-risk-neutral',
    bordaLinha: 'border-risk-neutral-line',
    bordaEsquerda: 'border-l-risk-neutral',
    varCor: 'var(--color-risk-neutral)',
    varTint: 'var(--color-risk-neutral-tint)',
    varLinha: 'var(--color-risk-neutral-line)',
  },
};

/** Faixas de rating do motor (§5 de `02-motor-de-risco.md`), usadas pelo gauge. */
export const FAIXAS_RATING: ReadonlyArray<{
  rating: Rating;
  de: number;
  ate: number;
  familia: FamiliaRisco;
}> = [
  { rating: 'D', de: 0, ate: 399, familia: 'd' },
  { rating: 'C', de: 400, ate: 599, familia: 'c' },
  { rating: 'B', de: 600, ate: 749, familia: 'b' },
  { rating: 'A', de: 750, ate: 1000, familia: 'a' },
];

/** Rating correspondente a um score, pelas faixas acima. */
export function ratingDoScore(score: number): Rating {
  if (score >= 750) return 'A';
  if (score >= 600) return 'B';
  if (score >= 400) return 'C';
  return 'D';
}
