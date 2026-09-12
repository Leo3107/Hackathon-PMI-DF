/**
 * Proxy server-side para o Flask. **Só pode ser importado por route handlers.**
 *
 * (`specs/04-camada-llm.md` §2.2 e `specs/00-decisoes.md` D3.)
 *
 * O browser nunca fala com o Flask. Estes handlers são a única ponte, e são **proxy puro**:
 * não interpretam corpo, não transformam JSON, não decidem nada de negócio.
 *
 * ## As três proibições
 *
 * 1. **Nunca** `await upstream.text()` ou `.json()`. O corpo é repassado como `ReadableStream`.
 *    Ler o corpo aqui bufferiza o NDJSON e mata o streaming **silenciosamente** — a tela
 *    continua funcionando, só que a prosa aparece toda de uma vez, 25 segundos depois. É o
 *    risco técnico nº 1 do projeto (HANDOFF §8).
 * 2. **Nunca** ler `OPENAI_API_KEY`. A variável não existe no processo do Next e não deve
 *    passar a existir: ela vive só no Flask.
 * 3. **Nunca** transformar o corpo. Nem `JSON.parse`, nem recompressão, nem reescrita de chave.
 *
 * `x-accel-buffering: no` e `cache-control: no-store, no-transform` são repassados para que
 * nenhum intermediário (nginx, CDN, o próprio Node) resolva acumular bytes por conta própria.
 *
 * Nota: `import 'server-only'` seria o guarda ideal, mas o pacote não é dependência do projeto
 * e o `package.json` pertence a outro agente. O guarda aqui é convencional: este módulo não é
 * importado por nenhum componente de cliente.
 */

import { ERRO_MOTOR_INDISPONIVEL } from './erros';

/** Base do serviço de cálculo. `127.0.0.1` e não `localhost`: evita resolução IPv6 no Windows. */
export const BASE_FLASK = process.env.LASTRO_API_URL ?? 'http://127.0.0.1:5001';

/** Deadline padrão. O executor do Flask degrada em 25s (`04` §2.4); 28s dá folga de 3s. */
export const TIMEOUT_PADRAO_MS = 28_000;

const CABECALHOS_DE_ERRO = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
} as const;

/** Resposta 503 canônica de motor fora do ar (`03-ux-e-telas.md` §9.4). */
export function respostaMotorIndisponivel(detalhe?: string): Response {
  return new Response(
    JSON.stringify({
      erro: ERRO_MOTOR_INDISPONIVEL.erro,
      detalhe: detalhe ?? ERRO_MOTOR_INDISPONIVEL.detalhe,
    }),
    { status: 503, headers: CABECALHOS_DE_ERRO },
  );
}

export function respostaDeErro(erro: string, status: number, detalhe?: string): Response {
  return new Response(JSON.stringify(detalhe ? { erro, detalhe } : { erro }), {
    status,
    headers: CABECALHOS_DE_ERRO,
  });
}

const METODOS_SEM_CORPO = new Set(['GET', 'HEAD']);

/**
 * Encaminha a requisição para `BASE_FLASK + caminho` e devolve a resposta **sem tocar no corpo**.
 *
 * @param req      Requisição original do route handler.
 * @param caminho  Caminho no Flask, começando com `/api/`.
 * @param timeoutMs Deadline de conexão. Use 5s para o ledger de custo, 3s para saúde.
 */
export async function proxyParaFlask(
  req: Request,
  caminho: string,
  timeoutMs: number = TIMEOUT_PADRAO_MS,
): Promise<Response> {
  const busca = new URL(req.url).search;
  const alvo = `${BASE_FLASK}${caminho}${busca}`;

  // Corpo lido como texto porque é pequeno (um id de cliente + estado de sessão) e porque
  // repassar o stream de entrada exigiria `duplex: 'half'`. A resposta, essa sim, não é lida.
  let corpo: string | undefined;
  if (!METODOS_SEM_CORPO.has(req.method)) {
    try {
      corpo = await req.text();
    } catch {
      return respostaDeErro('CORPO_INVALIDO', 400, 'Não foi possível ler o corpo da requisição.');
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(alvo, {
      method: req.method,
      headers: {
        'content-type': req.headers.get('content-type') ?? 'application/json',
        accept: req.headers.get('accept') ?? 'application/json, application/x-ndjson',
      },
      body: corpo,
      signal: AbortSignal.timeout(timeoutMs),
      cache: 'no-store',
    });
  } catch (causa) {
    const motivo = causa instanceof Error ? causa.message : String(causa);
    return respostaMotorIndisponivel(
      `Sem resposta do serviço de cálculo em ${hostDeBase()} (${motivo}).`,
    );
  }

  // ≥ 500 do Flask também é "motor indisponível" para a interface (§9.4): a tela não tem o que
  // mostrar e precisa do mesmo tratamento. 4xx é erro de contrato e passa adiante como está.
  if (upstream.status >= 500) {
    void upstream.body?.cancel();
    return respostaMotorIndisponivel(
      `O serviço de cálculo respondeu ${upstream.status} para ${caminho}.`,
    );
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: {
      'content-type':
        upstream.headers.get('content-type') ?? 'application/json; charset=utf-8',
      'cache-control': 'no-store, no-transform',
      'x-accel-buffering': upstream.headers.get('x-accel-buffering') ?? 'no',
    },
  });
}

function hostDeBase(): string {
  try {
    return new URL(BASE_FLASK).host;
  } catch {
    return BASE_FLASK;
  }
}
