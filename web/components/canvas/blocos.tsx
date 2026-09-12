import { ListaRica, Rico } from "@/components/canvas/rico";
import {
  BarraDePesos,
  BarraDeRatings,
  CadeiaDeAgentes,
  CascataDoRecalculo,
  DegrausDaRecomendacao,
  FaixasDeRedFlags,
  LinhaDoTempo,
  NumerosDoRetorno,
} from "@/components/canvas/graficos";
import type { IndicadoresDaCarteira } from "@/components/canvas/tipos";

export interface PropsCorpo {
  ind: IndicadoresDaCarteira;
  /** true no modo de leitura ampliada: libera as colunas de detalhe das tabelas. */
  expandido?: boolean;
}

export interface BlocoDoCanvas {
  numero: number;
  titulo: string;
  manchete: string;
  /** colunas da grade 12×3 (spec 07 §1.4.2) */
  area: string;
  denso?: boolean;
  Corpo: (props: PropsCorpo) => React.ReactElement;
}

/* ======================================================================== */
/* Bloco 1 · PROBLEMA & DIAGNÓSTICO                                          */
/* ======================================================================== */

const ITENS_1 = [
  "**A dor (Desafio §2):** elevação acentuada da inadimplência, pedidos **repentinos** de Recuperação Judicial e quebra de produtores rurais e agroindústrias na carteira. Quando o cliente entra em RJ, o fluxo de caixa é severamente comprometido e a recuperação do capital vira um processo demorado e complexo.",
  "**Causa 1, marco legal:** a Lei nº 14.112/2020 estendeu a RJ ao **produtor rural pessoa física** com apenas 2 anos de atividade comprovada (Livro Caixa Digital ou inscrição estadual) → escalada de pedidos formais de RJ no campo.",
  "**Causa 2, margem estrangulada:** El Niño e La Niña e quebra de safra + fertilizantes e insumos caros + soja e milho em queda → liquidez de médios e grandes produtores esgotada.",
  "**Causa 3, efeito cascata:** o calote do produtor contamina distribuidores, revendas, tradings, indústria de equipamentos e **fornecedores de tecnologia e serviços. A Krill Tech está no fim da cadeia, é atingida por último e sem visibilidade.**",
  "**Agravante jurídico (Desafio §4):** deferida a RJ, o **Stay Period de 180 dias** (prorrogáveis) impede executar garantias e protestar. Penhor entra no plano com deságio; só a alienação fiduciária sobrevive (crédito extraconcursal).",
  "**Diagnóstico:** o problema não é falta de dado. São **14 fontes públicas dispersas**, sem cruzamento, sem antecedência e sem tradução em decisão de limite, prazo e garantia. A análise hoje reage ao **atraso**; precisa reagir ao **sinal**, e a inadimplência técnica vem antes da financeira.",
];

const ITENS_1_FOLHA = [
  "**A dor (Desafio §2):** inadimplência em alta e pedidos **repentinos** de RJ de produtores e agroindústrias. Quando a RJ chega, o caixa trava e recuperar o capital vira um processo de anos.",
  "**Por que agora:** a Lei 14.112/2020 abriu a RJ ao **produtor rural pessoa física** com 2 anos de atividade comprovada; clima ruim, insumo caro e grão em queda estrangularam a margem; o calote sobe a cadeia e a **Krill Tech, que está no fim dela, é atingida por último e sem visibilidade**.",
  "**Agravante jurídico (§4):** deferida a RJ, o **Stay Period de 180 dias** impede executar garantia e protestar. Penhor entra no plano com deságio; só a alienação fiduciária sobrevive.",
  "**Diagnóstico:** não falta dado. Faltam **14 fontes dispersas** cruzadas a tempo e traduzidas em limite, prazo e garantia. Hoje a análise reage ao **atraso**; precisa reagir ao **sinal**.",
];

function Corpo1({ ind, expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <ListaRica itens={expandido ? ITENS_1 : ITENS_1_FOLHA} />
      <p className="canvas-nota" title={ind.degradado ? "valor indisponível nesta sessão" : undefined}>
        Na carteira demonstrativa: {ind.emCouD} de {ind.total} clientes em C ou D ·{" "}
        {ind.exposicaoEmRiscoEmRJ} de exposição sem proteção efetiva em cenário de RJ ·{" "}
        {ind.rjEmCurso} RJ em curso.
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 2 · PÚBLICO-ALVO / BENEFICIÁRIOS                                    */
/* ======================================================================== */

const ITENS_2 = [
  "**Usuário direto:** analista de crédito e cobrança da Krill Tech. Decide limite, prazo e garantia em venda a prazo, barter e CPR. Recebe score, parecer e alertas; **mantém a decisão final** e registra justificativa.",
  "**Usuários secundários:** gestor de crédito / CFO (visão de carteira, exposição em risco em RJ, provisão) · comercial (consulta pré-venda de prospect por CPF/CNPJ) · jurídico (Stay Period, natureza concursal × extraconcursal das garantias).",
  "**Beneficiários indiretos:** a Krill Tech (caixa preservado, menor provisão, capital de giro liberado) · o produtor rural adimplente (crédito mais rápido e barato porque o risco é discriminado, não generalizado por safra ou região) · a cadeia agro B2B, revendas, cooperativas e distribuidores, clientes futuros da plataforma · o mercado de crédito agro, com menos contaminação em cascata.",
  "**Quem não é usuário nesta versão:** o produtor. Seus dados são tratados exclusivamente para análise de crédito, sob base legal de proteção ao crédito (LGPD, art. 7º, X) e com fonte pública identificada.",
];

const ITENS_2_FOLHA = [
  "**Usuário direto:** o analista de crédito da Krill Tech. Decide limite, prazo e garantia em venda a prazo, barter e CPR; recebe score, parecer e alertas e **mantém a decisão final**, com justificativa registrada.",
  "**Secundários:** gestor de crédito e CFO (exposição em risco em RJ, provisão) · comercial (consulta de prospect por CPF/CNPJ) · jurídico (Stay Period, concursal × extraconcursal).",
  "**Beneficiários indiretos:** o caixa da Krill Tech · o produtor adimplente, que deixa de pagar pelo risco dos outros · a cadeia agro B2B, futura cliente da plataforma.",
  "**Quem não é usuário:** o produtor. Seus dados são tratados só para análise de crédito, sob proteção ao crédito (LGPD, art. 7º, X), com fonte pública identificada.",
];

function Corpo2({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <ListaRica itens={expandido ? ITENS_2 : ITENS_2_FOLHA} />
    </div>
  );
}

/* ======================================================================== */
/* Bloco 3 · LÓGICA DE FUNCIONAMENTO DA SOLUÇÃO                              */
/* ======================================================================== */

const FLUXO_BLOCO_3 = [
  "**Entrada**, CPF/CNPJ de um prospect (fluxo A: due diligence) ou carteira já cadastrada (fluxo B: monitoramento).",
  "**Agente Coletor & Parser**, consulta 14 fontes públicas + dados internos da Krill Tech; faz parsing de publicações de Diários de Justiça e de certidões em PDF; normaliza tudo em **fatos com fonte, data e evidência**.",
  "**Agente de Risco Agro & Climático**, cruza a localização do imóvel (CAR) com o zoneamento ZARC, a quebra de safra regional, a precipitação (INMET) e a produtividade (CONAB); **liga o clima ao dinheiro exposto** em barter e CPR.",
  "**Motor de Decisão & Scoring** *(ML quantitativo, proprietário)*, 7 dimensões → score 0–1000 → rating A–D; PD em 6, 12 e 24 meses; **índice de RJ separado**; regras de veto; red flags; recomendação parametrizada. Determinístico e auditável: **a soma dos fatores reconstrói o score.**",
  "**Agente Sintetizador & Gerador de Relatórios** *(LLM)*, recebe os números prontos e redige o parecer, o “por que este score” e a recomendação em linguagem natural, citando evidências. **Nunca inventa nem altera um número.**",
  "**Analista decide**, aprova, restringe ou suspende, com trilha de auditoria. O monitoramento contínuo recalcula quando um novo evento é identificado e o ciclo recomeça.",
];

const FLUXO_BLOCO_3_FOLHA = [
  "**Entrada:** CPF/CNPJ de um prospect (due diligence) ou a carteira já cadastrada (monitoramento).",
  "**Coletor & Parser:** 14 fontes mapeadas, **7 já consultadas de verdade**, mais o histórico interno; tudo vira **fato com fonte, data e evidência**.",
  "**Risco Agro & Climático:** cruza a localização do imóvel com zoneamento, quebra de safra, chuva e produtividade, e **liga o clima ao dinheiro exposto**.",
  "**Motor de Decisão & Scoring** *(ML)*: 7 dimensões → score 0–1000 → rating A–D, PD 6/12/24 m, **índice de RJ separado**, vetos e recomendação. **A soma dos fatores reconstrói o score.**",
  "**Sintetizador** *(linguagem)*: recebe os números prontos e redige o parecer citando evidências. **Nunca inventa nem altera um número.**",
  "**Analista decide**, com trilha de auditoria. Um novo evento recalcula e o ciclo recomeça.",
];

function Corpo3({ expandido }: PropsCorpo) {
  const fluxo = expandido ? FLUXO_BLOCO_3 : FLUXO_BLOCO_3_FOLHA;
  return (
    <div className="canvas-corpo">
      <CadeiaDeAgentes />
      <ol className="canvas-lista" style={{ counterReset: "fluxo" }}>
        {fluxo.map((item, i) => (
          <li key={i}>
            <strong>{i + 1}.</strong> <Rico texto={item} />
          </li>
        ))}
      </ol>
      <p className="canvas-nota">
        Stack próprio da equipe: motor de risco, coleta pública e camada de linguagem em Python,
        interface web em TypeScript, orçamento de LLM controlado e fallback determinístico. Ver a
        aba Arquitetura.
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 4 · SCORE & CLASSIFICAÇÃO DE RATING                                 */
/* ======================================================================== */

const FAIXAS_DETALHE = [
  { rating: "A", faixa: "750–1000", rotulo: "Baixo risco", pd: "≤ 5,6%" },
  { rating: "B", faixa: "600–749", rotulo: "Risco moderado", pd: "5,6% – 17,6%" },
  { rating: "C", faixa: "400–599", rotulo: "Risco elevado", pd: "17,6% – 44%" },
  { rating: "D", faixa: "0–399", rotulo: "Risco crítico / Alerta de RJ", pd: "> 44%" },
];

const ITENS_4 = [
  "Cada dimensão parte de 1000 e sofre penalidades e bônus por fatores com pontos explícitos; o score é a média ponderada. Todo ponto tem fonte e evidência.",
  "**PD 12m** por curva logística calibrada sobre o score (ex.: 604 → 17,1%); **PD 6m e 24m** derivadas por hazard ajustado à tendência, com PD6 < PD12 < PD24 por construção.",
  "**Risco de RJ** é indicador próprio (índice 0–100 → probabilidade), alimentado por sinais de insolvência coletiva: pluralidade de credores, dívida judicializada, PGFN, falência requerida. Considera **elegibilidade pela Lei 14.112/2020**: PF sem 2 anos comprovados não tem via de RJ.",
  "**Veto acima do score:** RJ, falência, embargo sobre bem em garantia, cadastro inapto, lista suja e fraude forçam **D**; execução fiscal > 50% da exposição ou CNDT relevante limitam a **C**. O score calculado **permanece visível** ao lado da classificação final, com o motivo nomeado.",
];

const ITENS_4_FOLHA = [
  "Cada dimensão parte de 1000 e perde pontos por fator, com fonte e evidência. **PD** por curva logística sobre o score (604 → 17,1%), sempre PD6 < PD12 < PD24.",
  "**Risco de RJ** é indicador próprio: pluralidade de credores, dívida judicializada, PGFN, e **elegibilidade pela Lei 14.112/2020**.",
  "**Veto acima do score:** RJ, falência, embargo sobre bem em garantia, cadastro inapto, lista suja e fraude forçam **D**. O score calculado **continua visível**, com o motivo nomeado.",
];

function Corpo4({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <BarraDeRatings />
      {expandido ? (
        <>
          <table className="canvas-tabela">
            <thead>
              <tr>
                <th>Rating</th>
                <th>Faixa</th>
                <th>Rótulo</th>
                <th>PD 12m aproximada</th>
              </tr>
            </thead>
            <tbody>
              {FAIXAS_DETALHE.map((f) => (
                <tr key={f.rating}>
                  <td>
                    <strong>{f.rating}</strong>
                  </td>
                  <td>{f.faixa}</td>
                  <td>{f.rotulo}</td>
                  <td>{f.pd}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            <Rico texto="**Sete dimensões e pesos:** Comportamental / histórico interno **22%** · Jurídico & processual **20%** · Agro & climático **15%** · Fiscal & trabalhista **14%** · Cadastral & societário **10%** · Garantias & exposição **10%** · Ambiental **9%**." />
          </p>
        </>
      ) : (
        <p className="canvas-nota">
          <Rico texto="PD 12m por faixa: **A** até 5,6% · **B** 5,6% a 17,6% · **C** 17,6% a 44% · **D** acima de 44%." />
        </p>
      )}
      <BarraDePesos />
      <ListaRica itens={expandido ? ITENS_4 : ITENS_4_FOLHA} />
    </div>
  );
}

/* ======================================================================== */
/* Bloco 5 · MATRIZ DE RED FLAGS                                             */
/* ======================================================================== */

function Corpo5() {
  return (
    <div className="canvas-corpo">
      <FaixasDeRedFlags />
      <p className="canvas-nota">
        <Rico texto="Sinal-assinatura de RJ: **três ou mais credores distintos executando**, não é disputa bilateral, é crise de liquidez generalizada, o precursor clássico do pedido." />
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 6 · RECOMENDAÇÃO DE DECISÃO OPERACIONAL                             */
/* ======================================================================== */

const ACOES_BLOCO_6 = [
  "“Reduzir limite aprovado de R$ 5.000.000 para R$ 3.500.000 (−30%)”",
  "“Reduzir prazo de pagamento de 120 para 60 dias”",
  "“Exigir garantia adicional de R$ 1.480.000 para cobrir a exposição desprotegida”",
  "“Converter penhor de safra (R$ 900.000) em alienação fiduciária para blindar o crédito em cenário de RJ”",
  "“Exigir pagamento à vista” · “Bloquear aumento de limite” · “Acionar garantia extraconcursal”",
  "“Reavaliar em 30 dias”, com prazo por rating: A 180 d · B 90 d · C 30 d · D 7 d",
];

const ACOES_BLOCO_6_FOLHA = [
  "“Reduzir limite aprovado de R$ 5.000.000 para R$ 3.500.000 (−30%)” · “Reduzir prazo de 120 para 60 dias”",
  "“Exigir garantia adicional de R$ 1.480.000 para cobrir a exposição desprotegida”",
  "“Converter penhor de safra (R$ 900.000) em alienação fiduciária para blindar o crédito em RJ”",
  "“Reavaliar em 30 dias”, com prazo por rating: A 180 d · B 90 d · C 30 d · D 7 d",
];

function Corpo6({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <DegrausDaRecomendacao />
      <div>
        <p>
          <Rico texto="**Ações parametrizadas com os números do cliente**, saídas reais do motor:" />
        </p>
        <ListaRica itens={expandido ? ACOES_BLOCO_6 : ACOES_BLOCO_6_FOLHA} />
      </div>
      <p>
        <Rico
          texto={
            expandido
              ? "**Por rating:** **A** mantém limite e prazo (revisa limite se utilização > 90%) · **B** mantém com monitoramento; restringe se a exposição em risco em RJ passar de 40% · **C** reduz limite e prazo, exige garantia extraconcursal; suspende novo prazo se a deterioração for acelerada · **D** suspende exposição e aciona garantias extraconcursais."
              : "**Por rating: A** mantém limite e prazo · **B** mantém sob monitoramento e restringe acima de 40% de exposição em risco em RJ · **C** reduz limite e prazo e exige garantia extraconcursal · **D** suspende exposição e aciona as extraconcursais."
          }
        />
      </p>
      <p className="canvas-rodape-bloco">
        Decisão final sujeita à avaliação do analista responsável.{" "}
        <span style={{ fontWeight: 400, color: "var(--color-fg-secondary)" }}>
          Toda decisão fica registrada com justificativa e marca de divergência em relação à
          recomendação.
        </span>
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 7 · MONITORAMENTO CONTÍNUO / EARLY WARNING SYSTEM                   */
/* ======================================================================== */

const ITENS_7 = [
  "**Eventos monitorados:** nova execução de título · novo protesto · inscrição em dívida ativa · distribuição ou deferimento de RJ · pedido de falência · embargo ambiental · alteração societária · covenant rompido · deterioração climática regional · atraso de pagamento · alteração cadastral.",
  "**Cadência honesta:** fontes públicas varridas em ciclos próprios (diário a semanal, conforme a fonte); dados internos a cada fechamento; **nenhuma fonte é assumida como tempo real**, e toda evidência exibe a data da consulta.",
  "**Recálculo com explicação:** ao capturar um evento, o motor atualiza os fatos, recalcula e produz o delta por fator. Exemplo: **712 → 604 (−108)**, sendo 2 novas execuções de título −42 · nova inscrição em dívida ativa −31 · deterioração climática regional −18 · atraso médio de 3 d para 11 d −17.",
  "**Alertas:** por severidade, com impacto em pontos, ação recomendada e prazo; central de alertas mais timeline do cliente. Alerta CRÍTICO abre recomendação de suspensão. A tendência em 90 dias alimenta a PD e a recomendação.",
  "**Demonstrável ao vivo:** o controle “Simular evento de monitoramento” injeta um evento em um cliente e o recálculo acontece diante da banca.",
];

const ITENS_7_FOLHA = [
  "**Eventos monitorados:** execução de título · protesto · dívida ativa · RJ distribuída ou deferida · pedido de falência · embargo ambiental · alteração societária · covenant rompido · clima · atraso de pagamento.",
  "**Cadência honesta:** cada fonte tem o seu ciclo, do diário ao semanal; **nada é assumido como tempo real** e toda evidência mostra a data da consulta.",
  "**Recálculo com explicação:** o evento atualiza os fatos e o motor devolve o delta por fator, como na cascata acima. A tendência em 90 dias alimenta a PD e a recomendação.",
  "**Demonstrável ao vivo:** “Simular evento de monitoramento” injeta um evento e o recálculo acontece diante da banca.",
];

function Corpo7({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <CascataDoRecalculo />
      <ListaRica itens={expandido ? ITENS_7 : ITENS_7_FOLHA} />
    </div>
  );
}

/* ======================================================================== */
/* Bloco 8 · ARQUITETURA DE NEGÓCIOS & CUSTOS                                */
/* ======================================================================== */

const CUSTOS = [
  {
    item: "Coleta de dados",
    valor: "55 mil",
    nota: "Cartórios de protesto ≈ 15 mil (consulta paga por documento) · agregador processual/DJE ≈ 36 mil · Receita, PGFN, TST, CRF, DataJud, SICAR, IBAMA, CONAB, ZARC, INMET: gratuitos",
  },
  {
    item: "Infraestrutura",
    valor: "48 mil",
    nota: "Aplicação, processamento, armazenamento de evidências, filas de revarredura",
  },
  {
    item: "Inferência do LLM",
    valor: "12 mil",
    nota: "≈ US$ 0,02 por parecer; parsing assistido de publicações. **O LLM não é o custo relevante.**",
  },
  {
    item: "Time de sustentação",
    valor: "360 mil",
    nota: "1 engenheiro + 0,5 cientista de dados + jurídico consultivo",
  },
  {
    item: "Validação de modelo e auditoria",
    valor: "30 mil",
    nota: "Backtesting semestral, revisão de pesos, relatório de disparidade",
  },
  { item: "Contingência (10%)", valor: "50 mil", nota: "" },
];

const ITENS_8_FOLHA = [
  "**Estágio 1, ferramenta interna:** custo alocado ao centro de crédito, retorno em perda evitada e provisão reduzida.",
  "**Estágio 2, SaaS para a cadeia agro B2B:** **R$ 60 a 120/mês** por cliente monitorado, **due diligence avulsa R$ 180** e relatório de carteira para comitê. Equilíbrio com cerca de 3 carteiras do porte da Krill Tech.",
];

function Corpo8({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <NumerosDoRetorno />
      <ListaRica
        itens={
          expandido
            ? [
                "**Estágio 1, ferramenta interna da Krill Tech:** custo alocado ao centro de crédito; retorno medido em perda evitada e provisão reduzida.",
                "**Estágio 2, plataforma SaaS para a cadeia agro B2B** (revendas, cooperativas, distribuidores): assinatura por cliente monitorado **R$ 60 a 120/mês** por faixa de exposição + **due diligence avulsa R$ 180** + relatório de carteira para comitê. Ponto de equilíbrio com cerca de 3 carteiras do porte da Krill Tech.",
                "**Premissas de custo:** 500 clientes monitorados · 150 due diligences/ano · recálculo por evento mais ciclo semanal · custos em R$, valores de 2026, mão de obra com encargos. **Implementação única, 6 meses: cerca de R$ 480 mil**, com equipe de 4 (2 engenheiros, 1 cientista de dados, 1 especialista de crédito como PM), integrações reais, backtesting e homologação.",
              ]
            : ITENS_8_FOLHA
        }
      />
      {expandido ? (
        <table className="canvas-tabela">
          <thead>
            <tr>
              <th>Operação anual recorrente</th>
              <th>R$/ano</th>
              <th>Nota</th>
            </tr>
          </thead>
          <tbody>
            {CUSTOS.map((c) => (
              <tr key={c.item}>
                <td>{c.item}</td>
                <td>{c.valor}</td>
                <td>
                  <Rico texto={c.nota} />
                </td>
              </tr>
            ))}
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td>
                <strong>≈ 555 mil</strong>
              </td>
              <td>
                <strong>≈ R$ 92 por cliente monitorado por mês</strong>
              </td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p className="canvas-nota">
          <Rico texto="**Operação anual, R$ mil:** coleta 55 · infraestrutura 48 · inferência do LLM 12 · time de sustentação 360 · validação de modelo 30 · contingência 50 · **total ≈ 555**. Implantação única de 6 meses: **≈ R$ 480 mil**." />
        </p>
      )}
      <p>
        <Rico
          texto={
            expandido
              ? "**Caso de retorno:** cliente com exposição de **R$ 2 milhões** entra em RJ sem garantia extraconcursal → crédito quirografário entra no plano com deságio severo e prazo de vários anos (Desafio §4); recuperação típica de 20 a 40% → **perda de R$ 1,2 a 1,6 milhão**, mais o custo financeiro do prazo. Uma RJ **antecipada em 90 dias**, com redução de limite, encurtamento de prazo e conversão de penhor em alienação fiduciária, preserva **cerca de R$ 1 milhão**. Retorno de cerca de 1,8× o custo anual com **um** caso."
              : "**Caso de retorno:** cerca de R$ 92 por cliente monitorado por mês. Exposição de **R$ 2 milhões** em RJ sem garantia extraconcursal: recuperação típica de 20 a 40%, **perda de R$ 1,2 a 1,6 milhão**. Antecipar essa RJ em 90 dias preserva **cerca de R$ 1 milhão**, 1,8× o custo anual com **um** caso."
          }
        />
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 9 · PREMISSAS, RESTRIÇÕES E RISCOS                                  */
/* ======================================================================== */

const RISCOS = [
  {
    risco: "Disponibilidade e latência das bases públicas",
    tratamento:
      "Cache por fonte com data de consulta visível; dado indisponível **não zera** a dimensão, mantém o último valor com selo de defasagem e gera red flag informativa",
  },
  {
    risco: "Qualidade do parsing de Diários de Justiça e certidões em PDF",
    tratamento:
      "Dupla via (regras + extrator de linguagem), nível de confiança por evidência; evidência de baixa confiança vai para fila de validação humana **antes** de penalizar o score",
  },
  {
    risco: "Falso negativo do modelo (cliente ruim classificado como bom)",
    tratamento:
      "Regras de veto por fato jurídico acima do score; red flags independentes da nota; tendência em 90 dias como gatilho; backtesting em carteira histórica com métrica de recall em RJ",
  },
  {
    risco: "Viés por região, porte ou tipo de pessoa",
    tratamento:
      "Pesos configuráveis e publicados na aba Metodologia; veto só por fato jurídico, nunca por segmento; relatório semestral de disparidade por UF, cultura e PF/PJ",
  },
  {
    risco: "Automação sem supervisão",
    tratamento:
      "Decisão sempre do analista; trilha de auditoria com justificativa; divergência em relação à recomendação destacada e revisada",
  },
  {
    risco: "Alucinação do modelo de linguagem",
    tratamento:
      "LLM só redige a partir do JSON de números e evidências; validador rejeita qualquer valor numérico ausente da entrada; degradação para texto determinístico",
  },
  {
    risco: "LGPD e uso de dado público",
    tratamento:
      "Base legal: proteção ao crédito (art. 7º, X) e legítimo interesse (art. 7º, IX); minimização; dados de PF só com finalidade de crédito; retenção definida; sem comercialização de dado; direito de revisão de decisão automatizada (art. 20) atendido pela decisão humana obrigatória",
  },
];

const RISCOS_FOLHA = [
  {
    risco: "Base pública fora do ar",
    tratamento: "Cache com data visível; dado ausente **não zera** a dimensão",
  },
  {
    risco: "Parsing ruim de DJE e certidão",
    tratamento: "Regras mais extrator; evidência fraca vai a revisão humana antes de penalizar",
  },
  {
    risco: "Falso negativo do modelo",
    tratamento: "Veto jurídico acima do score, red flags fora da nota, backtesting por recall",
  },
  {
    risco: "Viés por região ou porte",
    tratamento: "Pesos publicados, veto só por fato jurídico, relatório semestral de disparidade",
  },
  {
    risco: "Automação sem supervisão",
    tratamento: "A decisão é do analista, com trilha e divergência destacada",
  },
  {
    risco: "Alucinação da linguagem",
    tratamento: "O texto nasce do JSON; número fora da entrada é rejeitado e cai para o determinístico",
  },
  {
    risco: "LGPD e dado público",
    tratamento: "Proteção ao crédito (art. 7º, X), minimização, revisão humana (art. 20)",
  },
];

function Corpo9({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      {expandido ? (
        <>
          <p>
            <Rico texto="**Premissas:** a carteira demonstrativa é simulada e traz o selo em toda tela; a coleta pública de 7 fontes já é real e alimenta a consulta por documento · o analista permanece o decisor · a Krill Tech fornece histórico interno de pagamento para a fase de piloto." />
          </p>
          <p>
            <Rico texto="**Restrições:** prazo do hackathon · sem banco persistente nesta versão · orçamento de LLM limitado, com fallback determinístico · coeficientes calibrados por especialista, não treinados em histórico real." />
          </p>
        </>
      ) : (
        <p>
          <Rico texto="**Premissas e restrições:** carteira demonstrativa simulada, com selo em toda tela; coleta pública de 7 fontes já real; o analista é o decisor; sem banco persistente; orçamento de LLM limitado, com fallback; coeficientes calibrados, não treinados." />
        </p>
      )}
      <table className="canvas-tabela">
        <thead>
          <tr>
            <th>Risco</th>
            <th>Como a equipe lida</th>
          </tr>
        </thead>
        <tbody>
          {(expandido ? RISCOS : RISCOS_FOLHA).map((r) => (
            <tr key={r.risco}>
              <td style={{ width: "34%" }}>
                <strong>{r.risco}</strong>
              </td>
              <td>
                <Rico texto={r.tratamento} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 10 · PRÓXIMOS PASSOS                                                */
/* ======================================================================== */

const ITENS_10_FOLHA = (total: string) => [
  `**Fase 0 · Hackathon (hoje):** motor determinístico auditável, ${total} clientes simulados, **coleta pública real de 7 fontes com warehouse próprio**, parecer imprimível, monitoramento demonstrável.`,
  "**Fase 1 · Piloto (0–3 meses):** ampliar a coleta para TST/CNDT, Caixa/CRF, DataJud e DJE; ingerir o histórico interno da Krill Tech; validar com 50 clientes reais e 3 analistas; backtesting de 24 meses.",
  "**Fase 2 · Produção (3–6 meses):** parsing de DJE e cartórios; SICAR e ZARC; modelo **treinado sobre histórico real** no lugar dos coeficientes calibrados à mão, **mantendo a decomposição por fator**; alertas e SLA de recálculo.",
  "**Fase 3 · Escala (6–12 meses):** SaaS para revendas, cooperativas e distribuidores; API para ERPs; módulo de barter; relatório de carteira para comitê.",
  "**Fase 4 · Rede (12+ meses):** consórcio de inadimplência técnica da cadeia, com consentimento, e score de cadeia: quem fornece para quem, e onde a cascata começa.",
];

function Corpo10({ ind, expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <LinhaDoTempo />
      <ListaRica
        itens={
          expandido
            ? [
                `**Fase 0 · Hackathon (hoje):** protótipo funcional, com motor determinístico auditável, ${ind.total} clientes simulados, coleta pública real de 7 fontes em warehouse DuckDB, parecer imprimível, monitoramento demonstrável, Canvas e arquitetura dentro da aplicação.`,
                "**Fase 1 · Piloto (0–3 meses):** ampliar a coleta real para TST/CNDT, Caixa/CRF, DataJud e agregadores de DJE; ingestão do histórico interno da Krill Tech; validação com 50 clientes reais e 3 analistas; backtesting em 24 meses de histórico para calibrar pesos e curvas.",
                "**Fase 2 · Produção (3–6 meses):** parsing de DJEs e cartórios de protesto; SICAR e ZARC; modelo estatístico **treinado sobre histórico real** substitui os coeficientes calibrados à mão, **mantendo a decomposição por fator**; alertas por e-mail e mensageria; SLA de recálculo.",
                "**Fase 3 · Escala (6–12 meses):** oferta SaaS para revendas, cooperativas e distribuidores; API para ERPs; módulo de barter com acompanhamento de safra; relatório de carteira para comitê de crédito.",
                "**Fase 4 · Rede (12+ meses):** consórcio de dados de inadimplência técnica da cadeia agro, com consentimento; score de cadeia, que mostra quem fornece para quem e onde a cascata começa.",
              ]
            : ITENS_10_FOLHA(ind.total)
        }
      />
    </div>
  );
}

/* ======================================================================== */

export const BLOCOS: BlocoDoCanvas[] = [
  {
    numero: 1,
    titulo: "Problema & diagnóstico",
    manchete:
      "A Krill Tech descobre a RJ do cliente quando já é tarde: o crédito anterior ao pedido entra no plano com deságio severo e prazo de anos.",
    area: "1 / 1 / 2 / 5",
    Corpo: Corpo1,
  },
  {
    numero: 2,
    titulo: "Público-alvo / beneficiários",
    manchete:
      "O usuário é o analista de crédito da Krill Tech. O beneficiário é o caixa da empresa, e, na ponta, o produtor saudável que deixa de pagar pelo risco dos outros.",
    area: "1 / 5 / 2 / 8",
    Corpo: Corpo2,
  },
  {
    numero: 3,
    titulo: "Lógica de funcionamento da solução",
    manchete: "Quatro agentes, um contrato: máquina calcula, linguagem explica, analista decide.",
    area: "1 / 8 / 2 / 13",
    Corpo: Corpo3,
  },
  {
    numero: 4,
    titulo: "Score & classificação de rating",
    manchete:
      "Nota de 0 a 1000, quatro faixas, sete dimensões, e um risco de RJ medido em separado, porque inadimplência e RJ não são o mesmo evento.",
    area: "2 / 1 / 3 / 4",
    Corpo: Corpo4,
  },
  {
    numero: 5,
    titulo: "Matriz de red flags",
    manchete:
      "Toda red flag nasce do mesmo fato que penaliza o score, carrega pontos, fonte, data e evidência, e nunca diverge da nota.",
    area: "2 / 4 / 3 / 7",
    Corpo: Corpo5,
  },
  {
    numero: 6,
    titulo: "Recomendação de decisão operacional",
    manchete: "A regra escolhe a decisão e calcula os números; o LLM apenas redige; o analista assina.",
    area: "2 / 7 / 3 / 10",
    Corpo: Corpo6,
  },
  {
    numero: 7,
    titulo: "Monitoramento contínuo / early warning system",
    manchete:
      "Monitoramento contínuo com recálculo automático: cada evento relevante identificado move o score e diz, ponto a ponto, por que mudou.",
    area: "2 / 10 / 3 / 13",
    Corpo: Corpo7,
  },
  {
    numero: 8,
    titulo: "Arquitetura de negócios & custos",
    manchete:
      "Cerca de R$ 555 mil por ano para 500 clientes monitorados. Uma única RJ antecipada preserva cerca de R$ 1 milhão. A primeira RJ paga o ano; a segunda é resultado.",
    area: "3 / 1 / 4 / 5",
    denso: true,
    Corpo: Corpo8,
  },
  {
    numero: 9,
    titulo: "Premissas, restrições e riscos",
    manchete:
      "A carteira desta demonstração é simulada, e diz isso em toda tela. Os riscos que importam são falso negativo, parsing ruim e automação sem supervisão, e cada um tem tratamento nomeado.",
    area: "3 / 5 / 4 / 10",
    denso: true,
    Corpo: Corpo9,
  },
  {
    numero: 10,
    titulo: "Próximos passos",
    manchete: "Do protótipo ao piloto real em 3 meses; à produção em 6; à plataforma de cadeia em 12.",
    area: "3 / 10 / 4 / 13",
    Corpo: Corpo10,
  },
];
