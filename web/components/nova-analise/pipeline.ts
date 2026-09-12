/**
 * Semântica do pipeline de due diligence (`03-ux-e-telas.md` §6.4).
 *
 * **Regra dura:** a animação não é decorativa. Um estágio só é marcado como concluído quando o
 * dado correspondente **existe na resposta do motor** — a conferência está em `dadoDisponivel`,
 * que é função pura e testada. Os intervalos de 280ms a 700ms existem apenas para a sequência
 * ser legível; eles atrasam a revelação, nunca a antecipam.
 *
 * Todo o conteúdo exibido (achados, contadores, score) vem da `RespostaDueDiligence`. Este
 * módulo não calcula nada de risco.
 */

import type {
  AvaliacaoDeRisco,
  DimensaoId,
  EstagioPipeline,
  FonteId,
  RespostaDueDiligence,
  ResultadoEstagio,
} from '@/types';

/** Piso e teto do intervalo de revelação de cada estágio (§6.4). */
export const PISO_ESTAGIO_MS = 280;
export const TETO_ESTAGIO_MS = 700;

/** Texto que o motor devolve quando a fonte não retornou evidência — informação, não falha. */
export const SEM_REGISTRO = 'Nenhum registro encontrado';

export type StatusEstagio = 'pendente' | 'consultando' | 'concluido' | 'sem_dado' | 'falha';

export interface DefinicaoEstagio {
  id: EstagioPipeline;
  rotulo: string;
  /** Nomes das bases, exibidos sob o rótulo — o jurado precisa ver de onde vem o dado. */
  fontesExibidas: string[];
  /** Fontes cujas evidências alimentam o contador do estágio. */
  fontes: FonteId[];
  /** Dimensões que precisam existir na avaliação para o estágio poder ser concluído. */
  dimensoes: DimensaoId[];
}

/**
 * Os oito estágios, na ordem e com as fontes da tabela de §6.4. Espelha
 * `api/routes/due_diligence.py::_PIPELINE_DE_FONTES`; qualquer divergência aparece como
 * estágio que não conclui, nunca como número errado.
 */
export const ESTAGIOS: readonly DefinicaoEstagio[] = [
  {
    id: 'CADASTRAL',
    rotulo: 'Cadastral',
    fontesExibidas: ['Receita Federal', 'Redesim'],
    fontes: ['RECEITA_FEDERAL', 'REDESIM'],
    dimensoes: ['cadastral'],
  },
  {
    id: 'JURIDICO',
    rotulo: 'Jurídico',
    fontesExibidas: ['DataJud/CNJ', 'DJE', 'Cartórios de protesto'],
    fontes: ['DATAJUD_CNJ', 'DJE', 'CARTORIO_PROTESTO'],
    dimensoes: ['juridico'],
  },
  {
    id: 'FISCAL',
    rotulo: 'Fiscal',
    fontesExibidas: ['PGFN', 'TST/CNDT', 'Caixa CRF-FGTS'],
    fontes: ['PGFN', 'TST_CNDT', 'CAIXA_CRF_FGTS'],
    dimensoes: ['fiscal'],
  },
  {
    id: 'AMBIENTAL',
    rotulo: 'Ambiental',
    fontesExibidas: ['SICAR', 'IBAMA'],
    fontes: ['SICAR', 'IBAMA'],
    dimensoes: ['ambiental'],
  },
  {
    id: 'AGROCLIMATICO',
    rotulo: 'Agroclimático',
    fontesExibidas: ['MAPA/ZARC', 'CONAB', 'INMET'],
    fontes: ['MAPA_ZARC', 'CONAB', 'INMET'],
    dimensoes: ['agroclimatico'],
  },
  {
    id: 'INTERNO',
    rotulo: 'Interno',
    fontesExibidas: ['Histórico Krill Tech'],
    fontes: ['INTERNO_KRILLTECH'],
    dimensoes: ['comportamental', 'garantias'],
  },
  {
    id: 'SCORE',
    rotulo: 'Score',
    fontesExibidas: ['Motor de Decisão & Scoring'],
    fontes: [],
    dimensoes: [],
  },
  {
    id: 'RELATORIO',
    rotulo: 'Relatório',
    fontesExibidas: ['Agente Sintetizador'],
    fontes: [],
    dimensoes: [],
  },
] as const;

/** Índice do último estágio que o pipeline conclui aqui; `RELATORIO` roda na página do cliente. */
export const INDICE_SCORE = ESTAGIOS.findIndex((estagio) => estagio.id === 'SCORE');

/** Tolerância de fechamento da invariante I2, idêntica à do motor. */
export const TOLERANCIA_FECHAMENTO = 0.5;

export function resultadoDoEstagio(
  resposta: RespostaDueDiligence | null,
  id: EstagioPipeline,
): ResultadoEstagio | undefined {
  return resposta?.estagios?.find((estagio) => estagio.estagio === id);
}

/**
 * O coração da honestidade do pipeline: responde se o dado do estágio **chegou**.
 *
 * - estágios de coleta: a dimensão correspondente existe na avaliação **e** o motor devolveu
 *   o resultado daquele estágio sem falha;
 * - `SCORE`: há score calculado e a soma das contribuições fecha dentro da tolerância;
 * - `RELATORIO`: sempre `false` — a narrativa é gerada na página do cliente, e marcar este
 *   estágio como concluído aqui seria exatamente o teatro que a spec proíbe.
 */
export function dadoDisponivel(
  definicao: DefinicaoEstagio,
  resposta: RespostaDueDiligence | null,
): boolean {
  if (!resposta || !resposta.encontrado) return false;
  const avaliacao = resposta.avaliacao;
  if (!avaliacao) return false;

  if (definicao.id === 'RELATORIO') return false;

  if (definicao.id === 'SCORE') {
    return (
      Number.isFinite(avaliacao.scoreCalculado) &&
      Math.abs(avaliacao.auditoria?.diferenca ?? Number.NaN) <= TOLERANCIA_FECHAMENTO
    );
  }

  const resultado = resultadoDoEstagio(resposta, definicao.id);
  if (!resultado || resultado.status === 'falha') return false;

  const presentes = new Set<DimensaoId>(avaliacao.dimensoes.map((dimensao) => dimensao.id));
  return definicao.dimensoes.every((dimensao) => presentes.has(dimensao));
}

/** Status final de um estágio já revelado: distingue "sem dado" (permitido) de "falha". */
export function statusAposRevelar(
  definicao: DefinicaoEstagio,
  resposta: RespostaDueDiligence | null,
): StatusEstagio {
  if (!dadoDisponivel(definicao, resposta)) return 'falha';
  const achados = achadosDoEstagio(definicao, resposta);
  const vazio = achados.length === 0 || achados.every((linha) => linha === SEM_REGISTRO);
  return vazio ? 'sem_dado' : 'concluido';
}

export function achadosDoEstagio(
  definicao: DefinicaoEstagio,
  resposta: RespostaDueDiligence | null,
): string[] {
  return resultadoDoEstagio(resposta, definicao.id)?.achados ?? [];
}

/** Evidências que sustentam o estágio — o contador da tabela de §6.4. */
export function contarEvidencias(
  definicao: DefinicaoEstagio,
  avaliacao: AvaliacaoDeRisco | undefined,
): number {
  if (!avaliacao || definicao.fontes.length === 0) return 0;
  const fontes = new Set<FonteId>(definicao.fontes);
  return avaliacao.evidencias.filter((evidencia) => fontes.has(evidencia.fonte)).length;
}

/**
 * Intervalo de exibição do estágio, em ms. Usa a duração real medida pelo motor, presa entre o
 * piso e o teto da spec — abaixo de 280ms a sequência fica ilegível, acima de 700ms vira espera.
 */
export function duracaoDeExibicao(duracaoMs: number | undefined): number {
  if (!Number.isFinite(duracaoMs)) return PISO_ESTAGIO_MS;
  return Math.min(TETO_ESTAGIO_MS, Math.max(PISO_ESTAGIO_MS, Number(duracaoMs)));
}

/** Contador textual do estágio (R2: nunca só cor, nunca só ícone). */
export function contadorDoEstagio(
  definicao: DefinicaoEstagio,
  status: StatusEstagio,
  resposta: RespostaDueDiligence | null,
): string {
  if (status === 'pendente') return '—';
  if (status === 'consultando') return 'consultando…';
  if (status === 'falha') return 'sem resposta';

  if (definicao.id === 'SCORE') {
    const diferenca = resposta?.avaliacao?.auditoria?.diferenca ?? 0;
    return `fecha em ${Math.abs(diferenca).toFixed(2)} ponto(s)`;
  }
  if (definicao.id === 'RELATORIO') return 'na página do cliente';

  const total = contarEvidencias(definicao, resposta?.avaliacao);
  if (total === 0) return 'sem registro';
  return `${total} ${total === 1 ? 'documento' : 'documentos'}`;
}

export interface ItemDeRegistro {
  id: string;
  /** `HH:mm:ss` do instante em que a linha foi revelada. */
  hora: string;
  estagio: string;
  texto: string;
}

const HORA = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

export function horaDoRegistro(instante: Date): string {
  return HORA.format(instante);
}

/** Linhas do "registro da coleta" de um estágio recém-revelado. */
export function linhasDoRegistro(
  definicao: DefinicaoEstagio,
  resposta: RespostaDueDiligence | null,
  instante: Date,
): ItemDeRegistro[] {
  const achados = achadosDoEstagio(definicao, resposta);
  const textos = achados.length > 0 ? achados : [SEM_REGISTRO];
  const hora = horaDoRegistro(instante);
  return textos.map((texto, indice) => ({
    id: `${definicao.id}-${indice}`,
    hora,
    estagio: definicao.rotulo.toUpperCase(),
    texto,
  }));
}
