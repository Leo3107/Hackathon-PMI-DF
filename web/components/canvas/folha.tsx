"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ExternalLink, Presentation, Printer, X } from "lucide-react";

import { BLOCOS } from "@/components/canvas/blocos";
import { Rico } from "@/components/canvas/rico";
import type { IndicadoresDaCarteira } from "@/components/canvas/tipos";

/** 281 mm e 194 mm convertidos a 96 dpi, a folha A4 paisagem menos margens de 8 mm. */
const LARGURA_FOLHA_PX = 1062;
const ALTURA_FOLHA_PX = 733;
const ESCALA_MAXIMA = 1.7;

const BADGE_SIMULADO = "Dados simulados · protótipo demonstrativo";
const TITULO_IMPRESSAO = "Lastro_Project-Canvas_PMI-DF-2026";

export function FolhaCanvas({ indicadores }: { indicadores: IndicadoresDaCarteira }) {
  const [escala, setEscala] = useState(1);
  const [blocoAberto, setBlocoAberto] = useState<number | null>(null);
  const [apresentacao, setApresentacao] = useState(false);
  const raizRef = useRef<HTMLDivElement>(null);
  const palcoRef = useRef<HTMLDivElement>(null);
  const folhaRef = useRef<HTMLElement>(null);

  /*
   * Ajuste de corpo. A folha é uma página só, e é onde a banca lê: bloco com texto cortado é
   * pior do que bloco com texto pequeno. Cada corpo encolhe a própria tipografia, em passos de
   * 3%, até caber na caixa que a grade lhe deu. Quem couber de primeira não é tocado, então os
   * blocos leves continuam no tamanho cheio e só os densos cedem.
   */
  const ajustarCorpos = useCallback(() => {
    const folha = folhaRef.current;
    if (!folha) return;
    for (const corpo of folha.querySelectorAll<HTMLElement>(".canvas-corpo")) {
      corpo.style.fontSize = "";
      const base = Number.parseFloat(window.getComputedStyle(corpo).fontSize);
      if (!Number.isFinite(base) || base <= 0) continue;
      let tamanho = base;
      const minimo = base * 0.62;
      let passos = 0;
      while (corpo.scrollHeight > corpo.clientHeight + 1 && tamanho > minimo && passos < 28) {
        tamanho -= base * 0.03;
        corpo.style.fontSize = `${tamanho}px`;
        passos += 1;
      }
    }
  }, []);

  useLayoutEffect(() => {
    ajustarCorpos();
    const folha = folhaRef.current;
    if (!folha) return;
    const observador = new ResizeObserver(ajustarCorpos);
    observador.observe(folha);
    return () => observador.disconnect();
  }, [ajustarCorpos, indicadores]);

  useEffect(() => {
    if (!document.fonts?.ready) return;
    void document.fonts.ready.then(ajustarCorpos).catch(() => undefined);
  }, [ajustarCorpos]);

  /* Escala da folha: a folha inteira cabe sem rolagem em viewport ≥ 1280 × 720. */
  useLayoutEffect(() => {
    const palco = palcoRef.current;
    if (!palco) return;

    const recalcular = () => {
      const larguraDisponivel = palco.clientWidth;
      const alturaDisponivel = window.innerHeight - palco.getBoundingClientRect().top - 32;
      const proxima = Math.min(
        ESCALA_MAXIMA,
        larguraDisponivel / LARGURA_FOLHA_PX,
        Math.max(0.45, alturaDisponivel / ALTURA_FOLHA_PX),
      );
      setEscala(Number.isFinite(proxima) && proxima > 0 ? proxima : 1);
    };

    recalcular();
    const observador = new ResizeObserver(recalcular);
    observador.observe(palco);
    window.addEventListener("resize", recalcular);
    return () => {
      observador.disconnect();
      window.removeEventListener("resize", recalcular);
    };
  }, []);

  /* Exportação em PDF: nomeia o arquivo e restaura o título depois. */
  const exportarPdf = useCallback(() => {
    const tituloAnterior = document.title;
    document.title = TITULO_IMPRESSAO;
    const restaurar = () => {
      document.title = tituloAnterior;
      window.removeEventListener("afterprint", restaurar);
    };
    window.addEventListener("afterprint", restaurar);
    const imprimir = () => window.print();
    if (document.fonts?.ready) {
      void document.fonts.ready.then(imprimir).catch(imprimir);
    } else {
      imprimir();
    }
  }, []);

  const alternarApresentacao = useCallback(() => {
    const raiz = raizRef.current;
    if (!raiz) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => undefined);
    } else {
      void raiz.requestFullscreen?.().catch(() => undefined);
      setApresentacao(true);
    }
  }, []);

  useEffect(() => {
    const aoMudarTela = () => setApresentacao(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", aoMudarTela);
    return () => document.removeEventListener("fullscreenchange", aoMudarTela);
  }, []);

  /* Atalhos: 1…0 abrem os blocos 1…10, Esc fecha, setas navegam. */
  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.metaKey || evento.ctrlKey || evento.altKey) return;
      if (evento.key === "Escape") {
        if (blocoAberto !== null) {
          evento.preventDefault();
          setBlocoAberto(null);
        }
        return;
      }
      if (/^[0-9]$/.test(evento.key)) {
        const indice = evento.key === "0" ? 9 : Number(evento.key) - 1;
        evento.preventDefault();
        setBlocoAberto(indice);
        return;
      }
      if (blocoAberto === null) return;
      if (evento.key === "ArrowRight") {
        evento.preventDefault();
        setBlocoAberto((atual) => ((atual ?? 0) + 1) % BLOCOS.length);
      }
      if (evento.key === "ArrowLeft") {
        evento.preventDefault();
        setBlocoAberto((atual) => ((atual ?? 0) + BLOCOS.length - 1) % BLOCOS.length);
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [blocoAberto]);

  const bloco = blocoAberto === null ? null : BLOCOS[blocoAberto];

  return (
    <div className="canvas-raiz" ref={raizRef} data-apresentacao={apresentacao ? "true" : "false"}>
      <div className="canvas-toolbar no-print">
        <span style={{ fontWeight: 700, fontSize: 14 }}>Project Canvas</span>
        <span style={{ color: "var(--color-fg-tertiary)", fontSize: 12 }}>
          Entregável oficial · clique em um bloco para ler ampliado · teclas 1…0
        </span>
        <span style={{ flex: 1 }} />
        <button type="button" className="canvas-botao" onClick={alternarApresentacao}>
          <Presentation size={15} aria-hidden="true" /> Modo apresentação
        </button>
        <button type="button" className="canvas-botao canvas-botao--primario" onClick={exportarPdf}>
          <Printer size={15} aria-hidden="true" /> Exportar PDF (A4 paisagem)
        </button>
        <a className="canvas-botao" href="/carteira">
          Abrir protótipo <ExternalLink size={15} aria-hidden="true" />
        </a>
      </div>

      <div
        className="canvas-palco"
        ref={palcoRef}
        style={{ height: `${Math.round(ALTURA_FOLHA_PX * escala) + 32}px` }}
      >
        <div
          className="canvas-escala"
          style={{ "--canvas-escala": escala } as React.CSSProperties}
        >
          <section className="canvas-folha" ref={folhaRef} aria-label="Project Canvas do Lastro">
            <header
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "6mm",
                paddingBottom: "1.4mm",
                borderBottom: "0.3mm solid var(--color-line-default)",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "3mm" }}>
                  <span className="canvas-marca">LASTRO</span>
                  <span className="canvas-subtitulo">
                    Inteligência de risco de crédito e alerta precoce de RJ no agronegócio
                  </span>
                </div>
                <div className="canvas-tagline">Saber antes do calote. Proteger antes da RJ.</div>
                <div className="canvas-contexto">
                  Project Canvas · Hackathon PMI-DF 2026 · Edital 01/2026 · Desafio Krill Tech
                  {indicadores.hoje ? ` · ${indicadores.hoje}` : ""}
                </div>
              </div>
              <span className="canvas-badge-simulado">{BADGE_SIMULADO}</span>
            </header>

            <div className="canvas-grade">
              {BLOCOS.map((b, i) => (
                <div
                  key={b.numero}
                  role="button"
                  tabIndex={0}
                  className={`canvas-bloco${b.denso ? " canvas-bloco--denso" : ""}`}
                  style={{ gridArea: b.area }}
                  onClick={() => setBlocoAberto(i)}
                  onKeyDown={(evento) => {
                    if (evento.key === "Enter" || evento.key === " ") {
                      evento.preventDefault();
                      setBlocoAberto(i);
                    }
                  }}
                  aria-expanded={blocoAberto === i}
                  aria-label={`Bloco ${b.numero}, ${b.titulo}`}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "1.2mm" }}>
                    <span className="canvas-numeral" aria-hidden="true">
                      {b.numero}
                    </span>
                    <span className="canvas-titulo-bloco">{b.titulo}</span>
                  </div>
                  <p className="canvas-manchete">{b.manchete}</p>
                  <b.Corpo ind={indicadores} />
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      {bloco ? (
        <div
          className="canvas-scrim no-print"
          role="dialog"
          aria-modal="true"
          aria-label={`Bloco ${bloco.numero}, ${bloco.titulo}`}
          onClick={() => setBlocoAberto(null)}
        >
          <div className="canvas-leitura" onClick={(evento) => evento.stopPropagation()}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 12,
              }}
            >
              <span className="canvas-numeral" aria-hidden="true">
                {bloco.numero}
              </span>
              <span className="canvas-titulo-bloco">{bloco.titulo}</span>
              <span style={{ flex: 1 }} />
              <span className="canvas-badge-simulado">{BADGE_SIMULADO}</span>
              <button
                type="button"
                className="canvas-botao"
                onClick={() => setBlocoAberto(null)}
                aria-label="Fechar (Esc)"
              >
                <X size={15} aria-hidden="true" />
              </button>
            </div>
            <p className="canvas-manchete" style={{ marginBottom: 14 }}>
              <Rico texto={bloco.manchete} />
            </p>
            <bloco.Corpo ind={indicadores} expandido />
            <p
              style={{
                marginTop: 16,
                fontSize: 12,
                color: "var(--color-fg-tertiary)",
              }}
            >
              Esc fecha · ← → navegam entre os dez blocos
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
