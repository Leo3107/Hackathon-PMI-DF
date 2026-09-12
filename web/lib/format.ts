/**
 * Formatadores pt-BR do Lastro — `specs/05-design-system.md` §11.
 *
 * Funções puras, sem `Date.now()`. Datas relativas recebem a referência
 * explicitamente (coerente com o motor determinístico). `Intl` com locale
 * `pt-BR`. Arredondamento **sempre `halfExpand`** (meio para cima comercial:
 * 0,125 → 0,13; −0,125 → −0,13). Sinal negativo é **U+2212**.
 */

/** Sinal de menos tipográfico (U+2212). Nunca o hífen U+002D. */
export const MENOS = '−';

/** Travessão de valor ausente (U+2014). */
export const TRACO_LONGO = '—';

/** Espaço inquebrável (U+00A0) — separa "R$" do número. */
export const NBSP = ' ';

const LOCALE = 'pt-BR';
const FUSO = 'America/Sao_Paulo';

const SO_DATA = /^\d{4}-\d{2}-\d{2}$/;

function ehNumeroValido(valor: unknown): valor is number {
  return typeof valor === 'number' && Number.isFinite(valor);
}

/** Troca o hífen-menos do Intl pelo sinal tipográfico U+2212. */
function comMenosTipografico(texto: string): string {
  return texto.replace(/-/g, MENOS);
}

/** Arredondamento half-expand (afasta-se do zero no empate), para uso fora do Intl. */
function arredondarHalfExpand(valor: number, casas = 0): number {
  const fator = 10 ** casas;
  const sinal = valor < 0 ? -1 : 1;
  return (sinal * Math.round(Math.abs(valor) * fator)) / fator;
}

/* ------------------------------------------------------------------ */
/* Moeda                                                               */
/* ------------------------------------------------------------------ */

export interface OpcoesMoeda {
  /** Casas decimais. Padrão 2; use 0 em tabelas de grandes valores. */
  casas?: 0 | 2;
  /** Força o "+" explícito em valores positivos. */
  sinal?: boolean;
  /** Inclui o prefixo "R$". Padrão true. */
  prefixo?: boolean;
}

/**
 * `R$ 1.234.567,00` · `−R$ 1.234,00`.
 * Valor não numérico → `—` (U+2014).
 */
export function formatarMoeda(valor: number, opts: OpcoesMoeda = {}): string {
  if (!ehNumeroValido(valor)) return TRACO_LONGO;
  const { casas = 2, sinal = false, prefixo = true } = opts;

  const corpo = new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
    roundingMode: 'halfExpand',
  }).format(Math.abs(valor));

  return montarMoeda(valor, corpo, { sinal, prefixo });
}

function montarMoeda(
  valor: number,
  corpoAbsoluto: string,
  opts: { sinal: boolean; prefixo: boolean },
): string {
  const negativo = valor < 0;
  const prefixoSinal = negativo ? MENOS : opts.sinal && valor > 0 ? '+' : '';
  const moeda = opts.prefixo ? `R$${NBSP}` : '';
  return `${prefixoSinal}${moeda}${corpoAbsoluto}`;
}

export interface OpcoesMoedaCompacta {
  prefixo?: boolean;
  sinal?: boolean;
}

/**
 * Abreviada. Regras aplicadas ao |valor| **já arredondado na escala-alvo**,
 * para evitar "R$ 1.000 mil":
 *
 * - `|v| ≥ 1e9` → `R$ 1,2 bi` (1 casa, sempre — inclusive ",0")
 * - `|v| ≥ 1e6` → `R$ 1,2 mi` (1 casa, sempre)
 * - `|v| ≥ 1e3` → `R$ 850 mil` (0 casas)
 * - `|v| < 1e3` → `formatarMoeda(valor, { casas: 2 })`
 *
 * Promoção: `round(v/1e3) ≥ 1000` → trata como mi; `round(v/1e6, 1) ≥ 1000` → bi.
 */
export function formatarMoedaCompacta(valor: number, opts: OpcoesMoedaCompacta = {}): string {
  if (!ehNumeroValido(valor)) return TRACO_LONGO;
  const { prefixo = true, sinal = false } = opts;

  const absoluto = Math.abs(valor);
  if (absoluto < 1e3) {
    return formatarMoeda(valor, { casas: 2, prefixo, sinal });
  }

  const MIL = 1_000;
  const MILHAO = 1_000_000;
  const BILHAO = 1_000_000_000;

  let escala: number;
  let casas: 0 | 1;

  if (absoluto >= BILHAO) {
    escala = BILHAO;
    casas = 1;
  } else if (absoluto >= MILHAO) {
    escala = MILHAO;
    casas = 1;
  } else {
    escala = MIL;
    casas = 0;
  }

  // Promoção de escala quando o arredondamento estoura o milhar da escala atual.
  if (escala === MIL && arredondarHalfExpand(absoluto / MIL, 0) >= 1000) {
    escala = MILHAO;
    casas = 1;
  }
  if (escala === MILHAO && arredondarHalfExpand(absoluto / MILHAO, 1) >= 1000) {
    escala = BILHAO;
    casas = 1;
  }

  const sufixo = escala === BILHAO ? 'bi' : escala === MILHAO ? 'mi' : 'mil';

  const corpo = new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
    roundingMode: 'halfExpand',
  }).format(absoluto / escala);

  return `${montarMoeda(valor, corpo, { sinal, prefixo })} ${sufixo}`;
}

/* ------------------------------------------------------------------ */
/* Percentual                                                          */
/* ------------------------------------------------------------------ */

export interface OpcoesPercentual {
  /** Força o "+" explícito em valores positivos (variações). */
  sinal?: boolean;
}

/**
 * Entrada é **fração** (0,1713 → `17,1%`). O chamador é obrigado a escolher as casas:
 * PD e risco de RJ → 1 · coberturas e utilização de limite → 0 · variação → 1 com sinal.
 * Sem espaço antes de `%`. Frações ≥ 1 permitidas (cobertura 132%).
 * Valores positivos abaixo da menor casa representável → `<0,1%`.
 */
export function formatarPercentual(
  fracao: number,
  casas: 0 | 1 | 2,
  opts: OpcoesPercentual = {},
): string {
  if (!ehNumeroValido(fracao)) return TRACO_LONGO;
  const { sinal = false } = opts;

  // Positivo, porém abaixo da menor casa representável: "<0,1%" em vez de "0,0%".
  const limiar = 0.5 / 10 ** (casas + 2);
  if (fracao > 0 && fracao < limiar) {
    const menorRepresentavel = new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: casas,
      maximumFractionDigits: casas,
    }).format(1 / 10 ** casas);
    return `<${menorRepresentavel}%`;
  }

  const corpo = new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
    roundingMode: 'halfExpand',
  }).format(Math.abs(fracao * 100));

  const prefixoSinal = fracao < 0 ? MENOS : sinal && fracao > 0 ? '+' : '';
  return `${prefixoSinal}${corpo}%`;
}

/* ------------------------------------------------------------------ */
/* Números do motor                                                    */
/* ------------------------------------------------------------------ */

/** Inteiro sem separador de milhar: `604` · `1000`. Clamp 0..1000. */
export function formatarScore(score: number): string {
  if (!ehNumeroValido(score)) return TRACO_LONGO;
  const arredondado = Math.round(score);
  const limitado = Math.min(1000, Math.max(0, arredondado));
  return String(limitado);
}

/** `+12` · `−108` · `0` (zero sem sinal). Sufixo opcional: `−108 pts`. */
export function formatarDelta(delta: number, sufixo: 'pts' | 'pp' | '' = ''): string {
  if (!ehNumeroValido(delta)) return TRACO_LONGO;
  const inteiro = arredondarHalfExpand(delta, 0);
  const corpo =
    inteiro === 0
      ? '0'
      : inteiro < 0
        ? `${MENOS}${formatarNumero(Math.abs(inteiro), 0)}`
        : `+${formatarNumero(inteiro, 0)}`;
  return sufixo ? `${corpo} ${sufixo}` : corpo;
}

/** Inteiro ou decimal genérico em pt-BR: `18.342` · `0,42`. */
export function formatarNumero(valor: number, casas: 0 | 1 | 2 = 0): string {
  if (!ehNumeroValido(valor)) return TRACO_LONGO;
  return comMenosTipografico(
    new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: casas,
      maximumFractionDigits: casas,
      roundingMode: 'halfExpand',
    }).format(valor),
  );
}

/** Contador de tokens: `18,3k` · `1,25M` · `842`. */
export function formatarTokens(n: number): string {
  if (!ehNumeroValido(n)) return TRACO_LONGO;
  const absoluto = Math.abs(n);
  if (absoluto >= 1e6) return `${formatarNumero(n / 1e6, 2)}M`;
  if (absoluto >= 1e3) return `${formatarNumero(n / 1e3, 1)}k`;
  return formatarNumero(n, 0);
}

/* ------------------------------------------------------------------ */
/* Datas                                                               */
/* ------------------------------------------------------------------ */

export type FormatoData = 'curta' | 'media' | 'longa' | 'mes' | 'mesAno';

interface InstanteISO {
  data: Date;
  fuso: string;
}

/**
 * Datas puras (`2026-09-12`) são calendário, não instante: interpretá-las em
 * America/Sao_Paulo a partir da meia-noite UTC retrocederia um dia. Por isso
 * elas são fixadas em UTC; apenas datetimes completos usam o fuso de Brasília.
 */
function interpretar(iso: string): InstanteISO | null {
  if (typeof iso !== 'string' || iso.length === 0) return null;
  if (SO_DATA.test(iso)) {
    const data = new Date(`${iso}T00:00:00Z`);
    return Number.isNaN(data.getTime()) ? null : { data, fuso: 'UTC' };
  }
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? null : { data, fuso: FUSO };
}

/** Mês abreviado pt-BR em minúsculas e sem ponto ("set"). */
function mesCurto(data: Date, fuso: string): string {
  const bruto = new Intl.DateTimeFormat(LOCALE, { month: 'short', timeZone: fuso }).format(data);
  return bruto.replace(/\./g, '').toLowerCase();
}

function campo(data: Date, fuso: string, opcoes: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(LOCALE, { ...opcoes, timeZone: fuso }).format(data);
}

/**
 * `curta` → `12/09/2026` · `media` → `12 set 2026` · `longa` → `12 de setembro de 2026`
 * · `mes` → `set/26` · `mesAno` → `setembro de 2026`.
 */
export function formatarData(iso: string, formato: FormatoData = 'curta'): string {
  const instante = interpretar(iso);
  if (!instante) return TRACO_LONGO;
  const { data, fuso } = instante;

  switch (formato) {
    case 'media': {
      const dia = campo(data, fuso, { day: '2-digit' });
      const ano = campo(data, fuso, { year: 'numeric' });
      return `${dia} ${mesCurto(data, fuso)} ${ano}`;
    }
    case 'longa': {
      const dia = campo(data, fuso, { day: 'numeric' });
      const mes = campo(data, fuso, { month: 'long' });
      const ano = campo(data, fuso, { year: 'numeric' });
      return `${dia} de ${mes} de ${ano}`;
    }
    case 'mes': {
      const ano = campo(data, fuso, { year: '2-digit' });
      return `${mesCurto(data, fuso)}/${ano}`;
    }
    case 'mesAno': {
      const mes = campo(data, fuso, { month: 'long' });
      const ano = campo(data, fuso, { year: 'numeric' });
      return `${mes} de ${ano}`;
    }
    case 'curta':
    default:
      return campo(data, fuso, { day: '2-digit', month: '2-digit', year: 'numeric' });
  }
}

/** `12/09/2026 14:32` (24h, sem segundos). */
export function formatarDataHora(iso: string): string {
  const instante = interpretar(iso);
  if (!instante) return TRACO_LONGO;
  const { data, fuso } = instante;
  const dataFormatada = campo(data, fuso, { day: '2-digit', month: '2-digit', year: 'numeric' });
  const hora = campo(data, fuso, { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${dataFormatada} ${hora}`;
}

/** Dia de calendário (epoch-day) do instante no fuso indicado. */
function diaDeCalendario(instante: InstanteISO): number {
  const partes = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: instante.fuso,
  }).format(instante.data);
  const [ano, mes, dia] = partes.split('-').map(Number);
  return Math.floor(Date.UTC(ano, mes - 1, dia) / 86_400_000);
}

/**
 * Relativa a `referencia` — **obrigatória**, nunca `Date.now()`.
 * Diferença em dias inteiros de calendário:
 * `hoje` · `ontem` · `amanhã` · `há 12 dias` · `há 3 meses` · `há 2 anos` ·
 * `em 12 dias` · `em 2 meses`.
 */
export function formatarDataRelativa(iso: string, referencia: string): string {
  const alvo = interpretar(iso);
  const base = interpretar(referencia);
  if (!alvo || !base) return TRACO_LONGO;

  // Positivo = futuro em relação à referência.
  const dias = diaDeCalendario(alvo) - diaDeCalendario(base);
  const rtf = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });
  const absoluto = Math.abs(dias);
  const sinal = dias < 0 ? -1 : 1;

  if (absoluto <= 1) return rtf.format(dias, 'day');
  if (absoluto < 30) return rtf.format(dias, 'day');
  if (absoluto < 365) return rtf.format(sinal * Math.round(absoluto / 30), 'month');
  return rtf.format(sinal * Math.round(absoluto / 365), 'year');
}

/** `1 dia` · `12 dias` · `0 dias`. Variante curta para eixos: `90 d`. */
export function formatarDias(n: number, curto = false): string {
  if (!ehNumeroValido(n)) return TRACO_LONGO;
  const inteiro = arredondarHalfExpand(n, 0);
  const corpo = formatarNumero(Math.abs(inteiro), 0);
  const prefixo = inteiro < 0 ? MENOS : '';
  if (curto) return `${prefixo}${corpo} d`;
  return `${prefixo}${corpo} ${Math.abs(inteiro) === 1 ? 'dia' : 'dias'}`;
}

/* ------------------------------------------------------------------ */
/* Documentos, listas e probabilidades                                 */
/* ------------------------------------------------------------------ */

export interface OpcoesDocumento {
  /** CPF é mascarado por padrão; CNPJ é dado público e nunca é mascarado. */
  mascarar?: boolean;
}

/**
 * Aceita dígitos puros ou string já formatada. Detecta pelo comprimento
 * (11 = CPF, 14 = CNPJ). Entrada inválida volta inalterada.
 */
export function formatarDocumento(doc: string, opts: OpcoesDocumento = {}): string {
  if (typeof doc !== 'string') return String(doc ?? TRACO_LONGO);
  const { mascarar = true } = opts;
  const digitos = doc.replace(/\D/g, '');

  if (digitos.length === 14) {
    return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8, 12)}-${digitos.slice(12)}`;
  }

  if (digitos.length === 11) {
    if (mascarar) {
      return `•••.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-••`;
    }
    return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`;
  }

  return doc;
}

/** `Soja, Milho safrinha e Algodão` — Intl.ListFormat pt-BR conjunction long. */
export function formatarLista(itens: string[]): string {
  if (!Array.isArray(itens) || itens.length === 0) return TRACO_LONGO;
  return new Intl.ListFormat(LOCALE, { style: 'long', type: 'conjunction' }).format(itens);
}

/** Subconjunto estrutural de `RiscoRJ` de que o formatador depende. */
export interface EntradaRiscoRJ {
  probabilidade12m: number;
  eventoJaOcorrido: boolean;
}

/**
 * Clamp de exibição do risco de RJ: probabilidade 1 com evento já ocorrido
 * vira `Evento ocorrido`, não `100,0%` (não é previsão, é fato consumado).
 */
export function formatarProbabilidadeRJ(risco: EntradaRiscoRJ): string {
  if (!risco) return TRACO_LONGO;
  if (risco.eventoJaOcorrido) return 'Evento ocorrido';
  return formatarPercentual(risco.probabilidade12m, 1);
}
