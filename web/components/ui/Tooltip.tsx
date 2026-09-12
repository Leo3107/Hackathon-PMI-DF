'use client';

import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react';

import { cn } from './cn';
import { GLOSSARIO, type TermoGlossario } from './glossario';

export type LadoTooltip = 'cima' | 'baixo' | 'esquerda' | 'direita';

export interface TooltipProps {
  /** Texto curto (≤ 240 caracteres) ou nó. Ignorado quando `termo` está presente. */
  conteudo?: ReactNode;
  /** Se presente, o conteúdo vem de `GLOSSARIO[termo]`. */
  termo?: TermoGlossario;
  lado?: LadoTooltip;
  /** Atraso de abertura em ms. Padrão 150. */
  atraso?: number;
  /** Gatilho. Recebe `aria-describedby`. */
  children: ReactElement<{ 'aria-describedby'?: string }>;
  className?: string;
}

const POSICAO: Record<LadoTooltip, string> = {
  cima: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  baixo: 'top-full left-1/2 -translate-x-1/2 mt-2',
  esquerda: 'right-full top-1/2 -translate-y-1/2 mr-2',
  direita: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

const SETA: Record<LadoTooltip, string> = {
  cima: 'top-full left-1/2 -translate-x-1/2 -mt-[4px] border-r border-b',
  baixo: 'bottom-full left-1/2 -translate-x-1/2 -mb-[4px] border-l border-t',
  esquerda: 'left-full top-1/2 -translate-y-1/2 -ml-[4px] border-t border-r',
  direita: 'right-full top-1/2 -translate-y-1/2 -mr-[4px] border-b border-l',
};

const OPOSTO: Record<LadoTooltip, LadoTooltip> = {
  cima: 'baixo',
  baixo: 'cima',
  esquerda: 'direita',
  direita: 'esquerda',
};

/** Conteúdo do verbete do glossário, com a expansão em negrito. */
export function ConteudoGlossario({ termo }: { termo: TermoGlossario }) {
  const verbete = GLOSSARIO[termo];
  return (
    <span>
      {verbete.titulo ? <strong className="font-semibold">{verbete.titulo} </strong> : null}
      {verbete.texto}
    </span>
  );
}

/**
 * Tooltip do design system (spec §6.13). Abre em hover **e** em foco de teclado;
 * fecha em `Esc`. Faz flip automático quando não cabe no lado pedido.
 */
export function Tooltip({
  conteudo,
  termo,
  lado = 'cima',
  atraso = 150,
  children,
  className,
}: TooltipProps) {
  const [aberto, setAberto] = useState(false);
  const [ladoEfetivo, setLadoEfetivo] = useState<LadoTooltip>(lado);
  const id = useId();
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);
  const involucro = useRef<HTMLSpanElement>(null);

  const cancelar = useCallback(() => {
    if (temporizador.current) {
      clearTimeout(temporizador.current);
      temporizador.current = null;
    }
  }, []);

  const abrir = useCallback(() => {
    cancelar();
    temporizador.current = setTimeout(() => setAberto(true), atraso);
  }, [atraso, cancelar]);

  const fechar = useCallback(() => {
    cancelar();
    setAberto(false);
  }, [cancelar]);

  useEffect(() => cancelar, [cancelar]);

  useEffect(() => {
    if (!aberto) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === 'Escape') fechar();
    }
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aberto, fechar]);

  // Flip: se o lado pedido não cabe na viewport, usa o oposto.
  useLayoutEffect(() => {
    if (!aberto || !involucro.current) return;
    const caixa = involucro.current.getBoundingClientRect();
    const folga = 120;
    const cabe =
      lado === 'cima'
        ? caixa.top > folga
        : lado === 'baixo'
          ? window.innerHeight - caixa.bottom > folga
          : lado === 'esquerda'
            ? caixa.left > folga * 2
            : window.innerWidth - caixa.right > folga * 2;
    setLadoEfetivo(cabe ? lado : OPOSTO[lado]);
  }, [aberto, lado]);

  const gatilho = isValidElement(children)
    ? cloneElement(children, { 'aria-describedby': aberto ? id : undefined })
    : children;

  return (
    <span
      ref={involucro}
      className={cn('relative inline-flex', className)}
      onMouseEnter={abrir}
      onMouseLeave={fechar}
      onFocusCapture={abrir}
      onBlurCapture={fechar}
    >
      {gatilho}
      {aberto ? (
        <span
          role="tooltip"
          id={id}
          className={cn(
            'pointer-events-none absolute z-70 w-max max-w-[280px] rounded-md',
            'border border-line-strong bg-surface-raised px-[10px] py-2',
            'text-[12px]/[16px] font-normal text-fg-primary shadow-overlay',
            POSICAO[ladoEfetivo],
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              'absolute size-[6px] rotate-45 border-line-strong bg-surface-raised',
              SETA[ladoEfetivo],
            )}
          />
          {termo ? <ConteudoGlossario termo={termo} /> : conteudo}
        </span>
      ) : null}
    </span>
  );
}

export interface TermoProps {
  sigla: TermoGlossario;
  /** Sobrescreve o texto visível (padrão: a sigla do verbete). */
  children?: ReactNode;
  className?: string;
}

/**
 * Sigla do glossário com sublinhado pontilhado e Tooltip obrigatório.
 * Toda sigla do §6.13 aparece envolvida por este componente na primeira
 * ocorrência de cada página (checklist §12).
 */
export function Termo({ sigla, children, className }: TermoProps) {
  return (
    <Tooltip termo={sigla}>
      <abbr
        tabIndex={0}
        title=""
        className={cn(
          'cursor-help rounded-sm no-underline decoration-dotted underline-offset-[3px]',
          '[text-decoration-line:underline] [text-decoration-style:dotted]',
          '[text-decoration-color:var(--color-fg-tertiary)]',
          className,
        )}
      >
        {children ?? GLOSSARIO[sigla].sigla}
      </abbr>
    </Tooltip>
  );
}
