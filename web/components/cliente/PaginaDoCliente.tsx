'use client';

/**
 * Página do cliente — orquestração dos blocos de análise (`03-ux-e-telas.md` §4).
 *
 * ## Layout
 *
 * Grid de 12 colunas. O cabeçalho ocupa as 12. As faixas que mudam o que é **legalmente
 * possível hoje** — banda de veto e painel de Stay Period — entram logo abaixo, também em 12,
 * antes das duas colunas. Depois o grid se abre em **principal (8)**, que rola normalmente, e
 * **lateral (4)**, `sticky`, que mantém score, PD, risco de RJ e recomendação visíveis durante
 * toda a rolagem: são as respostas de "qual o risco" e "o que fazer", e o analista não deveria
 * precisar rolar de volta para relê-las.
 *
 * ## Resumo por padrão, completo sob demanda
 *
 * Abrir um cliente não é abrir um relatório: na esmagadora maioria das vezes o analista decide
 * com **poucos números** — score e o que o move, PD, risco de RJ, recomendação — e o resto é
 * aprofundamento que só interessa quando a decisão não é óbvia. Por isso a página nasce em
 * `modo = 'resumo'`, com a coluna principal reduzida a "o que mudou", "por que este score" e as
 * red flags **quando existem**; um botão largo abre o modo `'completo'` com decomposição por
 * dimensão, exposição e garantias, linha do tempo e registro da decisão.
 *
 * O que **nunca** se esconde: as faixas de veto e de Stay Period (mudam o que é legalmente
 * possível hoje, não são detalhe) e a coluna lateral inteira (é a resposta, não o anexo).
 *
 * Âncora de URL manda no modo: um link para `#exposicao` ou `#decisao` abre a página já em
 * completo, senão cairia num bloco que não existe.
 *
 * ## Números antes da prosa
 *
 * Uma única rodada de `fetch` traz tudo o que é número. Os dois blocos de prosa (a análise do
 * score e a justificativa da recomendação) abrem streams próprios e **só depois** que os números
 * chegaram. Falha de LLM degrada apenas o parágrafo; falha do motor derruba a tela inteira com
 * `ErrorState`, porque sem motor não existe número nenhum para mostrar.
 */

import { ChevronDown, ChevronUp } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useClientes, useSessaoParaApi } from '@/components/shell';
import { Button, Card, ErrorState, useReducedMotion } from '@/components/ui';
import type { Evidencia } from '@/types';

import { BlocoDimensoes, BlocoOQueMudou, BlocoPorQue, BlocoRedFlags } from './Analise';
import { BandaDeVeto, CabecalhoDoCliente, PainelStayPeriod } from './Cabecalho';
import { BlocoDecisao } from './Decisao';
import { DrawerDeEvidencia, DrawerDeFator } from './Evidencias';
import { BlocoExposicao } from './Exposicao';
import { BlocoLinhaDoTempo } from './LinhaDoTempo';
import {
  CardDePd,
  CardDeRecomendacao,
  CardDeRiscoRj,
  CardDeScore,
} from './Lateral';
import {
  comparacaoUtil,
  useDossie,
  useIndiceDeEvidencias,
  useIndiceDeFatores,
  useNarrativa,
} from './dados';

/** Quanto da análise está em tela. Ver o bloco "Resumo por padrão" no topo do arquivo. */
type ModoDaPagina = 'resumo' | 'completo';

/** `id` do container que o botão de expandir controla (`aria-controls`). */
const ID_ANALISE_COMPLETA = 'analise-completa';

export interface PaginaDoClienteProps {
  clienteId: string;
}

export function PaginaDoCliente({ clienteId }: PaginaDoClienteProps) {
  const sessao = useSessaoParaApi(clienteId);
  const dossie = useDossie(clienteId, sessao);
  const clientes = useClientes();

  const [evidenciaAberta, setEvidenciaAberta] = useState<string | null>(null);
  const [fatorAberto, setFatorAberto] = useState<string | null>(null);

  // O modo é carimbado com o cliente a que pertence: trocar de rota volta ao resumo por
  // derivação, sem um efeito que chame `setState` só para limpar. Expandir é uma preferência de
  // leitura *daquele* dossiê, não um estado de navegação que atravesse clientes.
  const [preferencia, setPreferencia] = useState<{ clienteId: string; modo: ModoDaPagina }>({
    clienteId,
    modo: 'resumo',
  });
  const modo: ModoDaPagina = preferencia.clienteId === clienteId ? preferencia.modo : 'resumo';

  const indiceDeEvidencias = useIndiceDeEvidencias(dossie.avaliacao);
  const indiceDeFatores = useIndiceDeFatores(dossie.avaliacao);

  // A comparação de 90 dias é publicada por cliente na lista avaliada do motor.
  const variacao = useMemo(
    () => comparacaoUtil(clientes.find((c) => c.cliente.id === clienteId)?.variacao90d),
    [clientes, clienteId],
  );

  const pronto = dossie.avaliacao !== null;
  const narrativaDoScore = useNarrativa('score', clienteId, sessao, pronto);
  const narrativaDaRecomendacao = useNarrativa('recomendacao', clienteId, sessao, pronto);

  const abrirEvidencia = useCallback((id: string) => {
    setFatorAberto(null);
    setEvidenciaAberta(id);
  }, []);

  const selecionarFator = useCallback((id: string) => {
    setEvidenciaAberta(null);
    setFatorAberto(id);
  }, []);

  const topo = useRef<HTMLDivElement>(null);
  const movimentoReduzido = useReducedMotion();

  const expandir = useCallback(
    () => setPreferencia({ clienteId, modo: 'completo' }),
    [clienteId],
  );

  const recolher = useCallback(() => {
    setPreferencia({ clienteId, modo: 'resumo' });
    // Recolher no fim de uma página longa deixaria o analista olhando para o rodapé de um
    // conteúdo que acabou de sumir: volta-se ao topo do resumo.
    topo.current?.scrollIntoView({
      behavior: movimentoReduzido ? 'auto' : 'smooth',
      block: 'start',
    });
  }, [clienteId, movimentoReduzido]);

  useAncoraDeBloco(pronto, modo, expandir);

  /* --- Estados de exceção ------------------------------------------- */

  if (dossie.naoEncontrado) {
    return (
      <ErrorState
        titulo="Cliente não encontrado"
        detalhe={`Nenhum cliente com o identificador "${clienteId}" na carteira. Verifique o endereço ou volte para a lista.`}
      />
    );
  }

  if (dossie.erro) {
    return (
      <ErrorState
        titulo="Motor de risco indisponível"
        detalhe={`${dossie.erro.message} A interface do Lastro não calcula risco: score, probabilidades, coberturas e recomendações vêm do serviço de cálculo em Python. Verifique se ele está de pé (npm run dev), a porta 5001 e a variável LASTRO_API_URL.`}
        aoTentarNovamente={dossie.recarregar}
      />
    );
  }

  const { cliente, avaliacao } = dossie;

  if (!cliente || !avaliacao) {
    return <EsqueletoDaPagina />;
  }

  const emVeto = avaliacao.vetosAtivos.length > 0;
  const stay = avaliacao.stayPeriod;
  const fechamentoQuebrado = Math.abs(avaliacao.auditoria.diferenca) > 0.5;
  const daCarteira = cliente.origem === 'CARTEIRA';
  const completo = modo === 'completo';
  const temRedFlags = avaliacao.redFlags.length > 0;

  const blocoRedFlags = (
    <BlocoRedFlags
      redFlags={avaliacao.redFlags}
      dataReferencia={avaliacao.dataReferencia}
      aoVerEvidencia={abrirEvidencia}
      aoSelecionarFator={selecionarFator}
    />
  );

  return (
    <div ref={topo} className="flex flex-col gap-4 scroll-mt-[88px]">
      {/* 1 — cabeçalho (12 col) */}
      <CabecalhoDoCliente
        cliente={cliente}
        ultimaVarredura={avaliacao.dataReferencia}
        parecerBloqueado={fechamentoQuebrado}
      />

      {/* 2 — banda de veto (12 col) — nunca colapsa: muda o que é possível hoje */}
      {emVeto ? (
        <BandaDeVeto
          vetos={avaliacao.vetosAtivos}
          scoreCalculado={String(avaliacao.scoreCalculado)}
          ratingCalculado={avaliacao.ratingCalculado}
          ratingFinal={avaliacao.ratingFinal}
          aoVerEvidencia={abrirEvidencia}
        />
      ) : null}

      {/* 3 — Stay Period (12 col) — idem */}
      {stay?.ativo ? <PainelStayPeriod stayPeriod={stay} /> : null}

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Coluna principal — 8 col */}
        <div className="flex min-w-0 flex-col gap-4 lg:col-span-8">
          {/* 4 — o que mudou */}
          {daCarteira && variacao ? (
            <BlocoOQueMudou variacao={variacao} aoSelecionarFator={selecionarFator} />
          ) : null}

          {/* 5 — por que este score */}
          <BlocoPorQue
            avaliacao={avaliacao}
            narrativa={narrativaDoScore}
            aoSelecionarFator={selecionarFator}
            fatorDestacado={fatorAberto}
          />

          {/* 7 — red flags: no resumo só quando existem; um card vazio não informa nada */}
          {!completo && temRedFlags ? blocoRedFlags : null}

          {/*
            Container dos blocos de aprofundamento. `contents` mantém os cards no fluxo da
            coluna e dá ao botão um alvo real de `aria-controls` mesmo no modo resumo.
          */}
          <div id={ID_ANALISE_COMPLETA} className="contents">
            {completo ? (
              <>
                {/* 6 — decomposição por dimensão */}
                <BlocoDimensoes
                  dimensoes={avaliacao.dimensoes}
                  auditoria={avaliacao.auditoria}
                  scoreExibido={avaliacao.scoreCalculado}
                  aoSelecionarFator={selecionarFator}
                />

                {/* 7 — red flags (sempre, inclusive vazio: aqui o "nada consta" é informação) */}
                {blocoRedFlags}

                {/* 8 — exposição e garantias */}
                {daCarteira ? (
                  <BlocoExposicao exposicao={avaliacao.exposicao} fatos={dossie.fatos} />
                ) : (
                  <Card as="section" className="flex flex-col gap-1">
                    <h2 className="type-section-title">Sem exposição atual</h2>
                    <p className="type-body text-fg-secondary">
                      Este documento não possui operações com a Krill Tech. A avaliação considera
                      apenas fontes externas — não há garantia, cobertura nem exposição em cenário
                      de RJ a apresentar.
                    </p>
                  </Card>
                )}

                {/* 9 — linha do tempo */}
                {daCarteira ? (
                  <BlocoLinhaDoTempo
                    avaliacao={avaliacao}
                    eventos={dossie.eventos}
                    aoVerEvidencia={abrirEvidencia}
                  />
                ) : null}

                {/* 12 — decisão do analista */}
                <BlocoDecisao cliente={cliente} avaliacao={avaliacao} />
              </>
            ) : null}
          </div>

          <BotaoDeAprofundamento completo={completo} aoAlternar={completo ? recolher : expandir} />
        </div>

        {/* Coluna lateral — 4 col, sticky. Completa nos dois modos: é a resposta. */}
        <aside
          aria-label="Resumo de risco e recomendação"
          className="flex min-w-0 flex-col gap-4 lg:col-span-4 lg:sticky lg:top-[76px] lg:self-start"
        >
          <CardDeScore
            avaliacao={avaliacao}
            variacao={variacao}
            aoVerEvidencia={abrirEvidencia}
          />
          <CardDePd pd={avaliacao.pd} />
          <CardDeRiscoRj risco={avaliacao.riscoRJ} />
          <CardDeRecomendacao
            recomendacao={avaliacao.recomendacao}
            narrativa={narrativaDaRecomendacao}
          />
        </aside>
      </div>

      <DrawerDeEvidencia
        evidencia={evidenciaSelecionada(indiceDeEvidencias, evidenciaAberta)}
        indiceDeFatores={indiceDeFatores}
        aoFechar={() => setEvidenciaAberta(null)}
        aoSelecionarFator={selecionarFator}
      />
      <DrawerDeFator
        entrada={fatorAberto ? (indiceDeFatores.get(fatorAberto) ?? null) : null}
        evidencias={indiceDeEvidencias}
        aoFechar={() => setFatorAberto(null)}
        aoAbrirEvidencia={abrirEvidencia}
      />
    </div>
  );
}

/**
 * Único controle de expansão da página.
 *
 * No resumo ele carrega a legenda do que revela — um "ver mais" sem promessa faz o analista
 * clicar às cegas ou, pior, desconfiar que o dado que procura não existe.
 */
function BotaoDeAprofundamento({
  completo,
  aoAlternar,
}: {
  completo: boolean;
  aoAlternar: () => void;
}) {
  return (
    <div className="flex flex-col items-stretch gap-1.5">
      <Button
        variante={completo ? 'secundario' : 'primario'}
        larguraTotal
        iconeDireita={completo ? ChevronUp : ChevronDown}
        aria-expanded={completo}
        aria-controls={ID_ANALISE_COMPLETA}
        onClick={aoAlternar}
      >
        {completo ? 'Ver menos' : 'Ver análise completa'}
      </Button>
      {completo ? null : (
        <p className="type-caption text-center">
          Decomposição por dimensão, exposição e garantias, linha do tempo e registro da decisão.
        </p>
      )}
    </div>
  );
}

function evidenciaSelecionada(
  indice: Map<string, Evidencia>,
  id: string | null,
): Evidencia | null {
  return id ? (indice.get(id) ?? null) : null;
}

/**
 * Esqueleto com a **forma real** do conteúdo (§9.1): mesma grade, mesmas alturas, mesma ordem.
 * Um spinner de página inteira esconderia o layout e faria a tela saltar quando os dados
 * chegassem.
 *
 * A forma imitada é a do **modo resumo**, que é o que aparece primeiro: coluna principal curta,
 * com o botão de aprofundamento ao pé, e lateral cheia.
 */
function EsqueletoDaPagina() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Carregando avaliação">
      <div className="flex flex-col gap-2 border-b border-line-subtle pb-4">
        <span className="esqueleto h-7 w-[340px]" />
        <span className="esqueleto h-4 w-[420px]" />
        <span className="esqueleto h-3 w-[300px]" />
      </div>
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="flex flex-col gap-4 lg:col-span-8">
          {[180, 260].map((altura, indice) => (
            <Card key={indice}>
              <span className="esqueleto block" style={{ height: altura }} />
            </Card>
          ))}
          <span className="esqueleto h-[var(--height-control)] w-full" />
        </div>
        <div className="flex flex-col gap-4 lg:col-span-4">
          {[240, 160, 200, 220].map((altura, indice) => (
            <Card key={indice}>
              <span className="esqueleto block" style={{ height: altura }} />
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Blocos que só existem no modo completo — uma âncora para qualquer um deles precisa expandir a
 * página antes de tentar rolar. `red-flags` entra na lista porque no resumo o card some quando
 * não há red flag: o modo completo é a única garantia de que o alvo do link existe.
 */
const BLOCOS_DO_MODO_COMPLETO = new Set([
  'dimensoes',
  'red-flags',
  'exposicao',
  'timeline',
  'decisao',
]);

/**
 * Âncoras de URL (`#por-que`, `#exposicao`, …): expande a página se preciso, rola até o bloco e
 * o destaca por 2s.
 *
 * São dois efeitos porque a ordem importa: o **modo** é decidido primeiro; o destaque só
 * consegue encontrar o alvo na renderização seguinte, quando o bloco já está montado — daí a
 * dependência em `modo` e o `ref` que garante que o realce aconteça uma única vez.
 *
 * O `scroll-margin-top` fica no próprio card; aqui só se cuida do realce, porque um link
 * externo que cai no meio de uma página longa precisa dizer onde exatamente parou.
 */
function useAncoraDeBloco(
  pronto: boolean,
  modo: ModoDaPagina,
  aoExigirModoCompleto: () => void,
): void {
  const destacado = useRef(false);

  useEffect(() => {
    if (!pronto || typeof window === 'undefined') return;
    const id = window.location.hash.slice(1);
    if (id && BLOCOS_DO_MODO_COMPLETO.has(id)) aoExigirModoCompleto();
  }, [pronto, aoExigirModoCompleto]);

  useEffect(() => {
    if (!pronto || destacado.current || typeof window === 'undefined') return;
    const id = window.location.hash.slice(1);
    if (!id) return;
    const alvo = document.getElementById(id);
    // Ainda não montado: o efeito roda de novo assim que `modo` vira 'completo'.
    if (!alvo) return;
    destacado.current = true;
    alvo.scrollIntoView({ block: 'start' });
    alvo.classList.add('ring-2', 'ring-accent-400');
    const relogio = window.setTimeout(
      () => alvo.classList.remove('ring-2', 'ring-accent-400'),
      2000,
    );
    return () => window.clearTimeout(relogio);
  }, [pronto, modo]);
}
