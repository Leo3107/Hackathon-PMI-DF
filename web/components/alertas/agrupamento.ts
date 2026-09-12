/**
 * Filtros, agrupamento e contagens da central de alertas (`03-ux-e-telas.md` §7).
 *
 * Funções puras: recebem a lista que o motor devolveu e a data de referência, e nunca leem o
 * relógio por conta própria — o mesmo contrato dos formatadores (05 §11), que é o que torna
 * estas regras testáveis.
 */

import type { Alerta as AlertaDeLinha } from '@/components/ui';
import type { Alerta, Severidade } from '@/types';

/** Ordem de exibição e de gravidade. Vale para chips, tiles e agrupamento por severidade. */
export const SEVERIDADES: readonly Severidade[] = ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA'] as const;

/** Rótulos da tela, na forma pedida por §7 — "Crítico", não "CRITICA". */
export const ROTULO_SEVERIDADE: Record<Severidade, string> = {
  CRITICA: 'Crítico',
  ALTA: 'Alto',
  MEDIA: 'Médio',
  BAIXA: 'Informativo',
};

export type FiltroAlerta = 'nao_lidos' | 'ultimos_7d' | 'ultimos_30d' | 'acao_pendente';

export const ROTULO_FILTRO: Record<FiltroAlerta, string> = {
  nao_lidos: 'Não lidos',
  ultimos_7d: 'Últimos 7 dias',
  ultimos_30d: 'Últimos 30 dias',
  acao_pendente: 'Com ação pendente',
};

export type Agrupamento = 'data' | 'cliente' | 'severidade';

export const ROTULO_AGRUPAMENTO: Record<Agrupamento, string> = {
  data: 'Por data',
  cliente: 'Por cliente',
  severidade: 'Por severidade',
};

export interface CriteriosDeAlertas {
  severidades: ReadonlySet<Severidade>;
  filtros: ReadonlySet<FiltroAlerta>;
  /** ISO date ou datetime — o "hoje" da tela. */
  referencia: string;
}

// ---------------------------------------------------------------------------
// Datas
// ---------------------------------------------------------------------------

function diaEpoch(iso: string): number | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  if (!partes) return null;
  const [, ano, mes, dia] = partes;
  return Math.floor(Date.UTC(Number(ano), Number(mes) - 1, Number(dia)) / 86_400_000);
}

/** Dias inteiros de calendário entre o alerta e a referência. Positivo = passado. */
export function idadeEmDias(iso: string, referencia: string): number | null {
  const alvo = diaEpoch(iso);
  const base = diaEpoch(referencia);
  if (alvo === null || base === null) return null;
  return base - alvo;
}

/** Buckets nomeados de §7.1 — a pergunta que traz o analista à central é temporal. */
export type BucketDeData = 'hoje' | 'ontem' | 'semana' | 'mes' | 'anteriores';

export const ROTULO_BUCKET: Record<BucketDeData, string> = {
  hoje: 'Hoje',
  ontem: 'Ontem',
  semana: 'Esta semana',
  mes: 'Últimos 30 dias',
  anteriores: 'Anteriores',
};

const ORDEM_BUCKET: BucketDeData[] = ['hoje', 'ontem', 'semana', 'mes', 'anteriores'];

export function bucketDaData(iso: string, referencia: string): BucketDeData {
  const dias = idadeEmDias(iso, referencia);
  if (dias === null) return 'anteriores';
  if (dias <= 0) return 'hoje';
  if (dias === 1) return 'ontem';
  if (dias <= 7) return 'semana';
  if (dias <= 30) return 'mes';
  return 'anteriores';
}

// ---------------------------------------------------------------------------
// Leitura e contagem
// ---------------------------------------------------------------------------

/**
 * Projeta o estado de leitura da sessão sobre a lista do motor. O servidor não persiste nada
 * (D3): quem sabe o que foi lido é o `localStorage`.
 */
export function aplicarLeitura(alertas: Alerta[], lidos: readonly string[]): Alerta[] {
  const conjunto = new Set(lidos);
  return alertas.map((alerta) =>
    conjunto.has(alerta.id) === alerta.lido ? alerta : { ...alerta, lido: conjunto.has(alerta.id) },
  );
}

/**
 * Adapta o `Alerta` do contrato de transporte ao tipo que `AlertRow` aceita: o primitivo não
 * admite `eventoId: null`, e o motor pode devolvê-lo nulo. Diferença de contrato, não de dado.
 */
export function paraAlertRow(alerta: Alerta): AlertaDeLinha {
  return { ...alerta, eventoId: alerta.eventoId ?? undefined };
}

export function contarPorSeveridade(alertas: Alerta[]): Record<Severidade, number> {
  const contagem: Record<Severidade, number> = { CRITICA: 0, ALTA: 0, MEDIA: 0, BAIXA: 0 };
  for (const alerta of alertas) contagem[alerta.severidade] += 1;
  return contagem;
}

export function contarNaoLidos(alertas: Alerta[]): number {
  return alertas.filter((alerta) => !alerta.lido).length;
}

export function temCriticoNaoLido(alertas: Alerta[]): boolean {
  return alertas.some((alerta) => alerta.severidade === 'CRITICA' && !alerta.lido);
}

// ---------------------------------------------------------------------------
// Filtro
// ---------------------------------------------------------------------------

/** "Ação pendente": há ação recomendada e ninguém a leu ainda. */
function temAcaoPendente(alerta: Alerta): boolean {
  return !alerta.lido && (alerta.acaoRecomendada ?? '').trim().length > 0;
}

/** Severidade e filtros combinam por **E** (§7.1). Sem severidade marcada, todas passam. */
export function filtrarAlertas(alertas: Alerta[], criterios: CriteriosDeAlertas): Alerta[] {
  const { severidades, filtros, referencia } = criterios;
  return alertas.filter((alerta) => {
    if (severidades.size > 0 && !severidades.has(alerta.severidade)) return false;
    if (filtros.has('nao_lidos') && alerta.lido) return false;
    if (filtros.has('acao_pendente') && !temAcaoPendente(alerta)) return false;

    const dias = idadeEmDias(alerta.data, referencia);
    if (filtros.has('ultimos_7d') && (dias === null || dias > 7)) return false;
    if (filtros.has('ultimos_30d') && (dias === null || dias > 30)) return false;
    return true;
  });
}

// ---------------------------------------------------------------------------
// Agrupamento
// ---------------------------------------------------------------------------

export interface GrupoDeAlertas {
  chave: string;
  titulo: string;
  alertas: Alerta[];
}

const PESO_SEVERIDADE: Record<Severidade, number> = {
  CRITICA: 0,
  ALTA: 1,
  MEDIA: 2,
  BAIXA: 3,
};

/** Mais recente primeiro; empate resolvido pela severidade. */
function ordenar(alertas: Alerta[]): Alerta[] {
  return [...alertas].sort((a, b) => {
    if (a.data !== b.data) return a.data < b.data ? 1 : -1;
    return PESO_SEVERIDADE[a.severidade] - PESO_SEVERIDADE[b.severidade];
  });
}

export function agrupar(
  alertas: Alerta[],
  modo: Agrupamento,
  referencia: string,
): GrupoDeAlertas[] {
  const ordenados = ordenar(alertas);

  if (modo === 'severidade') {
    return SEVERIDADES.map((severidade) => ({
      chave: severidade,
      titulo: ROTULO_SEVERIDADE[severidade],
      alertas: ordenados.filter((alerta) => alerta.severidade === severidade),
    })).filter((grupo) => grupo.alertas.length > 0);
  }

  if (modo === 'cliente') {
    const porCliente = new Map<string, GrupoDeAlertas>();
    for (const alerta of ordenados) {
      const grupo = porCliente.get(alerta.clienteId);
      if (grupo) grupo.alertas.push(alerta);
      else
        porCliente.set(alerta.clienteId, {
          chave: alerta.clienteId,
          titulo: alerta.clienteNome,
          alertas: [alerta],
        });
    }
    return [...porCliente.values()].sort((a, b) => a.titulo.localeCompare(b.titulo, 'pt-BR'));
  }

  return ORDEM_BUCKET.map((bucket) => ({
    chave: bucket,
    titulo: ROTULO_BUCKET[bucket],
    alertas: ordenados.filter((alerta) => bucketDaData(alerta.data, referencia) === bucket),
  })).filter((grupo) => grupo.alertas.length > 0);
}

// ---------------------------------------------------------------------------
// Estado vazio (§7.4)
// ---------------------------------------------------------------------------

export interface TextoDeVazio {
  titulo: string;
  descricao: string;
  /** `limpar` volta aos filtros padrão; `ver_todos` só desmarca "Não lidos". */
  acao: 'nenhuma' | 'limpar' | 'ver_todos';
}

/** O estado vazio precisa dizer **por que** está vazio (§9.1), não apenas "Nenhum dado". */
export function textoDoVazio(
  totalNaCarteira: number,
  criterios: CriteriosDeAlertas,
  todosLidos: boolean,
): TextoDeVazio {
  if (totalNaCarteira === 0) {
    return {
      titulo: 'Nenhum alerta na carteira',
      descricao:
        'O motor não gerou alertas para os clientes monitorados. Alertas nascem dos eventos de risco de cada cliente.',
      acao: 'nenhuma',
    };
  }

  if (criterios.filtros.has('nao_lidos') && todosLidos) {
    return {
      titulo: 'Você está em dia',
      descricao: 'Nenhum alerta pendente de leitura nesta sessão.',
      acao: 'ver_todos',
    };
  }

  const partes: string[] = [];
  if (criterios.severidades.size > 0) {
    partes.push(
      [...criterios.severidades]
        .map((severidade) => ROTULO_SEVERIDADE[severidade].toLowerCase())
        .join(', '),
    );
  }
  for (const filtro of criterios.filtros) partes.push(ROTULO_FILTRO[filtro].toLowerCase());

  return {
    titulo: 'Nenhum alerta com os filtros atuais',
    descricao:
      partes.length > 0
        ? `Nenhum alerta ${partes.join(' · ')}. Os demais alertas continuam na lista sem esses filtros.`
        : 'Nenhum alerta corresponde à combinação escolhida.',
    acao: 'limpar',
  };
}
