/**
 * Ledger de custo do LLM — `GET /api/llm/custo` → Flask `GET /api/llm/custo` (`04` §5.5).
 *
 * Consultado pelo `ContadorDeCusto` na montagem, a cada 20s e ao fim de cada stream. Deadline
 * curto (5s): é um indicador de topbar, não pode segurar a interface. Se o motor não responder,
 * o contador exibe "Flask indisponível" — estado textual, não só cor (I8).
 */

import { proxyParaFlask } from '@/lib/api/proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(req: Request): Promise<Response> {
  return proxyParaFlask(req, '/api/llm/custo', 5_000);
}
