import { describe, expect, it } from 'vitest';

import type { RegistroAuditoria } from '@/types';

import {
  clientesDaTrilha,
  estatisticasDaTrilha,
  filtrarTrilha,
  fraseDeDivergencia,
  justificativaCurta,
  resumoDaDivergencia,
  unirTrilha,
  type FiltroAuditoria,
} from './trilha';

const REFERENCIA = '2026-09-12T10:00:00-03:00';

function registro(
  id: string,
  dataHora: string,
  divergiu: boolean,
  extra: Partial<RegistroAuditoria> = {},
): RegistroAuditoria {
  return {
    id,
    clienteId: extra.clienteId ?? `cliente-${id}`,
    clienteNome: extra.clienteNome ?? `Cliente ${id}`,
    analista: 'Marina Rezende',
    dataHora,
    scoreNoMomento: 604,
    ratingNoMomento: 'C',
    recomendacaoGerada: 'SUSPENDER_NOVA_EXPOSICAO_A_PRAZO',
    decisaoAnalista: divergiu ? 'APROVAR_COM_RESTRICOES' : 'SUSPENDER',
    justificativa: 'Garantia extraconcursal reforçada em CPR registrada, com prazo de 30 dias.',
    divergiuDaRecomendacao: divergiu,
    ...extra,
  };
}

const TRILHA = [
  registro('1', '2026-09-11T14:32:00-03:00', true),
  registro('2', '2026-09-05T09:10:00-03:00', false),
  registro('3', '2026-06-30T16:00:00-03:00', true, {
    clienteId: 'cliente-1',
    clienteNome: 'Cliente 1',
  }),
];

describe('união da trilha', () => {
  it('junta dataset e sessão, ordena por data-hora decrescente e não duplica id', () => {
    const daSessao = [registro('4', '2026-09-12T08:00:00-03:00', false)];
    const unida = unirTrilha(TRILHA, daSessao);
    expect(unida.map((item) => item.id)).toEqual(['4', '1', '2', '3']);
  });

  it('a versão da sessão vence quando o mesmo id aparece dos dois lados', () => {
    const daSessao = [registro('1', '2026-09-11T14:32:00-03:00', false)];
    const unida = unirTrilha(TRILHA, daSessao);
    expect(unida).toHaveLength(3);
    expect(unida.find((item) => item.id === '1')?.divergiuDaRecomendacao).toBe(false);
  });
});

describe('filtros', () => {
  const filtrar = (filtros: FiltroAuditoria[], clienteId: string | null = null) =>
    filtrarTrilha(TRILHA, { filtros: new Set(filtros), clienteId, referencia: REFERENCIA });

  it('sem filtro, devolve tudo', () => {
    expect(filtrar([])).toHaveLength(3);
  });

  it('isola as decisões divergentes', () => {
    expect(filtrar(['divergentes']).map((item) => item.id)).toEqual(['1', '3']);
  });

  it('corta a janela de 30 dias por dia de calendário', () => {
    expect(filtrar(['ultimos_30d']).map((item) => item.id)).toEqual(['1', '2']);
  });

  it('filtra por cliente', () => {
    // Os registros 1 e 3 são do mesmo cliente — a trilha de um cliente pode ter várias decisões.
    expect(filtrar([], 'cliente-1').map((item) => item.id)).toEqual(['1', '3']);
    expect(filtrar([], 'cliente-2').map((item) => item.id)).toEqual(['2']);
  });
});

describe('divergência', () => {
  it('conta divergências e devolve a fração para o formatador', () => {
    const estatisticas = estatisticasDaTrilha(TRILHA);
    expect(estatisticas).toEqual({ total: 3, divergentes: 2, fracao: 2 / 3 });
    expect(estatisticasDaTrilha([])).toEqual({ total: 0, divergentes: 0, fracao: 0 });
  });

  it('escreve a frase do cabeçalho com concordância correta', () => {
    expect(fraseDeDivergencia({ total: 14, divergentes: 3, fracao: 3 / 14 }, '21%')).toBe(
      '3 de 14 decisões divergiram da recomendação (21%).',
    );
    expect(fraseDeDivergencia({ total: 1, divergentes: 1, fracao: 1 }, '100%')).toBe(
      '1 de 1 decisão divergiu da recomendação (100%).',
    );
    expect(fraseDeDivergencia({ total: 0, divergentes: 0, fracao: 0 }, '0%')).toContain(
      'Nenhuma decisão registrada',
    );
  });

  it('monta a linha "recomendado → decidido" exigida por §8.2', () => {
    expect(resumoDaDivergencia(TRILHA[0])).toBe(
      'Recomendado: SUSPENDER NOVA EXPOSIÇÃO A PRAZO  →  Decidido: APROVAR COM RESTRIÇÕES',
    );
  });
});

describe('apoio da tabela', () => {
  it('trunca a justificativa em 80 caracteres com reticências', () => {
    const longa = 'a'.repeat(120);
    expect(justificativaCurta(longa)).toHaveLength(81);
    expect(justificativaCurta('curta')).toBe('curta');
  });

  it('lista os clientes da trilha sem repetição e em ordem alfabética', () => {
    expect(clientesDaTrilha(TRILHA).map((cliente) => cliente.id)).toEqual([
      'cliente-1',
      'cliente-2',
    ]);
  });
});
