/**
 * Glossário de siglas (spec §6.13). Textos **obrigatórios e literais**.
 *
 * Toda sigla desta tabela aparece envolvida em `<Termo>` na primeira ocorrência
 * de cada página — é requisito do checklist de aceitação §12.
 */
export type TermoGlossario =
  | 'PD'
  | 'RJ'
  | 'CNDT'
  | 'CAR'
  | 'ZARC'
  | 'CPR'
  | 'EXTRACONCURSAL'
  | 'CONCURSAL'
  | 'STAY_PERIOD'
  | 'PGFN'
  | 'CRF_FGTS'
  | 'COVENANT'
  | 'BARTER'
  | 'HAIRCUT'
  | 'INADIMPLENCIA_TECNICA';

export interface VerbeteGlossario {
  /** Como a sigla é escrita na interface. */
  sigla: string;
  /** Expansão em negrito, quando existe. */
  titulo: string;
  /** Corpo do verbete. */
  texto: string;
}

export const GLOSSARIO: Record<TermoGlossario, VerbeteGlossario> = {
  PD: {
    sigla: 'PD',
    titulo: 'Probabilidade de Default.',
    texto:
      'Probabilidade estimada de o cliente ficar inadimplente no horizonte indicado (6, 12 ou 24 meses). Derivada do score por curva logística. Não é o mesmo que risco de RJ.',
  },
  RJ: {
    sigla: 'RJ',
    titulo: 'Recuperação Judicial (Lei 11.101/2005).',
    texto:
      'Processo em que o devedor renegocia dívidas sob supervisão judicial. Créditos anteriores ao pedido entram no plano com deságio; execuções ficam suspensas durante o Stay Period.',
  },
  CNDT: {
    sigla: 'CNDT',
    titulo: 'Certidão Negativa de Débitos Trabalhistas (TST).',
    texto:
      '"Positiva" indica débito trabalhista com trânsito em julgado e não quitado — passivo com preferência sobre credores quirografários.',
  },
  CAR: {
    sigla: 'CAR',
    titulo: 'Cadastro Ambiental Rural (SICAR).',
    texto:
      'Registro obrigatório do imóvel rural. Situação irregular ou ausente compromete a regularidade fundiária e o valor de execução da garantia.',
  },
  ZARC: {
    sigla: 'ZARC',
    titulo: 'Zoneamento Agrícola de Risco Climático (MAPA).',
    texto:
      'Classifica o risco climático da cultura na região e a janela de plantio recomendada. Base para seguro e crédito rural.',
  },
  CPR: {
    sigla: 'CPR',
    titulo: 'Cédula de Produto Rural.',
    texto:
      'Título de promessa de entrega de produto (CPR física) ou de pagamento em dinheiro (CPR financeira). Registrada, a CPR financeira é garantia extraconcursal.',
  },
  EXTRACONCURSAL: {
    sigla: 'extraconcursal',
    titulo: '',
    texto:
      'Crédito ou garantia fora dos efeitos da RJ (ex.: alienação fiduciária). Pode ser executado mesmo com plano em curso. É a única cobertura que protege de fato em cenário de RJ.',
  },
  CONCURSAL: {
    sigla: 'concursal',
    titulo: '',
    texto:
      'Crédito ou garantia sujeito ao plano de RJ (ex.: penhor, hipoteca, aval). Recebe com deságio e no prazo do plano aprovado pelos credores.',
  },
  STAY_PERIOD: {
    sigla: 'Stay Period',
    titulo: '',
    texto:
      'Suspensão de 180 dias (prorrogável uma vez) das execuções e cobranças contra o devedor após o deferimento da RJ (art. 6º, Lei 11.101/2005). Garantias extraconcursais não são atingidas.',
  },
  PGFN: {
    sigla: 'PGFN',
    titulo: 'Procuradoria-Geral da Fazenda Nacional.',
    texto:
      'Inscrição em dívida ativa federal; crédito tributário tem preferência sobre o crédito comercial.',
  },
  CRF_FGTS: {
    sigla: 'CRF/FGTS',
    titulo: 'Certificado de Regularidade do FGTS (Caixa).',
    texto: 'Irregularidade indica atraso de obrigações trabalhistas acessórias.',
  },
  COVENANT: {
    sigla: 'covenant',
    titulo: '',
    texto:
      'Cláusula contratual de desempenho (ex.: limite de endividamento). Rompida, configura inadimplência técnica — antes de qualquer atraso de pagamento.',
  },
  BARTER: {
    sigla: 'barter',
    titulo: '',
    texto:
      'Operação de troca: insumos fornecidos hoje contra entrega de safra futura. Exposição depende de produtividade, clima e integridade da área plantada.',
  },
  HAIRCUT: {
    sigla: 'haircut',
    titulo: '',
    texto:
      'Deságio aplicado ao valor declarado da garantia para estimar o valor de realização em execução. Varia por tipo (ex.: penhor de safra 40%, alienação fiduciária 20%).',
  },
  INADIMPLENCIA_TECNICA: {
    sigla: 'inadimplência técnica',
    titulo: '',
    texto:
      'Descumprimento de obrigação contratual não financeira — tipicamente um covenant rompido — configurado antes de qualquer atraso de pagamento. É o sinal que antecede o calote.',
  },
};

/** Texto plano do verbete, para `title` e `aria-label`. */
export function textoDoTermo(termo: TermoGlossario): string {
  const verbete = GLOSSARIO[termo];
  return verbete.titulo ? `${verbete.titulo} ${verbete.texto}` : verbete.texto;
}
