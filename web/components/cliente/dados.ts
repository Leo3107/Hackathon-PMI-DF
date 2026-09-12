'use client';

/**
 * Camada de dados da página do cliente (`specs/03-ux-e-telas.md` §4).
 *
 * Duas famílias de estado, deliberadamente separadas:
 *
 * 1. **Números** — `useDossie`. Vêm do motor determinístico em uma única rodada de `fetch`
 *    paralelo e renderizam assim que chegam. Nenhum deles depende do LLM (regra R1 / exigência 5).
 * 2. **Prosa** — `useNarrativa` e `useCopiloto`. Chegam por NDJSON e degradam sozinhas: se o
 *    stream falhar, o bloco de texto entra em erro local e a página inteira continua correta.
 *
 * O estado de sessão (eventos simulados, status de red flag) viaja no corpo de toda chamada que
 * recalcula risco — mudou a sessão, refaz a rodada. É por isso que marcar uma red flag como
 * analisada dispara recálculo: quem decide o efeito é o motor, não a tela (R6).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  ErroLastro,
  TEXTO_INICIAL,
  acumular,
  obterAvaliacao,
  obterCliente,
  obterEventos,
  obterHistorico,
  streamCopiloto,
  streamNarrativa,
  type TextoAcumulado,
} from '@/lib/api';
import type { EstadoStreaming } from '@/components/ui';
import type {
  AvaliacaoDeRisco,
  Cliente,
  ComparacaoDeAvaliacoes,
  EstadoDeSessaoApi,
  EventoDeRisco,
  FatosDoCliente,
  MensagemCopiloto,
  SnapshotHistorico,
  TarefaNarrativa,
} from '@/types';

/* ------------------------------------------------------------------ */
/* Dossiê — todos os números da tela                                   */
/* ------------------------------------------------------------------ */

export interface Dossie {
  cliente: Cliente | null;
  avaliacao: AvaliacaoDeRisco | null;
  eventos: EventoDeRisco[];
  /**
   * Fatos brutos do snapshot mais recente — a única origem de garantias, operações e parcelas
   * individuais, que a avaliação só publica agregadas. Recorte, nunca recálculo.
   */
  fatos: FatosDoCliente | null;
  carregando: boolean;
  /** `ErroLastro` quando o motor não respondeu; `null` no caminho feliz. */
  erro: ErroLastro | null;
  /** `true` quando o motor respondeu e disse que o id não existe. */
  naoEncontrado: boolean;
  recarregar: () => void;
}

const SEM_EVENTOS: EventoDeRisco[] = [];
const SEM_HISTORICO: SnapshotHistorico[] = [];

/**
 * Resultado de **uma** rodada, carimbado com a chave da rodada que o produziu.
 *
 * Guardar a chave junto do resultado permite derivar `carregando` na renderização
 * (`resultado.chave !== chave`) em vez de escrever `setCarregando(true)` no corpo do efeito —
 * o que dispararia uma renderização em cascata a cada troca de cliente ou de sessão.
 */
interface Rodada {
  chave: string;
  cliente: Cliente | null;
  avaliacao: AvaliacaoDeRisco | null;
  eventos: EventoDeRisco[];
  fatos: FatosDoCliente | null;
  erro: ErroLastro | null;
  naoEncontrado: boolean;
}

const RODADA_VAZIA: Rodada = {
  chave: '',
  cliente: null,
  avaliacao: null,
  eventos: SEM_EVENTOS,
  fatos: null,
  erro: null,
  naoEncontrado: false,
};

/** Identidade da rodada: muda quando muda o cliente, a sessão ou o pedido de nova tentativa. */
function chaveDaRodada(clienteId: string, sessao: EstadoDeSessaoApi, tentativa: number): string {
  return `${clienteId}|${tentativa}|${JSON.stringify(sessao)}`;
}

export function useDossie(clienteId: string, sessao: EstadoDeSessaoApi): Dossie {
  const [tentativa, setTentativa] = useState(0);
  const [rodada, setRodada] = useState<Rodada>(RODADA_VAZIA);
  const chave = chaveDaRodada(clienteId, sessao, tentativa);

  useEffect(() => {
    const controle = new AbortController();
    let vivo = true;

    // `eventos` e `historico` são acessórios: a ausência deles suprime a linha do tempo e a
    // tabela de garantias, nunca a página inteira.
    Promise.all([
      obterCliente(clienteId, controle.signal),
      obterAvaliacao(clienteId, sessao, controle.signal),
      obterEventos(clienteId, sessao, controle.signal).catch(() => SEM_EVENTOS),
      obterHistorico(clienteId, controle.signal).catch(() => SEM_HISTORICO),
    ])
      .then(([c, a, e, h]) => {
        if (!vivo) return;
        const recente = [...h].sort((x, y) => x.data.localeCompare(y.data)).at(-1);
        setRodada({
          chave,
          cliente: c,
          avaliacao: c === null ? null : a,
          eventos: e,
          fatos: recente?.fatos ?? null,
          erro: null,
          naoEncontrado: c === null,
        });
      })
      .catch((causa: unknown) => {
        if (!vivo || controle.signal.aborted) return;
        const naoEncontrado = causa instanceof ErroLastro && causa.naoEncontrado;
        setRodada({
          ...RODADA_VAZIA,
          chave,
          naoEncontrado,
          erro: naoEncontrado
            ? null
            : causa instanceof ErroLastro
              ? causa
              : new ErroLastro('ERRO_INTERNO', 500),
        });
      });

    return () => {
      vivo = false;
      controle.abort();
    };
  }, [clienteId, sessao, chave]);

  const recarregar = useCallback(() => setTentativa((n) => n + 1), []);
  const atual = rodada.chave === chave;
  // Recalcular por mudança de sessão mantém os números anteriores em tela até os novos
  // chegarem; trocar de cliente, não — seria mostrar o dossiê errado com o nome certo.
  const mesmoCliente = rodada.chave.startsWith(`${clienteId}|`);

  return {
    cliente: mesmoCliente ? rodada.cliente : null,
    avaliacao: mesmoCliente ? rodada.avaliacao : null,
    eventos: mesmoCliente ? rodada.eventos : SEM_EVENTOS,
    fatos: mesmoCliente ? rodada.fatos : null,
    carregando: !atual,
    erro: atual ? rodada.erro : null,
    naoEncontrado: atual && rodada.naoEncontrado,
    recarregar,
  };
}

/* ------------------------------------------------------------------ */
/* Narrativa — os dois blocos de prosa da página                       */
/* ------------------------------------------------------------------ */

export interface Narrativa {
  texto: string;
  estado: EstadoStreaming;
  origem: 'llm' | 'deterministico';
  modelo?: string;
  tentarNovamente: () => void;
}

interface FluxoDeNarrativa {
  chave: string;
  acumulado: TextoAcumulado;
  abriu: boolean;
  falhou: boolean;
  modelo?: string;
}

const FLUXO_VAZIO: FluxoDeNarrativa = {
  chave: '',
  acumulado: TEXTO_INICIAL,
  abriu: false,
  falhou: false,
};

function estadoDe(acumulado: TextoAcumulado, abriu: boolean, falhou: boolean): EstadoStreaming {
  if (falhou) return 'erro';
  if (acumulado.erro) return 'erro';
  if (!abriu || (!acumulado.concluido && acumulado.texto === '')) return 'aguardando';
  if (!acumulado.concluido) return 'transmitindo';
  return acumulado.degradou ? 'degradado' : 'concluido';
}

/**
 * Abre uma tarefa de narrativa e acumula os deltas.
 *
 * `pronto = false` segura o disparo até os números estarem em tela: o LLM nunca é o caminho
 * crítico de nada e não faz sentido gastar orçamento em um cliente que não carregou.
 */
export function useNarrativa(
  tarefa: TarefaNarrativa,
  clienteId: string,
  sessao: EstadoDeSessaoApi,
  pronto: boolean,
): Narrativa {
  const [tentativa, setTentativa] = useState(0);
  const [fluxo, setFluxo] = useState<FluxoDeNarrativa>(FLUXO_VAZIO);
  const chave = `${tarefa}|${chaveDaRodada(clienteId, sessao, tentativa)}`;

  useEffect(() => {
    if (!pronto) return;
    const controle = new AbortController();
    let vivo = true;

    void (async () => {
      try {
        for await (const evento of streamNarrativa(tarefa, { clienteId, sessao }, controle.signal)) {
          if (!vivo) return;
          setFluxo((atual) => {
            const base = atual.chave === chave ? atual : { ...FLUXO_VAZIO, chave };
            return {
              chave,
              acumulado: acumular(base.acumulado, evento),
              abriu: true,
              falhou: false,
              modelo: evento.t === 'inicio' ? evento.modelo : base.modelo,
            };
          });
        }
      } catch {
        if (vivo && !controle.signal.aborted) {
          setFluxo((atual) => ({
            ...(atual.chave === chave ? atual : { ...FLUXO_VAZIO, chave }),
            chave,
            falhou: true,
          }));
        }
      }
    })();

    return () => {
      vivo = false;
      controle.abort();
    };
  }, [tarefa, clienteId, sessao, pronto, chave]);

  const tentarNovamente = useCallback(() => setTentativa((n) => n + 1), []);
  const atual = fluxo.chave === chave ? fluxo : FLUXO_VAZIO;

  return {
    texto: atual.acumulado.texto,
    estado: estadoDe(atual.acumulado, atual.abriu, atual.falhou),
    origem: atual.acumulado.origem === 'openai' ? 'llm' : 'deterministico',
    modelo: atual.modelo,
    tentarNovamente,
  };
}

/* ------------------------------------------------------------------ */
/* Copiloto                                                            */
/* ------------------------------------------------------------------ */

export interface TurnoCopiloto {
  id: string;
  pergunta: string;
  resposta: string;
  estado: EstadoStreaming;
  origem: 'llm' | 'deterministico';
}

export interface Copiloto {
  turnos: TurnoCopiloto[];
  ocupado: boolean;
  perguntar: (pergunta: string) => void;
  limpar: () => void;
}

/** Histórico enviado ao modelo: máximo de 6 mensagens (`03-ux-e-telas.md` §4.12). */
const MAX_HISTORICO = 6;

export function useCopiloto(clienteId: string, sessao: EstadoDeSessaoApi): Copiloto {
  // A conversa é carimbada com o cliente a que pertence: trocar de rota zera o histórico por
  // derivação, sem um efeito que chame `setState` só para limpar.
  const [conversa, setConversa] = useState<{ clienteId: string; turnos: TurnoCopiloto[] }>({
    clienteId,
    turnos: [],
  });
  const [ocupado, setOcupado] = useState(false);
  const abortar = useRef<AbortController | null>(null);
  const turnos = useMemo(
    () => (conversa.clienteId === clienteId ? conversa.turnos : []),
    [conversa, clienteId],
  );

  useEffect(() => () => abortar.current?.abort(), []);

  const setTurnos = useCallback(
    (proximos: (atuais: TurnoCopiloto[]) => TurnoCopiloto[]) => {
      setConversa((atual) => ({
        clienteId,
        turnos: proximos(atual.clienteId === clienteId ? atual.turnos : []),
      }));
    },
    [clienteId],
  );

  const perguntar = useCallback(
    (pergunta: string) => {
      const texto = pergunta.trim();
      if (!texto || ocupado) return;

      const id = `turno-${Date.now()}`;
      const historico: MensagemCopiloto[] = turnos
        .flatMap((t): MensagemCopiloto[] => [
          { papel: 'usuario', texto: t.pergunta },
          { papel: 'assistente', texto: t.resposta },
        ])
        .slice(-MAX_HISTORICO);

      setTurnos((atuais) => [
        ...atuais,
        { id, pergunta: texto, resposta: '', estado: 'aguardando', origem: 'deterministico' },
      ]);
      setOcupado(true);

      const controle = new AbortController();
      abortar.current = controle;

      void (async () => {
        let estado: TextoAcumulado = TEXTO_INICIAL;
        try {
          for await (const evento of streamCopiloto(
            { clienteId, sessao, pergunta: texto, historico },
            controle.signal,
          )) {
            estado = acumular(estado, evento);
            const instantaneo = estado;
            setTurnos((atuais) =>
              atuais.map((t) =>
                t.id === id
                  ? {
                      ...t,
                      resposta: instantaneo.texto,
                      origem: instantaneo.origem === 'openai' ? 'llm' : 'deterministico',
                      estado: instantaneo.erro
                        ? 'erro'
                        : instantaneo.concluido
                          ? instantaneo.degradou
                            ? 'degradado'
                            : 'concluido'
                          : instantaneo.texto
                            ? 'transmitindo'
                            : 'aguardando',
                    }
                  : t,
              ),
            );
          }
        } catch {
          setTurnos((atuais) =>
            atuais.map((t) => (t.id === id ? { ...t, estado: 'erro' } : t)),
          );
        } finally {
          if (abortar.current === controle) abortar.current = null;
          setOcupado(false);
        }
      })();
    },
    [clienteId, sessao, ocupado, turnos, setTurnos],
  );

  const limpar = useCallback(() => {
    abortar.current?.abort();
    setConversa({ clienteId, turnos: [] });
  }, [clienteId]);

  return { turnos, ocupado, perguntar, limpar };
}

/* ------------------------------------------------------------------ */
/* Derivações de apresentação (nenhum número novo — só recorte)        */
/* ------------------------------------------------------------------ */

/**
 * Pontos da série temporal do score.
 *
 * O motor devolve `scoreApos` em cada `EventoDeRisco` e o score corrente na avaliação. A série
 * é a concatenação dos dois — **nenhum valor intermediário é inventado** (por isso a linha é
 * em degraus, `03-ux-e-telas.md` §5.1). A tela não recalcula score de snapshot: se o motor não
 * mandou, o ponto não existe.
 */
export interface PontoDaSerie {
  data: string;
  score: number;
  eventos: EventoDeRisco[];
}

export function serieDeScore(
  eventos: EventoDeRisco[],
  avaliacao: AvaliacaoDeRisco | null,
): PontoDaSerie[] {
  const porData = new Map<string, PontoDaSerie>();
  for (const evento of eventos) {
    const existente = porData.get(evento.data);
    if (existente) {
      existente.eventos.push(evento);
      existente.score = evento.scoreApos;
    } else {
      porData.set(evento.data, {
        data: evento.data,
        score: evento.scoreApos,
        eventos: [evento],
      });
    }
  }
  if (avaliacao) {
    const atual = porData.get(avaliacao.dataReferencia);
    if (atual) atual.score = avaliacao.scoreCalculado;
    else
      porData.set(avaliacao.dataReferencia, {
        data: avaliacao.dataReferencia,
        score: avaliacao.scoreCalculado,
        eventos: [],
      });
  }
  return [...porData.values()].sort((a, b) => a.data.localeCompare(b.data));
}

/** Índice `evidenciaId → Evidencia` para o laço evidência ↔ fator (R5). */
export function useIndiceDeEvidencias(avaliacao: AvaliacaoDeRisco | null) {
  return useMemo(() => {
    const mapa = new Map<string, AvaliacaoDeRisco['evidencias'][number]>();
    for (const evidencia of avaliacao?.evidencias ?? []) mapa.set(evidencia.id, evidencia);
    return mapa;
  }, [avaliacao]);
}

/** Índice `fatorId → FatorCalculado`, atravessando as sete dimensões. */
export function useIndiceDeFatores(avaliacao: AvaliacaoDeRisco | null) {
  return useMemo(() => {
    const mapa = new Map<
      string,
      { fator: AvaliacaoDeRisco['dimensoes'][number]['fatores'][number]; peso: number }
    >();
    for (const dimensao of avaliacao?.dimensoes ?? []) {
      for (const fator of dimensao.fatores) mapa.set(fator.id, { fator, peso: dimensao.peso });
    }
    return mapa;
  }, [avaliacao]);
}

/**
 * Comparação de 90 dias publicada pela lista de clientes.
 *
 * O contrato do motor expõe a variação por cliente em `ClienteAvaliado.variacao90d`
 * (`types/api.ts`). Enquanto a rota não responde, o bloco "O que mudou" simplesmente não
 * renderiza — ele é condicional por especificação (§4.10, bloco 4).
 */
export function comparacaoUtil(
  variacao: ComparacaoDeAvaliacoes | undefined,
): ComparacaoDeAvaliacoes | null {
  if (!variacao) return null;
  if (variacao.deltaScore === 0 && variacao.fatores.length === 0) return null;
  return variacao;
}
