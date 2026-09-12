'use client';

/**
 * Trilho de etapas da aba Arquitetura (`specs/07` §2.4.2).
 *
 * Grid CSS para o layout, um `<svg>` autoral por cima para as setas. Nenhuma biblioteca de
 * diagramação, o requisito é explícito. As coordenadas saem de `getBoundingClientRect()` dos
 * próprios cards depois do layout, recalculadas por `ResizeObserver`: nada fixo em pixel.
 *
 * **Desvio deliberado da spec.** A spec desenha as onze etapas numa única fileira de doze
 * colunas, com a fronteira como faixa vertical de 56 px. Em tela de projeção isso obriga a
 * rolagem horizontal e os cards ficam com 100 px, ilegível justamente no momento em que a
 * banca olha. Aqui a cadeia quebra em duas fileiras e **a fronteira vira a régua horizontal
 * entre elas**, ocupando a largura inteira. A separação entre o que calcula e o que escreve
 * fica mais evidente, não menos: é a linha mais larga da página.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { CornerDownLeft, User } from 'lucide-react';

import { ESTADO_POR_ETAPA, ETAPAS, FRONTEIRA, type Etapa } from './conteudo';

const ANTES = ['1', '2', '3', '4', '5', '6', '7'];
const DEPOIS = ['8', '9', '10', '11'];

const AGENTES_ANTES = [
  { rotulo: 'Agente Coletor & Parser', inicio: 1, fim: 4 },
  { rotulo: 'Risco Agro & Climático', inicio: 4, fim: 5 },
  { rotulo: 'Motor de Decisão & Scoring', inicio: 5, fim: 8 },
];

const AGENTES_DEPOIS = [
  { rotulo: 'Sintetizador & Gerador de Relatórios', inicio: 1, fim: 3 },
  { rotulo: 'Humano no circuito', inicio: 3, fim: 4 },
  { rotulo: 'Coletor + Motor, na revarredura', inicio: 4, fim: 5 },
];

const CAMADAS_ANTES = [
  { rotulo: 'Dados · fontes públicas', simbolo: '◌', classe: 'dados', inicio: 1, fim: 4 },
  { rotulo: 'ML quantitativo · produz número', simbolo: '▰', classe: 'ml', inicio: 4, fim: 8 },
];

const CAMADAS_DEPOIS = [
  { rotulo: 'Linguagem · produz texto', simbolo: '▱', classe: 'llm', inicio: 1, fim: 3 },
  { rotulo: 'Humano', simbolo: '●', classe: 'humano', inicio: 3, fim: 4 },
  { rotulo: 'Loop de monitoramento', simbolo: '↺', classe: 'loop', inicio: 4, fim: 5 },
];

const CLASSE_DE_CAMADA: Record<Etapa['camada'], string> = {
  DADOS: 'arq-card--dados',
  ML: 'arq-card--ml',
  ML_LLM: 'arq-card--ml',
  LLM: 'arq-card--llm',
  HUMANO: 'arq-card--humano',
  LOOP: 'arq-card--loop',
};

const CLASSE_DE_PILULA: Record<Etapa['camada'], string> = {
  DADOS: '',
  ML: ' arq-pilula--camada-ml',
  ML_LLM: ' arq-pilula--camada-ml',
  LLM: ' arq-pilula--camada-llm',
  HUMANO: '',
  LOOP: '',
};

export type Selecao =
  | { tipo: 'etapa'; etapa: Etapa }
  | { tipo: 'fronteira' }
  | { tipo: 'interface' };

interface Segmento {
  x1: number;
  y: number;
  x2: number;
  tracejado: boolean;
}

export function Trilho({
  selecao,
  aoSelecionar,
}: {
  selecao: Selecao | null;
  aoSelecionar: (selecao: Selecao) => void;
}) {
  const quadroRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef(new Map<string, HTMLElement>());
  const [segmentos, setSegmentos] = useState<Segmento[]>([]);
  const [caixa, setCaixa] = useState({ largura: 0, altura: 0 });

  const registrar = useCallback((numero: string, elemento: HTMLElement | null) => {
    if (elemento) cardsRef.current.set(numero, elemento);
    else cardsRef.current.delete(numero);
  }, []);

  const medir = useCallback(() => {
    const quadro = quadroRef.current;
    if (!quadro) return;
    const base = quadro.getBoundingClientRect();
    if (base.width === 0) return;

    const pares: Array<[string, string]> = [];
    for (const fila of [ANTES, DEPOIS]) {
      for (let i = 0; i < fila.length - 1; i += 1) pares.push([fila[i], fila[i + 1]]);
    }

    const proximos: Segmento[] = [];
    for (const [de, para] of pares) {
      const a = cardsRef.current.get(de)?.getBoundingClientRect();
      const b = cardsRef.current.get(para)?.getBoundingClientRect();
      if (!a || !b) continue;
      proximos.push({
        x1: a.right - base.left + 1,
        x2: b.left - base.left - 1,
        y: a.top - base.top + a.height / 2,
        // O único trecho que atravessa a rede pública é desenhado tracejado.
        tracejado: de === '1',
      });
    }

    setSegmentos(proximos);
    setCaixa({ largura: base.width, altura: quadro.scrollHeight });
  }, []);

  useLayoutEffect(() => {
    medir();
    const quadro = quadroRef.current;
    if (!quadro) return;
    const observador = new ResizeObserver(medir);
    observador.observe(quadro);
    for (const elemento of cardsRef.current.values()) observador.observe(elemento);
    window.addEventListener('resize', medir);
    return () => {
      observador.disconnect();
      window.removeEventListener('resize', medir);
    };
  }, [medir]);

  /* Fontes web trocam a métrica depois do primeiro paint e movem os cards. */
  useEffect(() => {
    if (!document.fonts?.ready) return;
    void document.fonts.ready.then(medir).catch(() => undefined);
  }, [medir]);

  const abertoEm = (numero: string) =>
    selecao?.tipo === 'etapa' && selecao.etapa.numero === numero;

  const cardsDe = (numeros: string[]) =>
    numeros.map((n) => {
      const etapa = ETAPAS.find((e) => e.numero === n);
      if (!etapa) return null;
      return etapa.numero === '9' ? (
        <CardBipartido
          key={n}
          etapa={etapa}
          aberto={abertoEm(n)}
          registrar={registrar}
          aoSelecionar={aoSelecionar}
        />
      ) : (
        <CardDeEtapa
          key={n}
          etapa={etapa}
          aberto={abertoEm(n)}
          registrar={registrar}
          aoSelecionar={aoSelecionar}
        />
      );
    });

  const chipsDe = (numeros: string[]) =>
    numeros.map((n) => {
      const etapa = ETAPAS.find((e) => e.numero === n);
      if (!etapa) return null;
      return (
        <a key={n} className="arq-chip-tela" href={etapa.href}>
          {etapa.chipTela}
        </a>
      );
    });

  return (
    <div className="arq-quadro" ref={quadroRef}>
      <Faixa colunas={7} itens={AGENTES_ANTES} />
      <FaixaDeCamada colunas={7} itens={CAMADAS_ANTES} />
      <div className="arq-grade arq-grade--7">{cardsDe(ANTES)}</div>
      <div className="arq-grade arq-grade--7 arq-grade--chips">{chipsDe(ANTES)}</div>

      <button
        type="button"
        className="arq-fronteira"
        aria-expanded={selecao?.tipo === 'fronteira'}
        onClick={() => aoSelecionar({ tipo: 'fronteira' })}
      >
        <span className="arq-fronteira-lado">
          <span aria-hidden="true">↓</span> {FRONTEIRA.acimaDireita}
        </span>
        <span className="arq-fronteira-nome">Fronteira</span>
        <span className="arq-fronteira-lado arq-fronteira-lado--volta">
          {FRONTEIRA.abaixoEsquerda} <span aria-hidden="true">↑</span>
        </span>
      </button>

      <Faixa colunas={4} itens={AGENTES_DEPOIS} />
      <FaixaDeCamada colunas={4} itens={CAMADAS_DEPOIS} />
      <div className="arq-grade arq-grade--4">{cardsDe(DEPOIS)}</div>
      <div className="arq-grade arq-grade--4 arq-grade--chips">{chipsDe(DEPOIS)}</div>

      <p className="arq-loop">
        <CornerDownLeft size={15} aria-hidden="true" />
        Do monitoramento contínuo de volta à coleta: novo evento, revarredura, recálculo, delta
        por fator, alerta.
      </p>

      <button
        type="button"
        className="arq-barra-web"
        aria-expanded={selecao?.tipo === 'interface'}
        onClick={() => aoSelecionar({ tipo: 'interface' })}
      >
        <span className="arq-pilula-servico arq-pilula-servico--ts">TS</span>
        web/ · Next.js · interface e proxy server-side, não recalcula nada
        <span className="arq-seta-proxy">HTTP interno (proxy) para api/</span>
      </button>

      <svg
        className="arq-conectores"
        width={caixa.largura}
        height={caixa.altura}
        viewBox={`0 0 ${caixa.largura || 1} ${caixa.altura || 1}`}
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <marker id="arq-seta" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill="var(--color-fg-tertiary)" />
          </marker>
        </defs>
        {segmentos.map((s, i) => (
          <line
            key={i}
            x1={s.x1}
            y1={s.y}
            x2={s.x2}
            y2={s.y}
            stroke="var(--color-fg-tertiary)"
            strokeWidth={1}
            strokeDasharray={s.tracejado ? '3 3' : undefined}
            markerEnd="url(#arq-seta)"
          />
        ))}
      </svg>
    </div>
  );
}

function Faixa({
  colunas,
  itens,
}: {
  colunas: number;
  itens: Array<{ rotulo: string; inicio: number; fim: number }>;
}) {
  return (
    <div className={`arq-grade arq-grade--${colunas} arq-grade--faixa`} aria-hidden="true">
      {itens.map((a) => (
        <div key={a.rotulo} className="arq-span" style={{ gridColumn: `${a.inicio} / ${a.fim}` }}>
          {a.rotulo}
        </div>
      ))}
    </div>
  );
}

function FaixaDeCamada({
  colunas,
  itens,
}: {
  colunas: number;
  itens: Array<{ rotulo: string; simbolo: string; classe: string; inicio: number; fim: number }>;
}) {
  return (
    <div className={`arq-grade arq-grade--${colunas} arq-grade--faixa`}>
      {itens.map((c) => (
        <div
          key={c.rotulo}
          className={`arq-span arq-span--camada-${c.classe}`}
          style={{ gridColumn: `${c.inicio} / ${c.fim}` }}
        >
          <span aria-hidden="true">{c.simbolo}</span> {c.rotulo}
        </div>
      ))}
    </div>
  );
}

function Estado({ numero }: { numero: string }) {
  const estado = ESTADO_POR_ETAPA[numero];
  if (!estado) return null;
  return (
    <span className={`arq-estado arq-estado--${estado.nivel.toLowerCase()}`}>
      <span aria-hidden="true">{estado.nivel === 'REAL' ? '●' : '◐'}</span>
      {estado.rotulo}
    </span>
  );
}

function CardDeEtapa({
  etapa,
  aberto,
  registrar,
  aoSelecionar,
}: {
  etapa: Etapa;
  aberto: boolean;
  registrar: (numero: string, elemento: HTMLElement | null) => void;
  aoSelecionar: (selecao: Selecao) => void;
}) {
  return (
    <button
      type="button"
      className={`arq-card ${CLASSE_DE_CAMADA[etapa.camada]}`}
      ref={(el) => registrar(etapa.numero, el)}
      aria-expanded={aberto}
      onClick={() => aoSelecionar({ tipo: 'etapa', etapa })}
    >
      <span className="arq-card-topo">
        <span className="arq-card-numero">{etapa.numero}</span>
        {etapa.camada === 'HUMANO' ? (
          <span className="arq-avatar" aria-hidden="true">
            <User size={13} strokeWidth={2.2} />
          </span>
        ) : null}
        <span
          className={`arq-pilula-servico${etapa.servico === 'TS' ? ' arq-pilula-servico--ts' : ''}`}
        >
          {etapa.servico === 'PY_TS' ? 'PY+TS' : etapa.servico}
        </span>
      </span>
      <span className="arq-card-nome">{etapa.nome}</span>
      <span className={`arq-pilula${CLASSE_DE_PILULA[etapa.camada]}`}>{etapa.camadaRotulo}</span>
      <span className="arq-card-fluxo">{etapa.entradaSaida}</span>
      <span className="arq-card-rodape">
        <Estado numero={etapa.numero} />
      </span>
    </button>
  );
}

/** Card 9: a regra decide de um lado, o modelo de linguagem redige do outro. */
function CardBipartido({
  etapa,
  aberto,
  registrar,
  aoSelecionar,
}: {
  etapa: Etapa;
  aberto: boolean;
  registrar: (numero: string, elemento: HTMLElement | null) => void;
  aoSelecionar: (selecao: Selecao) => void;
}) {
  return (
    <button
      type="button"
      className="arq-card arq-card--bipartido"
      ref={(el) => registrar(etapa.numero, el)}
      aria-expanded={aberto}
      aria-label="Etapa 9, Recomendação: a regra decide, o modelo de linguagem redige"
      onClick={() => aoSelecionar({ tipo: 'etapa', etapa })}
    >
      <span className="arq-meia arq-meia--regra">
        <span className="arq-card-numero">9</span>
        <span className="arq-card-nome">Recomendação</span>
        <span className="arq-meia-rotulo">A regra decide</span>
        <span className="arq-card-fluxo">
          Código da recomendação e ações parametrizadas com os números do cliente
        </span>
      </span>
      <span className="arq-meia arq-meia--llm">
        <span className="arq-meia-rotulo">A linguagem redige</span>
        <span className="arq-card-fluxo">
          Justificativa em texto, sem tocar em nenhum número
        </span>
      </span>
    </button>
  );
}
