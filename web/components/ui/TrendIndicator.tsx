import { cn } from './cn';
import { formatarDelta } from '@/lib/format';
import { CLASSES_RISCO, TENDENCIA } from './risco';
import type { Tendencia } from './tipos-ui';
import { Tooltip } from './Tooltip';

export interface TrendIndicatorProps {
  tendencia: Tendencia;
  /** Variação de score no período; renderizada por `formatarDelta`. */
  delta?: number;
  /** Delta já formatado pelo chamador; tem precedência sobre `delta`. */
  deltaTexto?: string;
  /** Ex.: "90d" → "−108 · 90d". */
  periodo?: string;
  tamanho?: 'sm' | 'md';
  /** Exige (e recebe automaticamente) tooltip com o rótulo completo. */
  somenteIcone?: boolean;
  /** Em `sm`, usa `rotuloCurto` em vez do rótulo completo. */
  rotuloCurto?: boolean;
  className?: string;
}

/**
 * Tendência do score (spec §6.5): `[Ícone] Rótulo  −108 · 90d`.
 *
 * Cor + rótulo textual + ícone, sempre os três — nenhum estado de risco é
 * comunicado só por cor (spec §3).
 */
export function TrendIndicator({
  tendencia,
  delta,
  deltaTexto,
  periodo,
  tamanho = 'md',
  somenteIcone = false,
  rotuloCurto,
  className,
}: TrendIndicatorProps) {
  const apresentacao = TENDENCIA[tendencia];
  const Icone = apresentacao.Icone;
  const classes = CLASSES_RISCO[apresentacao.familia];
  const usarCurto = rotuloCurto ?? tamanho === 'sm';
  const texto = usarCurto ? apresentacao.rotuloCurto : apresentacao.rotulo;

  const textoDelta = deltaTexto ?? (delta === undefined ? null : formatarDelta(delta));

  const sufixo = [textoDelta, periodo ?? null].filter(
    (parte): parte is string => parte !== null,
  );

  const descricao = [
    apresentacao.rotulo,
    textoDelta === null ? null : `variação de ${textoDelta} pontos`,
    periodo ? `em ${periodo}` : null,
  ]
    .filter(Boolean)
    .join(', ');

  if (somenteIcone) {
    return (
      <Tooltip conteudo={descricao}>
        <span
          role="img"
          aria-label={descricao}
          tabIndex={0}
          className={cn('inline-flex items-center rounded-sm', classes.texto, className)}
        >
          <Icone size={tamanho === 'sm' ? 14 : 16} strokeWidth={2} aria-hidden="true" />
        </span>
      </Tooltip>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap',
        tamanho === 'sm' ? 'text-[12px]/[16px]' : 'text-[13px]/[20px]',
        'font-medium',
        classes.texto,
        className,
      )}
      title={descricao}
    >
      <Icone size={tamanho === 'sm' ? 14 : 16} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      <span>{texto}</span>
      {sufixo.length > 0 ? <span className="tnum">{sufixo.join(' · ')}</span> : null}
    </span>
  );
}
