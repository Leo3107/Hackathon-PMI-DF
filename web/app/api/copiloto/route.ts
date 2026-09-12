/**
 * Proxy de streaming do copiloto de análise — `POST /api/copiloto` → Flask `POST /api/copiloto`.
 *
 * Mesmas regras da narrativa: NDJSON repassado sem leitura, sem buffer, sem transformação.
 * O pré-filtro anti-alucinação e a recusa fora de escopo são do Flask (`04` §8); aqui não há
 * nenhuma decisão de conteúdo.
 */

import { proxyParaFlask } from '@/lib/api/proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 30;

export function POST(req: Request): Promise<Response> {
  return proxyParaFlask(req, '/api/copiloto');
}
