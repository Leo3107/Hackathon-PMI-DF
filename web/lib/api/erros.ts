/**
 * Tratamento de erro uniforme do cliente de API.
 *
 * Regra R7 (`03-ux-e-telas.md` §0.4): erro nunca é tela branca. Todo estado de falha tem causa
 * nomeada, consequência e ação. Por isso **toda** falha vira um `ErroLastro` com código legível,
 * status HTTP e um texto de tela já pronto — nenhum componente precisa interpretar `fetch`.
 */

import type { CodigoErroApi, RespostaDeErro } from '@/types';

/** Contrato literal de "Flask fora do ar" (`03-ux-e-telas.md` §9.4). */
export const ERRO_MOTOR_INDISPONIVEL = {
  erro: 'MOTOR_INDISPONIVEL',
  detalhe: 'Sem resposta do serviço de cálculo em 127.0.0.1:5001',
} as const satisfies RespostaDeErro;

/** Sinônimo aceito na leitura — aparece no rascunho de `04-camada-llm.md` §2.2. */
const CODIGOS_DE_INDISPONIBILIDADE = new Set(['MOTOR_INDISPONIVEL', 'API_INDISPONIVEL']);

export class ErroLastro extends Error {
  readonly codigo: CodigoErroApi | string;
  readonly status: number;
  readonly detalhe?: string | unknown[];
  /** Caminho chamado, para o texto de diagnóstico. */
  readonly caminho?: string;

  constructor(
    codigo: CodigoErroApi | string,
    status: number,
    opcoes: { detalhe?: string | unknown[]; caminho?: string; causa?: unknown } = {},
  ) {
    super(mensagemDoCodigo(codigo, opcoes.detalhe));
    this.name = 'ErroLastro';
    this.codigo = codigo;
    this.status = status;
    this.detalhe = opcoes.detalhe;
    this.caminho = opcoes.caminho;
    if (opcoes.causa !== undefined) this.cause = opcoes.causa;
  }

  /** `true` quando o serviço de cálculo não respondeu — dispara a faixa global (§9.4). */
  get motorIndisponivel(): boolean {
    return CODIGOS_DE_INDISPONIBILIDADE.has(this.codigo) || this.status === 503;
  }

  get naoEncontrado(): boolean {
    return this.status === 404;
  }
}

const MENSAGENS: Record<string, string> = {
  MOTOR_INDISPONIVEL: 'Motor de risco indisponível — o serviço de cálculo não está respondendo.',
  API_INDISPONIVEL: 'Motor de risco indisponível — o serviço de cálculo não está respondendo.',
  CLIENTE_NAO_ENCONTRADO: 'Cliente não encontrado.',
  DOCUMENTO_NAO_ENCONTRADO: 'Documento não encontrado na base demonstrativa.',
  CORPO_INVALIDO: 'A requisição foi recusada pelo motor por conter dados inválidos.',
  AVALIACAO_INCONSISTENTE:
    'O motor recusou-se a devolver uma avaliação cujos números não fecham. Nenhum número parcial é exibido.',
  TAREFA_INVALIDA: 'Tarefa de narrativa desconhecida.',
  ROTA_NAO_ENCONTRADA: 'Esta rota ainda não existe no serviço de cálculo.',
  ERRO_INTERNO: 'O serviço de cálculo falhou ao processar a requisição.',
};

export function mensagemDoCodigo(codigo: string, detalhe?: string | unknown[]): string {
  const base = MENSAGENS[codigo] ?? `Falha na comunicação com o motor de risco (${codigo}).`;
  return typeof detalhe === 'string' && detalhe ? `${base} ${detalhe}` : base;
}

/** Normaliza qualquer coisa lançada em um `ErroLastro`. */
export function comoErroLastro(valor: unknown, caminho?: string): ErroLastro {
  if (valor instanceof ErroLastro) return valor;
  if (valor instanceof DOMException && valor.name === 'AbortError') {
    return new ErroLastro('MOTOR_INDISPONIVEL', 503, {
      detalhe: 'Tempo de resposta esgotado.',
      caminho,
      causa: valor,
    });
  }
  return new ErroLastro('MOTOR_INDISPONIVEL', 503, {
    detalhe: ERRO_MOTOR_INDISPONIVEL.detalhe,
    caminho,
    causa: valor,
  });
}

export function ehMotorIndisponivel(valor: unknown): boolean {
  return valor instanceof ErroLastro && valor.motorIndisponivel;
}

/** Texto curto para `ErrorState`, sem vazar stack nem jargão de rede. */
export function textoDeErro(valor: unknown): string {
  if (valor instanceof ErroLastro) return valor.message;
  return 'Falha inesperada na interface. Recarregue a página.';
}
