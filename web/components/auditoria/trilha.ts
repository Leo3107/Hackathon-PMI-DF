/**
 * Trilha de decisão humana — regras puras (`03-ux-e-telas.md` §8).
 *
 * A trilha tem duas origens e uma só verdade: o que o motor devolve em `GET /api/auditoria`
 * (registros do dataset) e o que o analista registrou nesta sessão, guardado em `localStorage`
 * (D11.3). A marca de divergência **nunca** é recalculada aqui — vem carimbada no registro
 * (R6); estas funções apenas contam, filtram e escrevem o texto.
 */

import type { CodigoRecomendacao, DecisaoAnalista, RegistroAuditoria } from '@/types';

export const ROTULO_RECOMENDACAO: Record<CodigoRecomendacao, string> = {
  APROVAR: 'Aprovar',
  APROVAR_COM_MONITORAMENTO_INTENSIVO: 'Aprovar com monitoramento intensivo',
  APROVAR_COM_REVISAO_DE_LIMITE: 'Aprovar com revisão de limite',
  APROVAR_COM_RESTRICOES: 'Aprovar com restrições',
  SUSPENDER_NOVA_EXPOSICAO_A_PRAZO: 'Suspender nova exposição a prazo',
  SUSPENDER_EXPOSICAO: 'Suspender exposição',
};

export const ROTULO_DECISAO: Record<DecisaoAnalista, string> = {
  APROVAR: 'Aprovar',
  APROVAR_COM_RESTRICOES: 'Aprovar com restrições',
  REVISAR: 'Revisar',
  SUSPENDER: 'Suspender',
  RECUSAR: 'Recusar',
};

export type FiltroAuditoria = 'divergentes' | 'ultimos_30d';

export const ROTULO_FILTRO_AUDITORIA: Record<FiltroAuditoria, string> = {
  divergentes: 'Divergentes',
  ultimos_30d: 'Últimos 30 dias',
};

/** Caracteres exibidos na célula antes de a linha ser expandida (§8.1). */
export const LIMITE_JUSTIFICATIVA = 80;

/**
 * Sessão primeiro, depois o dataset; empate de id fica com a versão da sessão, que é a mais
 * recente. Ordena por data e hora decrescente, como manda §8.1.
 */
export function unirTrilha(
  doMotor: RegistroAuditoria[],
  daSessao: RegistroAuditoria[],
): RegistroAuditoria[] {
  const porId = new Map<string, RegistroAuditoria>();
  for (const registro of doMotor) porId.set(registro.id, registro);
  for (const registro of daSessao) porId.set(registro.id, registro);
  return [...porId.values()].sort((a, b) => (a.dataHora < b.dataHora ? 1 : -1));
}

function diaEpoch(iso: string): number | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  if (!partes) return null;
  const [, ano, mes, dia] = partes;
  return Math.floor(Date.UTC(Number(ano), Number(mes) - 1, Number(dia)) / 86_400_000);
}

export interface CriteriosDaTrilha {
  filtros: ReadonlySet<FiltroAuditoria>;
  /** `null` = todos os clientes. */
  clienteId: string | null;
  /** ISO date ou datetime — o "hoje" da tela. */
  referencia: string;
}

export function filtrarTrilha(
  registros: RegistroAuditoria[],
  criterios: CriteriosDaTrilha,
): RegistroAuditoria[] {
  const base = diaEpoch(criterios.referencia);
  return registros.filter((registro) => {
    if (criterios.clienteId && registro.clienteId !== criterios.clienteId) return false;
    if (criterios.filtros.has('divergentes') && !registro.divergiuDaRecomendacao) return false;
    if (criterios.filtros.has('ultimos_30d')) {
      const dia = diaEpoch(registro.dataHora);
      if (dia === null || base === null || base - dia > 30) return false;
    }
    return true;
  });
}

export interface EstatisticasDaTrilha {
  total: number;
  divergentes: number;
  /** Fração 0..1, pronta para `formatarPercentual`. */
  fracao: number;
}

export function estatisticasDaTrilha(registros: RegistroAuditoria[]): EstatisticasDaTrilha {
  const total = registros.length;
  const divergentes = registros.filter((registro) => registro.divergiuDaRecomendacao).length;
  return { total, divergentes, fracao: total === 0 ? 0 : divergentes / total };
}

export interface ClienteDaTrilha {
  id: string;
  nome: string;
}

export function clientesDaTrilha(registros: RegistroAuditoria[]): ClienteDaTrilha[] {
  const porId = new Map<string, string>();
  for (const registro of registros) porId.set(registro.clienteId, registro.clienteNome);
  return [...porId.entries()]
    .map(([id, nome]) => ({ id, nome }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

/**
 * A linha extra, sempre visível, do §8.2. É a prova visual do human-in-the-loop: a máquina
 * recomendou uma coisa, a pessoa decidiu outra, e o registro guarda as duas.
 */
export function resumoDaDivergencia(registro: RegistroAuditoria): string {
  return `Recomendado: ${ROTULO_RECOMENDACAO[registro.recomendacaoGerada].toUpperCase()}  →  Decidido: ${ROTULO_DECISAO[registro.decisaoAnalista].toUpperCase()}`;
}

export function justificativaCurta(texto: string): string {
  const limpo = (texto ?? '').trim();
  if (limpo.length <= LIMITE_JUSTIFICATIVA) return limpo;
  return `${limpo.slice(0, LIMITE_JUSTIFICATIVA)}⋯`;
}

/** Frase do contador de divergência do cabeçalho (§8.1). */
export function fraseDeDivergencia(
  estatisticas: EstatisticasDaTrilha,
  percentual: string,
): string {
  if (estatisticas.total === 0) return 'Nenhuma decisão registrada até aqui.';
  const verbo = estatisticas.divergentes === 1 ? 'divergiu' : 'divergiram';
  return `${estatisticas.divergentes} de ${estatisticas.total} ${estatisticas.total === 1 ? 'decisão' : 'decisões'} ${verbo} da recomendação (${percentual}).`;
}
