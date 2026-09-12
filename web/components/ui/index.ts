/**
 * Design system do Lastro — ponto único de importação.
 *
 * ```ts
 * import { Card, DataTable, ScoreGauge } from '@/components/ui';
 * ```
 *
 * Especificação: `specs/05-design-system.md`.
 */

/* Fundações --------------------------------------------------------------- */
export { cn, type ValorClasse } from './cn';
export { classeFontes, inter, jetbrainsMono } from './fontes';
export { GLOSSARIO, type TermoGlossario, type VerbeteGlossario } from './glossario';
export {
  CLASSES_RISCO,
  FAIXAS_RATING,
  ICONE_EVIDENCIA,
  JURIDICO,
  NATUREZA_GARANTIA,
  RATING,
  SEVERIDADE,
  TENDENCIA,
  ratingDoScore,
  type ApresentacaoRisco,
  type ClassesRisco,
} from './risco';
export {
  NOME_CURTO_FONTE,
  NOME_DIMENSAO,
  type Alerta,
  type DimensaoId,
  type Evidencia,
  type FamiliaRisco,
  type FatorExibido,
  type FonteId,
  type NaturezaGarantia,
  type Rating,
  type Severidade,
  type StatusRedFlag,
  type Tendencia,
  type TipoEvidencia,
  type VetoAtivo,
} from './tipos-ui';

/* Geometria e utilitários ------------------------------------------------- */
export {
  GAUGE,
  SCORE_MAXIMO,
  SCORE_MINIMO,
  ancoraTexto,
  anguloDoScore,
  comprimentoArco,
  dashOffset,
  pathArco,
  pontoNoArco,
} from './gauge-geometry';
export { PadraoHachura, idHachura, type PadraoHachuraProps } from './hachura';
export { useFocoPreso, type OpcoesFocoPreso } from './usar-foco-preso';
export { useReducedMotion } from './usar-movimento-reduzido';

/* Primitivos genéricos ---------------------------------------------------- */
export { Badge, type AparenciaBadge, type BadgeProps, type VarianteBadge } from './Badge';
export { Button, type ButtonProps, type VarianteBotao } from './Button';
export { Card, type CardProps, type DestaqueCard } from './Card';
export {
  DataTable,
  type Coluna,
  type DataTableProps,
  type Ordenacao,
  type SelecaoTabela,
} from './DataTable';
export { Drawer, type DrawerProps } from './Drawer';
export { EmptyState, type EmptyStateProps } from './EmptyState';
export { ErrorState, type ErrorStateProps } from './ErrorState';
export { FilterChips, type FilterChipsProps, type OpcaoChip } from './FilterChips';
export { IconButton, type IconButtonProps } from './IconButton';
export { KpiTile, type KpiTileProps, type VariacaoKpi } from './KpiTile';
export { Modal, type ModalProps } from './Modal';
export {
  ProgressBar,
  familiaDeCobertura,
  type MarcaProgresso,
  type ProgressBarProps,
} from './ProgressBar';
export { SearchInput, type SearchInputProps } from './SearchInput';
export { SectionHeader, type SectionHeaderProps } from './SectionHeader';
export { Tooltip, Termo, ConteudoGlossario, type LadoTooltip, type TooltipProps, type TermoProps } from './Tooltip';

/* Compostos de risco ------------------------------------------------------ */
export { AlertRow, type AlertRowProps } from './AlertRow';
export { CostCounter, type CostCounterProps } from './CostCounter';
export { EvidenceCard, type EvidenceCardProps, type FatorRelacionado } from './EvidenceCard';
export { FactorBar, type FactorBarProps } from './FactorBar';
export { RatingBadge, type RatingBadgeProps } from './RatingBadge';
export { ScoreGauge, type ScoreGaugeProps } from './ScoreGauge';
export { StackedBar, type SegmentoBarra, type StackedBarProps } from './StackedBar';
export {
  StreamingText,
  type EstadoStreaming,
  type StreamingTextProps,
} from './StreamingText';
export { Timeline, type ItemTimeline, type TimelineProps } from './Timeline';
export { TrendIndicator, type TrendIndicatorProps } from './TrendIndicator';
