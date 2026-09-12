/**
 * Tipos estreitos de que os primitivos do design system dependem.
 *
 * Espelham `specs/01-modelo-de-dados.md`. Ficam aqui — e não em `types/` —
 * porque o design system é construído em paralelo aos contratos de domínio;
 * como são uniões de literais e interfaces estruturais, os tipos oficiais de
 * `@/types` são atribuíveis a estes sem conversão quando chegarem.
 */

export type Rating = 'A' | 'B' | 'C' | 'D';

export type Tendencia = 'melhorando' | 'estavel' | 'deteriorando' | 'deterioracao_acelerada';

export type Severidade = 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAIXA';

export type StatusRedFlag = 'nova' | 'analisada' | 'resolvida';

export type NaturezaGarantia = 'EXTRACONCURSAL' | 'CONCURSAL';

export type DimensaoId =
  | 'comportamental'
  | 'juridico'
  | 'fiscal'
  | 'agroclimatico'
  | 'cadastral'
  | 'ambiental'
  | 'garantias';

export type FonteId =
  | 'RECEITA_FEDERAL'
  | 'REDESIM'
  | 'DATAJUD_CNJ'
  | 'DJE'
  | 'CARTORIO_PROTESTO'
  | 'PGFN'
  | 'TST_CNDT'
  | 'CAIXA_CRF_FGTS'
  | 'SICAR'
  | 'IBAMA'
  | 'CONAB'
  | 'MAPA_ZARC'
  | 'INMET'
  | 'INTERNO_KRILLTECH';

export type TipoEvidencia =
  | 'CERTIDAO'
  | 'PROCESSO'
  | 'PUBLICACAO'
  | 'CADASTRO'
  | 'LAUDO'
  | 'SERIE_HISTORICA'
  | 'INTERNO';

/** Família cromática do §2.1 — resolve para `--color-risk-{familia}` e variantes. */
export type FamiliaRisco = 'a' | 'b' | 'c' | 'd' | 'neutral';

export interface Evidencia {
  id: string;
  fonte: FonteId;
  nomeFonte: string;
  tipo: TipoEvidencia;
  titulo: string;
  resumo: string;
  dataConsulta: string;
  dataDocumento?: string;
  /** Sempre true nesta versão: renderiza o selo "simulado" (D11.6). */
  simulada: true;
  urlFicticia?: string;
  fatoresRelacionados: string[];
}

export interface Alerta {
  id: string;
  clienteId: string;
  clienteNome: string;
  data: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  impacto: string;
  acaoRecomendada: string;
  lido: boolean;
  eventoId?: string;
}

export interface VetoAtivo {
  id: string;
  rotulo: string;
  efeito: 'FORCA_D' | 'TETO_C';
  justificativa: string;
  evidenciaIds: string[];
}

/** Subconjunto de `FatorCalculado` que `FactorBar` consome. */
export interface FatorExibido {
  id: string;
  rotulo: string;
  detalhe?: string;
  direcao: 'risco' | 'protecao';
  dimensao?: DimensaoId;
  /** `impactoGlobalAjustado` (contribuição) ou o delta do período. */
  impacto: number;
}

/** Rótulos humanos das fontes, para `Badge variante="fonte"`. */
export const NOME_CURTO_FONTE: Record<FonteId, string> = {
  RECEITA_FEDERAL: 'Receita Federal',
  REDESIM: 'REDESIM',
  DATAJUD_CNJ: 'DataJud — CNJ',
  DJE: 'Diário da Justiça',
  CARTORIO_PROTESTO: 'Cartório de protesto',
  PGFN: 'PGFN',
  TST_CNDT: 'TST — CNDT',
  CAIXA_CRF_FGTS: 'Caixa — CRF/FGTS',
  SICAR: 'SICAR',
  IBAMA: 'IBAMA',
  CONAB: 'CONAB',
  MAPA_ZARC: 'MAPA — ZARC',
  INMET: 'INMET',
  INTERNO_KRILLTECH: 'Interno — Krill Tech',
};

/** Rótulos das sete dimensões do motor. */
export const NOME_DIMENSAO: Record<DimensaoId, string> = {
  comportamental: 'Comportamental',
  juridico: 'Jurídico',
  fiscal: 'Fiscal',
  agroclimatico: 'Agroclimático',
  cadastral: 'Cadastral',
  ambiental: 'Ambiental',
  garantias: 'Garantias',
};
