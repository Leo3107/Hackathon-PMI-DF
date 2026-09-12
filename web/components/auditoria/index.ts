/**
 * Trilha de auditoria — ponto único de importação.
 *
 * ```ts
 * import { PaginaDeAuditoria } from '@/components/auditoria';
 * ```
 *
 * Especificação: `specs/03-ux-e-telas.md` §8.
 */

export { PaginaDeAuditoria } from './PaginaDeAuditoria';

export {
  LIMITE_JUSTIFICATIVA,
  ROTULO_DECISAO,
  ROTULO_FILTRO_AUDITORIA,
  ROTULO_RECOMENDACAO,
  clientesDaTrilha,
  estatisticasDaTrilha,
  filtrarTrilha,
  fraseDeDivergencia,
  justificativaCurta,
  resumoDaDivergencia,
  unirTrilha,
  type ClienteDaTrilha,
  type CriteriosDaTrilha,
  type EstatisticasDaTrilha,
  type FiltroAuditoria,
} from './trilha';
