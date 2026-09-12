/**
 * Proxy de streaming das três tarefas de narrativa (`specs/04-camada-llm.md` §2.1 e §2.2).
 *
 * | Rota no Next | Rota no Flask |
 * |---|---|
 * | `POST /api/narrativa/parecer` | `POST /api/narrativa/parecer` |
 * | `POST /api/narrativa/score` | `POST /api/narrativa/score` |
 * | `POST /api/narrativa/recomendacao` | `POST /api/narrativa/recomendacao` |
 *
 * Resposta: NDJSON, uma linha JSON por evento. `proxyParaFlask` devolve `upstream.body` sem
 * ler — **é o ponto onde bufferizar mataria o streaming em silêncio**. `force-dynamic` e o
 * repasse de `x-accel-buffering: no` completam a mitigação do risco técnico nº 1 do HANDOFF.
 *
 * A `OPENAI_API_KEY` não é lida aqui e não existe no processo do Next: ela vive só no Flask.
 */

import { proxyParaFlask, respostaDeErro } from '@/lib/api/proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const TAREFAS = new Set(['parecer', 'score', 'recomendacao']);

export async function POST(
  req: Request,
  ctx: { params: Promise<{ tarefa: string }> },
): Promise<Response> {
  const { tarefa } = await ctx.params;
  if (!TAREFAS.has(tarefa)) {
    return respostaDeErro('TAREFA_INVALIDA', 404, `Tarefa de narrativa desconhecida: ${tarefa}.`);
  }
  return proxyParaFlask(req, `/api/narrativa/${tarefa}`);
}
