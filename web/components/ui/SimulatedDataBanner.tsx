import { FlaskConical } from 'lucide-react';

import { cn } from './cn';

export interface SimulatedDataBannerProps {
  /** `app`: faixa fixa no topo. `impressao`: cabeçalho do PDF (§10.3). */
  variante?: 'app' | 'impressao';
  className?: string;
}

export const TEXTO_DADOS_SIMULADOS =
  'DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público';

/**
 * Aviso de dados simulados (spec §6.23, invariante I10: aparece em toda rota e
 * em todo PDF). Neutro — **não** usa âmbar, que é semântica de risco.
 *
 * As listras diagonais são a única exceção à proibição de gradiente fora do
 * gauge, permitida por serem textura de aviso e não decoração.
 */
export function SimulatedDataBanner({
  variante = 'app',
  className,
}: SimulatedDataBannerProps) {
  return (
    <div
      role="note"
      className={cn(
        'flex w-full items-center justify-center gap-2 border-b border-line-strong bg-surface-input px-4',
        'type-eyebrow text-fg-secondary',
        variante === 'app'
          ? 'no-print h-[var(--height-banner)]'
          : 'h-[var(--height-banner)]',
        className,
      )}
      style={{
        backgroundImage:
          'repeating-linear-gradient(135deg, transparent 0 10px, rgb(255 255 255 / 0.025) 10px 12px)',
      }}
    >
      <FlaskConical size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      <span>{TEXTO_DADOS_SIMULADOS}</span>
    </div>
  );
}
