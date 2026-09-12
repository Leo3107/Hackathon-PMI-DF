/**
 * Geometria do `ScoreGauge` (spec §7.1 e §7.8). Funções puras, testáveis.
 *
 * Varredura de 240°: `θ(score) = −120° + 240° × (score / 1000)`, medido a partir
 * das 12 horas, positivo no sentido horário. Score 0 → −120° ("8h"),
 * 500 → 0° (topo), 1000 → +120° ("4h"). A abertura de 120° na base acomoda o
 * `TrendIndicator` e os badges.
 */
export const GAUGE = {
  cx: 100,
  cy: 104,
  r: 80,
  sweep: 240,
  start: -120,
  strokeWidth: 12,
} as const;

export const SCORE_MINIMO = 0;
export const SCORE_MAXIMO = 1000;

const GRAUS_PARA_RADIANOS = Math.PI / 180;

function limitarScore(score: number): number {
  if (!Number.isFinite(score)) return SCORE_MINIMO;
  return Math.min(SCORE_MAXIMO, Math.max(SCORE_MINIMO, score));
}

/** Ângulo em graus do score, a partir das 12 horas. Clamp 0..1000. */
export function anguloDoScore(score: number): number {
  return GAUGE.start + GAUGE.sweep * (limitarScore(score) / SCORE_MAXIMO);
}

/** Ponto no arco: `x = cx + R·sin(θ)`, `y = cy − R·cos(θ)`. */
export function pontoNoArco(anguloGraus: number, raio: number = GAUGE.r): { x: number; y: number } {
  const radianos = anguloGraus * GRAUS_PARA_RADIANOS;
  return {
    x: GAUGE.cx + raio * Math.sin(radianos),
    y: GAUGE.cy - raio * Math.cos(radianos),
  };
}

/** Comprimento total do arco de 240°: `2π·R·(240/360)` = 335,10 para R = 80. */
export function comprimentoArco(raio: number = GAUGE.r): number {
  return 2 * Math.PI * raio * (GAUGE.sweep / 360);
}

/**
 * `stroke-dashoffset` do preenchimento: `L × (1 − score/1000)`.
 * Permite animar o arco por uma única propriedade (spec §7.6).
 */
export function dashOffset(score: number, raio: number = GAUGE.r): number {
  return comprimentoArco(raio) * (1 - limitarScore(score) / SCORE_MAXIMO);
}

/** Caminho SVG `M … A …` entre dois scores, no raio indicado. */
export function pathArco(
  scoreInicio: number,
  scoreFim: number,
  raio: number = GAUGE.r,
): string {
  const anguloInicio = anguloDoScore(scoreInicio);
  const anguloFim = anguloDoScore(scoreFim);
  const inicio = pontoNoArco(anguloInicio, raio);
  const fim = pontoNoArco(anguloFim, raio);
  const delta = anguloFim - anguloInicio;
  const arcoGrande = Math.abs(delta) > 180 ? 1 : 0;
  // y cresce para baixo: ângulo crescente é sentido horário na tela → sweep 1.
  const sentido = delta >= 0 ? 1 : 0;
  return [
    `M ${arredondar(inicio.x)} ${arredondar(inicio.y)}`,
    `A ${arredondar(raio)} ${arredondar(raio)} 0 ${arcoGrande} ${sentido} ${arredondar(fim.x)} ${arredondar(fim.y)}`,
  ].join(' ');
}

/**
 * Âncora do rótulo de tick conforme o quadrante:
 * `end` para θ < 0, `middle` para |θ| < 8°, `start` para θ > 0.
 */
export function ancoraTexto(anguloGraus: number): 'start' | 'middle' | 'end' {
  if (Math.abs(anguloGraus) < 8) return 'middle';
  return anguloGraus < 0 ? 'end' : 'start';
}

/** Arredonda a três casas para manter o atributo `d` legível e estável. */
function arredondar(valor: number): number {
  return Math.round(valor * 1000) / 1000;
}
