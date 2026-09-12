/* ------------------------------------------------------------------------ */
/* Conteúdo final da aba Arquitetura (spec 07 §2). Texto literal da spec.     */
/* ------------------------------------------------------------------------ */

export type Camada = "DADOS" | "ML" | "ML_LLM" | "LLM" | "HUMANO" | "LOOP";

export type Servico = "PY" | "TS" | "PY_TS";

export interface Etapa {
  numero: string;
  nome: string;
  agente: string;
  camada: Camada;
  camadaRotulo: string;
  entradaSaida: string;
  fontes: string;
  servico: Servico;
  servicoTexto: string;
  ondeAparece: string;
  chipTela: string;
  /** rota para a qual o chip "onde aparece" leva */
  href: string;
}

export const ETAPAS: Etapa[] = [
  {
    numero: "1",
    nome: "Fontes",
    agente: "Agente Coletor & Parser",
    camada: "DADOS",
    camadaRotulo: "Dados públicos",
    entradaSaida: "CPF/CNPJ → documentos, certidões, publicações, séries",
    fontes: "14 mapeadas, 7 consultadas de verdade",
    servico: "PY",
    servicoTexto:
      "coleta/ PY, um módulo por fonte, sobre httpx e DuckDB. Receita Federal, PGFN, IBAMA, IBGE/SIDRA, BCB/SICOR, clima e protestos são baixados de verdade; as demais seguem como contrato. A carteira de demonstração vem do dataset simulado em api/data/.",
    ondeAparece:
      "/nova-analise (busca por documento, que já cai na coleta pública) · /clientes/[id] › seção Evidências consultadas",
    chipTela: "nova análise",
    href: "/nova-analise",
  },
  {
    numero: "2",
    nome: "Coleta / Ingestão",
    agente: "Agente Coletor & Parser",
    camada: "DADOS",
    camadaRotulo: "Dados",
    entradaSaida: "Documentos brutos → Evidencia[] com fonte, data de consulta, tipo",
    fontes: "Todas",
    servico: "PY",
    servicoTexto:
      "coleta/ PY, warehouse DuckDB com a data de ingestão de cada carga, CLI própria (bulk, features, status) e cache por fonte. api/adaptadores/porta_coleta.py abre o warehouse em modo leitura, sem rede, e é a única fronteira de I/O do adaptador.",
    ondeAparece: "/clientes/[id] › Evidências (selo “consulta simulada” + data)",
    chipTela: "cliente › Evidências",
    href: "/carteira",
  },
  {
    numero: "3",
    nome: "Normalização",
    agente: "Agente Coletor & Parser",
    camada: "DADOS",
    camadaRotulo: "Dados",
    entradaSaida:
      "Evidências heterogêneas → FatosDoCliente tipado (interno, jurídico, fiscal, agro, cadastral, ambiental, operações, garantias)",
    fontes: "Todas",
    servico: "PY",
    servicoTexto:
      "api/ PY, coleta.features.build_features() monta 39 features e api/adaptadores/features_para_fatos.py as traduz em FatosDoCliente (pydantic v2, espelhando types/ do web/). Parsing de PDF e de DJE por regras continua sendo fase 2.",
    ondeAparece:
      "/clientes/[id] › cabeçalho e painéis de fatos; /metodologia › “Do fato ao fator”",
    chipTela: "cliente › Fatos",
    href: "/carteira",
  },
  {
    numero: "4",
    nome: "Feature engineering",
    agente: "Agente Coletor & Parser + Agente de Risco Agro & Climático",
    camada: "ML",
    camadaRotulo: "ML",
    entradaSaida:
      "FatosDoCliente → FatorCalculado[] por dimensão (pontos, direção, evidência)",
    fontes:
      "Interno, DataJud/DJE, cartórios, PGFN, TST, CRF, SICAR, IBAMA, CONAB, ZARC, INMET, RFB",
    servico: "PY",
    servicoTexto:
      "api/ PY, featurizers puros, um por dimensão, em api/scoring/; o Agente Agro cruza CAR × ZARC × quebra de safra × precipitação × produtividade",
    ondeAparece:
      "/clientes/[id] › Decomposição por dimensão (fatores com pontos e fonte)",
    chipTela: "cliente › Dimensões",
    href: "/carteira",
  },
  {
    numero: "5",
    nome: "Motor preditivo",
    agente: "Motor de Decisão & Scoring",
    camada: "ML",
    camadaRotulo: "ML",
    entradaSaida:
      "Fatores → score por dimensão → score 0–1000 → PD 6/12/24 m → índice e probabilidade de RJ",
    fontes: "Consome a etapa 4",
    servico: "PY",
    servicoTexto:
      "api/ PY, motor determinístico proprietário em Python: média ponderada, curva logística de PD, hazard por tendência, índice de RJ com elegibilidade (Lei 14.112/2020); coeficientes em api/scoring/config.py",
    ondeAparece:
      "/carteira › coluna Score/Rating · /clientes/[id] › gauge de score, PD nos três horizontes, Risco de RJ",
    chipTela: "carteira · gauge",
    href: "/carteira",
  },
  {
    numero: "6",
    nome: "Regras e red flags",
    agente: "Motor de Decisão & Scoring",
    camada: "ML",
    camadaRotulo: "ML / regras",
    entradaSaida:
      "Fatos + score → vetos (força D / teto C) → red flags por severidade → rating final",
    fontes: "Não se aplica",
    servico: "PY",
    servicoTexto:
      "api/ PY, tabela de gatilhos em api/scoring/config.py; red flags derivadas dos mesmos fatos",
    ondeAparece:
      "/clientes/[id] › Score calculado × Classificação final após regras, lista de red flags · /alertas",
    chipTela: "cliente › Regras",
    href: "/alertas",
  },
  {
    numero: "7",
    nome: "Score / PD / RJ",
    agente: "Motor de Decisão & Scoring",
    camada: "ML",
    camadaRotulo: "ML",
    entradaSaida:
      "Saída consolidada AvaliacaoDeRisco com auditoria de fechamento (diferenca = 0)",
    fontes: "Não se aplica",
    servico: "PY",
    servicoTexto:
      "api/ PY, função pura calcular_risco(fatos, config); invariantes I1–I6 em pytest (api/tests/); JSON devolvido ao web/ bate campo a campo com o tipo TypeScript",
    ondeAparece:
      "/carteira · /clientes/[id] · /metodologia › Auditoria de fechamento (“a soma dos fatores reconstrói o score”)",
    chipTela: "clientes › Auditoria",
    href: "/clientes",
  },
  {
    numero: "8",
    nome: "Camada de explicação",
    agente: "Agente Sintetizador & Gerador de Relatórios",
    camada: "LLM",
    camadaRotulo: "LLM",
    entradaSaida:
      "AvaliacaoDeRisco + evidências → texto “por que este score”, “por que mudou”, resumo executivo",
    fontes: "Não se aplica",
    servico: "PY",
    servicoTexto:
      "api/ PY, modelo de linguagem via API (SDK Python), prompts e guardas próprios; streaming repassado pelo proxy do web/ sem bufferizar; timeout 25 s; teto de orçamento; fallback determinístico",
    ondeAparece:
      "/clientes/[id] › Por que este score · Por que mudou · Copiloto “Pergunte sobre este cliente”",
    chipTela: "cliente › Por quê",
    href: "/carteira",
  },
  {
    numero: "9",
    nome: "Recomendação",
    agente: "Motor de Decisão & Scoring (decide) + Agente Sintetizador (redige)",
    camada: "ML_LLM",
    camadaRotulo: "ML → LLM",
    entradaSaida: "Regra escolhe código e ações parametrizadas → LLM redige a justificativa",
    fontes: "Não se aplica",
    servico: "PY",
    servicoTexto:
      "api/ PY, tabela de decisão da §12 do motor; o LLM recebe as ações prontas no mesmo serviço",
    ondeAparece:
      "/clientes/[id] › card Recomendação operacional · /clientes/[id]/parecer",
    chipTela: "cliente › Recomendação",
    href: "/carteira",
  },
  {
    numero: "10",
    nome: "Analista",
    agente: "Humano no circuito",
    camada: "HUMANO",
    camadaRotulo: "Humano",
    entradaSaida:
      "Recomendação → decisão (aprovar, restringir, revisar, suspender, recusar) + justificativa",
    fontes: "Não se aplica",
    servico: "TS",
    servicoTexto:
      "web/ TS, formulário de decisão e RegistroAuditoria em localStorage; enviado ao Flask junto da requisição quando altera o cálculo",
    ondeAparece: "/clientes/[id] › Registrar decisão · /auditoria",
    chipTela: "auditoria",
    href: "/auditoria",
  },
  {
    numero: "11",
    nome: "Monitoramento contínuo",
    agente: "Agente Coletor & Parser (revarredura) + Motor (recálculo)",
    camada: "LOOP",
    camadaRotulo: "Dados → ML",
    entradaSaida: "Novo evento → novos fatos → recálculo → delta por fator → alerta",
    fontes: "Todas, em ciclos por fonte",
    servico: "PY_TS",
    servicoTexto:
      "api/ PY, rota simular_evento no Flask injeta o evento e recalcula; snapshots recalculados; Σ deltas = Δ score (I6). web/ TS, dispara e exibe",
    ondeAparece:
      "/alertas › central · /clientes/[id] › timeline e “Por que mudou” · botão Simular evento de monitoramento",
    chipTela: "alertas · timeline",
    href: "/alertas",
  },
];

export const ETAPA_INTERFACE = {
  nome: "Interface (transversal)",
  camadaRotulo: "Apresentação",
  entradaSaida: "JSON do Flask → telas; stream de texto → prosa token a token",
  servicoTexto:
    "web/ TS, Next.js, React 19, Tailwind v4, SVG autoral do gauge; route handlers só fazem proxy; não recalcula nada",
  ondeAparece: "Todas as rotas",
};

export const FRONTEIRA = {
  nome: "Fronteira",
  regra: "Só números e evidências passam para a direita. Só texto volta para a esquerda.",
  servicoTexto:
    "api/ PY, contrato JSON de entrada do LLM montado a partir de AvaliacaoDeRisco; validador de saída rejeita números ausentes da entrada",
  ondeAparece: "Visível na própria aba como a régua horizontal entre as duas fileiras",
  acimaDireita: "Só números e evidências descem",
  abaixoEsquerda: "Só texto sobe",
};

export const TEXTO_PAINEL_LLM = {
  faz: "O que o LLM faz aqui: recebe o JSON com score, rating, PD, risco de RJ, fatores, red flags, garantias e evidências já calculados e escreve texto em português, citando a evidência de cada afirmação.",
  naoFaz:
    "O que o LLM não faz: não calcula, não arredonda, não estima, não escolhe a recomendação. Qualquer número no texto que não exista na entrada é rejeitado pelo validador e o bloco cai para o texto determinístico.",
};

export const TEXTO_PAINEL_ML = {
  faz: "O que o modelo quantitativo faz aqui: transforma fatos em pontos, pontos em score, score em probabilidade. Determinístico: a mesma entrada produz sempre a mesma saída, e a soma das contribuições reconstrói o resultado.",
  naoFaz:
    "O que ele não faz: não escreve texto. Toda frase que a banca lê vem da etapa 8 ou 9.",
};

export const TEXTO_PAINEL_FONTES =
  "Nenhuma chamada a órgão público é feita por esta aplicação. Os conectores existem como contrato na camada de repositório do serviço Python, não como implementação. A única chamada externa do sistema é a do modelo de linguagem, feita pelo Flask, com orçamento controlado.";

export const NOTA_FIXA = {
  titulo: "Este diagrama não é ilustrativo.",
  corpo:
    "Cada card das camadas ML e LLM aponta para código Python em execução no serviço api/ (Flask); cada card de interface aponta para a aplicação Next.js que você está usando agora. Os números que aparecem nas telas foram calculados pelo motor deste diagrama, nesta máquina, nesta sessão.",
};

export const LEGENDA = [
  {
    simbolo: "▰",
    titulo: "ML quantitativo / regras determinísticas",
    texto: "estima probabilidades, gera score. Produz números.",
    classe: "arq-legenda--ml",
  },
  {
    simbolo: "▱",
    titulo: "LLM",
    texto: "sintetiza evidências, explica, redige. Produz texto. Nunca produz número.",
    classe: "arq-legenda--llm",
  },
  {
    simbolo: "◌",
    titulo: "Fonte externa simulada",
    texto: "nenhuma chamada é feita.",
    classe: "arq-legenda--dados",
  },
  {
    simbolo: "●",
    titulo: "Humano no circuito",
    texto: "a decisão final é do analista.",
    classe: "arq-legenda--humano",
  },
];

/* ------------------------------------------------------------------------ */
/* §2.5, Mapeamento das fontes                                              */
/* ------------------------------------------------------------------------ */

export interface Fonte {
  id: string;
  nome: string;
  dimensaoDesafio: string;
  fornece: string;
  dimensaoScore: string;
  fatores: string;
  semIdProprio?: boolean;
}

export const FONTES: Fonte[] = [
  {
    id: "RECEITA_FEDERAL",
    nome: "Receita Federal, CNPJ Abertos",
    dimensaoDesafio: "Cadastral & Societário",
    fornece:
      "Situação cadastral, QSA, capital social, CNAE, filiais, data de abertura",
    dimensaoScore: "Cadastral & societário (10%)",
    fatores:
      "situacao_cadastral, tempo_atividade, capital_vs_exposicao, cnae_incompativel, qsa_estavel · veto VETO_CADASTRO_INAPTO",
  },
  {
    id: "REDESIM",
    nome: "Redesim",
    dimensaoDesafio: "Cadastral & Societário",
    fornece:
      "Alterações societárias, entrada/saída de sócios, mudança de administrador",
    dimensaoScore: "Cadastral & societário (10%)",
    fatores:
      "alteracao_societaria, saida_socio_majoritario · sinal de RJ “alteração de administrador em crise”",
  },
  {
    id: "DATAJUD_CNJ",
    nome: "DataJud do CNJ",
    dimensaoDesafio: "Processual & Jurídico",
    fornece:
      "Distribuição de execuções de título, pedidos de falência, RJ, partes e valores",
    dimensaoScore: "Jurídico & processual (20%)",
    fatores:
      "execucoes_titulo, materialidade_execucao, aceleracao_judicial, pluralidade_credores, pedido_falencia, rj_distribuida · vetos VETO_RJ, VETO_FALENCIA · índice de RJ",
  },
  {
    id: "DJE",
    nome: "Diários de Justiça Eletrônicos",
    dimensaoDesafio: "Processual & Jurídico",
    fornece:
      "Publicações: citações, deferimento de RJ, decisões de stay, editais",
    dimensaoScore: "Jurídico & processual (20%)",
    fatores: "Confirma e data os fatores acima; alimenta dataDeferimento do Stay Period",
  },
  {
    id: "DJE",
    semIdProprio: true,
    nome: "Jusbrasil / Escavador (agregadores)",
    dimensaoDesafio: "Processual & Jurídico",
    fornece:
      "Consolidação de publicações e processos por nome/documento, inclusive em tribunais sem API",
    dimensaoScore: "Jurídico & processual (20%)",
    fatores: "Mesmos fatores; reduz latência de captura de novos processos",
  },
  {
    id: "CARTORIO_PROTESTO",
    nome: "Cartórios de protesto",
    dimensaoDesafio: "Processual & Jurídico",
    fornece: "Protestos ativos, quantidade em 12 m, credores protestantes",
    dimensaoScore: "Jurídico & processual (20%)",
    fatores:
      "protestos, protesto_recorrente · sinal de RJ “protestos de credores distintos”",
  },
  {
    id: "PGFN",
    nome: "PGFN, dívida ativa",
    dimensaoDesafio: "Fiscal & Trabalhista",
    fornece:
      "Inscrições em dívida ativa, valor, evolução, parcelamentos e rompimentos, execuções fiscais",
    dimensaoScore: "Fiscal & trabalhista (14%)",
    fatores:
      "divida_ativa, divida_ativa_crescente, parcelamento_rompido · teto TETO_EXEC_FISCAL · índice de RJ",
  },
  {
    id: "TST_CNDT",
    nome: "TST, CNDT",
    dimensaoDesafio: "Fiscal & Trabalhista",
    fornece:
      "Certidão Negativa de Débitos Trabalhistas; débitos com trânsito em julgado",
    dimensaoScore: "Fiscal & trabalhista (14%) e Jurídico (20%)",
    fatores: "cndt_positiva, trabalhistas · teto TETO_CNDT",
  },
  {
    id: "CAIXA_CRF_FGTS",
    nome: "Caixa, CRF do FGTS",
    dimensaoDesafio: "Fiscal & Trabalhista",
    fornece: "Regularidade do FGTS",
    dimensaoScore: "Fiscal & trabalhista (14%)",
    fatores: "fgts_irregular, certidoes_negativas",
  },
  {
    id: "SICAR",
    nome: "SICAR",
    dimensaoDesafio: "Territorial & Ambiental",
    fornece:
      "Situação do CAR, área consolidada, reserva legal, APP, localização do imóvel",
    dimensaoScore: "Ambiental (9%) e Agro & climático (15%)",
    fatores:
      "car_ausente, car_irregular, sobreposicao_app, car_regular · fornece a localização que o Agente Agro cruza com ZARC/INMET",
  },
  {
    id: "IBAMA",
    nome: "IBAMA",
    dimensaoDesafio: "Territorial & Ambiental",
    fornece: "Embargos vigentes, autos de infração",
    dimensaoScore: "Ambiental (9%)",
    fatores:
      "embargo_ibama, auto_infracao · veto VETO_EMBARGO_GARANTIA quando o bem embargado está em garantia",
  },
  {
    id: "CONAB",
    nome: "CONAB",
    dimensaoDesafio: "Agronômico & Climático",
    fornece: "Produtividade média regional por cultura e safra; quebra de safra",
    dimensaoScore: "Agro & climático (15%)",
    fatores:
      "quebra_safra_regional, produtividade_abaixo · sinal de RJ “quebra > 25%”",
  },
  {
    id: "MAPA_ZARC",
    nome: "MAPA, ZARC",
    dimensaoDesafio: "Agronômico & Climático",
    fornece: "Risco climático da cultura por município e janela de plantio",
    dimensaoScore: "Agro & climático (15%)",
    fatores: "zarc_risco · sinal de RJ “ZARC alto/crítico”",
  },
  {
    id: "INMET",
    nome: "INMET",
    dimensaoDesafio: "Agronômico & Climático",
    fornece: "Séries históricas de precipitação e temperatura; desvio vs. normal",
    dimensaoScore: "Agro & climático (15%)",
    fatores: "desvio_precipitacao · evento MUDANCA_CLIMATICA no monitoramento",
  },
  {
    id: "INTERNO_KRILLTECH",
    nome: "Dados internos da Krill Tech",
    dimensaoDesafio: "Interno",
    fornece:
      "Histórico de pagamento, atrasos, renegociações, covenants, operações (venda a prazo, barter, CPR), garantias e limites",
    dimensaoScore: "Comportamental (22%) e Garantias & exposição (10%)",
    fatores:
      "atraso_medio, pior_atraso, pontualidade, renegociacoes, inadimplencia_tecnica, tendencia_atraso, relacionamento, historico_limpo, descoberto_extraconcursal, descoberto_total, utilizacao_limite, barter_sem_lastro",
  },
];

export const RODAPE_FONTES =
  "Nesta versão, nenhuma destas fontes é consultada. Os fatos vêm de um conjunto de dados fictício em api/data/, com documentos gerados e razões sociais inventadas, e toda evidência na aplicação traz o selo “consulta simulada” com a data. A camada de repositório do serviço Python já é a fronteira para integração real: trocar o dataset por conectores não altera nenhuma tela do Next.js.";

/* ------------------------------------------------------------------------ */
/* §2.7, O que está em execução agora                                       */
/* ------------------------------------------------------------------------ */

export interface LinhaExecucao {
  componente: string;
  caminho: string;
  estado: string;
  estadoRotulo: "Real." | "Parcial.";
  comoConfere: string;
}

export const EXECUCAO: LinhaExecucao[] = [
  {
    componente: "Camada de coleta pública",
    caminho: "coleta/ + api/adaptadores/ (Python)",
    estadoRotulo: "Real.",
    estado:
      "Sete fontes são baixadas de verdade e armazenadas num warehouse DuckDB: Receita Federal, PGFN, IBAMA, IBGE/SIDRA, BCB/SICOR, clima e protestos. O adaptador converte as 39 features em FatosDoCliente e relata a cobertura por dimensão. As outras sete fontes do mapa seguem como contrato, e a carteira de 18 clientes desta demonstração continua simulada.",
    comoConfere:
      "Consultar em /nova-analise um documento fora da carteira: a resposta vem da coleta pública, com o relatório de cobertura dizendo qual dimensão foi apurada e qual ficou cega",
  },
  {
    componente: "Motor de Decisão & Scoring",
    caminho: "api/scoring/ (Python)",
    estadoRotulo: "Real.",
    estado:
      "Função pura, determinística, com testes de invariantes (a soma dos fatores reconstrói o score). Coeficientes calibrados por especialista; treinamento estatístico sobre histórico real é Fase 2.",
    comoConfere:
      "Aba Metodologia › Auditoria de fechamento mostra diferença = 0 para cada cliente; pastilha viva “Flask · respondeu em {ms} ms” nesta página",
  },
  {
    componente: "Agente Sintetizador",
    caminho: "api/llm/ (Python)",
    estadoRotulo: "Real.",
    estado:
      "Chamada ao vivo ao modelo de linguagem via API, com streaming, timeout e teto de orçamento; fallback determinístico.",
    comoConfere:
      "Página do cliente › “Por que este score” chega token a token; contador de custo acumulado visível na interface",
  },
  {
    componente: "Agente Coletor & Parser e Agente de Risco Agro & Climático",
    caminho: "api/repository/, api/scoring/agro.py",
    estadoRotulo: "Parcial.",
    estado:
      "A lógica de normalização e de cruzamento (CAR × ZARC × safra × clima) roda de verdade sobre fatos simulados; os conectores às fontes públicas são contrato, não implementação.",
    comoConfere:
      "Evidências com selo “consulta simulada”; cards de fonte com badge SIMULADO, sem integração",
  },
  {
    componente: "Interface",
    caminho: "web/ (Next.js)",
    estadoRotulo: "Real.",
    estado:
      "Consome exclusivamente o JSON do Flask via proxy server-side; não recalcula nada.",
    comoConfere:
      "Desligar o Flask: a interface exibe estado de erro identificado, nunca números, porque não tem como produzi-los",
  },
];

export const FRASE_ENCERRAMENTO =
  "A diferença entre este diagrama e um slide é que ele pode ser desligado: pare o serviço Python e nenhum número aparece em tela nenhuma.";

/* ------------------------------------------------------------------------ */
/* Estado de execução por etapa.                                             */
/*                                                                           */
/* A spec 07 foi escrita quando a coleta ainda era contrato. Desde então a    */
/* camada `coleta/` passou a consultar fontes públicas de verdade, com        */
/* warehouse em DuckDB, e o adaptador `api/adaptadores/` liga essa coleta ao  */
/* motor. A página precisa dizer, etapa a etapa, o que roda hoje e o que      */
/* segue conceitual, é a diferença entre uma arquitetura e um slide.         */
/* ------------------------------------------------------------------------ */

export type NivelExecucao = "REAL" | "PARCIAL" | "CONCEITUAL";

export interface EstadoDaEtapa {
  nivel: NivelExecucao;
  rotulo: string;
  nota: string;
}

export const ESTADO_POR_ETAPA: Record<string, EstadoDaEtapa> = {
  "1": {
    nivel: "PARCIAL",
    rotulo: "Roda em parte",
    nota: "7 das 14 fontes são consultadas de verdade por coleta/: Receita Federal (dados abertos do CNPJ), PGFN, IBAMA, IBGE/SIDRA, BCB/SICOR, clima (NASA POWER, com INMET atrás da mesma interface) e protestos. As outras 7 seguem mapeadas como contrato, sem implementação, e a carteira de demonstração continua sendo um dataset simulado em api/data/.",
  },
  "2": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "coleta/ baixa, versiona e armazena as cargas num warehouse DuckDB, com CLI própria (bulk, features, status) e cache por fonte. Cada tabela guarda a data da ingestão, que é o que responde “esse dado está velho?”.",
  },
  "3": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "coleta.features.build_features() monta 39 features a partir do warehouse e api/adaptadores/features_para_fatos.py as traduz em FatosDoCliente. Campo sem fonte não vira zero: vira ausência declarada, e a dimensão cega sai da média ponderada com o peso redistribuído (api/adaptadores/cobertura.py).",
  },
  "4": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Featurizers puros em api/scoring/, um por dimensão, rodando sobre os fatos venham eles do dataset simulado ou da coleta pública. O caminho é o mesmo nos dois casos.",
  },
  "5": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Motor determinístico em Python. Coeficientes calibrados por especialista; o treinamento estatístico sobre histórico real é Fase 2, e a página diz isso em vez de insinuar o contrário.",
  },
  "6": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Tabela de gatilhos e red flags derivadas dos mesmos fatos que penalizam o score, no mesmo cálculo.",
  },
  "7": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Função pura calcular_risco(fatos, config), com as invariantes I1 a I6 cobertas por pytest. A auditoria de fechamento acompanha cada avaliação.",
  },
  "8": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Chamada ao vivo ao modelo de linguagem, com streaming repassado sem bufferizar, teto de orçamento e fallback determinístico completo.",
  },
  "9": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "A regra escolhe o código e parametriza as ações com os números do cliente; o texto de justificativa é redigido pelo modelo de linguagem sobre essas ações prontas.",
  },
  "10": {
    nivel: "REAL",
    rotulo: "Roda hoje",
    nota: "Formulário de decisão e trilha de auditoria na interface, em localStorage. Sem banco nesta versão, o que a página declara em vez de esconder.",
  },
  "11": {
    nivel: "PARCIAL",
    rotulo: "Roda em parte",
    nota: "O recálculo por evento é real e acontece no motor, diante da banca. O agendador que revarre as fontes em ciclo próprio é conceitual: hoje as cargas da coleta são disparadas pela CLI, não por agenda.",
  },
};

export const ORDEM_NIVEL: NivelExecucao[] = ["REAL", "PARCIAL", "CONCEITUAL"];

/* ------------------------------------------------------------------------ */
/* Quais das 14 fontes mapeadas são consultadas de verdade hoje.             */
/* ------------------------------------------------------------------------ */

export interface ColetaReal {
  /** casa com `Fonte.id` */
  fonteId: string;
  modulo: string;
  comoEColetada: string;
}

export const COLETA_REAL: ColetaReal[] = [
  {
    fonteId: "RECEITA_FEDERAL",
    modulo: "coleta/bulk/receita.py",
    comoEColetada:
      "Dados abertos do CNPJ, baixados por WebDAV do compartilhamento público e lidos direto do disco pelo read_csv do DuckDB. Cerca de 20 GB por competência, sem passar por memória.",
  },
  {
    fonteId: "PGFN",
    modulo: "coleta/bulk/pgfn.py",
    comoEColetada:
      "Arquivos trimestrais da dívida ativa da União, carregados por competência no warehouse.",
  },
  {
    fonteId: "IBAMA",
    modulo: "coleta/bulk/ibama.py",
    comoEColetada:
      "Autos de infração e termos de embargo, casados pelo CNPJ do autuado. CPF de pessoa física é guardado como veio e nada é derivado dele.",
  },
  {
    fonteId: "CONAB",
    modulo: "coleta/bulk/ibge_sidra.py",
    comoEColetada:
      "Produtividade municipal vem do IBGE/SIDRA, tabela 5457 da Produção Agrícola Municipal mais a LSPA, e não da CONAB. É a mesma pergunta, respondida por outra base oficial: quanto o município produziu por hectare, e quanto isso caiu.",
  },
  {
    fonteId: "INMET",
    modulo: "coleta/bulk/clima.py",
    comoEColetada:
      "Série diária da NASA POWER, em grade, com o INMET atrás da mesma interface. A anomalia contra a normal, o veranico e o déficit na fase crítica são calculados sobre a janela da safra, nunca sobre o ano civil.",
  },
  {
    fonteId: "CARTORIO_PROTESTO",
    modulo: "coleta/ondemand/protestos.py",
    comoEColetada:
      "Consulta por documento, com cache de 24 h. Não há API pública gratuita: o caminho do demo lê uma planilha preenchida à mão e a implementação de fornecedor homologado fica pronta atrás da mesma interface. O projeto não contorna CAPTCHA nem proteção anti-bot.",
  },
];

export const FONTE_EXTRA_BCB = {
  nome: "BCB, Matriz de Dados do Crédito Rural (SICOR)",
  modulo: "coleta/bulk/bcb_mdcr.py",
  papel:
    "Fonte que não estava no mapa das 14 e passou a ser coletada: valor e quantidade de contratos de custeio e investimento por município, com área financiada e o campo de seguro. É contexto regional de crédito, nunca dado individual.",
};

export const RODAPE_FONTES_ATUAL =
  "Sete destas fontes já são consultadas de verdade. O restante segue mapeado como contrato, sem implementação, e a carteira de 18 clientes desta demonstração continua vindo de um conjunto fictício em api/data/, com documentos gerados e razões sociais inventadas, toda evidência ali traz o selo “consulta simulada” com a data. Os dois caminhos chegam ao motor pela mesma porta: o adaptador em api/adaptadores/ converte as features da coleta pública em FatosDoCliente, que é exatamente o que o dataset simulado também entrega. Trocar um pelo outro não altera nenhuma tela do Next.js, e é por isso que a busca por um documento fora da carteira, em /nova-analise, já cai no caminho real.";

export const NOTA_COBERTURA = {
  titulo: "Dado ausente não vira dado bom.",
  corpo:
    "Quando uma fonte não responde, o campo não é preenchido com zero. A dimensão inteira sai da média ponderada e o peso é redistribuído entre as que foram apuradas, de modo que os pesos continuam somando 1,00 e a soma dos fatores continua reconstruindo o score. O relatório de cobertura mostra cada dimensão como apurada, parcial ou cega, porque “risco baixo” e “não olhei” produzem a mesma nota alta e só um dos dois é informação.",
};
