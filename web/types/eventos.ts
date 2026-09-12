/**
 * Contrato de tipos do Lastro — parte 3: série histórica, eventos, alertas e trilha de auditoria.
 *
 * Transcrição literal de `specs/01-modelo-de-dados.md`.
 */

import type {
  CodigoRecomendacao,
  DecisaoAnalista,
  FatosDoCliente,
  FonteId,
  Rating,
  Severidade,
  TipoEvento,
} from './dominio';

export interface SnapshotHistorico {
  /** ISO date. */
  data: string;
  fatos: FatosDoCliente;
}

export interface EventoDeRisco {
  id: string;
  clienteId: string;
  /** ISO date. */
  data: string;
  tipo: TipoEvento;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  fonte: FonteId;
  /** Derivado do recálculo do snapshot — nunca escrito à mão (D4). */
  scoreApos: number;
  deltaScore: number;
  evidenciaIds: string[];
}

export interface Alerta {
  id: string;
  clienteId: string;
  clienteNome: string;
  /** ISO date. */
  data: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  impacto: string;
  acaoRecomendada: string;
  /** Estado de sessão: sobrescrito por `lib/sessao.ts` no cliente. */
  lido: boolean;
  eventoId?: string | null;
}

export interface RegistroAuditoria {
  id: string;
  clienteId: string;
  clienteNome: string;
  /** Persona fixa de demonstração — ver `components/shell/persona.ts`. */
  analista: string;
  /** ISO datetime. */
  dataHora: string;
  scoreNoMomento: number;
  ratingNoMomento: Rating;
  recomendacaoGerada: CodigoRecomendacao;
  decisaoAnalista: DecisaoAnalista;
  justificativa: string;
  /** `true` quando o analista decidiu diferente do recomendado. Destacado na UI. */
  divergiuDaRecomendacao: boolean;
}

/** Corpo aceito por `POST /api/auditoria`. O `id` é atribuído pelo servidor. */
export type NovoRegistroAuditoria = Omit<RegistroAuditoria, 'id'>;
