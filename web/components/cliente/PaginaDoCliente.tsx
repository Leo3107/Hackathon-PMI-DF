'use client';

/**
 * Página do cliente — orquestração dos doze blocos (`03-ux-e-telas.md` §4).
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
 * ## Números antes da prosa
 *
 * Uma única rodada de `fetch` traz tudo o que é número. Os dois blocos de prosa (a análise do
 * score e a justificativa da recomendação) abrem streams próprios e **só depois** que os números
 * chegaram. Falha de LLM degrada apenas o parágrafo; falha do motor derruba a tela inteira com
 * `ErrorState`, porque sem motor não existe número nenhum para mostrar.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import { useClientes, useSessaoParaApi } from '@/components/shell';
import { Card, ErrorState } from '@/components/ui';
import type { Evidencia } from '@/types';

import { BlocoDimensoes, BlocoOQueMudou, BlocoPorQue, BlocoRedFlags } from './Analise';
import { BandaDeVeto, CabecalhoDoCliente, PainelStayPeriod } from './Cabecalho';
import { BlocoCopiloto } from './Copiloto';
import { BlocoDecisao } from './Decisao';
import { BlocoEvidencias, DrawerDeEvidencia, DrawerDeFator } from './Evidencias';
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
  useCopiloto,
  useDossie,
  useIndiceDeEvidencias,
  useIndiceDeFatores,
  useNarrativa,
} from './dados';

export interface PaginaDoClienteProps {
  clienteId: string;
}

export function PaginaDoCliente({ clienteId }: PaginaDoClienteProps) {
  const sessao = useSessaoParaApi(clienteId);
  const dossie = useDossie(clienteId, sessao);
  const clientes = useClientes();

  const [evidenciaAberta, setEvidenciaAberta] = useState<string | null>(null);
  const [fatorAberto, setFatorAberto] = useState<string | null>(null);

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
  const copiloto = useCopiloto(clienteId, sessao);

  const abrirEvidencia = useCallback((id: string) => {
    setFatorAberto(null);
    setEvidenciaAberta(id);
  }, []);

  const selecionarFator = useCallback((id: string) => {
    setEvidenciaAberta(null);
    setFatorAberto(id);
  }, []);

  useDestaqueDeAncora(pronto);

  /* --- Estados de exceção ------------------------------------------- */

  if (dossie.naoEncontrado) {
    return (
      <ErrorState
        titulo="Cliente não encontrado"
        detalhe={`Nenhum cliente com o identificador "${clienteId}" na base demonstrativa. Verifique o endereço ou volte para a lista.`}
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

  return (
    <div className="flex flex-col gap-4">
      {/* 1 — cabeçalho (12 col) */}
      <CabecalhoDoCliente
        cliente={cliente}
        ultimaVarredura={avaliacao.dataReferencia}
        parecerBloqueado={fechamentoQuebrado}
      />

      {/* 2 — banda de veto (12 col) */}
      {emVeto ? (
        <BandaDeVeto
          vetos={avaliacao.vetosAtivos}
          scoreCalculado={String(avaliacao.scoreCalculado)}
          ratingCalculado={avaliacao.ratingCalculado}
          ratingFinal={avaliacao.ratingFinal}
          aoVerEvidencia={abrirEvidencia}
        />
      ) : null}

      {/* 3 — Stay Period (12 col) */}
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

          {/* 6 — decomposição por dimensão */}
          <BlocoDimensoes
            dimensoes={avaliacao.dimensoes}
            auditoria={avaliacao.auditoria}
            scoreExibido={avaliacao.scoreCalculado}
            aoSelecionarFator={selecionarFator}
          />

          {/* 7 — red flags */}
          <BlocoRedFlags
            redFlags={avaliacao.redFlags}
            dataReferencia={avaliacao.dataReferencia}
            aoVerEvidencia={abrirEvidencia}
            aoSelecionarFator={selecionarFator}
          />

          {/* 8 — exposição e garantias */}
          {daCarteira ? (
            <BlocoExposicao exposicao={avaliacao.exposicao} fatos={dossie.fatos} />
          ) : (
            <Card as="section" className="flex flex-col gap-1">
              <h2 className="type-section-title">Sem exposição atual</h2>
              <p className="type-body text-fg-secondary">
                Este documento não possui operações com a Krill Tech. A avaliação considera apenas
                fontes externas — não há garantia, cobertura nem exposição em cenário de RJ a
                apresentar.
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

          {/* 10 — fontes e evidências */}
          <BlocoEvidencias
            avaliacao={avaliacao}
            indiceDeFatores={indiceDeFatores}
            aoAbrirEvidencia={abrirEvidencia}
            aoSelecionarFator={selecionarFator}
          />

          {/* 11 — copiloto */}
          <BlocoCopiloto copiloto={copiloto} />

          {/* 12 — decisão do analista */}
          <BlocoDecisao cliente={cliente} avaliacao={avaliacao} />
        </div>

        {/* Coluna lateral — 4 col, sticky */}
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
          {[220, 260, 200, 240].map((altura, indice) => (
            <Card key={indice}>
              <span className="esqueleto block" style={{ height: altura }} />
            </Card>
          ))}
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
 * Âncoras de URL (`#por-que`, `#exposicao`, …): rola até o bloco e o destaca por 2s.
 *
 * O `scroll-margin-top` fica no próprio card; aqui só se cuida do realce, porque um link
 * externo que cai no meio de uma página longa precisa dizer onde exatamente parou.
 */
function useDestaqueDeAncora(pronto: boolean): void {
  useEffect(() => {
    if (!pronto || typeof window === 'undefined') return;
    const id = window.location.hash.slice(1);
    if (!id) return;
    const alvo = document.getElementById(id);
    if (!alvo) return;
    alvo.scrollIntoView({ block: 'start' });
    alvo.classList.add('ring-2', 'ring-accent-400');
    const relogio = window.setTimeout(
      () => alvo.classList.remove('ring-2', 'ring-accent-400'),
      2000,
    );
    return () => window.clearTimeout(relogio);
  }, [pronto]);
}
