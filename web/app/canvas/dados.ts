import { headers } from "next/headers";

import {
  INDICADORES_FALLBACK,
  type IndicadoresDaCarteira,
} from "@/components/canvas/tipos";

/**
 * Valores dinâmicos do Canvas (spec 07 §0.3).
 *
 * Única função de busca de dados desta rota. Consulta a carteira pelo proxy do
 * Next (`/api/clientes`), que por sua vez fala com o serviço Flask. Qualquer
 * falha — serviço fora do ar, rota ainda inexistente, JSON em outro formato —
 * cai no fallback textual previsto na spec, sem quebrar a página: o Canvas é o
 * entregável oficial e não pode depender de rede.
 */
export async function obterIndicadoresDaCarteira(): Promise<IndicadoresDaCarteira> {
  const hoje = formatarData(new Date());
  try {
    const resposta = await fetch(`${await origem()}/api/clientes`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    if (!resposta.ok) return { ...INDICADORES_FALLBACK, hoje };
    const corpo: unknown = await resposta.json();
    const itens = extrairItens(corpo);
    if (itens.length === 0) return { ...INDICADORES_FALLBACK, hoje };

    const comRating = itens.filter((i) => typeof i.ratingFinal === "string");
    const comExposicao = itens.filter((i) => typeof i.exposicaoEmRiscoEmRJ === "number");
    const comVetos = itens.filter((i) => Array.isArray(i.vetosAtivos));
    const comEstado = itens.filter((i) => typeof i.estado === "string");

    return {
      total: String(itens.length),
      emCouD:
        comRating.length > 0
          ? String(comRating.filter((i) => i.ratingFinal === "C" || i.ratingFinal === "D").length)
          : INDICADORES_FALLBACK.emCouD,
      exposicaoEmRiscoEmRJ:
        comExposicao.length > 0
          ? formatarCompacto(
              comExposicao.reduce((soma, i) => soma + (i.exposicaoEmRiscoEmRJ ?? 0), 0),
            )
          : INDICADORES_FALLBACK.exposicaoEmRiscoEmRJ,
      comVeto:
        comVetos.length > 0
          ? String(comVetos.filter((i) => (i.vetosAtivos ?? []).length > 0).length)
          : INDICADORES_FALLBACK.comVeto,
      rjEmCurso:
        comEstado.length > 0
          ? String(comEstado.filter((i) => i.estado === "RJ_EM_CURSO").length)
          : INDICADORES_FALLBACK.rjEmCurso,
      hoje,
      degradado:
        comRating.length === 0 ||
        comExposicao.length === 0 ||
        comVetos.length === 0 ||
        comEstado.length === 0,
    };
  } catch {
    return { ...INDICADORES_FALLBACK, hoje };
  }
}

interface ItemDaCarteira {
  ratingFinal?: unknown;
  estado?: unknown;
  exposicaoEmRiscoEmRJ?: number;
  vetosAtivos?: unknown[];
}

function extrairItens(corpo: unknown): ItemDaCarteira[] {
  const bruto = Array.isArray(corpo)
    ? corpo
    : corpo && typeof corpo === "object" && Array.isArray((corpo as { clientes?: unknown }).clientes)
      ? ((corpo as { clientes: unknown[] }).clientes as unknown[])
      : [];
  return bruto.filter((i): i is ItemDaCarteira => Boolean(i) && typeof i === "object");
}

async function origem(): Promise<string> {
  const cabecalhos = await headers();
  const host = cabecalhos.get("x-forwarded-host") ?? cabecalhos.get("host") ?? "localhost:3000";
  const protocolo = cabecalhos.get("x-forwarded-proto") ?? "http";
  return `${protocolo}://${host}`;
}

function formatarData(data: Date): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(data);
}

/** BRL compacto, no formato pedido pela spec: `R$ 7,4 mi`. */
function formatarCompacto(valor: number): string {
  if (valor >= 1_000_000_000) return `R$ ${arredondar(valor / 1_000_000_000)} bi`;
  if (valor >= 1_000_000) return `R$ ${arredondar(valor / 1_000_000)} mi`;
  if (valor >= 1_000) return `R$ ${arredondar(valor / 1_000)} mil`;
  return `R$ ${arredondar(valor)}`;
}

function arredondar(valor: number): string {
  return valor.toFixed(1).replace(".", ",").replace(",0", "");
}
