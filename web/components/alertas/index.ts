/**
 * Central de alertas — ponto único de importação.
 *
 * ```ts
 * import { PaginaDeAlertas } from '@/components/alertas';
 * ```
 *
 * Especificação: `specs/03-ux-e-telas.md` §7.
 */

export { PaginaDeAlertas } from './PaginaDeAlertas';
export { FalhaDoMotor, type FalhaDoMotorProps } from './FalhaDoMotor';

export {
  ROTULO_AGRUPAMENTO,
  ROTULO_BUCKET,
  ROTULO_FILTRO,
  ROTULO_SEVERIDADE,
  SEVERIDADES,
  agrupar,
  aplicarLeitura,
  bucketDaData,
  contarNaoLidos,
  contarPorSeveridade,
  filtrarAlertas,
  idadeEmDias,
  paraAlertRow,
  temCriticoNaoLido,
  textoDoVazio,
  type Agrupamento,
  type BucketDeData,
  type CriteriosDeAlertas,
  type FiltroAlerta,
  type GrupoDeAlertas,
  type TextoDeVazio,
} from './agrupamento';
