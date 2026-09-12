import { describe, expect, it } from 'vitest';

import {
  MENOS,
  NBSP,
  formatarData,
  formatarDataHora,
  formatarDataRelativa,
  formatarDelta,
  formatarDias,
  formatarDocumento,
  formatarLista,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarPercentual,
  formatarProbabilidadeRJ,
  formatarScore,
  formatarTokens,
} from './format';

/**
 * Casos literais da tabela §11.1 de `specs/05-design-system.md`.
 *
 * Onde a tabela mostra "R$ 1.234.567,00", o separador entre o símbolo e o número
 * é o NBSP exigido pelo §11 ("garante 'R$' + NBSP"); nos literais abaixo ele
 * aparece como `${NBSP}` para não virar um espaço comum invisível no diff.
 * O sinal negativo é U+2212 (`MENOS`), nunca o hífen.
 */

describe('formatarMoeda', () => {
  it('formata valor inteiro com duas casas', () => {
    expect(formatarMoeda(1234567)).toBe(`R$${NBSP}1.234.567,00`);
  });

  it('usa U+2212 antes do símbolo em valores negativos', () => {
    expect(formatarMoeda(-1234.5)).toBe(`${MENOS}R$${NBSP}1.234,50`);
  });

  it('arredonda meio para cima (halfExpand)', () => {
    expect(formatarMoeda(0.125)).toBe(`R$${NBSP}0,13`);
  });

  it('aceita zero casas para tabelas de grandes valores', () => {
    expect(formatarMoeda(5_000_000, { casas: 0 })).toBe(`R$${NBSP}5.000.000`);
  });
});

describe('formatarMoedaCompacta', () => {
  it('abrevia milhões com uma casa', () => {
    expect(formatarMoedaCompacta(1_480_000)).toBe(`R$${NBSP}1,5 mi`);
  });

  it('promove milhar para milhão quando o arredondamento estoura', () => {
    expect(formatarMoedaCompacta(999_600)).toBe(`R$${NBSP}1,0 mi`);
  });

  it('abrevia milhares sem casas decimais', () => {
    expect(formatarMoedaCompacta(850_000)).toBe(`R$${NBSP}850 mil`);
  });

  it('mantém a escala de milhar quando o arredondamento não estoura', () => {
    expect(formatarMoedaCompacta(999_499)).toBe(`R$${NBSP}999 mil`);
  });

  it('mantém a casa decimal mesmo quando é zero', () => {
    expect(formatarMoedaCompacta(2_000_000)).toBe(`R$${NBSP}2,0 mi`);
  });

  it('cai para moeda cheia abaixo de mil', () => {
    expect(formatarMoedaCompacta(350)).toBe(`R$${NBSP}350,00`);
  });

  it('preserva o sinal tipográfico em negativos', () => {
    expect(formatarMoedaCompacta(-3_200_000)).toBe(`${MENOS}R$${NBSP}3,2 mi`);
  });

  it('suprime o prefixo quando pedido (eixos de gráfico)', () => {
    expect(formatarMoedaCompacta(1_250_000, { prefixo: false })).toBe('1,3 mi');
  });
});

describe('formatarPercentual', () => {
  it('formata fração com uma casa', () => {
    expect(formatarPercentual(0.1713, 1)).toBe('17,1%');
  });

  it('formata fração sem casas', () => {
    expect(formatarPercentual(0.1713, 0)).toBe('17%');
  });

  it('aceita frações acima de 1 (cobertura 132%)', () => {
    expect(formatarPercentual(1.32, 0)).toBe('132%');
  });

  it('usa "<" para valores abaixo da menor casa representável', () => {
    expect(formatarPercentual(0.0003, 1)).toBe('<0,1%');
  });

  it('usa U+2212 em variações negativas', () => {
    expect(formatarPercentual(-0.045, 1, { sinal: true })).toBe(`${MENOS}4,5%`);
  });

  it('usa "+" explícito em variações positivas', () => {
    expect(formatarPercentual(0.045, 1, { sinal: true })).toBe('+4,5%');
  });
});

describe('formatarScore', () => {
  it('arredonda para inteiro', () => {
    expect(formatarScore(603.5)).toBe('604');
  });

  it('faz clamp no teto 1000', () => {
    expect(formatarScore(1200)).toBe('1000');
  });

  it('não usa separador de milhar', () => {
    expect(formatarScore(1000)).toBe('1000');
  });
});

describe('formatarDelta', () => {
  it('usa U+2212 em quedas', () => {
    expect(formatarDelta(-108)).toBe(`${MENOS}108`);
  });

  it('usa "+" explícito e sufixo', () => {
    expect(formatarDelta(12, 'pts')).toBe('+12 pts');
  });

  it('não põe sinal no zero', () => {
    expect(formatarDelta(0)).toBe('0');
  });
});

describe('formatarNumero', () => {
  it('agrupa milhares', () => {
    expect(formatarNumero(18342)).toBe('18.342');
  });

  it('formata decimais com vírgula', () => {
    expect(formatarNumero(0.4231, 2)).toBe('0,42');
  });
});

describe('formatarTokens', () => {
  it('abrevia milhares com uma casa', () => {
    expect(formatarTokens(18342)).toBe('18,3k');
  });

  it('abrevia milhões com duas casas', () => {
    expect(formatarTokens(1_250_000)).toBe('1,25M');
  });

  it('mostra o inteiro abaixo de mil', () => {
    expect(formatarTokens(842)).toBe('842');
  });
});

describe('formatarData', () => {
  it('formato curto é o padrão', () => {
    expect(formatarData('2026-09-12')).toBe('12/09/2026');
  });

  it('formato médio usa mês abreviado minúsculo sem ponto', () => {
    expect(formatarData('2026-09-12', 'media')).toBe('12 set 2026');
  });

  it('formato longo é por extenso', () => {
    expect(formatarData('2026-09-12', 'longa')).toBe('12 de setembro de 2026');
  });

  it('formato de mês usa ano de dois dígitos', () => {
    expect(formatarData('2026-09-12', 'mes')).toBe('set/26');
  });

  it('formato mesAno é por extenso', () => {
    expect(formatarData('2026-09-12', 'mesAno')).toBe('setembro de 2026');
  });
});

describe('formatarDataHora', () => {
  it('usa 24h sem segundos, no fuso de Brasília', () => {
    expect(formatarDataHora('2026-09-12T14:32:00-03:00')).toBe('12/09/2026 14:32');
  });
});

describe('formatarDataRelativa', () => {
  it('mesmo dia', () => {
    expect(formatarDataRelativa('2026-09-12', '2026-09-12')).toBe('hoje');
  });

  it('véspera', () => {
    expect(formatarDataRelativa('2026-09-11', '2026-09-12')).toBe('ontem');
  });

  it('dias no passado', () => {
    expect(formatarDataRelativa('2026-08-31', '2026-09-12')).toBe('há 12 dias');
  });

  it('meses no passado', () => {
    expect(formatarDataRelativa('2026-06-10', '2026-09-12')).toBe('há 3 meses');
  });

  it('dias no futuro', () => {
    expect(formatarDataRelativa('2026-09-24', '2026-09-12')).toBe('em 12 dias');
  });

  it('anos no passado', () => {
    expect(formatarDataRelativa('2024-09-12', '2026-09-12')).toBe('há 2 anos');
  });

  it('nunca usa o relógio do sistema: a referência é quem manda', () => {
    const iso = '2026-09-12';
    expect(formatarDataRelativa(iso, '2026-09-13')).toBe('ontem');
    expect(formatarDataRelativa(iso, '2026-09-11')).toBe('amanhã');
  });
});

describe('formatarDias', () => {
  it('singular', () => {
    expect(formatarDias(1)).toBe('1 dia');
  });

  it('variante curta para eixos', () => {
    expect(formatarDias(90, true)).toBe('90 d');
  });

  it('plural no zero', () => {
    expect(formatarDias(0)).toBe('0 dias');
  });
});

describe('formatarDocumento', () => {
  it('CNPJ é dado público e nunca é mascarado', () => {
    expect(formatarDocumento('12345678000190')).toBe('12.345.678/0001-90');
  });

  it('CPF é mascarado por padrão', () => {
    expect(formatarDocumento('12345678909')).toBe('•••.456.789-••');
  });

  it('CPF sem máscara quando pedido explicitamente', () => {
    expect(formatarDocumento('123.456.789-09', { mascarar: false })).toBe('123.456.789-09');
  });

  it('entrada inválida volta inalterada', () => {
    expect(formatarDocumento('abc')).toBe('abc');
  });
});

describe('formatarLista', () => {
  it('usa "e" antes do último item', () => {
    expect(formatarLista(['Soja', 'Milho safrinha', 'Algodão'])).toBe(
      'Soja, Milho safrinha e Algodão',
    );
  });
});

describe('formatarProbabilidadeRJ', () => {
  it('evento consumado não vira probabilidade', () => {
    expect(formatarProbabilidadeRJ({ probabilidade12m: 1, eventoJaOcorrido: true })).toBe(
      'Evento ocorrido',
    );
  });

  it('probabilidade normal usa uma casa', () => {
    expect(formatarProbabilidadeRJ({ probabilidade12m: 0.183, eventoJaOcorrido: false })).toBe(
      '18,3%',
    );
  });
});
