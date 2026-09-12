'use client';

/**
 * Copiloto de análise (`03-ux-e-telas.md` §4.12).
 *
 * Card ancorado no fluxo principal — **não** é widget flutuante nem chat global: a pergunta é
 * sobre *este* cliente e a resposta se lê ao lado dos números que a sustentam. A resposta chega
 * por streaming; nenhum número da página depende dela.
 */

import { Send, Sparkles } from 'lucide-react';
import { useState } from 'react';

import {
  Button,
  Card,
  Drawer,
  SectionHeader,
  StreamingText,
} from '@/components/ui';

import type { Copiloto } from './dados';

const LIMITE = 300;
const AVISO_CONTADOR = 250;

/** Sugestões fixas da spec — o analista não precisa inventar a primeira pergunta. */
const SUGESTOES = [
  'Por que o score caiu?',
  'Qual garantia protege em cenário de RJ?',
  'O que mudou nos últimos 90 dias?',
];

export const RODAPE_COPILOTO =
  'O copiloto responde apenas com base nos dados desta avaliação. Não consulta internet nem bases externas.';

export interface BlocoCopilotoProps {
  copiloto: Copiloto;
}

export function BlocoCopiloto({ copiloto }: BlocoCopilotoProps) {
  const [expandido, setExpandido] = useState(false);

  const conversa = <Conversa copiloto={copiloto} />;

  return (
    <Card id="copiloto" as="section" aria-labelledby="titulo-copiloto" className="scroll-mt-[88px]">
      <SectionHeader
        nivel={2}
        titulo="Copiloto de análise"
        descricao="Perguntas em linguagem natural sobre esta avaliação."
        meta={<Sparkles size={14} strokeWidth={2} aria-hidden="true" />}
        acoes={
          <div className="flex gap-1">
            {copiloto.turnos.length > 0 ? (
              <Button variante="fantasma" tamanho="sm" onClick={copiloto.limpar}>
                Limpar
              </Button>
            ) : null}
            <Button variante="fantasma" tamanho="sm" onClick={() => setExpandido(true)}>
              Expandir
            </Button>
          </div>
        }
      />
      <h2 id="titulo-copiloto" className="sr-only">
        Copiloto de análise
      </h2>

      <div className="mt-3">{expandido ? null : conversa}</div>

      <p className="type-caption mt-3 border-t border-line-subtle pt-2">{RODAPE_COPILOTO}</p>

      <Drawer
        aberto={expandido}
        aoFechar={() => setExpandido(false)}
        titulo="Copiloto de análise"
        subtitulo="Conversa sobre esta avaliação"
        largura="larga"
      >
        {expandido ? conversa : null}
        <p className="type-caption mt-3 border-t border-line-subtle pt-2">{RODAPE_COPILOTO}</p>
      </Drawer>
    </Card>
  );
}

function Conversa({ copiloto }: { copiloto: Copiloto }) {
  const [pergunta, setPergunta] = useState('');

  function enviar(texto: string) {
    const limpo = texto.trim().slice(0, LIMITE);
    if (!limpo) return;
    copiloto.perguntar(limpo);
    setPergunta('');
  }

  return (
    <div className="flex flex-col gap-3">
      {copiloto.turnos.length > 0 ? (
        <ol className="flex flex-col gap-3">
          {copiloto.turnos.map((turno) => (
            <li key={turno.id} className="flex flex-col gap-2">
              <p className="type-body max-w-[80%] self-end rounded-lg rounded-br-sm bg-accent-tint px-3 py-2 text-fg-primary">
                {turno.pergunta}
              </p>
              <div className="max-w-[92%] self-start rounded-lg rounded-bl-sm border border-line-default bg-surface-sunken px-3 py-2">
                <StreamingText
                  texto={turno.resposta}
                  estado={turno.estado}
                  origem={turno.origem}
                  linhasEsqueleto={3}
                />
              </div>
            </li>
          ))}
        </ol>
      ) : null}

      <form
        className="flex items-end gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          enviar(pergunta);
        }}
      >
        <label className="min-w-0 flex-1">
          <span className="sr-only">Pergunte sobre este cliente</span>
          <textarea
            value={pergunta}
            rows={2}
            maxLength={LIMITE}
            placeholder="Pergunte sobre este cliente…"
            onChange={(evento) => setPergunta(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key === 'Enter' && !evento.shiftKey) {
                evento.preventDefault();
                enviar(pergunta);
              }
            }}
            className="transicao-controle type-body w-full resize-y rounded border border-line-default bg-surface-input px-3 py-2 text-fg-primary placeholder:text-fg-tertiary focus-visible:border-accent-line focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-400"
          />
        </label>
        <Button
          type="submit"
          variante="primario"
          iconeEsquerda={Send}
          carregando={copiloto.ocupado}
          disabled={copiloto.ocupado || pergunta.trim().length === 0}
        >
          Perguntar
        </Button>
      </form>

      {pergunta.length >= AVISO_CONTADOR ? (
        <p className="type-caption tnum" aria-live="polite">
          {pergunta.length}/{LIMITE} caracteres
        </p>
      ) : null}

      <div className="flex flex-wrap gap-1.5">
        {SUGESTOES.map((sugestao) => (
          <Button
            key={sugestao}
            variante="fantasma"
            tamanho="sm"
            disabled={copiloto.ocupado}
            onClick={() => enviar(sugestao)}
          >
            {sugestao}
          </Button>
        ))}
      </div>
    </div>
  );
}
