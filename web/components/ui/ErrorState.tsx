'use client';

import { RotateCcw, ServerCrash } from 'lucide-react';
import { useState } from 'react';

import { Button } from './Button';
import { cn } from './cn';

export interface ErrorStateProps {
  titulo?: string;
  /** Mensagem técnica, colapsada por padrão atrás de "Ver detalhes". */
  detalhe?: string;
  aoTentarNovamente?: () => void;
  compacto?: boolean;
  className?: string;
}

/**
 * Falha de carregamento (spec §6.22). **Neutro, sem vermelho**: vermelho
 * significa "este cliente é crítico", não "a API caiu" (spec §2).
 */
export function ErrorState({
  titulo = 'Não foi possível carregar',
  detalhe,
  aoTentarNovamente,
  compacto = false,
  className,
}: ErrorStateProps) {
  const [aberto, setAberto] = useState(false);

  return (
    <div
      role="alert"
      className={cn(
        'flex w-full flex-col items-center justify-center gap-3 px-4 text-center sm:px-6',
        compacto ? 'min-h-40 py-6' : 'min-h-80 py-12',
        className,
      )}
    >
      <span className="inline-flex size-14 items-center justify-center rounded-md bg-surface-input">
        <ServerCrash size={32} strokeWidth={1.5} className="text-fg-tertiary" aria-hidden="true" />
      </span>
      <p className="type-section-title max-w-full break-words text-fg-secondary">{titulo}</p>
      {detalhe ? (
        <div className="flex w-full min-w-0 flex-col items-center gap-2">
          <button
            type="button"
            aria-expanded={aberto}
            onClick={() => setAberto((anterior) => !anterior)}
            className="transicao-controle type-caption rounded-sm underline underline-offset-2 hover:text-fg-secondary"
          >
            {aberto ? 'Ocultar detalhes' : 'Ver detalhes'}
          </button>
          {aberto ? (
            <pre className="type-mono max-w-full overflow-x-auto rounded-sm border border-line-subtle bg-surface-sunken p-3 text-left break-words whitespace-pre-wrap scrollbar-thin sm:max-w-[64ch]">
              {detalhe}
            </pre>
          ) : null}
        </div>
      ) : null}
      {aoTentarNovamente ? (
        <Button
          variante="secundario"
          iconeEsquerda={RotateCcw}
          onClick={aoTentarNovamente}
          className="w-full sm:w-auto"
        >
          Tentar novamente
        </Button>
      ) : null}
    </div>
  );
}
