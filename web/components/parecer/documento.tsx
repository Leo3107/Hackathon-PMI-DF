'use client';

/**
 * `/clientes/[id]/parecer`, o Relatório Padronizado de Risco de Crédito e Alerta Precoce de
 * RJ/Insolvência (`specs/07` Parte 3).
 *
 * ## Paginação
 *
 * O documento é uma sequência de contêineres `.pc-pagina` de altura fixa A4, cada um com o
 * próprio cabeçalho e rodapé. Chromium não expõe contador de página para elemento arbitrário,
 * então `Página X de Y` só funciona se as páginas forem nossas. O alocador mede cada seção no
 * navegador, uma vez, num contêiner invisível da mesma largura, e empacota em ordem: nenhuma
 * seção é dividida, exceto as duas listas fatiáveis (red flags e evidências), que já chegam
 * cortadas em pedaços.
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { ArrowLeft, Printer } from 'lucide-react';

import { PERSONA } from '@/components/shell/persona';
import { decisoesDaSessao } from '@/lib/sessao';
import { useSessao, useSessaoParaApi } from '@/components/shell/usar-sessao';
import { formatarDataHora, formatarDocumento } from '@/lib/format';
import type { RedFlag, RegistroAuditoria } from '@/types';

import {
  registrarExportacao,
  useDossieDoParecer,
  useIdentificador,
  useProsaDoParecer,
} from './dados';
import {
  EVIDENCIAS_POR_PAGINA,
  RED_FLAGS_POR_PAGINA,
  SecaoAuditoria,
  SecaoAviso,
  SecaoEvidencias,
  SecaoExposicao,
  SecaoIdentificacao,
  SecaoMitigadores,
  SecaoPd,
  SecaoRecomendacao,
  SecaoResponsavel,
  SecaoResumo,
  SecaoRiscoRJ,
  SecaoRiscos,
  SecaoScore,
} from './secoes';

const BADGE = 'Dados simulados · protótipo demonstrativo';

const PX_POR_MM = 96 / 25.4;
/** 297 mm menos 22 mm de topo e 20 mm de base. */
/** Dois px de folga absorvem a diferença de arredondamento entre medir e paginar. */
const ALTURA_UTIL_PX = Math.round((297 - 22 - 20) * PX_POR_MM) - 6;
/** O `gap` de 7 mm entre seções conta na conta: ignorá-lo estoura a página por uma seção. */
const ESPACO_ENTRE_SECOES_PX = Math.round(6 * PX_POR_MM);
/** Título formal do documento, presente só na primeira página. */
const TITULO_FORMAL_PX = Math.round(24 * PX_POR_MM);

const ORDEM_SEVERIDADE: Record<string, number> = {
  CRITICA: 0,
  ALTA: 1,
  MEDIA: 2,
  BAIXA: 3,
};

interface Bloco {
  id: string;
  node: ReactNode;
}

export function PaginaDoParecer({ clienteId }: { clienteId: string }) {
  const sessao = useSessaoParaApi(clienteId);
  const { cliente, avaliacao, fatos, carregando, naoEncontrado, erro } = useDossieDoParecer(
    clienteId,
    sessao,
  );
  const identificador = useIdentificador(avaliacao, clienteId);
  const prosa = useProsaDoParecer(clienteId, sessao, avaliacao, cliente, Boolean(avaliacao));

  const [geradoEm] = useState(() => new Date().toISOString());

  // A decisão do analista vive na sessão do navegador (D11.3). Lida pelo store externo, e não
  // por efeito, para o primeiro paint do servidor bater com o do cliente.
  const estadoDaSessao = useSessao();
  const registro = useMemo<RegistroAuditoria | null>(
    () =>
      decisoesDaSessao(estadoDaSessao)
        .filter((d) => d.clienteId === clienteId)
        .sort((a, b) => a.dataHora.localeCompare(b.dataHora))
        .at(-1) ?? null,
    [estadoDaSessao, clienteId],
  );

  const blocos = useMemo<Bloco[]>(() => {
    if (!cliente || !avaliacao) return [];

    const redFlags = [...avaliacao.redFlags].sort(
      (a, b) =>
        (ORDEM_SEVERIDADE[a.severidade] ?? 9) - (ORDEM_SEVERIDADE[b.severidade] ?? 9) ||
        b.impactoEmPontos - a.impactoEmPontos,
    );
    const fatiasDeFlags = fatiar(redFlags, RED_FLAGS_POR_PAGINA);
    const totalEvidencias = Math.max(
      1,
      Math.ceil(avaliacao.evidencias.length / EVIDENCIAS_POR_PAGINA),
    );

    const lista: Bloco[] = [
      { id: 's1', node: <SecaoIdentificacao cliente={cliente} fatos={fatos} /> },
      {
        id: 's2',
        node: (
          <SecaoResponsavel
            avaliacao={avaliacao}
            identificador={identificador}
            geradoEm={formatarDataHora(geradoEm)}
            analista={PERSONA.assinatura}
          />
        ),
      },
      { id: 's3', node: <SecaoScore avaliacao={avaliacao} /> },
      { id: 's4', node: <SecaoPd avaliacao={avaliacao} /> },
      { id: 's5', node: <SecaoRiscoRJ avaliacao={avaliacao} /> },
      { id: 's6', node: <SecaoResumo bloco={prosa.blocos.resumo} /> },
    ];

    fatiasDeFlags.forEach((fatia, i) => {
      lista.push({
        id: `s7-${i}`,
        node: (
          <SecaoRiscos
            redFlags={fatia}
            bloco={i === 0 ? prosa.blocos.riscos : null}
            parte={i + 1}
            total={fatiasDeFlags.length}
          />
        ),
      });
    });

    lista.push({
      id: 's8',
      node: <SecaoMitigadores avaliacao={avaliacao} bloco={prosa.blocos.mitigadores} />,
    });
    lista.push({ id: 's9', node: <SecaoExposicao avaliacao={avaliacao} fatos={fatos} /> });
    lista.push({
      id: 's10',
      node: (
        <SecaoRecomendacao
          avaliacao={avaliacao}
          bloco={prosa.blocos.justificativa}
          registro={registro}
        />
      ),
    });

    for (let i = 0; i < totalEvidencias; i += 1) {
      lista.push({
        id: `s11-${i}`,
        node: (
          <SecaoEvidencias
            avaliacao={avaliacao}
            inicio={i * EVIDENCIAS_POR_PAGINA}
            parte={i + 1}
            total={totalEvidencias}
          />
        ),
      });
    }

    lista.push({ id: 's12', node: <SecaoAuditoria avaliacao={avaliacao} /> });
    lista.push({ id: 's13', node: <SecaoAviso identificador={identificador} /> });
    return lista;
  }, [cliente, avaliacao, fatos, identificador, geradoEm, prosa.blocos, registro]);

  const { paginas, medidor } = usePaginacao(blocos, prosa.prontos);

  const [aguardandoProsa, setAguardandoProsa] = useState(false);

  const imprimir = useCallback(
    () => {
      const anterior = document.title;
      const slug = (cliente?.razaoSocial ?? clienteId)
        .normalize('NFD')
        .replaceAll(/\p{M}/gu, '')
        .replaceAll(/[^a-zA-Z0-9]+/g, '-')
        .replaceAll(/^-|-$/g, '');
      document.title = `Lastro_Parecer_${slug}_${geradoEm.slice(0, 10)}`;
      const restaurar = () => {
        document.title = cliente
          ? `Parecer de Risco - ${cliente.razaoSocial} · Lastro`
          : anterior;
        window.removeEventListener('afterprint', restaurar);
      };
      window.addEventListener('afterprint', restaurar);
      registrarExportacao(identificador);
      // Um quadro de atraso para o alocador fechar `Página X de Y` antes do diálogo abrir.
      window.requestAnimationFrame(() => window.print());
    },
    [cliente, clienteId, geradoEm, identificador],
  );

  /**
   * Botão primário durante o streaming: espera a prosa fechar e só então imprime (§3.9). O
   * prazo é o do próprio acumulador de prosa, que sempre termina, com IA ou com texto padrão,
   * de modo que o clique nunca fica pendurado.
   */
  const exportar = useCallback(() => {
    if (prosa.transmitindo) setAguardandoProsa(true);
    else imprimir();
  }, [prosa.transmitindo, imprimir]);

  const exportarComTextoPadrao = useCallback(() => {
    prosa.usarTextoPadrao();
    setAguardandoProsa(true);
  }, [prosa]);

  useEffect(() => {
    if (!aguardandoProsa || prosa.transmitindo) return;
    // Fora do corpo do efeito: imprimir é efeito colateral de navegador, e o reset do estado
    // acompanha a impressão em vez de disparar uma renderização em cascata.
    const disparo = window.setTimeout(() => {
      setAguardandoProsa(false);
      imprimir();
    }, 0);
    return () => window.clearTimeout(disparo);
  }, [aguardandoProsa, prosa.transmitindo, imprimir]);

  /* Ctrl/Cmd + P na rota passa pela mesma sequência. */
  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'p') {
        evento.preventDefault();
        exportar();
      }
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [exportar]);

  if (carregando) {
    return <Aviso titulo="Montando o parecer" texto="Consultando o motor de risco." />;
  }
  if (naoEncontrado) {
    return (
      <Aviso
        titulo="Cliente não encontrado"
        texto="Não há cliente com este identificador na carteira demonstrativa."
        clienteId={clienteId}
      />
    );
  }
  if (erro || !cliente || !avaliacao) {
    return (
      <Aviso
        titulo="Sem dados para exportar"
        texto={erro ?? 'O motor de risco não devolveu uma avaliação para este cliente.'}
        clienteId={clienteId}
      />
    );
  }

  const total = paginas.length;

  return (
    <div className="pc-raiz">
      <div className="pc-barra no-print">
        <a className="pc-botao" href={`/clientes/${encodeURIComponent(clienteId)}`}>
          <ArrowLeft size={15} aria-hidden="true" /> Voltar ao cliente
        </a>
        <span className="pc-barra-id pc-num">{identificador}</span>
        <span className="pc-barra-estado">
          {prosa.transmitindo
            ? `gerando texto ${prosa.prontos}/4`
            : prosa.semIa
              ? 'texto padrão (sem IA)'
              : 'texto concluído'}
        </span>
        <span className="pc-barra-espaco" />
        {prosa.transmitindo ? (
          <button type="button" className="pc-botao" onClick={exportarComTextoPadrao}>
            Exportar agora com texto padrão
          </button>
        ) : null}
        <button
          type="button"
          className="pc-botao pc-botao--primario"
          onClick={exportar}
        >
          <Printer size={15} aria-hidden="true" />
          {aguardandoProsa ? 'Aguardando o texto...' : 'Exportar relatório'}
        </button>
      </div>

      {medidor}

      <div className="pc-palco">
        {paginas.map((pagina, i) => (
          <article className="pc-pagina" key={i}>
            <header className="pc-cabecalho">
              <div>
                <strong>LASTRO</strong> · Parecer de Risco
                <br />
                <span className="pc-cabecalho-cliente">
                  {cliente.razaoSocial} · {formatarDocumento(cliente.documento)} (simulado)
                </span>
              </div>
              <div className="pc-cabecalho-direita">
                <span className="pc-badge">{BADGE}</span>
                <br />
                <span className="pc-num">{identificador}</span>
              </div>
            </header>

            <span className="pc-marca-dagua" aria-hidden="true">
              SIMULADO
            </span>

            <div className="pc-corpo">
              {i === 0 ? (
                <div className="pc-titulo-formal">
                  <h1>
                    Relatório Padronizado de Risco de Crédito e Alerta Precoce de
                    RJ/Insolvência
                  </h1>
                  <p>
                    Emitido pela plataforma Lastro para a Krill Tech. Os números vêm do motor
                    determinístico; os trechos marcados como texto de IA foram redigidos a partir
                    desses números, sem alterá-los.
                  </p>
                </div>
              ) : null}
              {pagina.map((bloco) => (
                <div key={bloco.id}>{bloco.node}</div>
              ))}
            </div>

            <footer className="pc-rodape">
              <div>
                Gerado em {formatarDataHora(geradoEm)} · Analista responsável:{' '}
                {PERSONA.nome} · Krill Tech
                <br />
                Análise automatizada de apoio à decisão. Avaliação final sob responsabilidade do
                analista responsável.
              </div>
              <div className="pc-num">
                Página {i + 1} de {total}
              </div>
            </footer>
          </article>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Alocador de páginas                                                 */
/* ------------------------------------------------------------------ */

/**
 * Mede cada bloco fora da tela, na largura útil da página, e empacota em ordem. Remede quando
 * a prosa termina de chegar, porque o texto do modelo muda a altura das seções 6, 7, 8 e 10.
 */
function usePaginacao(blocos: Bloco[], versaoDaProsa: number) {
  const medidorRef = useRef<HTMLDivElement>(null);
  const [alturas, setAlturas] = useState<Record<string, number>>({});

  useLayoutEffect(() => {
    const raiz = medidorRef.current;
    if (!raiz) return;
    const proximas: Record<string, number> = {};
    for (const filho of Array.from(raiz.children)) {
      const id = (filho as HTMLElement).dataset.bloco;
      if (id) proximas[id] = (filho as HTMLElement).offsetHeight;
    }
    setAlturas((atual) => (mesmasAlturas(atual, proximas) ? atual : proximas));
  }, [blocos, versaoDaProsa]);

  const paginas = useMemo(() => {
    if (blocos.length === 0) return [];
    const saida: Bloco[][] = [];
    let atual: Bloco[] = [];
    let usado = 0;
    // A primeira página carrega o título formal do documento.
    let teto = ALTURA_UTIL_PX - TITULO_FORMAL_PX - ESPACO_ENTRE_SECOES_PX;

    for (const bloco of blocos) {
      const altura = (alturas[bloco.id] ?? 0) + (atual.length > 0 ? ESPACO_ENTRE_SECOES_PX : 0);
      if (atual.length > 0 && usado + altura > teto) {
        saida.push(atual);
        atual = [];
        usado = alturas[bloco.id] ?? 0;
        teto = ALTURA_UTIL_PX;
        atual.push(bloco);
        continue;
      }
      atual.push(bloco);
      usado += altura;
    }
    if (atual.length > 0) saida.push(atual);
    return saida;
  }, [blocos, alturas]);

  const medidor = (
    <div className="pc-medidor" aria-hidden="true" ref={medidorRef}>
      {blocos.map((bloco) => (
        <div key={bloco.id} data-bloco={bloco.id}>
          {bloco.node}
        </div>
      ))}
    </div>
  );

  return { paginas, medidor };
}

function mesmasAlturas(a: Record<string, number>, b: Record<string, number>): boolean {
  const chavesA = Object.keys(a);
  if (chavesA.length !== Object.keys(b).length) return false;
  return chavesA.every((k) => a[k] === b[k]);
}

function fatiar(flags: RedFlag[], tamanho: number): RedFlag[][] {
  if (flags.length === 0) return [[]];
  const saida: RedFlag[][] = [];
  for (let i = 0; i < flags.length; i += tamanho) saida.push(flags.slice(i, i + tamanho));
  return saida;
}

function Aviso({
  titulo,
  texto,
  clienteId,
}: {
  titulo: string;
  texto: string;
  clienteId?: string;
}) {
  return (
    <div className="pc-raiz pc-raiz--aviso">
      <div className="pc-aviso-caixa">
        <h1>{titulo}</h1>
        <p>{texto}</p>
        {clienteId ? (
          <a className="pc-botao" href={`/clientes/${encodeURIComponent(clienteId)}`}>
            <ArrowLeft size={15} aria-hidden="true" /> Voltar ao cliente
          </a>
        ) : null}
      </div>
    </div>
  );
}
