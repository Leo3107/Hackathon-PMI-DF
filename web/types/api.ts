/**
 * Contrato de transporte entre a interface e o Flask.
 *
 * Os tipos de `dominio.ts`, `avaliacao.ts` e `eventos.ts` são transcrição de
 * `specs/01-modelo-de-dados.md`. Os deste arquivo cobrem o que só existe na **fronteira**:
 * envelopes de erro (`03-ux-e-telas.md` §9.4), estado de sessão (`00-decisoes.md` D3),
 * protocolo NDJSON e ledger de custo (`04-camada-llm.md` §2.3 e §5.5), e os agregados de
 * carteira que `/carteira` consome (`03-ux-e-telas.md` §2).
 *
 * ⚠️ Os agregados (`ResumoCarteira`, `ClienteAvaliado`) são o contrato **proposto por WS6**
 * para as rotas de dados do Flask, que ainda não existem. O WS3 deve espelhá-los; qualquer
 * divergência se resolve aqui, não na tela.
 */

import type { AvaliacaoDeRisco, ComparacaoDeAvaliacoes } from './avaliacao';
import type {
  Cliente,
  EstadoCliente,
  Rating,
  Severidade,
  StatusRedFlag,
  Tendencia,
  TipoEvento,
} from './dominio';
import type { Alerta } from './eventos';

// ---------------------------------------------------------------------------
// Erros
// ---------------------------------------------------------------------------

/**
 * Códigos de erro do contrato.
 *
 * `MOTOR_INDISPONIVEL` é o código canônico de "Flask fora do ar" (`03-ux-e-telas.md` §9.4).
 * `API_INDISPONIVEL` aparece no rascunho de `04-camada-llm.md` §2.2 e é aceito como sinônimo
 * na leitura, nunca emitido pelo nosso proxy.
 */
export type CodigoErroApi =
  | 'MOTOR_INDISPONIVEL'
  | 'API_INDISPONIVEL'
  | 'CORPO_INVALIDO'
  | 'CLIENTE_NAO_ENCONTRADO'
  | 'DOCUMENTO_NAO_ENCONTRADO'
  | 'AVALIACAO_INCONSISTENTE'
  | 'TAREFA_INVALIDA'
  | 'ROTA_NAO_ENCONTRADA'
  | 'ERRO_INTERNO';

export interface RespostaDeErro {
  erro: CodigoErroApi | string;
  detalhe?: string | unknown[];
}

// ---------------------------------------------------------------------------
// Estado de sessão enviado ao motor
// ---------------------------------------------------------------------------

export interface EventoSimulado {
  tipo: TipoEvento;
  /** ISO datetime da injeção. */
  data: string;
}

/**
 * Mutações locais que alteram o cálculo (D3 · "Estado de sessão"). Viajam no corpo de toda
 * requisição que recalcula risco; nada é persistido no servidor.
 */
export interface EstadoDeSessaoApi {
  eventosSimulados: EventoSimulado[];
  /** `redFlagId` → status. */
  statusRedFlags: Record<string, StatusRedFlag>;
}

// ---------------------------------------------------------------------------
// Agregados de carteira e lista
// ---------------------------------------------------------------------------

/** Linha da lista de clientes: identidade + avaliação recalculada + variação em 90 dias. */
export interface ClienteAvaliado {
  cliente: Cliente;
  avaliacao: AvaliacaoDeRisco;
  variacao90d?: ComparacaoDeAvaliacoes;
  alertasNaoLidos: number;
}

export interface FatiaDeConcentracao {
  rotulo: string;
  exposicao: number;
  /** 0..1 */
  pct: number;
  clientes: number;
}

export interface PontoMatrizDeRisco {
  clienteId: string;
  razaoSocial: string;
  /** 0..1 */
  pd12m: number;
  exposicaoTotal: number;
  exposicaoEmRiscoEmRJ: number;
  rating: Rating;
  temVeto: boolean;
}

export interface LinhaDinheiroEmRisco {
  clienteId: string;
  razaoSocial: string;
  uf: string;
  exposicaoTotal: number;
  exposicaoEmRisco: number;
  exposicaoEmRiscoEmRJ: number;
  rating: Rating;
  temVeto: boolean;
  tendencia: Tendencia;
}

export type MotivoAtencao = 'VETO_ATIVO' | 'MAIOR_QUEDA_90D' | 'ALERTA_CRITICO';

/** Cartão da faixa de atenção imediata (`03-ux-e-telas.md` §2.2). Seleção é do motor, não da tela. */
export interface CartaoDeAtencao {
  motivo: MotivoAtencao;
  eyebrow: string;
  clienteId: string;
  razaoSocial: string;
  /** Uma linha de causa nomeada. */
  causa: string;
  /** Uma linha com o número financeiro relevante, já formatado pelo Flask. */
  numero: string;
  acao: string;
  severidade: Severidade;
}

export interface ResumoCarteira {
  /** ISO date. */
  dataReferencia: string;
  /** ISO datetime da última varredura — exibido quando não há atenção imediata. */
  ultimaVarredura: string;
  atencaoImediata: CartaoDeAtencao[];
  exposicaoTotal: number;
  exposicaoAVencer90d: number;
  exposicaoEmRisco: number;
  exposicaoEmRiscoEmRJ: number;
  exposicaoCritica: number;
  /** 0..1 */
  pctExposicaoEmRisco: number;
  /** 0..1 */
  pctExposicaoCritica: number;
  clientesCriticos: number;
  /** 0..1 */
  coberturaExtraconcursal: number;
  /** 0..1 */
  coberturaTotal: number;
  totalClientes: number;
  clientesPorEstado: Record<EstadoCliente, number>;
  clientesPorRating: Record<Rating, { clientes: number; exposicao: number }>;
  alertas30d: { total: number; porSeveridade: Record<Severidade, number> };
  deterioracao: {
    clientes: number;
    /** Limiar em pontos usado na contagem (ex.: 25). */
    limiarPontos: number;
    aceleradas: number;
  };
  concentracaoPorCultura: FatiaDeConcentracao[];
  concentracaoPorUf: FatiaDeConcentracao[];
  matrizDeRisco: PontoMatrizDeRisco[];
  dinheiroEmRisco: LinhaDinheiroEmRisco[];
}

// ---------------------------------------------------------------------------
// Due diligence (fluxo A)
// ---------------------------------------------------------------------------

export type EstagioPipeline =
  | 'CADASTRAL'
  | 'JURIDICO'
  | 'FISCAL'
  | 'AMBIENTAL'
  | 'AGROCLIMATICO'
  | 'INTERNO'
  | 'SCORE'
  | 'RELATORIO';

export interface ResultadoEstagio {
  estagio: EstagioPipeline;
  rotulo: string;
  status: 'ok' | 'falha';
  /** Achados em uma linha cada, prontos para a tela. */
  achados: string[];
  duracaoMs: number;
}

export interface RespostaDueDiligence {
  encontrado: boolean;
  documento: string;
  cliente?: Cliente;
  avaliacao?: AvaliacaoDeRisco;
  estagios: ResultadoEstagio[];
}

// ---------------------------------------------------------------------------
// Simulação de evento (D10)
// ---------------------------------------------------------------------------

export interface RespostaSimulacao {
  clienteId: string;
  evento: EventoSimulado;
  scoreAnterior: number;
  scoreAtual: number;
  deltaScore: number;
  avaliacao: AvaliacaoDeRisco;
  variacao: ComparacaoDeAvaliacoes;
  alertaGerado?: Alerta;
}

// ---------------------------------------------------------------------------
// Saúde do serviço
// ---------------------------------------------------------------------------

export interface RespostaSaude {
  ok: boolean;
  servico: string;
  versao?: string;
  llmHabilitado?: boolean;
  /** ISO datetime da resposta. */
  dataHora?: string;
}

// ---------------------------------------------------------------------------
// Camada de linguagem — ledger de custo (`04` §5.5)
// ---------------------------------------------------------------------------

export type MotivoLlmDesligado =
  | 'LLM_DESLIGADO'
  | 'SEM_CHAVE'
  | 'ORCAMENTO'
  | 'DISJUNTOR'
  | 'FORCADO_POR_ENV';

export type OrigemNarrativa = 'openai' | 'deterministico' | 'fixture';

export interface ChamadaLlm {
  id: string;
  /** ISO datetime. */
  dataHora: string;
  tarefa: TarefaNarrativa | 'copiloto';
  clienteId: string;
  origemFinal: OrigemNarrativa;
  tokensEntrada: number;
  tokensSaida: number;
  custoUsd: number;
  duracaoMs: number;
  status: 'ok' | 'degradado' | 'erro';
  motivo: string | null;
}

export interface RespostaCusto {
  habilitado: boolean;
  engineAtivo: OrigemNarrativa;
  modelo: string;
  orcamentoUsd: number;
  custoAcumuladoUsd: number;
  reservadoUsd: number;
  /** 0..100 — percentual do orçamento, já calculado pelo servidor. */
  pctOrcamento: number;
  chamadas: { total: number; openai: number; deterministico: number; fixture: number };
  tokens: { entrada: number; saida: number; raciocinio: number };
  incidentes: number;
  motivoDesligado: MotivoLlmDesligado | null;
  ultimas: ChamadaLlm[];
}

// ---------------------------------------------------------------------------
// Camada de linguagem — protocolo NDJSON (`04` §2.3)
// ---------------------------------------------------------------------------

export type TarefaNarrativa = 'parecer' | 'score' | 'recomendacao';

export interface MensagemCopiloto {
  papel: 'usuario' | 'assistente';
  texto: string;
}

export interface PedidoNarrativa {
  clienteId: string;
  sessao?: EstadoDeSessaoApi;
}

export interface PedidoCopiloto extends PedidoNarrativa {
  pergunta: string;
  historico?: MensagemCopiloto[];
}

export type MotivoSubstituicao =
  | 'TIMEOUT'
  | 'FALHA_REDE'
  | 'FIDELIDADE_NUMERICA'
  | 'SAIDA_VAZIA';

export interface EventoInicio {
  t: 'inicio';
  tarefa: TarefaNarrativa | 'copiloto';
  origem: OrigemNarrativa;
  modelo?: string;
  requisicaoId: string;
  clienteId: string;
}

export interface EventoDelta {
  t: 'delta';
  d: string;
}

export interface EventoSubstituir {
  t: 'substituir';
  motivo: MotivoSubstituicao;
}

export interface UsoDeTokens {
  entrada: number;
  saida: number;
  raciocinio: number;
  estimado: boolean;
  custoUsd: number;
}

export interface AcumuladoDeCusto {
  custoUsd: number;
  chamadas: number;
  pctOrcamento: number;
}

export interface EventoFim {
  t: 'fim';
  origem: OrigemNarrativa;
  motivoDegradacao: MotivoSubstituicao | null;
  uso: UsoDeTokens;
  acumulado: AcumuladoDeCusto;
  duracaoMs: number;
}

export interface EventoErroStream {
  t: 'erro';
  codigo: string;
  mensagem: string;
}

/**
 * Garantias do protocolo: `inicio` é sempre o primeiro evento; `fim` ou `erro` é sempre o
 * último; nunca há `delta` depois de `fim`.
 */
export type EventoNarrativa =
  | EventoInicio
  | EventoDelta
  | EventoSubstituir
  | EventoFim
  | EventoErroStream;
