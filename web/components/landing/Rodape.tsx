/** Rodapé de uma linha: nome e o que o produto é. Nada de colunas de links. */
export function Rodape() {
  return (
    <footer className="mt-auto border-t border-line-subtle bg-surface-page px-4 py-8 sm:px-6">
      <div className="mx-auto flex w-full max-w-[1152px] flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <span className="font-display text-[18px] font-bold tracking-tight text-fg-primary">Lastro</span>
        <span className="text-[14px] text-fg-tertiary">
          Inteligência de risco de crédito no agronegócio
        </span>
      </div>
    </footer>
  );
}
