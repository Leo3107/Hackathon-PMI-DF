import { User } from "lucide-react";

/* ------------------------------------------------------------------------ */
/* Elementos gráficos obrigatórios do Canvas (spec 07 §1.4.3)                 */
/* Todos dimensionados em `em`, para escalarem junto com a folha e com o      */
/* modo de leitura ampliada.                                                  */
/* ------------------------------------------------------------------------ */

/** 1 · Bloco 3 — cadeia de 5 pastilhas com setas. */
export function CadeiaDeAgentes() {
  return (
    <div className="canvas-cadeia" aria-label="Cadeia de agentes do pipeline">
      <div className="canvas-pastilha canvas-pastilha--ml">
        Coletor &amp; Parser<small>ML</small>
      </div>
      <span className="canvas-seta" aria-hidden="true">
        →
      </span>
      <div className="canvas-pastilha canvas-pastilha--ml">
        Risco Agro &amp; Climático<small>ML</small>
      </div>
      <span className="canvas-seta" aria-hidden="true">
        →
      </span>
      <div className="canvas-pastilha canvas-pastilha--ml">
        Motor de Decisão &amp; Scoring<small>ML</small>
      </div>
      <span className="canvas-seta" aria-hidden="true">
        →
      </span>
      <div className="canvas-pastilha canvas-pastilha--llm">
        Sintetizador<small>linguagem</small>
      </div>
      <span className="canvas-seta" aria-hidden="true">
        →
      </span>
      <div className="canvas-pastilha canvas-pastilha--humano">
        <span
          style={{ display: "inline-flex", justifyContent: "center" }}
          aria-hidden="true"
        >
          <User size="1.1em" strokeWidth={2.2} />
        </span>
        Analista<small>decide</small>
      </div>
    </div>
  );
}

const FAIXAS_RATING = [
  { rating: "A", faixa: "750–1000", cor: "var(--color-risk-a)" },
  { rating: "B", faixa: "600–749", cor: "var(--color-risk-b)" },
  { rating: "C", faixa: "400–599", cor: "var(--color-risk-c)" },
  { rating: "D", faixa: "0–399", cor: "var(--color-risk-d)" },
];

/** 2a · Bloco 4 — barra segmentada A/B/C/D com as faixas dentro. */
export function BarraDeRatings() {
  return (
    <div className="canvas-barra-rating" aria-label="Faixas de rating">
      {FAIXAS_RATING.map((f) => (
        <div
          key={f.rating}
          className="canvas-segmento"
          style={{ background: f.cor, flex: "1 1 0" }}
        >
          {f.rating} · {f.faixa}
        </div>
      ))}
    </div>
  );
}

const PESOS = [
  { rotulo: "Comportamental", pct: 22 },
  { rotulo: "Jurídico", pct: 20 },
  { rotulo: "Agro & clima", pct: 15 },
  { rotulo: "Fiscal", pct: 14 },
  { rotulo: "Cadastral", pct: 10 },
  { rotulo: "Garantias", pct: 10 },
  { rotulo: "Ambiental", pct: 9 },
];

/** 2b · Bloco 4 — barra proporcional de pesos das 7 dimensões. */
export function BarraDePesos() {
  return (
    <div className="canvas-barra-pesos" aria-label="Pesos das sete dimensões">
      {PESOS.map((p) => (
        <div key={p.rotulo} className="canvas-peso" style={{ flex: `${p.pct} 1 0` }}>
          <strong>{p.pct}%</strong>
          <br />
          {p.rotulo}
        </div>
      ))}
    </div>
  );
}

const SEVERIDADES = [
  {
    simbolo: "▲",
    rotulo: "CRÍTICA",
    cor: "var(--color-risk-d)",
    tint: "var(--color-risk-d-tint)",
    texto:
      "veto imediato: RJ ajuizada ou deferida · pedido de falência · embargo do IBAMA sobre bem dado em garantia · inclusão na lista suja (trabalho análogo ao escravo) · fraude confirmada.",
  },
  {
    simbolo: "!",
    rotulo: "ALTA",
    cor: "var(--color-risk-c)",
    tint: "var(--color-risk-c-tint)",
    texto:
      "agir em até 7 dias: ≥ 2 execuções de título em 90 dias · protestos recorrentes (≥ 3 em 12 meses) · dívida ativa PGFN crescente · covenant contratual rompido (inadimplência técnica) · queda de score > 80 pontos em 90 dias · CNDT positiva.",
  },
  {
    simbolo: "●",
    rotulo: "MÉDIA",
    cor: "var(--color-risk-b)",
    tint: "var(--color-risk-b-tint)",
    texto:
      "revisar em 30 dias: alteração societária relevante · saída de sócio majoritário · ZARC elevado para alto/crítico · quebra de safra regional > 20% · certidão vencida · endividamento crescente · CAR irregular.",
  },
  {
    simbolo: "i",
    rotulo: "BAIXA / INFORMATIVA",
    cor: "var(--color-risk-neutral)",
    tint: "var(--color-risk-neutral-tint)",
    texto:
      "alteração de endereço ou CNAE · nova filial · atualização cadastral · variação climática dentro do esperado.",
  },
];

/** 3 · Bloco 5 — quatro faixas empilhadas de severidade. */
export function FaixasDeRedFlags() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.3em" }}>
      {SEVERIDADES.map((s) => (
        <div
          key={s.rotulo}
          className="canvas-faixa-severidade"
          style={{ color: s.cor, background: s.tint }}
        >
          <span aria-hidden="true">{s.simbolo}</span>
          <span style={{ color: "inherit" }}>
            <strong style={{ color: "inherit" }}>{s.rotulo}</strong>
            <span style={{ color: "var(--color-fg-secondary)" }}> — {s.texto}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

const DEGRAUS = [
  { rotulo: "APROVAR", cor: "var(--color-risk-a)" },
  { rotulo: "APROVAR COM REVISÃO DE LIMITE", cor: "var(--color-risk-a)" },
  { rotulo: "APROVAR COM MONITORAMENTO INTENSIVO", cor: "var(--color-risk-b)" },
  { rotulo: "APROVAR COM RESTRIÇÕES", cor: "var(--color-risk-c)" },
  { rotulo: "SUSPENDER NOVA EXPOSIÇÃO A PRAZO", cor: "var(--color-risk-d)" },
  { rotulo: "SUSPENDER EXPOSIÇÃO", cor: "var(--color-risk-d)" },
];

/** 4 · Bloco 6 — seis degraus da recomendação, verde → vermelho. */
export function DegrausDaRecomendacao() {
  return (
    <div className="canvas-degraus" aria-label="Escala de recomendação">
      {DEGRAUS.map((d, i) => (
        <div
          key={d.rotulo}
          className="canvas-degrau"
          style={{
            background: d.cor,
            paddingTop: `${0.3 + i * 0.16}em`,
            opacity: i === 1 ? 0.86 : 1,
          }}
        >
          {d.rotulo}
        </div>
      ))}
    </div>
  );
}

const CASCATA = [
  { rotulo: "2 novas execuções de título", pontos: -42 },
  { rotulo: "nova inscrição em dívida ativa", pontos: -31 },
  { rotulo: "deterioração climática regional", pontos: -18 },
  { rotulo: "atraso médio (3 d → 11 d)", pontos: -17 },
];

/** 5 · Bloco 7 — 712 → 604 (−108) como mini-cascata de 4 barras. */
export function CascataDoRecalculo() {
  const maior = Math.max(...CASCATA.map((c) => Math.abs(c.pontos)));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.35em" }}>
      <div className="canvas-delta-grande">712 → 604 (−108)</div>
      <div className="canvas-cascata">
        {CASCATA.map((c) => (
          <div key={c.rotulo} className="canvas-cascata-barra">
            <span>
              <strong style={{ color: "var(--color-risk-c)" }}>{c.pontos}</strong>
            </span>
            <i style={{ height: `${(Math.abs(c.pontos) / maior) * 62}%` }} />
            <span>{c.rotulo}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** 6 · Bloco 8 — dois números grandes com o “×1,8” entre eles. */
export function NumerosDoRetorno() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "0.5em",
        padding: "0.4em 0.6em",
        border: "0.25pt solid var(--color-line-default)",
        borderRadius: "0.3em",
        background: "var(--color-surface-card)",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div className="canvas-numero-grande">R$ 555 mil/ano</div>
        <div style={{ color: "var(--color-fg-tertiary)" }}>custo de operação</div>
      </div>
      <div className="canvas-multiplicador">×1,8</div>
      <div style={{ textAlign: "center" }}>
        <div className="canvas-numero-grande">≈ R$ 1 mi por RJ antecipada</div>
        <div style={{ color: "var(--color-fg-tertiary)" }}>perda evitada</div>
      </div>
    </div>
  );
}

const MARCOS = [
  { horizonte: "Fase 0 · hoje", rotulo: "Hackathon" },
  { horizonte: "Fase 1 · 0–3 m", rotulo: "Piloto" },
  { horizonte: "Fase 2 · 3–6 m", rotulo: "Produção" },
  { horizonte: "Fase 3 · 6–12 m", rotulo: "Escala" },
  { horizonte: "Fase 4 · 12+ m", rotulo: "Rede" },
];

/** 7 · Bloco 10 — linha do tempo com 5 marcos. */
export function LinhaDoTempo() {
  return (
    <div className="canvas-timeline" aria-label="Linha do tempo dos próximos passos">
      {MARCOS.map((m) => (
        <div key={m.rotulo} className="canvas-marco">
          <div style={{ fontWeight: 700, color: "var(--color-fg-primary)" }}>{m.rotulo}</div>
          <div style={{ color: "var(--color-fg-tertiary)" }}>{m.horizonte}</div>
        </div>
      ))}
    </div>
  );
}
