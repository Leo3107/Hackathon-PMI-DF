'use client';

import { CircuitBoard, LoaderCircle, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from './cn';
import { ErrorState } from './ErrorState';

export type EstadoStreaming =
  | 'aguardando'
  | 'transmitindo'
  | 'concluido'
  | 'degradado'
  | 'erro';

export interface StreamingTextProps {
  /** Acumulado até agora. */
  texto: string;
  estado: EstadoStreaming;
  /** Padrão 4 — usado em `aguardando`. */
  linhasEsqueleto?: number;
  origem: 'llm' | 'deterministico';
  /** Ex.: "gpt-5.4-mini". */
  modelo?: string;
  aoTentarNovamente?: () => void;
  className?: string;
}

const LARGURAS = ['92%', '100%', '78%', '60%'];

/** Markdown mínimo: parágrafos, `**negrito**` e listas com "- ". */
function renderizarInline(trecho: string, chave: string): ReactNode[] {
  return trecho.split(/(\*\*[^*]+\*\*)/g).map((parte, indice) =>
    parte.startsWith('**') && parte.endsWith('**') && parte.length > 4 ? (
      <strong key={`${chave}-${indice}`} className="font-semibold text-fg-primary">
        {parte.slice(2, -2)}
      </strong>
    ) : (
      <span key={`${chave}-${indice}`}>{parte}</span>
    ),
  );
}

function Prosa({ texto, cursor }: { texto: string; cursor: boolean }) {
  const blocos = texto.split(/\n{2,}/);
  return (
    <div className="type-prose flex flex-col gap-3 text-fg-secondary">
      {blocos.map((bloco, indiceBloco) => {
        const linhas = bloco.split('\n');
        const ultimo = indiceBloco === blocos.length - 1;
        const lista = linhas.every((linha) => linha.trimStart().startsWith('- ')) && linhas[0] !== '';

        if (lista) {
          return (
            <ul key={indiceBloco} className="flex list-disc flex-col gap-1 pl-5">
              {linhas.map((linha, indice) => (
                <li key={indice}>{renderizarInline(linha.trimStart().slice(2), `${indiceBloco}-${indice}`)}</li>
              ))}
            </ul>
          );
        }

        return (
          <p key={indiceBloco}>
            {renderizarInline(bloco, String(indiceBloco))}
            {cursor && ultimo ? (
              <span className="streaming-cursor ml-0.5" aria-hidden="true" />
            ) : null}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Prosa do LLM (spec §6.20). Todo número que aparece aqui é **texto**: a fonte
 * de verdade é o motor determinístico, e nenhum número desta prosa recebe cor
 * de risco (invariante I7).
 */
export function StreamingText({
  texto,
  estado,
  linhasEsqueleto = 4,
  origem,
  modelo,
  aoTentarNovamente,
  className,
}: StreamingTextProps) {
  if (estado === 'erro') {
    return (
      <ErrorState
        compacto
        titulo="Não foi possível gerar o parecer textual"
        aoTentarNovamente={aoTentarNovamente}
        className={className}
      />
    );
  }

  if (estado === 'aguardando') {
    return (
      <div className={cn('flex flex-col gap-2', className)} aria-busy="true">
        <p className="type-eyebrow inline-flex items-center gap-1.5">
          <LoaderCircle size={12} strokeWidth={2} className="girando" aria-hidden="true" />
          Gerando parecer
        </p>
        {Array.from({ length: linhasEsqueleto }).map((_, indice) => (
          <span
            key={indice}
            className="esqueleto h-[14px]"
            style={{ width: LARGURAS[indice % LARGURAS.length] }}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-2', className)} aria-live="polite">
      <Prosa texto={texto} cursor={estado === 'transmitindo'} />

      {estado === 'concluido' ? (
        <p className="type-caption no-print inline-flex items-center gap-1.5">
          <Sparkles size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          {origem === 'llm'
            ? `Gerado por IA${modelo ? ` · ${modelo}` : ''} · os números vêm do motor determinístico`
            : 'Texto padrão · os números vêm do motor determinístico'}
        </p>
      ) : null}

      {estado === 'degradado' ? (
        <p className="type-caption inline-flex items-center gap-1.5">
          <CircuitBoard size={12} strokeWidth={2} className="shrink-0" aria-hidden="true" />
          Texto padrão — LLM indisponível ou orçamento atingido
        </p>
      ) : null}
    </div>
  );
}
