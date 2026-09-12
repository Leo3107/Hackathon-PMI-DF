import { describe, expect, it } from 'vitest';

import type { Alerta, Severidade } from '@/types';

import {
  ROTULO_SEVERIDADE,
  agrupar,
  aplicarLeitura,
  bucketDaData,
  contarNaoLidos,
  contarPorSeveridade,
  filtrarAlertas,
  idadeEmDias,
  temCriticoNaoLido,
  textoDoVazio,
  type FiltroAlerta,
} from './agrupamento';

const REFERENCIA = '2026-09-12';

function alerta(
  id: string,
  data: string,
  severidade: Severidade,
  extra: Partial<Alerta> = {},
): Alerta {
  return {
    id,
    clienteId: `cliente-${id}`,
    clienteNome: `Cliente ${id}`,
    data,
    severidade,
    titulo: `Alerta ${id}`,
    descricao: 'Descrição do alerta.',
    impacto: 'R$ 1.000.000 de exposição afetada.',
    acaoRecomendada: 'Suspender novo fornecimento a prazo.',
    lido: false,
    ...extra,
  };
}

const ALERTAS: Alerta[] = [
  alerta('a', '2026-09-12', 'CRITICA'),
  alerta('b', '2026-09-11', 'ALTA'),
  alerta('c', '2026-09-08', 'MEDIA'),
  alerta('d', '2026-08-25', 'BAIXA'),
  alerta('e', '2026-05-02', 'ALTA'),
];

describe('buckets de data', () => {
  it('nomeia os buckets de §7.1 a partir da referência', () => {
    expect(bucketDaData('2026-09-12', REFERENCIA)).toBe('hoje');
    expect(bucketDaData('2026-09-11', REFERENCIA)).toBe('ontem');
    expect(bucketDaData('2026-09-08', REFERENCIA)).toBe('semana');
    expect(bucketDaData('2026-08-25', REFERENCIA)).toBe('mes');
    expect(bucketDaData('2026-05-02', REFERENCIA)).toBe('anteriores');
  });

  it('aceita datetime ISO e mede dias inteiros de calendário', () => {
    expect(idadeEmDias('2026-09-10T23:59:00-03:00', REFERENCIA)).toBe(2);
    expect(idadeEmDias('não é data', REFERENCIA)).toBeNull();
  });
});

describe('leitura e contagem', () => {
  it('projeta o estado de leitura da sessão sobre a lista do motor', () => {
    const comLeitura = aplicarLeitura(ALERTAS, ['a', 'c']);
    expect(comLeitura.find((item) => item.id === 'a')?.lido).toBe(true);
    expect(comLeitura.find((item) => item.id === 'b')?.lido).toBe(false);
    expect(contarNaoLidos(comLeitura)).toBe(3);
    // Não muta a lista original — ela é a resposta do motor.
    expect(ALERTAS.every((item) => item.lido === false)).toBe(true);
  });

  it('conta por severidade nas quatro faixas', () => {
    expect(contarPorSeveridade(ALERTAS)).toEqual({ CRITICA: 1, ALTA: 2, MEDIA: 1, BAIXA: 1 });
  });

  it('detecta crítico não lido, que é o que exige confirmação em modal', () => {
    expect(temCriticoNaoLido(ALERTAS)).toBe(true);
    expect(temCriticoNaoLido(aplicarLeitura(ALERTAS, ['a']))).toBe(false);
  });

  it('usa os rótulos da tela, não os códigos do contrato', () => {
    expect(ROTULO_SEVERIDADE.CRITICA).toBe('Crítico');
    expect(ROTULO_SEVERIDADE.BAIXA).toBe('Informativo');
  });
});

describe('filtros', () => {
  const criterios = (
    severidades: Severidade[],
    filtros: FiltroAlerta[],
    lista = ALERTAS,
  ) => filtrarAlertas(lista, {
    severidades: new Set(severidades),
    filtros: new Set(filtros),
    referencia: REFERENCIA,
  });

  it('sem filtro, devolve tudo', () => {
    expect(criterios([], [])).toHaveLength(5);
  });

  it('combina severidade e janela temporal por E', () => {
    expect(criterios(['ALTA'], ['ultimos_7d']).map((item) => item.id)).toEqual(['b']);
    expect(criterios(['ALTA'], []).map((item) => item.id)).toEqual(['b', 'e']);
    expect(criterios([], ['ultimos_30d']).map((item) => item.id)).toEqual(['a', 'b', 'c', 'd']);
  });

  it('"não lidos" e "com ação pendente" respeitam a leitura da sessão', () => {
    const lidos = aplicarLeitura(ALERTAS, ['a', 'b']);
    expect(criterios([], ['nao_lidos'], lidos).map((item) => item.id)).toEqual(['c', 'd', 'e']);
    expect(criterios([], ['acao_pendente'], lidos)).toHaveLength(3);
  });
});

describe('agrupamento', () => {
  it('agrupa por data nos buckets nomeados, mais recente primeiro', () => {
    const grupos = agrupar(ALERTAS, 'data', REFERENCIA);
    expect(grupos.map((grupo) => grupo.titulo)).toEqual([
      'Hoje',
      'Ontem',
      'Esta semana',
      'Últimos 30 dias',
      'Anteriores',
    ]);
    expect(grupos[0].alertas.map((item) => item.id)).toEqual(['a']);
  });

  it('agrupa por severidade na ordem de gravidade e omite faixas vazias', () => {
    const grupos = agrupar(ALERTAS.slice(0, 2), 'severidade', REFERENCIA);
    expect(grupos.map((grupo) => grupo.titulo)).toEqual(['Crítico', 'Alto']);
  });

  it('agrupa por cliente em ordem alfabética', () => {
    const grupos = agrupar(ALERTAS, 'cliente', REFERENCIA);
    expect(grupos).toHaveLength(5);
    expect(grupos[0].titulo).toBe('Cliente a');
  });
});

describe('estado vazio', () => {
  const semFiltro = { severidades: new Set<Severidade>(), filtros: new Set<FiltroAlerta>(), referencia: REFERENCIA };

  it('diz por que está vazio quando a carteira não tem alerta', () => {
    const texto = textoDoVazio(0, semFiltro, false);
    expect(texto.titulo).toBe('Nenhum alerta na carteira');
    expect(texto.acao).toBe('nenhuma');
  });

  it('reconhece "você está em dia" quando tudo foi lido e o filtro é não lidos', () => {
    const texto = textoDoVazio(5, { ...semFiltro, filtros: new Set<FiltroAlerta>(['nao_lidos']) }, true);
    expect(texto.titulo).toBe('Você está em dia');
    expect(texto.acao).toBe('ver_todos');
  });

  it('nomeia os filtros ativos quando a combinação não devolve nada', () => {
    const texto = textoDoVazio(
      5,
      {
        severidades: new Set<Severidade>(['CRITICA']),
        filtros: new Set<FiltroAlerta>(['ultimos_7d']),
        referencia: REFERENCIA,
      },
      false,
    );
    expect(texto.acao).toBe('limpar');
    expect(texto.descricao).toContain('crítico');
    expect(texto.descricao).toContain('últimos 7 dias');
  });
});
