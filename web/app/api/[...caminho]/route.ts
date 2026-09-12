/**
 * Proxy genérico para o Flask — `/api/<qualquer coisa>` → `http://127.0.0.1:5001/api/<mesma coisa>`.
 *
 * Cobre **todas** as rotas de dados do motor com um mapeamento 1:1 de caminho:
 *
 * | Rota no Next (browser) | Rota no Flask |
 * |---|---|
 * | `POST /api/carteira` | `POST /api/carteira` |
 * | `POST /api/clientes` | `POST /api/clientes` |
 * | `GET  /api/clientes/:id` | `GET  /api/clientes/:id` |
 * | `POST /api/clientes/:id/avaliacao` | idem |
 * | `GET  /api/clientes/:id/historico` | idem |
 * | `POST /api/clientes/:id/eventos` | idem |
 * | `POST /api/clientes/:id/simular-evento` | idem |
 * | `POST /api/alertas` | idem |
 * | `GET/POST /api/auditoria` | idem |
 * | `POST /api/due-diligence` | idem |
 *
 * Por que um catch-all em vez de um arquivo por rota: o proxy é **puro** — não valida corpo,
 * não conhece regra de negócio, e o único parâmetro que varia é o caminho. Enumerar dez
 * arquivos idênticos criaria dez oportunidades de divergir do Flask sem ganhar nada. As rotas
 * de streaming e a de custo têm handler próprio porque precisam de deadline e `maxDuration`
 * diferentes, e rota estática/dinâmica tem precedência sobre catch-all no App Router.
 *
 * `force-dynamic` impede qualquer tentativa de cache ou pré-render: toda chamada é ao vivo.
 */

import { proxyParaFlask } from '@/lib/api/proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 30;

type Contexto = { params: Promise<{ caminho: string[] }> };

async function encaminhar(req: Request, ctx: Contexto): Promise<Response> {
  const { caminho } = await ctx.params;
  const alvo = caminho.map(encodeURIComponent).join('/');
  return proxyParaFlask(req, `/api/${alvo}`);
}

export const GET = encaminhar;
export const POST = encaminhar;
export const PUT = encaminhar;
export const PATCH = encaminhar;
export const DELETE = encaminhar;
