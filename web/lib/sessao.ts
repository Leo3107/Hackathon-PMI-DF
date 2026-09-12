/**
 * Estado de sessão do analista — `localStorage`, chave `lastro:sessao:v1`.
 *
 * Decisões D3 ("Estado de sessão") e D11.3: o Lastro não tem banco nem autenticação. O que o
 * analista faz durante a demonstração — registrar decisão, marcar red flag, marcar alerta como
 * lido, simular evento — vive no navegador e sobrevive a um refresh no meio do pitch. Nada é
 * persistido no servidor.
 *
 * Duas categorias, com destinos diferentes:
 *
 * | Categoria | Onde importa |
 * |---|---|
 * | `eventosSimulados`, `statusRedFlags` | **Alteram o cálculo**: viajam no corpo de toda chamada ao motor (`EstadoDeSessaoApi`). |
 * | `decisoes`, `alertasLidos` | Só interface: trilha de auditoria e badge da sidebar. |
 *
 * ## Tolerância a `localStorage` indisponível
 *
 * Modo privativo do Safari, storage desabilitado por política, cota estourada, ou simplesmente
 * SSR: **nada disso pode derrubar a página**. Toda leitura e escrita é embrulhada em try/catch e
 * cai para um espelho em memória. O comportamento degradado é "a sessão não sobrevive ao
 * refresh", nunca "a tela quebrou".
 */

import type { EstadoDeSessaoApi, EventoSimulado, RegistroAuditoria, StatusRedFlag, TipoEvento } from '@/types';

export const CHAVE_SESSAO = 'lastro:sessao:v1';

/** Evento disparado a cada mutação, para os componentes reagirem sem prop drilling. */
export const EVENTO_SESSAO = 'lastro:sessao';

export const VERSAO_SESSAO = 1;

/** Um evento simulado, com o cliente a que pertence — para listar e desfazer (§1.5). */
export interface EventoSimuladoDaSessao extends EventoSimulado {
  /** Identificador local, usado pelo "Desfazer". */
  id: string;
  clienteId: string;
  clienteNome: string;
}

export interface EstadoDeSessao {
  versao: number;
  eventosSimulados: EventoSimuladoDaSessao[];
  /** `redFlagId` → status atribuído pelo analista. */
  statusRedFlags: Record<string, StatusRedFlag>;
  /** Ids de alertas marcados como lidos nesta sessão. */
  alertasLidos: string[];
  /** Trilha de auditoria da demonstração, mais recente primeiro. */
  decisoes: RegistroAuditoria[];
}

export const SESSAO_VAZIA: EstadoDeSessao = {
  versao: VERSAO_SESSAO,
  eventosSimulados: [],
  statusRedFlags: {},
  alertasLidos: [],
  decisoes: [],
};

// ---------------------------------------------------------------------------
// Acesso tolerante ao armazenamento
// ---------------------------------------------------------------------------

/** Espelho em memória: é o estado real quando `localStorage` não está disponível. */
let memoria: EstadoDeSessao = SESSAO_VAZIA;
let armazenamentoUtilizavel: boolean | null = null;

function armazenamento(): Storage | null {
  if (typeof window === 'undefined') return null;
  if (armazenamentoUtilizavel === false) return null;
  try {
    const teste = '__lastro__';
    window.localStorage.setItem(teste, teste);
    window.localStorage.removeItem(teste);
    armazenamentoUtilizavel = true;
    return window.localStorage;
  } catch {
    armazenamentoUtilizavel = false;
    return null;
  }
}

/** `true` quando as decisões **não** sobreviverão a um refresh. A UI pode avisar discretamente. */
export function armazenamentoIndisponivel(): boolean {
  if (typeof window === 'undefined') return true;
  armazenamento();
  return armazenamentoUtilizavel === false;
}

function normalizar(bruto: unknown): EstadoDeSessao {
  if (!bruto || typeof bruto !== 'object') return SESSAO_VAZIA;
  const objeto = bruto as Partial<EstadoDeSessao>;
  // Versão diferente: descarta em silêncio em vez de tentar migrar um protótipo.
  if (objeto.versao !== VERSAO_SESSAO) return SESSAO_VAZIA;
  return {
    versao: VERSAO_SESSAO,
    eventosSimulados: Array.isArray(objeto.eventosSimulados) ? objeto.eventosSimulados : [],
    statusRedFlags:
      objeto.statusRedFlags && typeof objeto.statusRedFlags === 'object'
        ? objeto.statusRedFlags
        : {},
    alertasLidos: Array.isArray(objeto.alertasLidos) ? objeto.alertasLidos : [],
    decisoes: Array.isArray(objeto.decisoes) ? objeto.decisoes : [],
  };
}

export function lerSessao(): EstadoDeSessao {
  const store = armazenamento();
  if (!store) return memoria;
  try {
    const cru = store.getItem(CHAVE_SESSAO);
    if (!cru) return memoria;
    memoria = normalizar(JSON.parse(cru));
    return memoria;
  } catch {
    return memoria;
  }
}

function gravar(proxima: EstadoDeSessao): EstadoDeSessao {
  memoria = proxima;
  const store = armazenamento();
  if (store) {
    try {
      store.setItem(CHAVE_SESSAO, JSON.stringify(proxima));
    } catch {
      // Cota estourada ou storage bloqueado: segue com o espelho em memória.
    }
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<EstadoDeSessao>(EVENTO_SESSAO, { detail: proxima }));
  }
  return proxima;
}

function mutar(f: (atual: EstadoDeSessao) => EstadoDeSessao): EstadoDeSessao {
  return gravar(f(lerSessao()));
}

/** Assina mutações locais **e** de outra aba (evento `storage`). Devolve o cancelador. */
export function assinarSessao(ouvinte: (estado: EstadoDeSessao) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const local = (evento: Event) => ouvinte((evento as CustomEvent<EstadoDeSessao>).detail);
  const outraAba = (evento: StorageEvent) => {
    if (evento.key === CHAVE_SESSAO || evento.key === null) ouvinte(lerSessao());
  };
  window.addEventListener(EVENTO_SESSAO, local);
  window.addEventListener('storage', outraAba);
  return () => {
    window.removeEventListener(EVENTO_SESSAO, local);
    window.removeEventListener('storage', outraAba);
  };
}

// ---------------------------------------------------------------------------
// Projeção para o motor
// ---------------------------------------------------------------------------

/**
 * Recorta o estado no formato que o Flask espera (`EstadoDeSessaoApi`).
 *
 * Sem `clienteId`, devolve só o status das red flags: enviar eventos de um cliente ao cálculo
 * de outro corromperia o score exibido.
 */
export function sessaoParaApi(
  clienteId?: string,
  estado: EstadoDeSessao = lerSessao(),
): EstadoDeSessaoApi {
  const eventos = clienteId
    ? estado.eventosSimulados.filter((e) => e.clienteId === clienteId)
    : [];
  return {
    eventosSimulados: eventos.map(({ tipo, data }) => ({ tipo, data })),
    statusRedFlags: estado.statusRedFlags,
  };
}

// ---------------------------------------------------------------------------
// Mutações
// ---------------------------------------------------------------------------

function novoId(prefixo: string): string {
  const aleatorio =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);
  return `${prefixo}-${aleatorio}`;
}

export function registrarEventoSimulado(entrada: {
  clienteId: string;
  clienteNome: string;
  tipo: TipoEvento;
  data?: string;
}): EventoSimuladoDaSessao {
  const evento: EventoSimuladoDaSessao = {
    id: novoId('ev'),
    clienteId: entrada.clienteId,
    clienteNome: entrada.clienteNome,
    tipo: entrada.tipo,
    data: entrada.data ?? new Date().toISOString(),
  };
  mutar((atual) => ({ ...atual, eventosSimulados: [...atual.eventosSimulados, evento] }));
  return evento;
}

/** "Desfazer" do popover de simulação (§1.5): remove o evento e o próximo cálculo volta ao que era. */
export function desfazerEventoSimulado(id: string): void {
  mutar((atual) => ({
    ...atual,
    eventosSimulados: atual.eventosSimulados.filter((e) => e.id !== id),
  }));
}

export function eventosSimuladosDoCliente(
  clienteId: string,
  estado: EstadoDeSessao = lerSessao(),
): EventoSimuladoDaSessao[] {
  return estado.eventosSimulados.filter((e) => e.clienteId === clienteId);
}

export function definirStatusRedFlag(redFlagId: string, status: StatusRedFlag): void {
  mutar((atual) => ({
    ...atual,
    statusRedFlags: { ...atual.statusRedFlags, [redFlagId]: status },
  }));
}

export function marcarAlertaComoLido(alertaId: string): void {
  mutar((atual) =>
    atual.alertasLidos.includes(alertaId)
      ? atual
      : { ...atual, alertasLidos: [...atual.alertasLidos, alertaId] },
  );
}

export function marcarAlertasComoLidos(ids: string[]): void {
  mutar((atual) => ({
    ...atual,
    alertasLidos: Array.from(new Set([...atual.alertasLidos, ...ids])),
  }));
}

export function alertaEstaLido(alertaId: string, estado: EstadoDeSessao = lerSessao()): boolean {
  return estado.alertasLidos.includes(alertaId);
}

/** Grava a decisão do analista. O registro já vem carimbado pelo motor (`registrarDecisao`). */
export function registrarDecisaoNaSessao(registro: RegistroAuditoria): void {
  mutar((atual) => ({ ...atual, decisoes: [registro, ...atual.decisoes] }));
}

export function decisoesDaSessao(estado: EstadoDeSessao = lerSessao()): RegistroAuditoria[] {
  return estado.decisoes;
}

/**
 * "Restaurar dados da demonstração" (D11.3) — apaga decisões, eventos simulados e marcações de
 * leitura. Quem chama é o `Modal` de confirmação da sidebar, que depois recarrega a rota.
 */
export function restaurarDemonstracao(): void {
  const store = armazenamento();
  if (store) {
    try {
      store.removeItem(CHAVE_SESSAO);
    } catch {
      // Ignorado: o `gravar` abaixo já repõe o estado vazio em memória.
    }
  }
  gravar(SESSAO_VAZIA);
}

/** `true` quando há algo a restaurar — a ação fica desabilitada numa sessão intocada. */
export function sessaoTemAlteracoes(estado: EstadoDeSessao = lerSessao()): boolean {
  return (
    estado.eventosSimulados.length > 0 ||
    estado.alertasLidos.length > 0 ||
    estado.decisoes.length > 0 ||
    Object.keys(estado.statusRedFlags).length > 0
  );
}
