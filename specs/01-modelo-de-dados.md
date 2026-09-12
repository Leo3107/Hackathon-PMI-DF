# 01 — Modelo de dados

> Contrato de tipos do produto. Vive em `types/`. **Nenhum subagente inventa campo novo sem
> registrar aqui.** Estrutura pensada para que a troca de mock por API real não force refatoração
> de tela: o repositório é assíncrono e os fatos brutos são separados das avaliações derivadas.

Referências: prompt do usuário §26 · `02-motor-de-risco.md`

---

## Princípio de separação

```
FatosDoCliente       ← dado bruto, "o que as fontes disseram". É o que um dia virá de API.
      ↓ calcularRisco() — função pura
AvaliacaoDeRisco     ← tudo que é derivado. NUNCA persistido no mock, sempre recalculado.
```

Regra: **se um valor pode ser derivado, ele não existe em `FatosDoCliente`.** Score, PD, rating,
coberturas, red flags e recomendação são todos derivados. Isso elimina por construção a
possibilidade de o mock discordar do motor.

---

## Enums e uniões

```ts
export type Rating = 'A' | 'B' | 'C' | 'D';

export type DimensaoId =
  | 'comportamental' | 'juridico' | 'fiscal'
  | 'agroclimatico' | 'cadastral' | 'ambiental' | 'garantias';

export type Tendencia =
  | 'melhorando' | 'estavel' | 'deteriorando' | 'deterioracao_acelerada';

export type Severidade = 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAIXA';

export type StatusRedFlag = 'nova' | 'analisada' | 'resolvida';

export type TipoPessoa = 'PF' | 'PJ';

export type TipoOperacao = 'VENDA_A_PRAZO' | 'BARTER' | 'CPR';

export type TipoGarantia =
  | 'ALIENACAO_FIDUCIARIA' | 'CPR_FINANCEIRA' | 'CPR_FISICA'
  | 'PENHOR_SAFRA' | 'PENHOR_MAQUINA' | 'HIPOTECA' | 'AVAL_FIANCA';

/** Distinção jurídica decisiva em cenário de RJ. Ver 02-motor-de-risco.md §10. */
export type NaturezaGarantia = 'EXTRACONCURSAL' | 'CONCURSAL';

export type EstadoCliente = 'ATIVO' | 'EM_OBSERVACAO' | 'SUSPENSO' | 'RJ_EM_CURSO' | 'FALENCIA';

export type RiscoZarc = 'baixo' | 'moderado' | 'alto' | 'critico';

export type FonteId =
  | 'RECEITA_FEDERAL' | 'REDESIM' | 'DATAJUD_CNJ' | 'DJE' | 'CARTORIO_PROTESTO'
  | 'PGFN' | 'TST_CNDT' | 'CAIXA_CRF_FGTS' | 'SICAR' | 'IBAMA'
  | 'CONAB' | 'MAPA_ZARC' | 'INMET' | 'INTERNO_KRILLTECH';

export type CodigoRecomendacao =
  | 'APROVAR'
  | 'APROVAR_COM_MONITORAMENTO_INTENSIVO'
  | 'APROVAR_COM_REVISAO_DE_LIMITE'
  | 'APROVAR_COM_RESTRICOES'
  | 'SUSPENDER_NOVA_EXPOSICAO_A_PRAZO'
  | 'SUSPENDER_EXPOSICAO';

export type DecisaoAnalista =
  | 'APROVAR' | 'APROVAR_COM_RESTRICOES' | 'REVISAR' | 'SUSPENDER' | 'RECUSAR';
```

---

## Identidade do cliente

```ts
export interface Cliente {
  id: string;                      // slug estável, ex.: 'vale-do-araguaia'
  razaoSocial: string;
  nomeFantasia?: string;
  documento: string;               // CPF ou CNPJ formatado, dígito verificador válido, SIMULADO
  tipoPessoa: TipoPessoa;
  municipio: string;
  uf: string;
  atividade: string;               // ex.: 'Produtor rural — grãos'
  cnaePrincipal: string;
  culturas: string[];              // ex.: ['Soja', 'Milho safrinha']
  inicioRelacionamento: string;    // ISO date
  estado: EstadoCliente;
  /** Distingue o fluxo A (due diligence) do fluxo B (monitoramento). Ver 03-ux-e-telas.md */
  origem: 'CARTEIRA' | 'PROSPECT';
}
```

---

## Fatos brutos (o que viria das fontes)

```ts
export interface FatosDoCliente {
  clienteId: string;
  /** Data de referência dos fatos. O motor NUNCA lê o relógio; recebe esta data. */
  dataReferencia: string;          // ISO date

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

export interface FatosInternos {
  atrasoMedioDias12m: number;
  atrasoMedioDias90d: number;
  piorAtrasoDias12m: number;
  pctTitulosPagosEmDia12m: number;   // 0..1
  renegociacoes12m: number;
  semAtrasoRelevante24m: boolean;
  /** Inadimplência TÉCNICA: covenants contratuais rompidos e ainda vigentes. */
  covenantsRompidos: CovenantRompido[];
}

export interface CovenantRompido {
  id: string;
  descricao: string;            // ex.: 'Endividamento total acima de 2,5× o patrimônio'
  limiteContratual: string;
  valorApurado: string;
  dataDeteccao: string;         // ISO date
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
  /** RJ ajuizada ou deferida. Ver Stay Period em 02-motor-de-risco.md §9. */
  recuperacaoJudicial?: {
    dataDistribuicao: string;
    dataDeferimento?: string;
    diasProrrogadosStay: number;
  };
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
  quebraSafraRegionalPct: number;       // 0..100
  desvioPrecipitacaoPct: number;        // pode ser negativo
  produtividadeVsMediaRegionalPct: number; // negativo = abaixo da média
  areaTotalHa: number;
  areaIrrigadaHa: number;
  seguroAgricolaVigente: boolean;
  safraReferencia: string;              // ex.: '2025/26'
}

export interface FatosCadastrais {
  situacaoRfb: 'ATIVA' | 'SUSPENSA' | 'INAPTA' | 'BAIXADA';
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
}

export interface FatosAmbientais {
  embargoIbamaVigente: boolean;
  /** Agrava para gatilho de veto: embargo recai sobre bem dado em garantia. */
  embargoSobreImovelEmGarantia: boolean;
  autoInfracaoNaoQuitado: boolean;
  situacaoCar: 'ATIVO_REGULAR' | 'PENDENTE' | 'IRREGULAR' | 'AUSENTE';
  sobreposicaoAppOuReserva: boolean;
}
```

---

## Exposição e garantias

```ts
export interface Operacao {
  id: string;
  tipo: TipoOperacao;
  descricao: string;             // ex.: 'Fornecimento de defensivos — safra 2025/26'
  saldoDevedor: number;
  dataContratacao: string;
  parcelas: Parcela[];
  /** Barter: safra prometida em contrapartida. Conecta risco agro ao dinheiro exposto. */
  barter?: {
    cultura: string;
    sacasPrometidas: number;
    precoReferenciaSaca: number;
    cprVinculadaId?: string;     // ausente = barter sem lastro formal (penalidade D4)
  };
}

export interface Parcela {
  id: string;
  vencimento: string;            // ISO date
  valor: number;
  status: 'A_VENCER' | 'PAGA' | 'EM_ATRASO';
  diasAtraso?: number;
}

export interface Garantia {
  id: string;
  tipo: TipoGarantia;
  /** DERIVADO do tipo por tabela fixa — nunca digitado no mock. Ver 02 §10. */
  natureza: NaturezaGarantia;
  descricao: string;
  valorDeclarado: number;
  /** valorDeclarado × (1 − haircut do tipo). Calculado, não digitado. */
  valorAtualizado: number;
  registrada: boolean;
  dataAvaliacao: string;
  /** true quando o bem está sob embargo ambiental — aciona VETO_EMBARGO_GARANTIA. */
  bemEmbargado?: boolean;
}
```

---

## Evidências

```ts
export interface Evidencia {
  id: string;
  fonte: FonteId;
  nomeFonte: string;              // rótulo humano: 'DataJud — CNJ'
  tipo: 'CERTIDAO' | 'PROCESSO' | 'PUBLICACAO' | 'CADASTRO' | 'LAUDO' | 'SERIE_HISTORICA' | 'INTERNO';
  titulo: string;
  resumo: string;
  dataConsulta: string;           // ISO date
  dataDocumento?: string;
  /** Sempre true nesta versão. Renderiza o selo "consulta simulada". */
  simulada: true;
  urlFicticia?: string;
  /** Fatores do motor que esta evidência sustenta. Liga evidência → número. */
  fatoresRelacionados: string[];
}
```

---

## Saída do motor (derivada, nunca persistida)

```ts
export interface FatorCalculado {
  id: string;
  dimensao: DimensaoId;
  rotulo: string;                 // texto pronto para a UI, em pt-BR
  detalhe?: string;               // ex.: 'atraso médio subiu de 3 para 11 dias'
  pontos: number;                 // sempre positivo
  direcao: 'risco' | 'protecao';
  /** peso(dimensão) × pontos × sinal. Soma de todos reconstrói o score. Ver I2. */
  impactoGlobal: number;
  impactoGlobalAjustado: number;  // após redistribuição de saturação
  fonte: FonteId;
  evidenciaIds: string[];
}

export interface DimensaoAvaliada {
  id: DimensaoId;
  rotulo: string;
  score: number;                  // 0..1000
  peso: number;                   // 0..1
  contribuicao: number;           // score × peso
  tendencia: Tendencia;
  fatores: FatorCalculado[];
  fontes: FonteId[];
  saturou: boolean;
}

export interface ProbabilidadeDeDefault {
  pd6m: number;   // 0..1
  pd12m: number;
  pd24m: number;
  metodo: string; // texto curto explicando a derivação, exibido em tooltip
}

export interface RiscoRJ {
  /** 0..1, ou 1 quando o evento já ocorreu. */
  probabilidade12m: number;
  eventoJaOcorrido: boolean;
  rjIndex: number;                // 0..100
  rjIndexEfetivo: number;
  elegivel: boolean;
  motivoInelegibilidade?: string;
  sinais: { rotulo: string; pontos: number }[];
}

export interface StayPeriod {
  ativo: boolean;
  dataDeferimento: string;
  diasDecorridos: number;
  diasRestantes: number;
  bloqueios: string[];            // o que a Krill Tech NÃO pode fazer
  permitido: string[];            // o que segue possível (extraconcursal)
}

export interface VetoAtivo {
  id: string;
  rotulo: string;
  efeito: 'FORCA_D' | 'TETO_C';
  justificativa: string;
  evidenciaIds: string[];
}

export interface ExposicaoCalculada {
  exposicaoTotal: number;
  limiteAprovado: number;
  limiteUtilizadoPct: number;
  aVencer90d: number;
  emAtraso: number;
  porTipoOperacao: Record<TipoOperacao, number>;
  valorExtraconcursal: number;
  valorConcursal: number;
  coberturaExtraconcursal: number;
  coberturaTotal: number;
  exposicaoProtegida: number;
  exposicaoEmRisco: number;
  /** O número que ninguém mais mostra. Ver 02 §10. */
  exposicaoEmRiscoEmRJ: number;
}

export interface RedFlag {
  id: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  data: string;
  fonte: FonteId;
  impactoEmPontos: number;        // negativo
  status: StatusRedFlag;
  evidenciaIds: string[];
  fatorId?: string;
}

export interface AcaoRecomendada {
  id: string;
  rotulo: string;                 // já parametrizado com os números do cliente
  detalhe?: string;
  prioridade: 1 | 2 | 3;
}

export interface Recomendacao {
  codigo: CodigoRecomendacao;
  rotulo: string;
  acoes: AcaoRecomendada[];
  prazoReavaliacaoDias: number;
  /** Preenchido pelo LLM em runtime; nunca vem do mock. Ver 04-camada-llm.md */
  explicacao?: string;
  aviso: 'Decisão final sujeita à avaliação do analista responsável.';
}

export interface AvaliacaoDeRisco {
  clienteId: string;
  dataReferencia: string;
  scoreCalculado: number;
  ratingCalculado: Rating;
  ratingFinal: Rating;
  vetosAtivos: VetoAtivo[];
  dimensoes: DimensaoAvaliada[];
  pd: ProbabilidadeDeDefault;
  riscoRJ: RiscoRJ;
  stayPeriod?: StayPeriod;
  exposicao: ExposicaoCalculada;
  tendencia: Tendencia;
  redFlags: RedFlag[];
  recomendacao: Recomendacao;
  evidencias: Evidencia[];
  auditoria: {
    somaImpactos: number;
    scoreReconstruido: number;
    /** Deve ser 0 (tolerância 0,5). Testado para os 18 clientes. Ver I2. */
    diferenca: number;
  };
}
```

---

## Série histórica e eventos

```ts
export interface SnapshotHistorico {
  data: string;
  fatos: FatosDoCliente;
}

export interface EventoDeRisco {
  id: string;
  clienteId: string;
  data: string;
  tipo:
    | 'NOVA_EXECUCAO' | 'NOVO_PROTESTO' | 'DIVIDA_ATIVA' | 'PEDIDO_RJ' | 'PEDIDO_FALENCIA'
    | 'EMBARGO_AMBIENTAL' | 'ALTERACAO_SOCIETARIA' | 'COVENANT_ROMPIDO'
    | 'MUDANCA_CLIMATICA' | 'ATRASO_PAGAMENTO' | 'CADASTRAL' | 'RECALCULO';
  severidade: Severidade;
  titulo: string;
  descricao: string;
  fonte: FonteId;
  scoreApos: number;              // derivado do recálculo do snapshot
  deltaScore: number;
  evidenciaIds: string[];
}

export interface Alerta {
  id: string;
  clienteId: string;
  clienteNome: string;
  data: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  impacto: string;
  acaoRecomendada: string;
  lido: boolean;
  eventoId?: string;
}
```

---

## Trilha de auditoria (human-in-the-loop)

```ts
export interface RegistroAuditoria {
  id: string;
  clienteId: string;
  clienteNome: string;
  analista: string;
  dataHora: string;               // ISO datetime
  scoreNoMomento: number;
  ratingNoMomento: Rating;
  recomendacaoGerada: CodigoRecomendacao;
  decisaoAnalista: DecisaoAnalista;
  justificativa: string;
  /** true quando o analista decidiu diferente do recomendado. Destacado na UI. */
  divergiuDaRecomendacao: boolean;
}
```

---

## Repositório (fronteira para API futura)

Toda leitura de dado passa por aqui. Assinatura assíncrona desde já, para que a troca do mock
por `fetch` não toque nenhum componente.

```ts
export interface RepositorioLastro {
  listarClientes(): Promise<Cliente[]>;
  obterCliente(id: string): Promise<Cliente | null>;
  obterFatosAtuais(clienteId: string): Promise<FatosDoCliente>;
  obterHistorico(clienteId: string): Promise<SnapshotHistorico[]>;
  obterEventos(clienteId: string): Promise<EventoDeRisco[]>;
  listarAlertas(): Promise<Alerta[]>;
  listarAuditoria(): Promise<RegistroAuditoria[]>;
  registrarDecisao(r: Omit<RegistroAuditoria, 'id'>): Promise<RegistroAuditoria>;
  /** Due diligence de prospect: resolve documento → perfil demonstrativo. */
  consultarDocumento(doc: string): Promise<Cliente | null>;
  /** Demo ao vivo: injeta evento e devolve os fatos recalculados. Ver 00 D10. */
  simularEvento(clienteId: string, tipo: EventoDeRisco['tipo']): Promise<FatosDoCliente>;
}
```

Implementação `MockRepositorio` em `lib/repository/mock.ts`. Mutações de sessão
(decisões do analista, eventos simulados, status de red flag) vivem em `localStorage`
sob a chave `lastro:sessao:v1`, com ação "Restaurar dados da demonstração".
