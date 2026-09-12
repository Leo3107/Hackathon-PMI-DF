/**
 * Consumo do protocolo NDJSON da camada de linguagem (`specs/04-camada-llm.md` §2.3 e §2.5).
 *
 * Uma linha JSON por evento, terminada em `\n`. Garantias do protocolo: `inicio` é sempre o
 * primeiro evento; `fim` ou `erro` é sempre o último; nunca há `delta` depois de `fim`.
 *
 * Regra R1 (`03-ux-e-telas.md` §0.4): **nenhum número em tela espera o LLM.** Estas funções
 * entregam só prosa. Se o stream falhar inteiro, a tela já tem todos os números renderizados e
 * mostra o bloco de prosa em erro local — nunca derruba a página (§9.3).
 *
 * O leitor é um `AsyncGenerator`: o texto sai em pedaços, sem `await` de resposta inteira. Ler
 * o corpo de uma vez aqui teria o mesmo efeito de bufferizar no proxy — a prosa apareceria toda
 * junta, depois de segundos de tela parada.
 */

import type {
  EventoNarrativa,
  OrigemNarrativa,
  PedidoCopiloto,
  PedidoNarrativa,
  TarefaNarrativa,
} from '@/types';

import { notificarUsoDeLlm, registrarFalha, registrarSucesso } from './disponibilidade';
import { ErroLastro, comoErroLastro } from './erros';

/** Deadline do cliente: 3s acima do deadline do executor no Flask (25s). */
const TIMEOUT_STREAM_MS = 28_000;

async function abrirStream(
  caminho: string,
  corpo: unknown,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/x-ndjson' },
      body: JSON.stringify(corpo),
      cache: 'no-store',
      signal: signal ?? AbortSignal.timeout(TIMEOUT_STREAM_MS),
    });
  } catch (causa) {
    registrarFalha();
    throw comoErroLastro(causa, caminho);
  }

  if (!resposta.ok || !resposta.body) {
    let codigo = 'ERRO_INTERNO';
    try {
      const json = (await resposta.json()) as { erro?: string };
      if (typeof json?.erro === 'string') codigo = json.erro;
    } catch {
      /* corpo vazio */
    }
    if (resposta.status >= 500 || resposta.status === 503) registrarFalha();
    throw new ErroLastro(codigo, resposta.status, { caminho });
  }

  registrarSucesso();
  return resposta.body;
}

/** Decodifica o corpo linha a linha. Linhas em branco e lixo parcial são ignorados. */
export async function* lerNdjson(
  corpo: ReadableStream<Uint8Array>,
): AsyncGenerator<EventoNarrativa, void, void> {
  const leitor = corpo.getReader();
  const decodificador = new TextDecoder();
  let resto = '';
  try {
    for (;;) {
      const { done, value } = await leitor.read();
      if (done) break;
      resto += decodificador.decode(value, { stream: true });
      let quebra = resto.indexOf('\n');
      while (quebra !== -1) {
        const linha = resto.slice(0, quebra).trim();
        resto = resto.slice(quebra + 1);
        if (linha) {
          const evento = analisarLinha(linha);
          if (evento) yield evento;
        }
        quebra = resto.indexOf('\n');
      }
    }
    const ultima = resto.trim();
    if (ultima) {
      const evento = analisarLinha(ultima);
      if (evento) yield evento;
    }
  } finally {
    leitor.releaseLock();
  }
}

function analisarLinha(linha: string): EventoNarrativa | null {
  try {
    const objeto = JSON.parse(linha) as EventoNarrativa;
    return typeof objeto?.t === 'string' ? objeto : null;
  } catch {
    return null; // Linha truncada por queda de conexão: o `fim` nunca chegará e a UI trata.
  }
}

/**
 * Abre uma das três tarefas de narrativa.
 *
 * ```ts
 * for await (const ev of streamNarrativa('parecer', { clienteId })) {
 *   if (ev.t === 'delta') acumular(ev.d);
 *   if (ev.t === 'substituir') zerar();
 * }
 * ```
 */
export async function* streamNarrativa(
  tarefa: TarefaNarrativa,
  pedido: PedidoNarrativa,
  signal?: AbortSignal,
): AsyncGenerator<EventoNarrativa, void, void> {
  const corpo = await abrirStream(`/api/narrativa/${tarefa}`, comSessaoPadrao(pedido), signal);
  yield* comNotificacaoDeUso(lerNdjson(corpo));
}

export async function* streamCopiloto(
  pedido: PedidoCopiloto,
  signal?: AbortSignal,
): AsyncGenerator<EventoNarrativa, void, void> {
  const corpo = await abrirStream('/api/copiloto', comSessaoPadrao(pedido), signal);
  yield* comNotificacaoDeUso(lerNdjson(corpo));
}

function comSessaoPadrao<T extends PedidoNarrativa>(pedido: T): T {
  return pedido.sessao
    ? pedido
    : { ...pedido, sessao: { eventosSimulados: [], statusRedFlags: {} } };
}

/** No `fim`, avisa o `ContadorDeCusto` para revalidar o ledger (`04` §5.6). */
async function* comNotificacaoDeUso(
  fonte: AsyncGenerator<EventoNarrativa, void, void>,
): AsyncGenerator<EventoNarrativa, void, void> {
  for await (const evento of fonte) {
    yield evento;
    if (evento.t === 'fim') notificarUsoDeLlm();
  }
}

/**
 * Acumulador de texto do protocolo, para quem não quer tratar cada evento.
 * Respeita `substituir` zerando o texto — é assim que a degradação para narrativa
 * determinística aparece sem piscar conteúdo velho.
 */
export interface TextoAcumulado {
  texto: string;
  origem: OrigemNarrativa;
  degradou: boolean;
  concluido: boolean;
  erro?: { codigo: string; mensagem: string };
}

export function acumular(estado: TextoAcumulado, evento: EventoNarrativa): TextoAcumulado {
  switch (evento.t) {
    case 'inicio':
      return { ...estado, origem: evento.origem, texto: '', concluido: false };
    case 'delta':
      return { ...estado, texto: estado.texto + evento.d };
    case 'substituir':
      return { ...estado, texto: '', degradou: true };
    case 'fim':
      return {
        ...estado,
        origem: evento.origem,
        degradou: evento.motivoDegradacao !== null,
        concluido: true,
      };
    case 'erro':
      return {
        ...estado,
        concluido: true,
        erro: { codigo: evento.codigo, mensagem: evento.mensagem },
      };
  }
}

export const TEXTO_INICIAL: TextoAcumulado = {
  texto: '',
  origem: 'deterministico',
  degradou: false,
  concluido: false,
};
