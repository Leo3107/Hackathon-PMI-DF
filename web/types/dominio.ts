/**
 * Contrato de tipos do Lastro — parte 1: identidade, fatos brutos, exposição e evidências.
 *
 * Transcrição literal de `specs/01-modelo-de-dados.md`. **Estes tipos são o contrato da API**
 * (00-decisoes.md D3): o Flask serializa exatamente estas chaves, em camelCase. Divergência
 * entre um modelo pydantic de `api/models/` e um tipo daqui é bug, não preferência.
 *
 * Princípio de separação que governa o arquivo: se um valor pode ser derivado, ele **não**
 * existe em `FatosDoCliente`. Score, PD, rating, coberturas, red flags e recomendação vivem
 * todos em `./avaliacao.ts`.
 */

// ---------------------------------------------------------------------------
// Enums e uniões
// ---------------------------------------------------------------------------

export type Rating = 'A' | 'B' | 'C' | 'D';

export type DimensaoId =
  | 'comportamental'
  | 'juridico'
  | 'fiscal'
  | 'agroclimatico'
  | 'cadastral'
  | 'ambiental'
  | 'garantias';

export type Tendencia = 'melhorando' | 'estavel' | 'deteriorando' | 'deterioracao_acelerada';

export type Severidade = 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAIXA';

export type StatusRedFlag = 'nova' | 'analisada' | 'resolvida';

export type TipoPessoa = 'PF' | 'PJ';

export type TipoOperacao = 'VENDA_A_PRAZO' | 'BARTER' | 'CPR';

export type TipoGarantia =
  | 'ALIENACAO_FIDUCIARIA'
  | 'CPR_FINANCEIRA'
  | 'CPR_FISICA'
  | 'PENHOR_SAFRA'
  | 'PENHOR_MAQUINA'
  | 'HIPOTECA'
  | 'AVAL_FIANCA';

/** Distinção jurídica decisiva em cenário de RJ. Ver `02-motor-de-risco.md` §10. */
export type NaturezaGarantia = 'EXTRACONCURSAL' | 'CONCURSAL';

export type EstadoCliente = 'ATIVO' | 'EM_OBSERVACAO' | 'SUSPENSO' | 'RJ_EM_CURSO' | 'FALENCIA';

export type RiscoZarc = 'baixo' | 'moderado' | 'alto' | 'critico';

export type FonteId =
  | 'RECEITA_FEDERAL'
  | 'REDESIM'
  | 'DATAJUD_CNJ'
  | 'DJE'
  | 'CARTORIO_PROTESTO'
  | 'PGFN'
  | 'TST_CNDT'
  | 'CAIXA_CRF_FGTS'
  | 'SICAR'
  | 'IBAMA'
  | 'CONAB'
  | 'MAPA_ZARC'
  | 'INMET'
  | 'INTERNO_KRILLTECH';

export type CodigoRecomendacao =
  | 'APROVAR'
  | 'APROVAR_COM_MONITORAMENTO_INTENSIVO'
  | 'APROVAR_COM_REVISAO_DE_LIMITE'
  | 'APROVAR_COM_RESTRICOES'
  | 'SUSPENDER_NOVA_EXPOSICAO_A_PRAZO'
  | 'SUSPENDER_EXPOSICAO';

export type DecisaoAnalista =
  | 'APROVAR'
  | 'APROVAR_COM_RESTRICOES'
  | 'REVISAR'
  | 'SUSPENDER'
  | 'RECUSAR';

/** Distingue o fluxo A (due diligence) do fluxo B (monitoramento). Ver `03-ux-e-telas.md` §0.3. */
export type OrigemCliente = 'CARTEIRA' | 'PROSPECT';

export type SituacaoRfb = 'ATIVA' | 'SUSPENSA' | 'INAPTA' | 'BAIXADA';

export type SituacaoCar = 'ATIVO_REGULAR' | 'PENDENTE' | 'IRREGULAR' | 'AUSENTE';

export type StatusParcela = 'A_VENCER' | 'PAGA' | 'EM_ATRASO';

export type TipoEvidencia =
  | 'CERTIDAO'
  | 'PROCESSO'
  | 'PUBLICACAO'
  | 'CADASTRO'
  | 'LAUDO'
  | 'SERIE_HISTORICA'
  | 'INTERNO';

export type TipoEvento =
  | 'NOVA_EXECUCAO'
  | 'NOVO_PROTESTO'
  | 'DIVIDA_ATIVA'
  | 'PEDIDO_RJ'
  | 'PEDIDO_FALENCIA'
  | 'EMBARGO_AMBIENTAL'
  | 'ALTERACAO_SOCIETARIA'
  | 'COVENANT_ROMPIDO'
  | 'MUDANCA_CLIMATICA'
  | 'ATRASO_PAGAMENTO'
  | 'CADASTRAL'
  | 'RECALCULO';

// ---------------------------------------------------------------------------
// Identidade do cliente
// ---------------------------------------------------------------------------

export interface Cliente {
  /** Slug estável, ex.: `vale-do-araguaia`. */
  id: string;
  razaoSocial: string;
  nomeFantasia?: string | null;
  /** CPF ou CNPJ formatado, dígito verificador válido, **simulado**. */
  documento: string;
  tipoPessoa: TipoPessoa;
  municipio: string;
  uf: string;
  /** ex.: `Produtor rural — grãos`. */
  atividade: string;
  cnaePrincipal: string;
  /** ex.: `['Soja', 'Milho safrinha']`. */
  culturas: string[];
  /** ISO date. */
  inicioRelacionamento: string;
  estado: EstadoCliente;
  origem: OrigemCliente;
}

// ---------------------------------------------------------------------------
// Fatos brutos — o que as fontes disseram
// ---------------------------------------------------------------------------

export interface CovenantRompido {
  id: string;
  /** ex.: `Endividamento total acima de 2,5× o patrimônio`. */
  descricao: string;
  limiteContratual: string;
  valorApurado: string;
  /** ISO date. */
  dataDeteccao: string;
}

export interface FatosInternos {
  atrasoMedioDias12m: number;
  atrasoMedioDias90d: number;
  piorAtrasoDias12m: number;
  /** 0..1 */
  pctTitulosPagosEmDia12m: number;
  renegociacoes12m: number;
  semAtrasoRelevante24m: boolean;
  /** Inadimplência **técnica**: covenants contratuais rompidos e ainda vigentes. */
  covenantsRompidos: CovenantRompido[];
}

export interface RecuperacaoJudicial {
  /** ISO date. */
  dataDistribuicao: string;
  /** ISO date. */
  dataDeferimento?: string | null;
  diasProrrogadosStay: number;
}

export interface FatosJuridicos {
  execucoesTitulo12m: number;
  execucoesTitulo90d: number;
  valorTotalEmExecucao: number;
  credoresDistintosExecutando: number;
  protestosAtivos: number;
  protestos12m: number;
  credoresProtestantes180d: number;
  acoesTrabalhistasTransitadas: number;
  pedidoFalencia: boolean;
  /** RJ ajuizada ou deferida. Ver Stay Period em `02-motor-de-risco.md` §9. */
  recuperacaoJudicial?: RecuperacaoJudicial | null;
  semLitigio36m: boolean;
  fraudeConfirmada: boolean;
  listaSujaTrabalhoEscravo: boolean;
}

export interface FatosFiscais {
  dividaAtivaPgfn: number;
  dividaAtivaPgfn90dAtras: number;
  cndtPositiva: boolean;
  valorDebitoTrabalhista: number;
  crfFgtsRegular: boolean;
  parcelamentoRompido12m: boolean;
  execucoesFiscais: number;
  valorExecucoesFiscais: number;
  todasCertidoesNegativas: boolean;
}

export interface FatosAgro {
  riscoZarc: RiscoZarc;
  /** 0..100 */
  quebraSafraRegionalPct: number;
  /** Pode ser negativo. */
  desvioPrecipitacaoPct: number;
  /** Negativo = abaixo da média. */
  produtividadeVsMediaRegionalPct: number;
  areaTotalHa: number;
  areaIrrigadaHa: number;
  seguroAgricolaVigente: boolean;
  /** ex.: `2025/26`. */
  safraReferencia: string;
  /** Culturas consideradas pelo motor agroclimático. Presente em `api/models/fatos.py`. */
  culturas?: string[];
}

export interface FatosCadastrais {
  situacaoRfb: SituacaoRfb;
  anosAtividade: number;
  capitalSocial: number;
  alteracaoSocietaria180d: boolean;
  saidaSocioMajoritario12m: boolean;
  qsaEstavel5anos: boolean;
  cnaeCompativel: boolean;
  /** Lei 14.112/2020 — habilita produtor rural PF a pedir RJ. */
  possuiLivroCaixaDigital: boolean;
  possuiInscricaoEstadual: boolean;
  anosAtividadeComprovada: number;
  /**
   * Repetido nos fatos para que o motor decida elegibilidade a RJ sem depender de `Cliente`
   * (`api/models/fatos.py`). A identidade canônica continua em `Cliente.tipoPessoa`.
   */
  tipoPessoa?: TipoPessoa | null;
}

export interface FatosAmbientais {
  embargoIbamaVigente: boolean;
  /** Agrava para gatilho de veto: embargo recai sobre bem dado em garantia. */
  embargoSobreImovelEmGarantia: boolean;
  autoInfracaoNaoQuitado: boolean;
  situacaoCar: SituacaoCar;
  sobreposicaoAppOuReserva: boolean;
}

export interface FatosDoCliente {
  clienteId: string;
  /** ISO date. O motor **nunca** lê o relógio; recebe esta data. */
  dataReferencia: string;
  interno: FatosInternos;
  juridico: FatosJuridicos;
  fiscal: FatosFiscais;
  agro: FatosAgro;
  cadastral: FatosCadastrais;
  ambiental: FatosAmbientais;
  operacoes: Operacao[];
  garantias: Garantia[];
  limiteAprovado: number;
  patrimonioDeclarado: number;
  faturamentoEstimadoAnual: number;
  /** Evidências que sustentam estes fatos. Toda red flag aponta para uma. */
  evidencias: Evidencia[];
}

// ---------------------------------------------------------------------------
// Exposição e garantias
// ---------------------------------------------------------------------------

export interface Parcela {
  id: string;
  /** ISO date. */
  vencimento: string;
  valor: number;
  status: StatusParcela;
  diasAtraso?: number | null;
}

export interface Barter {
  cultura: string;
  sacasPrometidas: number;
  precoReferenciaSaca: number;
  /** Ausente = barter sem lastro formal (penalidade D4 do motor). */
  cprVinculadaId?: string | null;
}

export interface Operacao {
  id: string;
  tipo: TipoOperacao;
  /** ex.: `Fornecimento de defensivos — safra 2025/26`. */
  descricao: string;
  saldoDevedor: number;
  /** ISO date. */
  dataContratacao: string;
  parcelas: Parcela[];
  /** Barter: safra prometida em contrapartida. Conecta risco agro ao dinheiro exposto. */
  barter?: Barter;
}

export interface Garantia {
  id: string;
  tipo: TipoGarantia;
  /** **Derivado** do tipo por tabela fixa — nunca digitado no mock. Ver `02` §10. */
  natureza: NaturezaGarantia;
  descricao: string;
  valorDeclarado: number;
  /** `valorDeclarado × (1 − haircut do tipo)`. Calculado, não digitado. */
  valorAtualizado: number;
  registrada: boolean;
  /** ISO date. */
  dataAvaliacao: string;
  /** `true` quando o bem está sob embargo ambiental — aciona `VETO_EMBARGO_GARANTIA`. */
  bemEmbargado?: boolean | null;
}

// ---------------------------------------------------------------------------
// Evidências
// ---------------------------------------------------------------------------

export interface Evidencia {
  id: string;
  fonte: FonteId;
  /** Rótulo humano: `DataJud — CNJ`. */
  nomeFonte: string;
  tipo: TipoEvidencia;
  titulo: string;
  resumo: string;
  /** ISO date. */
  dataConsulta: string;
  /** ISO date. */
  dataDocumento?: string | null;
  /** Sempre `true` nesta versão. Renderiza o selo "consulta simulada" (D11.6). */
  simulada: true;
  urlFicticia?: string | null;
  /** Fatores do motor que esta evidência sustenta. Liga evidência → número (R5). */
  fatoresRelacionados: string[];
}
