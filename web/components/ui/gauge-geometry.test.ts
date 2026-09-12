import { describe, expect, it } from 'vitest';

import {
  GAUGE,
  ancoraTexto,
  anguloDoScore,
  comprimentoArco,
  dashOffset,
  pathArco,
  pontoNoArco,
} from './gauge-geometry';

/** Testes obrigatórios da spec §7.8. */
describe('anguloDoScore', () => {
  it('score 0 fica em −120°', () => {
    expect(anguloDoScore(0)).toBe(-120);
  });

  it('score 500 fica no topo', () => {
    expect(anguloDoScore(500)).toBe(0);
  });

  it('score 1000 fica em +120°', () => {
    expect(anguloDoScore(1000)).toBe(120);
  });

  it('score 750 (piso do rating A) fica em +60°', () => {
    expect(anguloDoScore(750)).toBe(60);
  });

  it('faz clamp fora de 0..1000', () => {
    expect(anguloDoScore(-200)).toBe(-120);
    expect(anguloDoScore(1500)).toBe(120);
  });
});

describe('comprimentoArco', () => {
  it('vale 335,10 para R = 80', () => {
    expect(comprimentoArco()).toBeCloseTo(335.1, 1);
    expect(Math.abs(comprimentoArco() - 335.103)).toBeLessThan(0.01);
  });
});

describe('pontoNoArco', () => {
  it('ângulo 0 aponta para o topo do arco', () => {
    const ponto = pontoNoArco(0);
    expect(ponto.x).toBeCloseTo(100, 10);
    expect(ponto.y).toBeCloseTo(24, 10);
  });

  it('usa o centro e o raio declarados em GAUGE', () => {
    const ponto = pontoNoArco(90, GAUGE.r);
    expect(ponto.x).toBeCloseTo(GAUGE.cx + GAUGE.r, 10);
    expect(ponto.y).toBeCloseTo(GAUGE.cy, 10);
  });
});

describe('dashOffset', () => {
  it('score 0 esconde o arco inteiro', () => {
    expect(dashOffset(0)).toBeCloseTo(comprimentoArco(), 10);
  });

  it('score 1000 preenche o arco inteiro', () => {
    expect(dashOffset(1000)).toBeCloseTo(0, 10);
  });

  it('score 500 preenche metade', () => {
    expect(dashOffset(500)).toBeCloseTo(comprimentoArco() / 2, 10);
  });
});

describe('pathArco', () => {
  it('começa no ponto do score inicial e termina no do final', () => {
    // −120° e +120°: y = 104 − 80·cos(±120°) = 144 nas duas pontas.
    expect(pathArco(0, 1000)).toBe('M 30.718 144 A 80 80 0 1 1 169.282 144');
  });

  it('arco menor que 180° não usa large-arc-flag', () => {
    expect(pathArco(500, 750)).toContain('0 0 1');
  });
});

describe('ancoraTexto', () => {
  it('quadrante esquerdo alinha à direita', () => {
    expect(ancoraTexto(anguloDoScore(400))).toBe('end');
  });

  it('topo alinha ao centro', () => {
    expect(ancoraTexto(anguloDoScore(500))).toBe('middle');
  });

  it('quadrante direito alinha à esquerda', () => {
    expect(ancoraTexto(anguloDoScore(750))).toBe('start');
  });
});
