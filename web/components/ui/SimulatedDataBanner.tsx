import { FlaskConical } from 'lucide-react';

import { cn } from './cn';

export interface SimulatedDataBannerProps {
  /** `app`: faixa fixa no topo. `impressao`: cabeçalho do PDF (§10.3). */
  variante?: 'app' | 'impressao';
  className?: string;
}

export const TEXTO_DADOS_SIMULADOS =
  'Dados simulados. Protótipo demonstrativo, nenhuma consulta real a órgão público.';

/**
 * Aviso de dados simulados (spec §6.23, invariante I10: aparece em toda rota e
 * em todo PDF). Neutro — **não** usa âmbar, que é semântica de risco.
 *
 * Sem textura: a hachura diagonal era adorno, e o que faz o aviso ser lido é o
 * texto com o frasco ao lado, não o fundo listrado.
 */
export function SimulatedDataBanner({
  variante = 'app',
  className,
}: SimulatedDataBannerProps) {
  return (
    <div
      role="note"
      className={cn(
        'flex w-full items-center justify-center gap-2 border-b border-line-default bg-surface-input px-4',
        'text-[11px]/[16px] font-medium text-fg-tertiary',
        variante === 'app'
          ? 'no-print h-[var(--height-banner)]'
          : 'h-[var(--height-banner)]',
        className,
      )}
    >
      <FlaskConical size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
      <span>{TEXTO_DADOS_SIMULADOS}</span>
    </div>
  );
}
