/**
 * Sonda de saúde — `GET /api/saude` → Flask `GET /api/saude`.
 *
 * É a rota que a faixa global de "motor indisponível" (`03-ux-e-telas.md` §9.4) consulta em
 * backoff de 2s, 4s, 8s, 16s e 30s até o serviço voltar, e a que alimenta a quarta pastilha
 * viva de `/arquitetura` (`07` §Parte 2).
 *
 * Deadline de 3s: a sonda precisa falhar rápido para a faixa dizer "tentativa 3" em vez de ficar
 * pendurada. A resposta 503 `MOTOR_INDISPONIVEL` do proxy já é o contrato esperado pela faixa.
 */

import { proxyParaFlask } from '@/lib/api/proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(req: Request): Promise<Response> {
  return proxyParaFlask(req, '/api/saude', 3_000);
}
