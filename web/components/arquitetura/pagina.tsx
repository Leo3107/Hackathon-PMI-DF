'use client';

/**
 * `/arquitetura`, o pipeline da solução, e a prova de que ele está em execução.
 *
 * Duas coisas precisam ficar inequívocas em uma tela:
 *
 * 1. **ML quantitativo e modelo de linguagem são camadas distintas**, com uma fronteira
 *    desenhada entre elas. Números saem do motor; texto sai da linguagem; o LLM nunca inventa
 *    score. A distinção não é só de cor: tem faixa rotulada, borda diferente, pictograma e
 *    texto no próprio card.
 * 2. **Qual etapa roda de verdade hoje e qual é conceitual.** A camada de coleta deixou de ser
 *    contrato: `coleta/` consulta sete fontes públicas e grava num warehouse DuckDB, e
 *    `api/adaptadores/` liga essa coleta ao motor. A página diz isso etapa a etapa, em vez de
 *    deixar o jurado supor.
 */

import { useCallback, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

import {
  COLETA_REAL,
  ESTADO_POR_ETAPA,
  ETAPA_INTERFACE,
  EXECUCAO,
  FONTES,
  FONTE_EXTRA_BCB,
  FRASE_ENCERRAMENTO,
  FRONTEIRA,
  LEGENDA,
  NOTA_COBERTURA,
  NOTA_FIXA,
  RODAPE_FONTES_ATUAL,
  TEXTO_PAINEL_FONTES,
  TEXTO_PAINEL_LLM,
  TEXTO_PAINEL_ML,
} from './conteudo';
import { Trilho, type Selecao } from './diagrama';

interface Saude {
  estado: 'consultando' | 'ok' | 'fora';
  ms?: number;
}

export function PaginaDaArquitetura({ totalDeClientes }: { totalDeClientes: number }) {
  const [selecao, setSelecao] = useState<Selecao | null>(null);
  const saude = useSaudeDoMotor();

  const aoSelecionar = useCallback((proxima: Selecao) => {
    setSelecao((atual) => {
      if (atual?.tipo === 'etapa' && proxima.tipo === 'etapa') {
        return atual.etapa.numero === proxima.etapa.numero ? null : proxima;
      }
      return atual?.tipo === proxima.tipo ? null : proxima;
    });
  }, []);

  // As sete fontes reais: as seis do mapa original mais a Matriz de Dados do Crédito Rural.
  const reais = COLETA_REAL.length + 1;

  return (
    <div className="arq-raiz">
      <div className="arq-largura">
        <header>
          <h1 className="arq-titulo">Arquitetura da solução</h1>
          <p className="arq-subtitulo">
            Pipeline de referência do desafio (§6), implementação própria da equipe, e é isto
            que está rodando agora. O motor calcula; o modelo de linguagem só escreve sobre o
            que o motor já calculou.
          </p>

          <div className="arq-faixa-estado">
            <span className="arq-pastilha-fato">
              <strong>{reais} fontes públicas</strong> consultadas de verdade
            </span>
            <span className="arq-pastilha-fato">
              <strong>14 fontes</strong> mapeadas
            </span>
            <span className="arq-pastilha-fato">
              <strong>{totalDeClientes}</strong> clientes simulados na carteira
            </span>
            <PastilhaDeSaude saude={saude} />
          </div>

          <div className="arq-nota-fixa">
            <strong>{NOTA_FIXA.titulo}</strong> {NOTA_FIXA.corpo}
          </div>
        </header>

        <div className="arq-cabecalho-diagrama">
          <h2 className="arq-secao-titulo">Da fonte pública à decisão do analista</h2>
          <div className="arq-legenda">
            {LEGENDA.map((item) => (
              <div key={item.titulo} className={`arq-legenda-item ${item.classe}`}>
                <span aria-hidden="true">{item.simbolo}</span>
                <span>
                  <strong>{item.titulo}</strong>, {item.texto}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="arq-diagrama">
          <div className="arq-rolagem">
            <Trilho selecao={selecao} aoSelecionar={aoSelecionar} />
          </div>
          <Painel selecao={selecao} />
        </div>

        <section className="arq-secao">
          <h2 className="arq-secao-titulo">
            De onde vêm os fatos, e o que cada fonte move no score
          </h2>
          <p className="arq-secao-apoio">
            Sete destas fontes já são baixadas e versionadas num warehouse próprio. As demais
            continuam sendo contrato. Cada card diz de qual das duas se trata.
          </p>

          <div className="arq-grade-fontes">
            {FONTES.map((fonte, i) => {
              const real = COLETA_REAL.find((c) => c.fonteId === fonte.id && !fonte.semIdProprio);
              return (
                <article
                  key={`${fonte.id}-${i}`}
                  className={`arq-card-fonte${real ? ' arq-card-fonte--real' : ''}`}
                >
                  <span className={real ? 'arq-badge-real' : 'arq-badge-simulado'}>
                    {real ? 'Coletada' : 'Sem integração'}
                  </span>
                  <h3>{fonte.nome}</h3>
                  <p className="arq-fonte-fornece">{fonte.fornece}</p>
                  {real ? (
                    <p className="arq-fonte-real">
                      {real.comoEColetada} <span className="arq-mono">{real.modulo}</span>
                    </p>
                  ) : null}
                  <dl>
                    <dt>Alimenta</dt>
                    <dd>{fonte.dimensaoScore}</dd>
                    <dt>Fatores que move</dt>
                    <dd className="arq-mono">{fonte.fatores}</dd>
                  </dl>
                </article>
              );
            })}

            <article className="arq-card-fonte arq-card-fonte--real">
              <span className="arq-badge-real">Coletada</span>
              <h3>{FONTE_EXTRA_BCB.nome}</h3>
              <p className="arq-fonte-fornece">{FONTE_EXTRA_BCB.papel}</p>
              <p className="arq-fonte-real">
                <span className="arq-mono">{FONTE_EXTRA_BCB.modulo}</span>
              </p>
            </article>
          </div>

          <div className="arq-rodape-secao">{RODAPE_FONTES_ATUAL}</div>

          <div className="arq-nota-fixa">
            <strong>{NOTA_COBERTURA.titulo}</strong> {NOTA_COBERTURA.corpo}
          </div>
        </section>

        <section className="arq-secao">
          <h2 className="arq-secao-titulo">O que está em execução agora</h2>
          <table className="arq-tabela">
            <thead>
              <tr>
                <th scope="col">Componente</th>
                <th scope="col">Estado nesta versão</th>
                <th scope="col">Como o jurado confere</th>
              </tr>
            </thead>
            <tbody>
              {EXECUCAO.map((linha) => (
                <tr key={linha.componente}>
                  <th scope="row">
                    {linha.componente}
                    <br />
                    <span className="arq-mono">{linha.caminho}</span>
                  </th>
                  <td>
                    <span
                      className={
                        linha.estadoRotulo === 'Real.'
                          ? 'arq-estado-real'
                          : 'arq-estado-parcial'
                      }
                    >
                      {linha.estadoRotulo.replace('.', '')}
                    </span>{' '}
                    {linha.estado}
                  </td>
                  <td>{linha.comoConfere}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p className="arq-encerramento">{FRASE_ENCERRAMENTO}</p>
        </section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Pastilha viva, prova, em tela, que o motor é um processo real       */
/* ------------------------------------------------------------------ */

/**
 * Consulta `GET /api/saude` pelo proxy do Next e cronometra a resposta. Degrada em silêncio:
 * o motor fora do ar vira um rótulo cinza com ícone, nunca um erro na página.
 */
function useSaudeDoMotor(): Saude {
  const [saude, setSaude] = useState<Saude>({ estado: 'consultando' });

  useEffect(() => {
    const controle = new AbortController();
    const inicio = performance.now();
    void fetch('/api/saude', { cache: 'no-store', signal: controle.signal })
      .then((resposta) => {
        if (!resposta.ok) throw new Error('sem saúde');
        return resposta.json();
      })
      .then(() => {
        setSaude({ estado: 'ok', ms: Math.round(performance.now() - inicio) });
      })
      .catch(() => {
        if (!controle.signal.aborted) setSaude({ estado: 'fora' });
      });
    return () => controle.abort();
  }, []);

  return saude;
}

function PastilhaDeSaude({ saude }: { saude: Saude }) {
  if (saude.estado === 'ok') {
    return (
      <span className="arq-pastilha-fato arq-pastilha-fato--viva">
        <span aria-hidden="true">●</span> 2 serviços em execução ·{' '}
        <strong>Flask, Python 3.13, respondeu em {saude.ms} ms</strong>
      </span>
    );
  }
  if (saude.estado === 'fora') {
    return (
      <span className="arq-pastilha-fato arq-pastilha-fato--indisponivel">
        <AlertTriangle size={13} aria-hidden="true" /> Flask indisponível
      </span>
    );
  }
  return (
    <span className="arq-pastilha-fato arq-pastilha-fato--indisponivel">
      Consultando o motor...
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Painel lateral                                                      */
/* ------------------------------------------------------------------ */

/** Par rótulo/valor do painel. Cada par vive num `div` para o grid não desencontrá-los. */
function Ficha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="arq-ficha">
      <dt>{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Painel({ selecao }: { selecao: Selecao | null }) {
  if (selecao === null) {
    return (
      <aside className="arq-painel arq-painel--vazio">
        <p>
          Clique em qualquer etapa do trilho para ver o que entra, o que sai, em qual serviço o
          código roda e onde aquilo aparece no produto.
        </p>
        <p>
          A régua hachurada entre as duas fileiras é a fronteira entre o que calcula e o que
          escreve. Ela também abre.
        </p>
      </aside>
    );
  }

  if (selecao.tipo === 'fronteira') {
    return (
      <aside className="arq-painel">
        <h3 className="arq-painel-titulo">{FRONTEIRA.nome}</h3>
        <p className="arq-painel-regra">{FRONTEIRA.regra}</p>
        <dl>
          <Ficha rotulo="Executa em">{FRONTEIRA.servicoTexto}</Ficha>
          <Ficha rotulo="Onde aparece">{FRONTEIRA.ondeAparece}</Ficha>
        </dl>
      </aside>
    );
  }

  if (selecao.tipo === 'interface') {
    return (
      <aside className="arq-painel">
        <h3 className="arq-painel-titulo">{ETAPA_INTERFACE.nome}</h3>
        <dl>
          <Ficha rotulo="Camada">{ETAPA_INTERFACE.camadaRotulo}</Ficha>
          <Ficha rotulo="Entra e sai">{ETAPA_INTERFACE.entradaSaida}</Ficha>
          <Ficha rotulo="Executa em">{ETAPA_INTERFACE.servicoTexto}</Ficha>
          <Ficha rotulo="Onde aparece">{ETAPA_INTERFACE.ondeAparece}</Ficha>
        </dl>
      </aside>
    );
  }

  const { etapa } = selecao;
  const estado = ESTADO_POR_ETAPA[etapa.numero];
  const temMl = etapa.camada === 'ML' || etapa.camada === 'ML_LLM';
  const temLlm = etapa.camada === 'LLM' || etapa.camada === 'ML_LLM';

  return (
    <aside className="arq-painel">
      <h3 className="arq-painel-titulo">
        <span className="arq-card-numero">{etapa.numero}</span> {etapa.nome}
      </h3>

      {estado ? (
        <p className={`arq-estado arq-estado--${estado.nivel.toLowerCase()} arq-estado--bloco`}>
          <span aria-hidden="true">{estado.nivel === 'REAL' ? '●' : '◐'}</span>
          {estado.rotulo}
        </p>
      ) : null}
      {estado ? <p className="arq-painel-nota">{estado.nota}</p> : null}

      <dl>
        <Ficha rotulo="Agente de referência">{etapa.agente}</Ficha>
        <Ficha rotulo="Camada">{etapa.camadaRotulo}</Ficha>
        <Ficha rotulo="Entra e sai">{etapa.entradaSaida}</Ficha>
        <Ficha rotulo="Fontes">{etapa.fontes}</Ficha>
        <Ficha rotulo="Executa em">
          {etapa.servico === 'TS'
            ? 'web/ (Next.js, TypeScript)'
            : etapa.servico === 'PY'
              ? 'api/ (Flask, Python 3.13)'
              : 'api/ (Flask, Python 3.13) e web/ (Next.js, TypeScript)'}
        </Ficha>
        <Ficha rotulo="Detalhe de implementação">{etapa.servicoTexto}</Ficha>
        <Ficha rotulo="Onde aparece no produto">
          <a className="arq-painel-link" href={etapa.href}>
            {etapa.ondeAparece}
          </a>
        </Ficha>
      </dl>

      {etapa.numero === '1' ? <p className="arq-painel-nota">{TEXTO_PAINEL_FONTES}</p> : null}

      {temMl ? (
        <div className="arq-painel-camada arq-painel-camada--ml">
          <p>{TEXTO_PAINEL_ML.faz}</p>
          <p>{TEXTO_PAINEL_ML.naoFaz}</p>
        </div>
      ) : null}
      {temLlm ? (
        <div className="arq-painel-camada arq-painel-camada--llm">
          <p>{TEXTO_PAINEL_LLM.faz}</p>
          <p>{TEXTO_PAINEL_LLM.naoFaz}</p>
        </div>
      ) : null}
    </aside>
  );
}
