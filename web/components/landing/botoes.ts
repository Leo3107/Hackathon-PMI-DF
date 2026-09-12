/**
 * Classes dos CTAs da landing.
 *
 * O `Button` de `components/ui` é `<button>` de 32px para telas de trabalho; aqui os CTAs são
 * links pill grandes, à la monday.com, então as classes vivem separadas e os dois botões
 * "Entrar" (nav e hero) saem da mesma fonte para nunca divergirem.
 */

export const CTA_BASE =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-pill font-semibold ' +
  'transition-[background-color,border-color,box-shadow,transform] duration-150 ease-out ' +
  'active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-400';

/** Índigo sólido, o único acento da página. */
export const CTA_PRIMARIO = `${CTA_BASE} bg-accent-500 text-fg-inverse shadow-card hover:bg-accent-600 hover:shadow-raised`;

/** Contornado, sobre o branco do hero. */
export const CTA_SECUNDARIO = `${CTA_BASE} border border-line-strong bg-surface-card text-fg-primary hover:bg-surface-hover`;
