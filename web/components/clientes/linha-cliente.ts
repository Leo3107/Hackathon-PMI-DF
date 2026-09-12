/**
 * Modelo de linha da lista de clientes (`03-ux-e-telas.md` §3) — e todas as regras de filtro,
 * busca e ordenação, isoladas em funções puras para serem testáveis sem DOM.
 *
 * **Ponto único de leitura de `ClienteAvaliado`.** O contrato dos agregados foi *proposto* pelo
 * workstream do shell e pode mudar quando a API existir; concentrando a leitura aqui, a tela
 * inteira sobrevive a uma renomeação de campo com uma edição neste arquivo.
 *
 * R6 continua valendo: nada aqui recalcula risco. O que se faz é **selecionar** e **ordenar** o
 * que o motor já decidiu — mais o limiar do quartil superior de exposição, que é critério de
 * triagem da tela, não número de risco.
 */

import type { ClienteAvaliado, Rating, Severidade, Tendencia, TipoPessoa } from '@/types';

export type ValorFiltro =
  | 'todos'
  | 'rating-a'
  | 'rating-b'
  | 'rating-c'
  | 'rating-d'
  | 'com-alerta'
  | 'veto'
  | 'deterioracao'
  | 'alta-exposicao';

export const FILTROS: ValorFiltro[] = [
  'todos',
  'rating-a',
  'rating-b',
  'rating-c',
  'rating-d',
  'com-alerta',
  'veto',
  'deterioracao',
  'alta-exposicao',
];

export const ROTULO_FILTRO: Record<ValorFiltro, string> = {
  todos: 'Todos',
  'rating-a': 'Rating A',
  'rating-b': 'Rating B',
  'rating-c': 'Rating C',
  'rating-d': 'Rating D',
  'com-alerta': 'Com alerta',
  veto: 'Com gatilho de veto',
  deterioracao: 'Deterioração recente',
  'alta-exposicao': 'Alta exposição',
};

export type ChaveOrdem =
  | 'score'
  | 'exposicao'
  | 'pd'
  | 'variacao'
  | 'alertas'
  | 'risco_rj'
  | 'cobertura';

export type Direcao = 'asc' | 'desc';

export const ORDENS: ChaveOrdem[] = [
  'score',
  'exposicao',
  'pd',
  'variacao',
  'alertas',
  'risco_rj',
  'cobertura',
];

/** Direção do **primeiro** clique em cada coluna (§3.5). Pior sempre no topo. */
export const DIRECAO_PADRAO: Record<ChaveOrdem, Direcao> = {
  score: 'asc',
  exposicao: 'desc',
  pd: 'desc',
  variacao: 'asc',
  alertas: 'desc',
  risco_rj: 'desc',
  cobertura: 'asc',
};

/** Queda de score, em pontos, que caracteriza deterioração recente (§3.3). */
export const LIMIAR_DETERIORACAO = -25;

export type FaixaRJ = 'baixo' | 'moderado' | 'alto' | 'critico' | 'ocorrido';

export const ROTULO_FAIXA_RJ: Record<FaixaRJ, string> = {
  baixo: 'baixo',
  moderado: 'moderado',
  alto: 'alto',
  critico: 'crítico',
  ocorrido: 'ocorrido',
};

/** Faixas textuais de risco de RJ (§4.4). Classificação de exibição, não cálculo de risco. */
export function faixaDeRJ(probabilidade12m: number, eventoJaOcorrido: boolean): FaixaRJ {
  if (eventoJaOcorrido) return 'ocorrido';
  if (probabilidade12m < 0.05) return 'baixo';
  if (probabilidade12m < 0.15) return 'moderado';
  if (probabilidade12m <= 0.3) return 'alto';
  return 'critico';
}

/**
 * Campos que o Flask **pode** acrescentar a `ClienteAvaliado` e que a lista aproveita quando
 * existirem: a coluna 7 (próximo vencimento) e a severidade da pastilha da coluna 13 não são
 * deriváveis do contrato atual, porque parcelas e alertas não viajam no agregado.
 */
interface ExtrasDoAgregado {
  proximoVencimento?: { data: string; diasRestantes?: number; diasAtraso?: number } | null;
  severidadeMaximaAlerta?: Severidade | null;
  alertasTotal?: number;
}

export interface LinhaCliente {
  id: string;
  razaoSocial: string;
  nomeFantasia: string | null;
  documento: string;
  /** Só dígitos — permite buscar com e sem máscara. */
  documentoNumeros: string;
  municipio: string;
  uf: string;
  tipoPessoa: TipoPessoa;
  culturas: string[];
  exposicaoTotal: number;
  exposicaoEmRiscoEmRJ: number;
  coberturaTotal: number;
  proximoVencimento: { data: string; diasRestantes: number | null; diasAtraso: number | null } | null;
  score: number;
  ratingCalculado: Rating;
  ratingFinal: Rating;
  temVeto: boolean;
  rotuloVeto: string | null;
  pd12m: number;
  probabilidadeRJ: number;
  eventoRJOcorrido: boolean;
  faixaRJ: FaixaRJ;
  tendencia: Tendencia;
  /** `null` quando não há snapshot anterior (prospect ou cliente novo). */
  deltaScore: number | null;
  alertasNaoLidos: number;
  severidadeMaximaAlerta: Severidade | null;
  /** Texto pré-normalizado para a busca de §3.4. */
  indiceDeBusca: string;
}

export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

export function somenteDigitos(texto: string): string {
  return texto.replace(/\D+/g, '');
}

export function paraLinha(avaliado: ClienteAvaliado): LinhaCliente {
  const { cliente, avaliacao, variacao90d, alertasNaoLidos } = avaliado;
  const extras = avaliado as ClienteAvaliado & ExtrasDoAgregado;

  const documentoNumeros = somenteDigitos(cliente.documento);
  const veto = avaliacao.vetosAtivos[0] ?? null;

  const proximo = extras.proximoVencimento ?? null;

  return {
    id: cliente.id,
    razaoSocial: cliente.razaoSocial,
    nomeFantasia: cliente.nomeFantasia ?? null,
    documento: cliente.documento,
    documentoNumeros,
    municipio: cliente.municipio,
    uf: cliente.uf,
    tipoPessoa: cliente.tipoPessoa,
    culturas: cliente.culturas ?? [],
    exposicaoTotal: avaliacao.exposicao.exposicaoTotal,
    exposicaoEmRiscoEmRJ: avaliacao.exposicao.exposicaoEmRiscoEmRJ,
    coberturaTotal: avaliacao.exposicao.coberturaTotal,
    proximoVencimento: proximo
      ? {
          data: proximo.data,
          diasRestantes: proximo.diasRestantes ?? null,
          diasAtraso: proximo.diasAtraso ?? null,
        }
      : null,
    score: avaliacao.scoreCalculado,
    ratingCalculado: avaliacao.ratingCalculado,
    ratingFinal: avaliacao.ratingFinal,
    temVeto: avaliacao.vetosAtivos.length > 0,
    rotuloVeto: veto?.rotulo ?? null,
    pd12m: avaliacao.pd.pd12m,
    probabilidadeRJ: avaliacao.riscoRJ.probabilidade12m,
    eventoRJOcorrido: avaliacao.riscoRJ.eventoJaOcorrido,
    faixaRJ: faixaDeRJ(avaliacao.riscoRJ.probabilidade12m, avaliacao.riscoRJ.eventoJaOcorrido),
    tendencia: avaliacao.tendencia,
    deltaScore: variacao90d ? variacao90d.deltaScore : null,
    alertasNaoLidos,
    severidadeMaximaAlerta: extras.severidadeMaximaAlerta ?? null,
    indiceDeBusca: normalizar(
      [
        cliente.razaoSocial,
        cliente.nomeFantasia ?? '',
        cliente.documento,
        documentoNumeros,
        cliente.municipio,
        cliente.uf,
      ].join(' '),
    ),
  };
}

/**
 * Limiar do quartil superior de exposição (§3.3, chip "Alta exposição"). Percentil 75 pelo
 * método do valor mais próximo, sem interpolação: com 18 clientes qualquer interpolação seria
 * precisão fingida.
 */
export function limiarAltaExposicao(linhas: LinhaCliente[]): number {
  if (linhas.length === 0) return Number.POSITIVE_INFINITY;
  const valores = linhas.map((linha) => linha.exposicaoTotal).sort((a, b) => a - b);
  const indice = Math.min(valores.length - 1, Math.ceil(valores.length * 0.75) - 1);
  return valores[Math.max(0, indice)];
}

export function atendeAoFiltro(
  linha: LinhaCliente,
  filtro: ValorFiltro,
  limiarExposicao: number,
): boolean {
  switch (filtro) {
    case 'todos':
      return true;
    case 'rating-a':
      return linha.ratingFinal === 'A';
    case 'rating-b':
      return linha.ratingFinal === 'B';
    case 'rating-c':
      return linha.ratingFinal === 'C';
    case 'rating-d':
      return linha.ratingFinal === 'D';
    case 'com-alerta':
      return linha.alertasNaoLidos > 0;
    case 'veto':
      return linha.temVeto;
    case 'deterioracao':
      return linha.deltaScore !== null && linha.deltaScore <= LIMIAR_DETERIORACAO;
    case 'alta-exposicao':
      return linha.exposicaoTotal >= limiarExposicao;
    default:
      return true;
  }
}

export function contarFiltros(
  linhas: LinhaCliente[],
  limiarExposicao: number,
): Record<ValorFiltro, number> {
  const contagens = {} as Record<ValorFiltro, number>;
  for (const filtro of FILTROS) {
    contagens[filtro] = linhas.filter((linha) => atendeAoFiltro(linha, filtro, limiarExposicao)).length;
  }
  return contagens;
}

export function atendeABusca(linha: LinhaCliente, termo: string): boolean {
  const alvo = normalizar(termo);
  if (!alvo) return true;
  const digitos = somenteDigitos(termo);
  if (digitos.length >= 3 && linha.documentoNumeros.includes(digitos)) return true;
  return linha.indiceDeBusca.includes(alvo);
}

export interface CriteriosDeLista {
  filtro: ValorFiltro;
  busca: string;
  cultura: string | null;
  uf: string | null;
  ordem: ChaveOrdem;
  direcao: Direcao;
}

/** Valor de ordenação por chave. `null` vai sempre para o fim, qualquer que seja a direção. */
export function valorDeOrdem(linha: LinhaCliente, ordem: ChaveOrdem): number | null {
  switch (ordem) {
    case 'score':
      return linha.score;
    case 'exposicao':
      return linha.exposicaoTotal;
    case 'pd':
      return linha.pd12m;
    case 'variacao':
      return linha.deltaScore;
    case 'alertas':
      return linha.alertasNaoLidos;
    case 'risco_rj':
      return linha.exposicaoEmRiscoEmRJ;
    case 'cobertura':
      return linha.coberturaTotal;
    default:
      return null;
  }
}

export function ordenarLinhas(
  linhas: LinhaCliente[],
  ordem: ChaveOrdem,
  direcao: Direcao,
): LinhaCliente[] {
  const fator = direcao === 'asc' ? 1 : -1;
  return [...linhas].sort((a, b) => {
    const va = valorDeOrdem(a, ordem);
    const vb = valorDeOrdem(b, ordem);
    if (va === null && vb === null) return a.razaoSocial.localeCompare(b.razaoSocial, 'pt-BR');
    if (va === null) return 1;
    if (vb === null) return -1;
    if (va === vb) return a.razaoSocial.localeCompare(b.razaoSocial, 'pt-BR');
    return fator * (va - vb);
  });
}

/** Pipeline completo: filtro **E** busca **E** recortes de drill-down, depois ordenação. */
export function aplicarCriterios(
  linhas: LinhaCliente[],
  criterios: CriteriosDeLista,
  limiarExposicao: number,
): LinhaCliente[] {
  const culturaAlvo = criterios.cultura ? normalizar(criterios.cultura) : null;
  const ufAlvo = criterios.uf ? normalizar(criterios.uf) : null;

  const filtradas = linhas.filter((linha) => {
    if (!atendeAoFiltro(linha, criterios.filtro, limiarExposicao)) return false;
    if (!atendeABusca(linha, criterios.busca)) return false;
    if (culturaAlvo && !linha.culturas.some((c) => normalizar(c) === culturaAlvo)) return false;
    if (ufAlvo && normalizar(linha.uf) !== ufAlvo) return false;
    return true;
  });

  return ordenarLinhas(filtradas, criterios.ordem, criterios.direcao);
}
