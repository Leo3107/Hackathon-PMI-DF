'use client';

/**
 * Controle "Registrar evento de risco" (D9/D10 · `03-ux-e-telas.md` §1.5).
 *
 * Vive na barra lateral, logo abaixo de "Clientes", e está disponível em **todas** as rotas
 * com shell. Desenha-se como item da lista de navegação, mas não é um item de navegação: não
 * recebe o realce de rota ativa e abre um popover ancorado à direita da barra.
 *
 * O que este componente **não** faz: inventar número. Ele registra o evento na sessão, chama
 * o motor e ele **recalcula de verdade** a partir dos fatos alterados (D4). O score novo que a
 * tela do cliente anima veio do Python, não daqui.
 *
 * Reversível: cada evento registrado aparece listado com ação `Desfazer`, que o remove da
 * sessão — o próximo cálculo volta ao estado anterior sozinho, porque o estado de sessão é
 * entrada do motor, não um patch aplicado sobre o resultado.
 */

import { Undo2, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui';
import { simularEvento } from '@/lib/api';
import { formatarDelta, formatarScore } from '@/lib/format';
import {
  desfazerEventoSimulado,
  registrarEventoSimulado,
  sessaoParaApi,
} from '@/lib/sessao';
import type { TipoEvento } from '@/types';

import { Popover } from './Popover';
import { recarregarClientes, useClientes } from './usar-clientes';
import { useSessao } from './usar-sessao';

interface OpcaoDeEvento {
  tipo: TipoEvento;
  rotulo: string;
  /** Efeito esperado, em uma linha — o analista precisa saber o que vai acontecer antes. */
  efeito: string;
}

const OPCOES: OpcaoDeEvento[] = [
  {
    tipo: 'NOVA_EXECUCAO',
    rotulo: 'Nova execução de título',
    efeito: 'Agrava a dimensão jurídica e eleva o índice de risco de RJ.',
  },
  {
    tipo: 'PEDIDO_RJ',
    rotulo: 'Pedido de Recuperação Judicial',
    efeito: 'Evento já ocorrido: abre Stay Period e reclassifica a exposição concursal.',
  },
  {
    tipo: 'EMBARGO_AMBIENTAL',
    rotulo: 'Embargo do IBAMA sobre imóvel em garantia',
    efeito: 'Aciona VETO_EMBARGO_GARANTIA — força rating D.',
  },
  {
    tipo: 'COVENANT_ROMPIDO',
    rotulo: 'Quebra de covenant (inadimplência técnica)',
    efeito: 'Inadimplência técnica sem atraso financeiro: derruba a dimensão comportamental.',
  },
];

export interface SimularEventoProps {
  /** Cliente da rota atual, quando houver — pré-seleciona o select. */
  clienteIdAtual?: string;
}

export function SimularEvento({ clienteIdAtual }: SimularEventoProps) {
  const router = useRouter();
  const sessao = useSessao();
  const clientes = useClientes();
  // Estado derivado, não sincronizado por efeito: a escolha explícita do analista vence; sem
  // ela, vale o cliente da rota atual e, na falta dele, o primeiro da carteira.
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const clienteId = escolhido ?? clienteIdAtual ?? clientes[0]?.cliente.id ?? '';
  const [tipo, setTipo] = useState<TipoEvento>('NOVA_EXECUCAO');
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  async function confirmar() {
    if (!clienteId) return;
    const nome =
      clientes.find((c) => c.cliente.id === clienteId)?.cliente.razaoSocial ?? clienteId;
    setEnviando(true);
    try {
      registrarEventoSimulado({ clienteId, clienteNome: nome, tipo });
      const resposta = await simularEvento(clienteId, tipo, sessaoParaApi(clienteId));
      setAviso(
        `Evento registrado. Score recalculado pelo motor: ${formatarScore(
          resposta.scoreAnterior,
        )} → ${formatarScore(resposta.scoreAtual)} (${formatarDelta(
          resposta.deltaScore,
          'pts',
        )}).`,
      );
      recarregarClientes();
      router.push(`/clientes/${clienteId}`);
      router.refresh();
    } catch {
      setAviso('Não foi possível registrar o evento: o motor de risco não respondeu.');
    } finally {
      setEnviando(false);
    }
  }

  function desfazer(id: string) {
    desfazerEventoSimulado(id);
    setAviso(null);
    recarregarClientes();
    router.refresh();
  }

  return (
    <Popover
      rotulo="Registrar evento de risco"
      ancoragem="lateral"
      largura={360}
      className="mx-2"
      gatilho={({ aberto, alternar, id, controla }) => (
        <button
          id={id}
          type="button"
          aria-label="Registrar evento de risco"
          aria-haspopup="dialog"
          aria-expanded={aberto}
          aria-controls={controla}
          onClick={alternar}
          className="transicao-controle flex h-9 w-full items-center gap-2 rounded-md px-3 text-fg-secondary hover:bg-surface-hover hover:text-fg-primary"
        >
          <Zap aria-hidden className="size-4 shrink-0" />
          <span className="type-label min-w-0 flex-1 truncate text-left text-current">
            Registrar evento
          </span>
        </button>
      )}
    >
      <p className="type-eyebrow mb-3 text-fg-tertiary">
        Registra um evento de monitoramento e recalcula o risco no motor
      </p>

      <label className="type-label mb-1 block text-fg-secondary" htmlFor="evento-cliente">
        Cliente
      </label>
      <select
        id="evento-cliente"
        value={clienteId}
        onChange={(e) => setEscolhido(e.target.value)}
        className="mb-3 h-8 w-full rounded border border-line-default bg-surface-input px-2 type-body text-fg-primary"
      >
        {clientes.length === 0 && <option value="">Carteira indisponível</option>}
        {clientes.map(({ cliente }) => (
          <option key={cliente.id} value={cliente.id}>
            {cliente.razaoSocial}
          </option>
        ))}
      </select>

      <fieldset className="mb-3">
        <legend className="type-label mb-1 text-fg-secondary">Evento</legend>
        {OPCOES.map((opcao) => (
          <label
            key={opcao.tipo}
            className="mb-1.5 flex cursor-pointer gap-2 rounded px-1 py-1 hover:bg-surface-hover"
          >
            <input
              type="radio"
              name="tipo-de-evento"
              value={opcao.tipo}
              checked={tipo === opcao.tipo}
              onChange={() => setTipo(opcao.tipo)}
              className="mt-1 accent-accent-500"
            />
            <span className="min-w-0">
              <span className="type-body block text-fg-primary">{opcao.rotulo}</span>
              <span className="type-caption block text-fg-secondary">{opcao.efeito}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <Button
        variante="primario"
        larguraTotal
        iconeEsquerda={Zap}
        carregando={enviando}
        disabled={!clienteId || enviando}
        onClick={() => void confirmar()}
      >
        Registrar evento
      </Button>

      {aviso && (
        <p role="status" className="type-caption mt-2 text-fg-secondary">
          {aviso}
        </p>
      )}

      {sessao.eventosSimulados.length > 0 && (
        <div className="mt-3 border-t border-line-subtle pt-2">
          <p className="type-eyebrow mb-1 text-fg-tertiary">Eventos desta sessão</p>
          <ul>
            {sessao.eventosSimulados.map((evento) => (
              <li key={evento.id} className="flex items-center gap-2 py-0.5">
                <span className="type-caption min-w-0 flex-1 truncate text-fg-secondary">
                  {evento.clienteNome} · {horaCurta(evento.data)}
                </span>
                <Button
                  tamanho="sm"
                  variante="fantasma"
                  iconeEsquerda={Undo2}
                  onClick={() => desfazer(evento.id)}
                >
                  Desfazer
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Popover>
  );
}

function horaCurta(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
}
