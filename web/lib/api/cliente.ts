/**
 * Cliente de API tipado — uma função por endpoint.
 *
 * Espelha a interface `RepositorioLastro` de `specs/01-modelo-de-dados.md`, mas sobre HTTP:
 * o que era `MockRepositorio` virou o Flask (D3, revisão de stack).
 *
 * ## Origem da requisição
 *
 * Os caminhos são **idênticos** nos dois lados — `/api/clientes` no Next é `/api/clientes` no
 * Flask — então só muda a origem:
 *
 * - **No browser**: caminho relativo → route handler do Next (`web/app/api/**`) → Flask.
 *   O browser nunca fala com a porta 5001.
 * - **No servidor** (Server Component, `generateMetadata`): vai direto ao Flask. Dar um salto
 *   a menos evita o Next chamar a si mesmo, o que trava em build e é lento em runtime.
 *
 * ## Erro
 *
 * Toda função lança `ErroLastro`. Flask fora do ar, timeout, ou 5xx viram sempre
 * `MOTOR_INDISPONIVEL` (503) — o contrato de `03-ux-e-telas.md` §9.4. Nenhuma função devolve
 * `null` silencioso, exceto onde "não encontrado" é resposta legítima de negócio.
 */

import type {
  Alerta,
  AvaliacaoDeRisco,
  Cliente,
  ClienteAvaliado,
  EstadoDeSessaoApi,
  EventoDeRisco,
  NovoRegistroAuditoria,
  RegistroAuditoria,
  RespostaCusto,
  RespostaDueDiligence,
  RespostaSaude,
  RespostaSimulacao,
  ResumoCarteira,
  SnapshotHistorico,
  TipoEvento,
} from '@/types';

import { registrarFalha, registrarSucesso } from './disponibilidade';
import { ErroLastro, comoErroLastro } from './erros';

const TIMEOUT_PADRAO_MS = 15_000;

function noServidor(): boolean {
  return typeof window === 'undefined';
}

/** Origem das requisições: vazia no browser (relativo), Flask direto no servidor. */
function origem(): string {
  return noServidor() ? (process.env.LASTRO_API_URL ?? 'http://127.0.0.1:5001') : '';
}

interface OpcoesRequisicao {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  corpo?: unknown;
  timeoutMs?: number;
  /** Repassado para o `AbortController` da tela (troca de rota, desmontagem). */
  signal?: AbortSignal;
}

async function requisitar<T>(caminho: string, opcoes: OpcoesRequisicao = {}): Promise<T> {
  const { metodo = 'GET', corpo, timeoutMs = TIMEOUT_PADRAO_MS, signal } = opcoes;
  const url = `${origem()}${caminho}`;

  let resposta: Response;
  try {
    resposta = await fetch(url, {
      method: metodo,
      headers: corpo === undefined ? { accept: 'application/json' } : {
        accept: 'application/json',
        'content-type': 'application/json',
      },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      cache: 'no-store',
      signal: signal ?? AbortSignal.timeout(timeoutMs),
    });
  } catch (causa) {
    registrarFalha();
    throw comoErroLastro(causa, caminho);
  }

  // Tolerância de integração: as rotas de leitura são `POST` porque carregam o estado de
  // sessão que altera o cálculo (D3). Se o WS3 as tiver publicado como `GET`, repete uma vez
  // pelo método que o motor aceita, em vez de quebrar a tela por divergência de verbo.
  if (resposta.status === 405 && metodo === 'POST') {
    return requisitar<T>(caminho, { ...opcoes, metodo: 'GET', corpo: undefined });
  }

  if (!resposta.ok) {
    const erro = await erroDaResposta(resposta, caminho);
    if (erro.motorIndisponivel) registrarFalha();
    else registrarSucesso();
    throw erro;
  }

  registrarSucesso();
  if (resposta.status === 204) return undefined as T;
  try {
    return (await resposta.json()) as T;
  } catch (causa) {
    throw new ErroLastro('ERRO_INTERNO', 502, {
      detalhe: 'O motor devolveu uma resposta que não é JSON.',
      caminho,
      causa,
    });
  }
}

async function erroDaResposta(resposta: Response, caminho: string): Promise<ErroLastro> {
  let codigo = resposta.status === 404 ? 'ROTA_NAO_ENCONTRADA' : 'ERRO_INTERNO';
  let detalhe: string | unknown[] | undefined;
  try {
    const corpo = (await resposta.json()) as { erro?: string; detalhe?: string | unknown[] };
    if (typeof corpo?.erro === 'string') codigo = corpo.erro;
    if (corpo?.detalhe !== undefined) detalhe = corpo.detalhe;
  } catch {
    // Corpo vazio ou HTML de erro: o status já basta.
  }
  if (resposta.status >= 500) codigo = 'MOTOR_INDISPONIVEL';
  return new ErroLastro(codigo, resposta.status, { detalhe, caminho });
}

/** Envelope de sessão enviado a toda rota que recalcula risco (D3 · estado de sessão). */
function comSessao(sessao: EstadoDeSessaoApi | undefined, extra: Record<string, unknown> = {}) {
  return { sessao: sessao ?? { eventosSimulados: [], statusRedFlags: {} }, ...extra };
}

// ---------------------------------------------------------------------------
// Saúde
// ---------------------------------------------------------------------------

/** Não lança: devolve `{ ok: false }` quando o motor não responde. Usado pela faixa global. */
export async function verificarSaude(signal?: AbortSignal): Promise<RespostaSaude> {
  try {
    return await requisitar<RespostaSaude>('/api/saude', { timeoutMs: 3_000, signal });
  } catch {
    return { ok: false, servico: 'lastro-api' };
  }
}

// ---------------------------------------------------------------------------
// Carteira e clientes
// ---------------------------------------------------------------------------

export function obterCarteira(
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<ResumoCarteira> {
  return requisitar<ResumoCarteira>('/api/carteira', {
    metodo: 'POST',
    corpo: comSessao(sessao),
    signal,
  });
}

export function listarClientes(
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<ClienteAvaliado[]> {
  return requisitar<ClienteAvaliado[]>('/api/clientes', {
    metodo: 'POST',
    corpo: comSessao(sessao),
    signal,
  });
}

/** Devolve `null` quando o id não existe — "cliente inexistente" é estado de tela, não erro. */
export async function obterCliente(id: string, signal?: AbortSignal): Promise<Cliente | null> {
  try {
    return await requisitar<Cliente>(`/api/clientes/${encodeURIComponent(id)}`, { signal });
  } catch (causa) {
    if (causa instanceof ErroLastro && causa.naoEncontrado) return null;
    throw causa;
  }
}

export function obterAvaliacao(
  clienteId: string,
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<AvaliacaoDeRisco> {
  return requisitar<AvaliacaoDeRisco>(
    `/api/clientes/${encodeURIComponent(clienteId)}/avaliacao`,
    { metodo: 'POST', corpo: comSessao(sessao), signal },
  );
}

export function obterHistorico(
  clienteId: string,
  signal?: AbortSignal,
): Promise<SnapshotHistorico[]> {
  return requisitar<SnapshotHistorico[]>(
    `/api/clientes/${encodeURIComponent(clienteId)}/historico`,
    { signal },
  );
}

export function obterEventos(
  clienteId: string,
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<EventoDeRisco[]> {
  return requisitar<EventoDeRisco[]>(
    `/api/clientes/${encodeURIComponent(clienteId)}/eventos`,
    { metodo: 'POST', corpo: comSessao(sessao), signal },
  );
}

// ---------------------------------------------------------------------------
// Alertas e auditoria
// ---------------------------------------------------------------------------

export function listarAlertas(
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<Alerta[]> {
  return requisitar<Alerta[]>('/api/alertas', {
    metodo: 'POST',
    corpo: comSessao(sessao),
    signal,
  });
}

export function listarAuditoria(signal?: AbortSignal): Promise<RegistroAuditoria[]> {
  return requisitar<RegistroAuditoria[]>('/api/auditoria', { signal });
}

/**
 * Registra a decisão do analista. O servidor não persiste (D3 · sem banco); a trilha vive em
 * `localStorage` via `lib/sessao.ts`. Esta chamada existe para o Flask carimbar id e data-hora
 * e calcular `divergiuDaRecomendacao` — a interface não decide isso (R6).
 */
export function registrarDecisao(
  registro: NovoRegistroAuditoria,
  signal?: AbortSignal,
): Promise<RegistroAuditoria> {
  return requisitar<RegistroAuditoria>('/api/auditoria', {
    metodo: 'POST',
    corpo: registro,
    signal,
  });
}

// ---------------------------------------------------------------------------
// Due diligence e simulação
// ---------------------------------------------------------------------------

/** Fluxo A. `encontrado: false` é resposta normal, não erro (§6.5). */
export function consultarDocumento(
  documento: string,
  signal?: AbortSignal,
): Promise<RespostaDueDiligence> {
  return requisitar<RespostaDueDiligence>('/api/due-diligence', {
    metodo: 'POST',
    corpo: { documento },
    timeoutMs: 30_000,
    signal,
  });
}

/** D10 — injeta um evento e o motor **recalcula de verdade**. Nada é escrito à mão. */
export function simularEvento(
  clienteId: string,
  tipo: TipoEvento,
  sessao?: EstadoDeSessaoApi,
  signal?: AbortSignal,
): Promise<RespostaSimulacao> {
  return requisitar<RespostaSimulacao>(
    `/api/clientes/${encodeURIComponent(clienteId)}/simular-evento`,
    { metodo: 'POST', corpo: comSessao(sessao, { tipo }), signal },
  );
}

// ---------------------------------------------------------------------------
// Camada de linguagem — ledger de custo
// ---------------------------------------------------------------------------

export function obterCustoLlm(signal?: AbortSignal): Promise<RespostaCusto> {
  return requisitar<RespostaCusto>('/api/llm/custo', { timeoutMs: 5_000, signal });
}
