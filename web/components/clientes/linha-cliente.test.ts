import { describe, expect, it } from 'vitest';

import type { ClienteAvaliado, Rating, Tendencia } from '@/types';

import {
  LIMIAR_DETERIORACAO,
  aplicarCriterios,
  atendeABusca,
  atendeAoFiltro,
  contarFiltros,
  faixaDeRJ,
  limiarAltaExposicao,
  normalizar,
  ordenarLinhas,
  paraLinha,
  somenteDigitos,
} from './linha-cliente';

interface Semente {
  id: string;
  razaoSocial: string;
  documento: string;
  municipio: string;
  uf: string;
  culturas?: string[];
  exposicao: number;
  exposicaoEmRiscoEmRJ?: number;
  coberturaTotal?: number;
  score: number;
  rating: Rating;
  ratingCalculado?: Rating;
  vetos?: number;
  pd12m: number;
  probabilidadeRJ?: number;
  eventoRJOcorrido?: boolean;
  tendencia?: Tendencia;
  delta?: number | null;
  alertas?: number;
}

/**
 * Fábrica mínima: o teste exercita as regras de seleção e ordenação, não a forma completa do
 * contrato. Os campos ausentes de `AvaliacaoDeRisco` não são lidos por `paraLinha`.
 */
function avaliado(semente: Semente): ClienteAvaliado {
  return {
    cliente: {
      id: semente.id,
      razaoSocial: semente.razaoSocial,
      nomeFantasia: null,
      documento: semente.documento,
      tipoPessoa: 'PJ',
      municipio: semente.municipio,
      uf: semente.uf,
      atividade: 'Produtor rural — grãos',
      cnaePrincipal: '0111-3/01',
      culturas: semente.culturas ?? ['Soja'],
      inicioRelacionamento: '2019-03-01',
      estado: 'ATIVO',
      origem: 'CARTEIRA',
    },
    avaliacao: {
      clienteId: semente.id,
      dataReferencia: '2026-09-12',
      scoreCalculado: semente.score,
      ratingCalculado: semente.ratingCalculado ?? semente.rating,
      ratingFinal: semente.rating,
      vetosAtivos: Array.from({ length: semente.vetos ?? 0 }, (_, i) => ({
        id: `veto-${i}`,
        rotulo: 'Embargo do IBAMA sobre imóvel em garantia',
        efeito: 'FORCA_D' as const,
        justificativa: 'Garantia juridicamente comprometida.',
        evidenciaIds: [],
      })),
      pd: { pd6m: semente.pd12m / 2, pd12m: semente.pd12m, pd24m: semente.pd12m * 2, metodo: 'x' },
      riscoRJ: {
        probabilidade12m: semente.probabilidadeRJ ?? 0.02,
        eventoJaOcorrido: semente.eventoRJOcorrido ?? false,
        rjIndex: 10,
        rjIndexEfetivo: 10,
        elegivel: true,
        sinais: [],
      },
      exposicao: {
        exposicaoTotal: semente.exposicao,
        exposicaoEmRiscoEmRJ: semente.exposicaoEmRiscoEmRJ ?? semente.exposicao / 2,
        coberturaTotal: semente.coberturaTotal ?? 0.7,
      },
      tendencia: semente.tendencia ?? 'estavel',
    },
    variacao90d:
      semente.delta === null || semente.delta === undefined
        ? undefined
        : ({ deltaScore: semente.delta } as ClienteAvaliado['variacao90d']),
    alertasNaoLidos: semente.alertas ?? 0,
  } as unknown as ClienteAvaliado;
}

const CARTEIRA = [
  avaliado({
    id: 'vale-araguaia',
    razaoSocial: 'Fazenda Vale do Araguaia Ltda',
    documento: '12.345.678/0001-90',
    municipio: 'Querência',
    uf: 'MT',
    culturas: ['Soja', 'Milho safrinha'],
    exposicao: 14_200_000,
    score: 604,
    rating: 'C',
    pd12m: 0.171,
    tendencia: 'deterioracao_acelerada',
    delta: -108,
    alertas: 3,
  }),
  avaliado({
    id: 'serra-azul',
    razaoSocial: 'Agro Serra Azul Ltda',
    documento: '98.765.432/0001-10',
    municipio: 'Luís Eduardo Magalhães',
    uf: 'BA',
    culturas: ['Algodão'],
    exposicao: 4_820_000,
    score: 612,
    rating: 'D',
    ratingCalculado: 'B',
    vetos: 1,
    pd12m: 0.164,
    delta: -12,
    alertas: 1,
  }),
  avaliado({
    id: 'cerrado-graos',
    razaoSocial: 'Cerrado Grãos S/A',
    documento: '11.222.333/0001-44',
    municipio: 'Rio Verde',
    uf: 'GO',
    culturas: ['Soja', 'Milho'],
    exposicao: 22_000_000,
    score: 318,
    rating: 'D',
    pd12m: 0.42,
    probabilidadeRJ: 1,
    eventoRJOcorrido: true,
    delta: -64,
    alertas: 5,
  }),
  avaliado({
    id: 'campo-limpo',
    razaoSocial: 'Campo Limpo Agropecuária',
    documento: '55.666.777/0001-88',
    municipio: 'Patos de Minas',
    uf: 'MG',
    culturas: ['Café'],
    exposicao: 2_100_000,
    score: 812,
    rating: 'A',
    pd12m: 0.021,
    delta: 14,
  }),
].map(paraLinha);

describe('faixaDeRJ', () => {
  it('classifica pelas fronteiras da spec e nunca confunde com PD', () => {
    expect(faixaDeRJ(0.049, false)).toBe('baixo');
    expect(faixaDeRJ(0.05, false)).toBe('moderado');
    expect(faixaDeRJ(0.1499, false)).toBe('moderado');
    expect(faixaDeRJ(0.15, false)).toBe('alto');
    expect(faixaDeRJ(0.3, false)).toBe('alto');
    expect(faixaDeRJ(0.31, false)).toBe('critico');
  });

  it('evento já ocorrido não é previsão: vira "ocorrido" em qualquer probabilidade', () => {
    expect(faixaDeRJ(0.01, true)).toBe('ocorrido');
    expect(faixaDeRJ(1, true)).toBe('ocorrido');
  });
});

describe('paraLinha', () => {
  it('lê o rating final, preserva o calculado e sinaliza o veto', () => {
    const serra = CARTEIRA.find((linha) => linha.id === 'serra-azul');
    expect(serra?.ratingFinal).toBe('D');
    expect(serra?.ratingCalculado).toBe('B');
    expect(serra?.temVeto).toBe(true);
    expect(serra?.rotuloVeto).toContain('IBAMA');
  });

  it('devolve delta nulo quando não há snapshot anterior', () => {
    const semHistorico = paraLinha(
      avaliado({
        id: 'novo',
        razaoSocial: 'Prospect Ltda',
        documento: '00.000.000/0001-00',
        municipio: 'Sorriso',
        uf: 'MT',
        exposicao: 0,
        score: 700,
        rating: 'B',
        pd12m: 0.08,
        delta: null,
      }),
    );
    expect(semHistorico.deltaScore).toBeNull();
  });
});

describe('busca (§3.4)', () => {
  it('ignora acento e caixa', () => {
    expect(normalizar('Querência')).toBe('querencia');
    const vale = CARTEIRA[0];
    expect(atendeABusca(vale, 'querencia')).toBe(true);
    expect(atendeABusca(vale, 'QUERÊNCIA')).toBe(true);
  });

  it('casa documento com e sem máscara', () => {
    const vale = CARTEIRA[0];
    expect(somenteDigitos('12.345.678/0001-90')).toBe('12345678000190');
    expect(atendeABusca(vale, '12345678')).toBe(true);
    expect(atendeABusca(vale, '12.345.678')).toBe(true);
  });

  it('casa município e razão social, e recusa o que não existe', () => {
    expect(atendeABusca(CARTEIRA[1], 'luis eduardo')).toBe(true);
    expect(atendeABusca(CARTEIRA[1], 'serrinha')).toBe(false);
  });
});

describe('filtros (§3.3)', () => {
  const limiar = limiarAltaExposicao(CARTEIRA);

  it('quartil superior de exposição inclui apenas o topo da carteira', () => {
    expect(limiar).toBe(14_200_000);
    expect(atendeAoFiltro(CARTEIRA[2], 'alta-exposicao', limiar)).toBe(true);
    expect(atendeAoFiltro(CARTEIRA[3], 'alta-exposicao', limiar)).toBe(false);
  });

  it('deterioração usa o limiar de −25 pontos em 90 dias', () => {
    expect(LIMIAR_DETERIORACAO).toBe(-25);
    expect(atendeAoFiltro(CARTEIRA[0], 'deterioracao', limiar)).toBe(true);
    expect(atendeAoFiltro(CARTEIRA[1], 'deterioracao', limiar)).toBe(false);
  });

  it('conta todos os nove chips, inclusive os de contagem zero', () => {
    const contagens = contarFiltros(CARTEIRA, limiar);
    expect(contagens.todos).toBe(4);
    expect(contagens['rating-d']).toBe(2);
    expect(contagens['rating-b']).toBe(0);
    expect(contagens.veto).toBe(1);
    expect(contagens['com-alerta']).toBe(3);
  });
});

describe('ordenação (§3.5)', () => {
  it('score crescente coloca o pior cliente no topo', () => {
    expect(ordenarLinhas(CARTEIRA, 'score', 'asc').map((l) => l.id)).toEqual([
      'cerrado-graos',
      'vale-araguaia',
      'serra-azul',
      'campo-limpo',
    ]);
  });

  it('exposição decrescente coloca o maior dinheiro no topo', () => {
    expect(ordenarLinhas(CARTEIRA, 'exposicao', 'desc')[0].id).toBe('cerrado-graos');
  });

  it('variação crescente coloca a maior queda no topo', () => {
    expect(ordenarLinhas(CARTEIRA, 'variacao', 'asc')[0].id).toBe('vale-araguaia');
  });

  it('mantém linhas sem valor no fim, em qualquer direção', () => {
    const comNulo = [
      ...CARTEIRA,
      paraLinha(
        avaliado({
          id: 'sem-historico',
          razaoSocial: 'Sem Histórico Ltda',
          documento: '00.111.222/0001-33',
          municipio: 'Sinop',
          uf: 'MT',
          exposicao: 1_000,
          score: 700,
          rating: 'B',
          pd12m: 0.05,
          delta: null,
        }),
      ),
    ];
    expect(ordenarLinhas(comNulo, 'variacao', 'asc').at(-1)?.id).toBe('sem-historico');
    expect(ordenarLinhas(comNulo, 'variacao', 'desc').at(-1)?.id).toBe('sem-historico');
  });
});

describe('aplicarCriterios', () => {
  const limiar = limiarAltaExposicao(CARTEIRA);

  it('combina filtro e busca por E lógico', () => {
    const resultado = aplicarCriterios(
      CARTEIRA,
      { filtro: 'rating-d', busca: 'cerrado', cultura: null, uf: null, ordem: 'score', direcao: 'asc' },
      limiar,
    );
    expect(resultado.map((l) => l.id)).toEqual(['cerrado-graos']);
  });

  it('devolve vazio quando a busca não cabe no filtro — o estado vazio de §3.7', () => {
    const resultado = aplicarCriterios(
      CARTEIRA,
      { filtro: 'rating-a', busca: 'cerrado', cultura: null, uf: null, ordem: 'score', direcao: 'asc' },
      limiar,
    );
    expect(resultado).toHaveLength(0);
  });

  it('aplica os recortes de drill-down da carteira (cultura e UF)', () => {
    const porCultura = aplicarCriterios(
      CARTEIRA,
      { filtro: 'todos', busca: '', cultura: 'Soja', uf: null, ordem: 'score', direcao: 'asc' },
      limiar,
    );
    expect(porCultura.map((l) => l.id)).toEqual(['cerrado-graos', 'vale-araguaia']);

    const porUf = aplicarCriterios(
      CARTEIRA,
      { filtro: 'todos', busca: '', cultura: null, uf: 'mt', ordem: 'score', direcao: 'asc' },
      limiar,
    );
    expect(porUf.map((l) => l.id)).toEqual(['vale-araguaia']);
  });
});
