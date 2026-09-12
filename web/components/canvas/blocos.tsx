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

function Corpo1({ ind }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <ListaRica
        itens={[
          "**A dor (Desafio §2):** elevação acentuada da inadimplência, pedidos **repentinos** de Recuperação Judicial e quebra de produtores rurais e agroindústrias na carteira. Quando o cliente entra em RJ, o fluxo de caixa é severamente comprometido e a recuperação do capital vira um processo demorado e complexo.",
          "**Causa 1 — marco legal:** a Lei nº 14.112/2020 estendeu a RJ ao **produtor rural pessoa física** com apenas 2 anos de atividade comprovada (Livro Caixa Digital ou inscrição estadual) → escalada de pedidos formais de RJ no campo.",
          "**Causa 2 — margem estrangulada:** El Niño/La Niña e quebra de safra + fertilizantes e insumos caros + soja e milho em queda → liquidez de médios e grandes produtores esgotada.",
          "**Causa 3 — efeito cascata:** o calote do produtor contamina distribuidores, revendas, tradings, indústria de equipamentos e **fornecedores de tecnologia e serviços — a Krill Tech está no fim da cadeia, é atingida por último e sem visibilidade.**",
          "**Agravante jurídico (Desafio §4):** deferida a RJ, o **Stay Period de 180 dias** (prorrogáveis) impede executar garantias e protestar. Penhor entra no plano com deságio; só a alienação fiduciária sobrevive (crédito extraconcursal).",
          "**Diagnóstico:** o problema não é falta de dado. São **14 fontes públicas dispersas**, sem cruzamento, sem antecedência e sem tradução em decisão de limite, prazo e garantia. A análise hoje reage ao **atraso**; precisa reagir ao **sinal** — a inadimplência técnica vem antes da financeira.",
        ]}
      />
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

function Corpo2() {
  return (
    <div className="canvas-corpo">
      <ListaRica
        itens={[
          "**Usuário direto:** analista de crédito e cobrança da Krill Tech. Decide limite, prazo e garantia em venda a prazo, barter e CPR. Recebe score, parecer e alertas; **mantém a decisão final** e registra justificativa.",
          "**Usuários secundários:** gestor de crédito / CFO (visão de carteira, exposição em risco em RJ, provisão) · comercial (consulta pré-venda de prospect por CPF/CNPJ) · jurídico (Stay Period, natureza concursal × extraconcursal das garantias).",
          "**Beneficiários indiretos:** a Krill Tech (caixa preservado, menor provisão, capital de giro liberado) · o produtor rural adimplente (crédito mais rápido e barato porque o risco é discriminado, não generalizado por safra ou região) · a cadeia agro B2B — revendas, cooperativas, distribuidores — clientes futuros da plataforma · o mercado de crédito agro, com menos contaminação em cascata.",
          "**Quem não é usuário nesta versão:** o produtor. Seus dados são tratados exclusivamente para análise de crédito, sob base legal de proteção ao crédito (LGPD, art. 7º, X) e com fonte pública identificada.",
        ]}
      />
    </div>
  );
}

/* ======================================================================== */
/* Bloco 3 · LÓGICA DE FUNCIONAMENTO DA SOLUÇÃO                              */
/* ======================================================================== */

const FLUXO_BLOCO_3 = [
  "**Entrada** — CPF/CNPJ de um prospect (fluxo A: due diligence) ou carteira já cadastrada (fluxo B: monitoramento).",
  "**Agente Coletor & Parser** — consulta 14 fontes públicas + dados internos da Krill Tech; faz parsing de publicações de Diários de Justiça e de certidões em PDF; normaliza tudo em **fatos com fonte, data e evidência**.",
  "**Agente de Risco Agro & Climático** — cruza a localização do imóvel (CAR) com o zoneamento ZARC, a quebra de safra regional, a precipitação (INMET) e a produtividade (CONAB); **liga o clima ao dinheiro exposto** em barter e CPR.",
  "**Motor de Decisão & Scoring** *(ML quantitativo, proprietário)* — 7 dimensões → score 0–1000 → rating A–D; PD em 6, 12 e 24 meses; **índice de RJ separado**; regras de veto; red flags; recomendação parametrizada. Determinístico e auditável: **a soma dos fatores reconstrói o score.**",
  "**Agente Sintetizador & Gerador de Relatórios** *(LLM)* — recebe os números prontos e redige o parecer, o “por que este score” e a recomendação em linguagem natural, citando evidências. **Nunca inventa nem altera um número.**",
  "**Analista decide** — aprova, restringe ou suspende, com trilha de auditoria. O monitoramento contínuo recalcula quando um novo evento é identificado e o ciclo recomeça.",
];

function Corpo3() {
  return (
    <div className="canvas-corpo">
      <CadeiaDeAgentes />
      <ol className="canvas-lista" style={{ counterReset: "fluxo" }}>
        {FLUXO_BLOCO_3.map((item, i) => (
          <li key={i}>
            <strong>{i + 1}.</strong> <Rico texto={item} />
          </li>
        ))}
      </ol>
      <p className="canvas-nota">
        Stack próprio da equipe: motor de risco e camada de linguagem em Python (serviço de API),
        interface web em TypeScript, orçamento de LLM controlado e fallback determinístico. Ver aba
        Arquitetura.
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

function Corpo4({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <BarraDeRatings />
      <table className="canvas-tabela">
        <thead>
          <tr>
            <th>Rating</th>
            {expandido ? <th>Faixa</th> : null}
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
              {expandido ? <td>{f.faixa}</td> : null}
              <td>{f.rotulo}</td>
              <td>{f.pd}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        <Rico texto="**Sete dimensões e pesos:** Comportamental / histórico interno **22%** · Jurídico & processual **20%** · Agro & climático **15%** · Fiscal & trabalhista **14%** · Cadastral & societário **10%** · Garantias & exposição **10%** · Ambiental **9%**." />
      </p>
      <BarraDePesos />
      <ListaRica
        itens={[
          "Cada dimensão parte de 1000 e sofre penalidades e bônus por fatores com pontos explícitos; o score é a média ponderada. Todo ponto tem fonte e evidência.",
          "**PD 12m** por curva logística calibrada sobre o score (ex.: 604 → 17,1%); **PD 6m e 24m** derivadas por hazard ajustado à tendência — PD6 < PD12 < PD24 por construção.",
          "**Risco de RJ** é indicador próprio (índice 0–100 → probabilidade), alimentado por sinais de insolvência coletiva: pluralidade de credores, dívida judicializada, PGFN, falência requerida. Considera **elegibilidade pela Lei 14.112/2020** — PF sem 2 anos comprovados não tem via de RJ.",
          "**Veto acima do score:** RJ, falência, embargo sobre bem em garantia, cadastro inapto, lista suja e fraude forçam **D**; execução fiscal > 50% da exposição ou CNDT relevante limitam a **C**. O score calculado **permanece visível** ao lado da classificação final, com o motivo nomeado.",
        ]}
      />
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
        <Rico texto="Sinal-assinatura de RJ: **três ou mais credores distintos executando** — não é disputa bilateral, é crise de liquidez generalizada, o precursor clássico do pedido." />
      </p>
    </div>
  );
}

/* ======================================================================== */
/* Bloco 6 · RECOMENDAÇÃO DE DECISÃO OPERACIONAL                             */
/* ======================================================================== */

function Corpo6() {
  return (
    <div className="canvas-corpo">
      <DegrausDaRecomendacao />
      <div>
        <p>
          <Rico texto="**Ações parametrizadas com os números do cliente** (exemplos reais do motor):" />
        </p>
        <ListaRica
          itens={[
            "“Reduzir limite aprovado de R$ 5.000.000 para R$ 3.500.000 (−30%)”",
            "“Reduzir prazo de pagamento de 120 para 60 dias”",
            "“Exigir garantia adicional de R$ 1.480.000 para cobrir a exposição desprotegida”",
            "“Converter penhor de safra (R$ 900.000) em alienação fiduciária para blindar o crédito em cenário de RJ”",
            "“Exigir pagamento à vista” · “Bloquear aumento de limite” · “Acionar garantia extraconcursal”",
            "“Reavaliar em 30 dias” — prazo por rating: A 180 d · B 90 d · C 30 d · D 7 d",
          ]}
        />
      </div>
      <p>
        <Rico texto="**Por rating:** **A** mantém limite e prazo (revisa limite se utilização > 90%) · **B** mantém com monitoramento; restringe se a exposição em risco em RJ passar de 40% · **C** reduz limite e prazo, exige garantia extraconcursal; suspende novo prazo se a deterioração for acelerada · **D** suspende exposição e aciona garantias extraconcursais." />
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

function Corpo7() {
  return (
    <div className="canvas-corpo">
      <CascataDoRecalculo />
      <ListaRica
        itens={[
          "**Eventos monitorados:** nova execução de título · novo protesto · inscrição em dívida ativa · distribuição ou deferimento de RJ · pedido de falência · embargo ambiental · alteração societária · covenant rompido · deterioração climática regional · atraso de pagamento · alteração cadastral.",
          "**Cadência honesta:** fontes públicas varridas em ciclos próprios (diário a semanal, conforme a fonte); dados internos a cada fechamento; **nenhuma fonte é assumida como tempo real** — toda evidência exibe a data da consulta.",
          "**Recálculo com explicação:** ao capturar um evento, o motor atualiza os fatos, recalcula e produz o delta por fator. Exemplo: **712 → 604 (−108)** — 2 novas execuções de título −42 · nova inscrição em dívida ativa −31 · deterioração climática regional −18 · atraso médio (3 d → 11 d) −17.",
          "**Alertas:** por severidade, com impacto em pontos, ação recomendada e prazo; central de alertas + timeline do cliente. Alerta CRÍTICO abre recomendação de suspensão. Tendência em 90 dias (melhorando · estável · deteriorando · deterioração acelerada) alimenta a PD e a recomendação.",
          "**Demonstrável ao vivo:** o controle “Simular evento de monitoramento” injeta um evento em um cliente e o recálculo acontece diante da banca.",
        ]}
      />
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

function Corpo8({ expandido }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <NumerosDoRetorno />
      <ListaRica
        itens={[
          "**Estágio 1 — ferramenta interna da Krill Tech:** custo alocado ao centro de crédito; retorno medido em perda evitada e provisão reduzida.",
          "**Estágio 2 — plataforma SaaS para a cadeia agro B2B** (revendas, cooperativas, distribuidores): assinatura por cliente monitorado **R$ 60 a 120/mês** por faixa de exposição + **due diligence avulsa R$ 180** + relatório de carteira para comitê. Ponto de equilíbrio com ≈ 3 carteiras do porte da Krill Tech.",
        ]}
      />
      <p>
        <Rico texto="**Premissas de custo:** 500 clientes monitorados · 150 due diligences/ano · recálculo por evento + ciclo semanal · custos em R$, valores de 2026, mão de obra com encargos. **Implementação (única, 6 meses): ≈ R$ 480 mil** — equipe de 4 (2 engenheiros, 1 cientista de dados, 1 especialista de crédito atuando como PM), integrações reais, backtesting e homologação." />
      </p>
      <table className="canvas-tabela">
        <thead>
          <tr>
            <th>Operação anual recorrente</th>
            <th>R$/ano</th>
            {expandido ? <th>Nota</th> : null}
          </tr>
        </thead>
        <tbody>
          {CUSTOS.map((c) => (
            <tr key={c.item}>
              <td>{c.item}</td>
              <td>{c.valor}</td>
              {expandido ? (
                <td>
                  <Rico texto={c.nota} />
                </td>
              ) : null}
            </tr>
          ))}
          <tr>
            <td>
              <strong>Total</strong>
            </td>
            <td>
              <strong>≈ 555 mil</strong>
            </td>
            {expandido ? (
              <td>
                <strong>≈ R$ 92 por cliente monitorado por mês</strong>
              </td>
            ) : null}
          </tr>
        </tbody>
      </table>
      {expandido ? null : (
        <p className="canvas-nota">≈ R$ 92 por cliente monitorado por mês.</p>
      )}
      <p>
        <Rico texto="**Caso de retorno:** cliente com exposição de **R$ 2 milhões** entra em RJ sem garantia extraconcursal → crédito quirografário entra no plano com deságio severo e prazo de vários anos (Desafio §4); recuperação típica de 20 a 40% → **perda de R$ 1,2 a 1,6 milhão**, mais o custo financeiro do prazo. Uma RJ **antecipada em 90 dias** — redução de limite, encurtamento de prazo e conversão de penhor em alienação fiduciária — preserva **≈ R$ 1 milhão**. Retorno ≈ 1,8× o custo anual com **um** caso." />
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
      "Cache por fonte com data de consulta visível; dado indisponível **não zera** a dimensão — mantém o último valor com selo de defasagem e gera red flag informativa",
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

function Corpo9() {
  return (
    <div className="canvas-corpo">
      <p>
        <Rico texto="**Premissas:** dados desta versão são simulados e nenhuma integração real é feita ou insinuada · as fontes públicas da §5 do desafio existem e são acessíveis · o analista permanece o decisor · a Krill Tech fornece histórico interno de pagamento para a fase de piloto." />
      </p>
      <p>
        <Rico texto="**Restrições:** prazo do hackathon · sem backend persistente nesta versão · LLM com orçamento limitado e fallback determinístico · coeficientes calibrados por especialista, não treinados em histórico real." />
      </p>
      <table className="canvas-tabela">
        <thead>
          <tr>
            <th>Risco</th>
            <th>Como a equipe lida</th>
          </tr>
        </thead>
        <tbody>
          {RISCOS.map((r) => (
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

function Corpo10({ ind }: PropsCorpo) {
  return (
    <div className="canvas-corpo">
      <LinhaDoTempo />
      <ListaRica
        itens={[
          `**Fase 0 · Hackathon (hoje):** protótipo funcional — motor determinístico auditável, ${ind.total} clientes simulados, parecer imprimível, monitoramento demonstrável, Canvas e arquitetura dentro da aplicação.`,
          "**Fase 1 · Piloto (0–3 meses):** integrações reais com Receita Federal, PGFN, TST/CNDT, Caixa/CRF e DataJud; ingestão do histórico interno da Krill Tech; validação com 50 clientes reais e 3 analistas; backtesting em 24 meses de histórico para calibrar pesos e curvas.",
          "**Fase 2 · Produção (3–6 meses):** parsing de DJEs e cartórios de protesto; SICAR, IBAMA, ZARC, CONAB e INMET; modelo estatístico **treinado sobre histórico real** substitui os coeficientes calibrados à mão, **mantendo a decomposição por fator**; alertas por e-mail e mensageria; SLA de recálculo.",
          "**Fase 3 · Escala (6–12 meses):** oferta SaaS para revendas, cooperativas e distribuidores; API para ERPs; módulo de barter com acompanhamento de safra; relatório de carteira para comitê de crédito.",
          "**Fase 4 · Rede (12+ meses):** consórcio de dados de inadimplência técnica da cadeia agro, com consentimento; score de cadeia — quem fornece para quem, e onde a cascata começa.",
        ]}
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
      "O usuário é o analista de crédito da Krill Tech. O beneficiário é o caixa da empresa — e, na ponta, o produtor saudável que deixa de pagar pelo risco dos outros.",
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
      "Nota de 0 a 1000, quatro faixas, sete dimensões — e um risco de RJ medido em separado, porque inadimplência e RJ não são o mesmo evento.",
    area: "2 / 1 / 3 / 4",
    Corpo: Corpo4,
  },
  {
    numero: 5,
    titulo: "Matriz de red flags",
    manchete:
      "Toda red flag nasce do mesmo fato que penaliza o score — carrega pontos, fonte, data e evidência, e nunca diverge da nota.",
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
      "Esta versão é 100% simulada, e diz isso em toda tela. Os riscos que importam são falso negativo, parsing ruim e automação sem supervisão — cada um tem tratamento nomeado.",
    area: "3 / 5 / 4 / 9",
    denso: true,
    Corpo: Corpo9,
  },
  {
    numero: 10,
    titulo: "Próximos passos",
    manchete: "Do protótipo ao piloto real em 3 meses; à produção em 6; à plataforma de cadeia em 12.",
    area: "3 / 9 / 4 / 13",
    Corpo: Corpo10,
  },
];
