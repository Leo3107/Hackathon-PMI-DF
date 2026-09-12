'use client';

/**
 * Copiloto de análise como widget flutuante global (`03-ux-e-telas.md` §4.12).
 *
 * Antes era um card no meio da página do cliente; virou bolinha fixa no canto inferior direito,
 * presente em toda rota com shell. O motivo é de fluxo, não de estética: a pergunta costuma
 * nascer *enquanto* o analista lê a carteira ou a lista de evidências, e um card ancorado obriga
 * a rolar até ele e perder o lugar da leitura.
 *
 * Três decisões que valem registro:
 *
 * 1. **Não é modal.** Nada de foco preso nem scrim — o painel abre por cima, mas a página
 *    continua legível e clicável, que é exatamente o ponto de tirar o copiloto do fluxo.
 * 2. **Um cliente por vez.** O motor exige `cliente_id` (`PedidoCopiloto`). Dentro de
 *    `/clientes/<id>` o contexto vem da rota; fora dela, o painel pede que o analista escolha e
 *    segura o envio até lá — inventar um cliente "padrão" produziria resposta certa sobre a
 *    empresa errada.
 * 3. **Trocar de cliente zera a conversa**, por derivação dentro de `useCopiloto`: histórico de
 *    um cliente não é contexto válido para outro.
 *
 * Some na impressão (`print:hidden`): o parecer é documento, não tela de trabalho.
 */

import { Send, Sparkles, X } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useEffect, useId, useRef, useState, type RefObject } from 'react';

import { Button, IconButton, StreamingText } from '@/components/ui';

import { useClientes } from './usar-clientes';
import { useCopiloto } from './usar-copiloto';
import { useSessaoParaApi } from './usar-sessao';

const LIMITE = 300;
const AVISO_CONTADOR = 250;

/** Sugestões fixas da spec — o analista não precisa inventar a primeira pergunta. */
const SUGESTOES = [
  'Por que o score caiu?',
  'Qual garantia protege em cenário de RJ?',
  'O que mudou nos últimos 90 dias?',
];

export const RODAPE_COPILOTO =
  'O copiloto responde com base nos dados desta avaliação e nas fontes consultadas para ela.';

/** Cliente da rota atual, quando a rota é `/clientes/<id>` (inclusive `/clientes/<id>/parecer`). */
function clienteDaRota(pathname: string): string | undefined {
  return /^\/clientes\/([^/]+)/.exec(pathname)?.[1];
}

export function CopilotoFlutuante() {
  const pathname = usePathname();
  const clientes = useClientes();
  const [aberto, setAberto] = useState(false);
  // Escolha explícita do analista, usada só fora de uma página de cliente: dentro dela o
  // contexto é a rota, e discordar dela seria responder sobre outra empresa que a da tela.
  const [escolhido, setEscolhido] = useState('');

  const clienteDaPagina = clienteDaRota(pathname);
  const clienteId = clienteDaPagina ?? escolhido;
  const sessao = useSessaoParaApi(clienteId || undefined);
  const copiloto = useCopiloto(clienteId, sessao);

  const razaoSocial =
    clientes.find((c) => c.cliente.id === clienteId)?.cliente.razaoSocial ?? null;

  const painelId = useId();
  const campo = useRef<HTMLTextAreaElement | null>(null);
  const fimDaLista = useRef<HTMLDivElement | null>(null);

  // Escape fecha de qualquer lugar da página — o painel não prende o foco, então o atalho
  // precisa valer mesmo com o cursor fora dele.
  useEffect(() => {
    if (!aberto) return;
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === 'Escape') setAberto(false);
    }
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aberto]);

  // Abrir já com o cursor no campo: o widget existe para perguntar, não para ser lido.
  useEffect(() => {
    if (aberto) campo.current?.focus();
  }, [aberto]);

  // Acompanha o streaming da última resposta sem roubar o scroll da página (o alvo está dentro
  // da lista rolável, e `block: 'nearest'` não mexe em ancestrais que já estão na posição).
  useEffect(() => {
    if (aberto) fimDaLista.current?.scrollIntoView({ block: 'nearest' });
  }, [aberto, copiloto.turnos]);

  if (!aberto) {
    return (
      <button
        type="button"
        aria-label="Abrir copiloto de análise"
        aria-expanded={false}
        aria-controls={painelId}
        onClick={() => setAberto(true)}
        className="transicao-controle transicao-elevacao fixed right-5 bottom-5 z-50 flex size-[52px] items-center justify-center rounded-full border border-transparent bg-accent-500 text-fg-inverse shadow-raised hover:-translate-y-px hover:bg-accent-600 active:translate-y-0 active:scale-[0.98] print:hidden"
      >
        <Sparkles size={22} strokeWidth={2} aria-hidden="true" />
      </button>
    );
  }

  return (
    <section
      id={painelId}
      aria-label="Copiloto de análise"
      className="fixed right-5 bottom-5 z-50 flex h-[min(560px,calc(100vh-6rem))] w-[min(400px,calc(100vw-2rem))] flex-col rounded-xl border border-line-default bg-surface-raised shadow-overlay print:hidden"
    >
      <header className="flex shrink-0 items-start gap-2 border-b border-line-subtle px-3 py-2.5">
        <Sparkles
          size={16}
          strokeWidth={2}
          aria-hidden="true"
          className="mt-0.5 shrink-0 text-accent-500"
        />
        <div className="min-w-0 flex-1">
          <p className="type-section-title">Copiloto de análise</p>
          <p className="type-caption truncate">
            {clienteId
              ? (razaoSocial ?? clienteId)
              : 'Escolha um cliente para começar'}
          </p>
        </div>
        {copiloto.turnos.length > 0 ? (
          <Button variante="fantasma" tamanho="sm" onClick={copiloto.limpar}>
            Limpar
          </Button>
        ) : null}
        <IconButton
          icone={X}
          rotulo="Fechar copiloto de análise"
          tamanho="sm"
          aria-expanded
          aria-controls={painelId}
          onClick={() => setAberto(false)}
        />
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {clienteDaPagina ? null : <SeletorDeCliente valor={escolhido} aoEscolher={setEscolhido} />}

        {copiloto.turnos.length === 0 ? (
          <p className="type-caption">
            {clienteId
              ? 'Perguntas em linguagem natural sobre esta avaliação.'
              : 'O copiloto responde sobre um cliente por vez — escolha acima para liberar o envio.'}
          </p>
        ) : (
          <ol className="flex flex-col gap-3" aria-live="polite" aria-busy={copiloto.ocupado}>
            {copiloto.turnos.map((turno) => (
              <li key={turno.id} className="flex flex-col gap-2">
                <p className="type-body max-w-[85%] self-end rounded-lg rounded-br-sm bg-accent-tint px-3 py-2 text-fg-primary">
                  {turno.pergunta}
                </p>
                <div className="max-w-[95%] self-start rounded-lg rounded-bl-sm border border-line-default bg-surface-sunken px-3 py-2">
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
        )}
        <div ref={fimDaLista} />
      </div>

      <Formulario copiloto={copiloto} temCliente={Boolean(clienteId)} campo={campo} />
    </section>
  );
}

/**
 * Seletor exibido apenas fora de uma página de cliente. `<select>` nativo de propósito: a
 * carteira cabe numa lista curta e teclado/leitor de tela já funcionam de graça.
 */
function SeletorDeCliente({
  valor,
  aoEscolher,
}: {
  valor: string;
  aoEscolher: (id: string) => void;
}) {
  const clientes = useClientes();
  const id = useId();

  return (
    <div className="mb-3">
      <label className="type-label mb-1 block text-fg-secondary" htmlFor={id}>
        Sobre qual cliente?
      </label>
      <select
        id={id}
        value={valor}
        onChange={(evento) => aoEscolher(evento.target.value)}
        className="transicao-controle type-body h-8 w-full rounded border border-line-default bg-surface-input px-2 text-fg-primary"
      >
        <option value="">
          {clientes.length === 0 ? 'Carteira indisponível' : 'Selecione um cliente…'}
        </option>
        {clientes.map(({ cliente }) => (
          <option key={cliente.id} value={cliente.id}>
            {cliente.razaoSocial}
          </option>
        ))}
      </select>
    </div>
  );
}

function Formulario({
  copiloto,
  temCliente,
  campo,
}: {
  copiloto: ReturnType<typeof useCopiloto>;
  temCliente: boolean;
  campo: RefObject<HTMLTextAreaElement | null>;
}) {
  const [pergunta, setPergunta] = useState('');

  function enviar(texto: string) {
    const limpo = texto.trim().slice(0, LIMITE);
    if (!limpo || !temCliente) return;
    copiloto.perguntar(limpo);
    setPergunta('');
  }

  return (
    <div className="shrink-0 border-t border-line-subtle px-3 pt-2.5 pb-3">
      {/* Sugestões só fazem sentido com cliente definido — sem ele, o envio está travado. */}
      {temCliente ? (
        <div className="mb-2 flex flex-wrap gap-1.5">
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
            ref={campo}
            value={pergunta}
            rows={2}
            maxLength={LIMITE}
            disabled={!temCliente}
            placeholder={temCliente ? 'Pergunte sobre este cliente…' : 'Escolha um cliente acima…'}
            onChange={(evento) => setPergunta(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key === 'Enter' && !evento.shiftKey) {
                evento.preventDefault();
                enviar(pergunta);
              }
            }}
            className="transicao-controle type-body w-full resize-none rounded border border-line-default bg-surface-input px-3 py-2 text-fg-primary placeholder:text-fg-tertiary focus-visible:border-accent-line focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-400 disabled:text-fg-disabled"
          />
        </label>
        <Button
          type="submit"
          variante="primario"
          iconeEsquerda={Send}
          carregando={copiloto.ocupado}
          disabled={!temCliente || copiloto.ocupado || pergunta.trim().length === 0}
        >
          Perguntar
        </Button>
      </form>

      {pergunta.length >= AVISO_CONTADOR ? (
        <p className="type-caption tnum mt-1" aria-live="polite">
          {pergunta.length}/{LIMITE} caracteres
        </p>
      ) : null}

      <p className="type-caption mt-2">{RODAPE_COPILOTO}</p>
    </div>
  );
}
