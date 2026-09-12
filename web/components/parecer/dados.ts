'use client';

/**
 * Busca e preparo de dados do Parecer de Risco (`specs/07` Parte 3).
 *
 * **Uma única função de busca** (`useDossieDoParecer`): a rota não espalha `fetch` por
 * componente. Números e listas chegam do motor e renderizam de imediato; a prosa chega depois,
 * por streaming, e nunca é caminho crítico de nada, se o modelo de linguagem não responder, o
 * documento sai completo com o texto determinístico e a etiqueta correspondente.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  ErroLastro,
  TEXTO_INICIAL,
  acumular,
  obterAvaliacao,
  obterCliente,
  obterHistorico,
  streamNarrativa,
  type TextoAcumulado,
} from '@/lib/api';
import { formatarMoeda, formatarPercentual, formatarScore } from '@/lib/format';
import type {
  AvaliacaoDeRisco,
  Cliente,
  EstadoDeSessaoApi,
  FatosDoCliente,
} from '@/types';

/* ------------------------------------------------------------------ */
/* Dossiê                                                              */
/* ------------------------------------------------------------------ */

export interface DossieDoParecer {
  cliente: Cliente | null;
  avaliacao: AvaliacaoDeRisco | null;
  fatos: FatosDoCliente | null;
  carregando: boolean;
  naoEncontrado: boolean;
  erro: string | null;
}

const VAZIO: DossieDoParecer = {
  cliente: null,
  avaliacao: null,
  fatos: null,
  carregando: true,
  naoEncontrado: false,
  erro: null,
};

export function useDossieDoParecer(
  clienteId: string,
  sessao: EstadoDeSessaoApi,
): DossieDoParecer {
  const [dossie, setDossie] = useState<DossieDoParecer>(VAZIO);

  useEffect(() => {
    const controle = new AbortController();
    let vivo = true;

    Promise.all([
      obterCliente(clienteId, controle.signal),
      obterAvaliacao(clienteId, sessao, controle.signal),
      obterHistorico(clienteId, controle.signal).catch(() => []),
    ])
      .then(([cliente, avaliacao, historico]) => {
        if (!vivo) return;
        const recente = [...historico].sort((a, b) => a.data.localeCompare(b.data)).at(-1);
        setDossie({
          cliente,
          avaliacao: cliente === null ? null : avaliacao,
          fatos: recente?.fatos ?? null,
          carregando: false,
          naoEncontrado: cliente === null,
          erro: null,
        });
      })
      .catch((causa: unknown) => {
        if (!vivo || controle.signal.aborted) return;
        const naoEncontrado = causa instanceof ErroLastro && causa.naoEncontrado;
        setDossie({
          ...VAZIO,
          carregando: false,
          naoEncontrado,
          erro: naoEncontrado
            ? null
            : causa instanceof ErroLastro
              ? causa.message
              : 'Não foi possível falar com o motor de risco.',
        });
      });

    return () => {
      vivo = false;
      controle.abort();
    };
  }, [clienteId, sessao]);

  return dossie;
}

/* ------------------------------------------------------------------ */
/* Identificador do documento                                          */
/* ------------------------------------------------------------------ */

/**
 * `LSTR-{clienteId}-{AAAAMMDD}-{hash6}`, com `hash6` derivado do JSON canônico da avaliação
 * sem os campos de prosa. Mesma avaliação, mesmo identificador, é o que permite conferir dois
 * PDFs impressos em momentos diferentes.
 */
export function useIdentificador(avaliacao: AvaliacaoDeRisco | null, clienteId: string): string {
  const [hash, setHash] = useState<string | null>(null);

  const canonico = useMemo(() => {
    if (!avaliacao) return null;
    const { recomendacao, ...resto } = avaliacao;
    const semProsa = {
      ...resto,
      recomendacao: { ...recomendacao, explicacao: null },
    };
    return JSON.stringify(semProsa, Object.keys(semProsa).sort());
  }, [avaliacao]);

  useEffect(() => {
    if (canonico === null) return;
    let vivo = true;
    void (async () => {
      const digerido = await digerir(canonico);
      if (vivo) setHash(digerido);
    })();
    return () => {
      vivo = false;
    };
  }, [canonico]);

  if (!avaliacao) return '-';
  const data = avaliacao.dataReferencia.replaceAll('-', '');
  return `LSTR-${clienteId.toUpperCase()}-${data}-${hash ?? '······'}`;
}

async function digerir(texto: string): Promise<string> {
  try {
    const bytes = new TextEncoder().encode(texto);
    const buffer = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(buffer)]
      .slice(0, 3)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    // Contexto sem `crypto.subtle` (http em rede local): FNV-1a serve, o identificador
    // continua estável para a mesma avaliação, que é a propriedade que importa.
    let h = 0x811c9dc5;
    for (let i = 0; i < texto.length; i += 1) {
      h ^= texto.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h.toString(16).padStart(8, '0').slice(0, 6);
  }
}

/* ------------------------------------------------------------------ */
/* Prosa                                                               */
/* ------------------------------------------------------------------ */

export type ChaveDeProsa = 'resumo' | 'riscos' | 'mitigadores' | 'justificativa';

export const CHAVES_DE_PROSA: ChaveDeProsa[] = [
  'resumo',
  'riscos',
  'mitigadores',
  'justificativa',
];

export interface BlocoDeProsa {
  texto: string;
  /** `llm` só quando o texto veio do modelo de linguagem e chegou ao fim. */
  origem: 'llm' | 'padrao';
  concluido: boolean;
}

export interface Prosa {
  blocos: Record<ChaveDeProsa, BlocoDeProsa>;
  /** Quantos dos quatro blocos já estão prontos, para o contador do botão de exportar. */
  prontos: number;
  transmitindo: boolean;
  /** `true` quando nenhum bloco virá do modelo de linguagem. */
  semIa: boolean;
  /** Substitui os blocos pendentes pelo texto determinístico e encerra o stream. */
  usarTextoPadrao: () => void;
}

/** Teto do documento para a prosa chegar. 3 s acima do leitor de stream de `lib/api`. */
const DEADLINE_DA_PROSA_MS = 31_000;

const LIMITES: Record<ChaveDeProsa, number> = {
  resumo: 900,
  riscos: 700,
  mitigadores: 400,
  justificativa: 600,
};

/** Título de nível 2 do parecer → bloco do documento. */
const TITULO_PARA_CHAVE: Array<[RegExp, ChaveDeProsa]> = [
  [/resumo executivo/i, 'resumo'],
  [/principais riscos/i, 'riscos'],
  [/fatores mitigadores/i, 'mitigadores'],
  [/recomenda/i, 'justificativa'],
];

/**
 * Abre **uma** tarefa de narrativa (`parecer`) e reparte o markdown de volta nos quatro blocos
 * de prosa do documento. Uma chamada, não quatro: o orçamento do modelo é limitado (D5) e o
 * texto do parecer já vem com exatamente estas seções.
 */
export function useProsaDoParecer(
  clienteId: string,
  sessao: EstadoDeSessaoApi,
  avaliacao: AvaliacaoDeRisco | null,
  cliente: Cliente | null,
  pronto: boolean,
): Prosa {
  const [acumulado, setAcumulado] = useState<TextoAcumulado>(TEXTO_INICIAL);
  const [falhou, setFalhou] = useState(false);
  const [desistiu, setDesistiu] = useState(false);
  const [expirou, setExpirou] = useState(false);

  /*
   * Prazo próprio do documento. O executor no serviço de linguagem tem 25 s e o leitor de
   * stream tem 28 s, mas um salto que devolve os cabeçalhos e depois não escreve byte nenhum
   * deixaria o parecer preso em "gerando texto" para sempre. Passado o prazo, o texto
   * determinístico assume e o documento fica exportável. Nenhum número depende disto.
   */
  useEffect(() => {
    if (!pronto || desistiu) return;
    const relogio = window.setTimeout(() => setExpirou(true), DEADLINE_DA_PROSA_MS);
    return () => window.clearTimeout(relogio);
  }, [pronto, desistiu]);

  useEffect(() => {
    if (!pronto || desistiu) return;
    const controle = new AbortController();
    let vivo = true;

    void (async () => {
      try {
        for await (const evento of streamNarrativa(
          'parecer',
          { clienteId, sessao },
          controle.signal,
        )) {
          if (!vivo) return;
          setAcumulado((atual) => acumular(atual, evento));
        }
      } catch {
        if (vivo && !controle.signal.aborted) setFalhou(true);
      }
    })();

    return () => {
      vivo = false;
      controle.abort();
    };
  }, [clienteId, sessao, pronto, desistiu]);

  const usarTextoPadrao = useCallback(() => setDesistiu(true), []);

  return useMemo(() => {
    const padrao = textosPadrao(avaliacao, cliente);
    const daIa = repartir(acumulado.texto);
    const veioDoModelo = acumulado.origem === 'openai' && !falhou && !acumulado.erro;
    const encerrado =
      desistiu || falhou || expirou || acumulado.concluido || Boolean(acumulado.erro);

    const blocos = {} as Record<ChaveDeProsa, BlocoDeProsa>;
    let prontos = 0;
    for (const chave of CHAVES_DE_PROSA) {
      const bruto = daIa[chave];
      const temTexto = Boolean(bruto) && (encerrado || bruto.length > 0);
      const usaIa = veioDoModelo && temTexto;
      const texto = usaIa ? truncar(bruto, LIMITES[chave]) : padrao[chave];
      // Um bloco só conta como pronto quando o stream acabou, ou quando já veio um título
      // posterior, sinal de que aquela seção foi fechada pelo modelo.
      const concluido = encerrado || (usaIa && daIa.fechados.has(chave));
      if (concluido) prontos += 1;
      blocos[chave] = {
        texto,
        origem: usaIa && concluido ? 'llm' : 'padrao',
        concluido,
      };
    }

    return {
      blocos,
      prontos,
      transmitindo: !encerrado,
      semIa: encerrado && !veioDoModelo,
      usarTextoPadrao,
    };
  }, [acumulado, falhou, desistiu, expirou, avaliacao, cliente, usarTextoPadrao]);
}

interface Repartido extends Record<ChaveDeProsa, string> {
  fechados: Set<ChaveDeProsa>;
}

/** Quebra o markdown de seis títulos em pedaços por `## `. */
function repartir(markdown: string): Repartido {
  const saida: Repartido = {
    resumo: '',
    riscos: '',
    mitigadores: '',
    justificativa: '',
    fechados: new Set<ChaveDeProsa>(),
  };
  if (!markdown) return saida;

  const partes = markdown.split(/^##\s+/m).slice(1);
  const vistos: ChaveDeProsa[] = [];
  for (const parte of partes) {
    const quebra = parte.indexOf('\n');
    const titulo = quebra === -1 ? parte : parte.slice(0, quebra);
    const corpo = quebra === -1 ? '' : parte.slice(quebra + 1);
    const par = TITULO_PARA_CHAVE.find(([padrao]) => padrao.test(titulo));
    if (!par) continue;
    saida[par[1]] = limpar(corpo);
    vistos.push(par[1]);
  }
  // Todo bloco menos o último visto já foi fechado por um título posterior.
  for (const chave of vistos.slice(0, -1)) saida.fechados.add(chave);
  return saida;
}

/** Tira marcação de markdown: o documento impresso não renderiza markdown. */
function limpar(texto: string): string {
  return texto
    .replaceAll(/\*\*(.+?)\*\*/g, '$1')
    .replaceAll(/^\s*[-*]\s+/gm, '')
    .replaceAll(/^\s*\d+\.\s+/gm, '')
    .split('\n')
    .map((linha) => linha.trim())
    .filter(Boolean)
    .join(' ')
    .trim();
}

/** Corta em fronteira de frase, como manda a §3.6. */
function truncar(texto: string, limite: number): string {
  if (texto.length <= limite) return texto;
  const recorte = texto.slice(0, limite);
  const fim = Math.max(recorte.lastIndexOf('. '), recorte.lastIndexOf('; '));
  if (fim > limite * 0.5) return `${recorte.slice(0, fim + 1)} ...`;
  return `${recorte.trimEnd()} ...`;
}

export const SEM_MITIGADORES =
  'Nenhum fator de proteção materializado na data de referência.';

/**
 * Texto determinístico dos quatro blocos, montado por template a partir dos números do motor.
 * É o que aparece quando o modelo de linguagem está desligado, estourou o orçamento ou não
 * respondeu, e é o que a suíte de teste vê, porque teste não chama o modelo (D6).
 */
export function textosPadrao(
  avaliacao: AvaliacaoDeRisco | null,
  cliente: Cliente | null,
): Record<ChaveDeProsa, string> {
  if (!avaliacao) {
    return {
      resumo: 'Aguardando a avaliação do motor de risco.',
      riscos: 'Aguardando a avaliação do motor de risco.',
      mitigadores: SEM_MITIGADORES,
      justificativa: 'Aguardando a avaliação do motor de risco.',
    };
  }

  const nome = cliente?.razaoSocial ?? avaliacao.clienteId;
  const local = cliente ? `${cliente.municipio}, ${cliente.uf}` : 'município não informado';
  const veto = avaliacao.vetosAtivos[0];
  const protecoes = avaliacao.dimensoes
    .flatMap((d) => d.fatores)
    .filter((f) => f.direcao === 'protecao');
  const criticas = avaliacao.redFlags.filter(
    (r) => r.severidade === 'CRITICA' || r.severidade === 'ALTA',
  );

  return {
    resumo: [
      `${nome} (${local}) tem score calculado de ${formatarScore(avaliacao.scoreCalculado)} e classificação final ${avaliacao.ratingFinal}.`,
      veto
        ? `A classificação final resulta da regra de negócio ${veto.rotulo}, aplicada acima do score.`
        : `Não há regra de negócio rebaixando a classificação na data de referência.`,
      `A probabilidade de inadimplência em 12 meses é de ${formatarPercentual(avaliacao.pd.pd12m, 1)} e a exposição total é de ${formatarMoeda(avaliacao.exposicao.exposicaoTotal)}, dos quais ${formatarMoeda(avaliacao.exposicao.exposicaoEmRiscoEmRJ)} ficam sem proteção efetiva em cenário de recuperação judicial.`,
      `A recomendação do motor é ${avaliacao.recomendacao.rotulo}, com reavaliação em ${avaliacao.recomendacao.prazoReavaliacaoDias} dias.`,
    ].join(' '),

    riscos: criticas.length
      ? `São ${criticas.length} sinais de severidade crítica ou alta na data de referência, encabeçados por ${criticas[0].titulo}. A lista acima traz cada um com a fonte, a data e o impacto em pontos apurado pelo motor.`
      : 'Nenhuma red flag de severidade crítica ou alta na data de referência. A lista acima traz os sinais de severidade média e informativa identificados.',

    mitigadores: protecoes.length
      ? `São ${protecoes.length} fatores de proteção na data de referência. A cobertura extraconcursal é de ${formatarPercentual(avaliacao.exposicao.coberturaExtraconcursal, 1)} da exposição, e é a única parcela que permanece executável se o cliente pedir recuperação judicial.`
      : SEM_MITIGADORES,

    justificativa: `A recomendação ${avaliacao.recomendacao.rotulo} decorre da combinação entre a classificação ${avaliacao.ratingFinal}, a probabilidade de inadimplência de ${formatarPercentual(avaliacao.pd.pd12m, 1)} em 12 meses e a exposição de ${formatarMoeda(avaliacao.exposicao.exposicaoEmRisco)} sem cobertura de garantia. As ações listadas acima foram parametrizadas pelo motor com os números deste cliente, na ordem de prioridade indicada.`,
  };
}

/* ------------------------------------------------------------------ */
/* Registro de exportação                                              */
/* ------------------------------------------------------------------ */

const CHAVE_EXPORTACOES = 'lastro:pareceres:v1';

/**
 * Anotação de sessão: par `{identificador, dataHora}` de cada parecer exportado.
 *
 * Vive em chave própria, e não dentro de `lastro:sessao:v1`, para não disputar escrita com o
 * estado de sessão da aplicação, um `read-modify-write` concorrente ali perderia eventos
 * simulados, que é dado que o analista acabou de produzir.
 */
export function registrarExportacao(identificador: string): void {
  try {
    const bruto = window.localStorage.getItem(CHAVE_EXPORTACOES);
    const lista: unknown = bruto ? JSON.parse(bruto) : [];
    const anterior = Array.isArray(lista) ? lista : [];
    window.localStorage.setItem(
      CHAVE_EXPORTACOES,
      JSON.stringify([...anterior, { identificador, dataHora: new Date().toISOString() }]),
    );
  } catch {
    // Armazenamento indisponível (janela anônima, cota estourada): a exportação continua.
  }
}
