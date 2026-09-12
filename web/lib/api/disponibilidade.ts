/**
 * Sinal global de disponibilidade do motor de risco.
 *
 * `03-ux-e-telas.md` §9.4 exige dois níveis simultâneos quando o Flask cai: uma faixa global
 * persistente com tentativa automática, e um `ErrorState` no conteúdo. A faixa precisa saber
 * do estado **sem** ser quem faz as chamadas — por isso o cliente de API publica aqui o
 * resultado de cada requisição e a faixa apenas escuta.
 *
 * Módulo isomórfico: no servidor as funções são no-op silenciosas.
 */

export interface EstadoDoMotor {
  disponivel: boolean;
  /** ISO datetime da última resposta bem-sucedida, se houve alguma. */
  ultimaRespostaOk: string | null;
  /** Tentativas de reconexão desde a queda. */
  tentativas: number;
}

const NOME_EVENTO = 'lastro:motor';

let estado: EstadoDoMotor = { disponivel: true, ultimaRespostaOk: null, tentativas: 0 };

export function estadoDoMotor(): EstadoDoMotor {
  return estado;
}

function publicar(proximo: EstadoDoMotor): void {
  const mudou =
    proximo.disponivel !== estado.disponivel ||
    proximo.tentativas !== estado.tentativas ||
    proximo.ultimaRespostaOk !== estado.ultimaRespostaOk;
  estado = proximo;
  if (!mudou || typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<EstadoDoMotor>(NOME_EVENTO, { detail: proximo }));
}

/** Chamado pelo cliente de API a cada resposta bem-sucedida do motor. */
export function registrarSucesso(): void {
  publicar({ disponivel: true, ultimaRespostaOk: new Date().toISOString(), tentativas: 0 });
}

/** Chamado a cada falha de conexão ou 5xx. Incrementa o contador de tentativas. */
export function registrarFalha(): void {
  publicar({
    disponivel: false,
    ultimaRespostaOk: estado.ultimaRespostaOk,
    tentativas: estado.tentativas + 1,
  });
}

export function assinarEstadoDoMotor(ouvinte: (estado: EstadoDoMotor) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = (evento: Event) => ouvinte((evento as CustomEvent<EstadoDoMotor>).detail);
  window.addEventListener(NOME_EVENTO, handler);
  return () => window.removeEventListener(NOME_EVENTO, handler);
}

/** Evento emitido no `fim` de todo stream, para o contador de custo revalidar (`04` §5.6). */
export const EVENTO_USO_LLM = 'lastro:llm:uso';

export function notificarUsoDeLlm(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(EVENTO_USO_LLM));
}
