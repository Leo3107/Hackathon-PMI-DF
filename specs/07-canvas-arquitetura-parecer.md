# 07 — Project Canvas, Aba Arquitetura e Parecer de Risco imprimível

> Três superfícies do **Lastro** voltadas à banca: a página que **é** o entregável oficial (`/canvas`),
> a página que prova a credibilidade técnica (`/arquitetura`) e o documento que materializa o
> "Relatório Padronizado de Risco de Crédito e Alerta Precoce de RJ/Insolvência" (`/clientes/[id]/parecer`).
>
> Onde este arquivo traz texto de interface, o texto é **final** — copiar para o código sem reescrever.
> Fonte numérica de tudo: `02-motor-de-risco.md`. Decisões que vencem qualquer coisa aqui: `00-decisoes.md`.

Referências: Documento de Desafio §2, §3, §4, §5, §6, §7.1 · `00-decisoes.md` D1, D2, D4, D5, D6, D7, D9, D11 · `01-modelo-de-dados.md` · `02-motor-de-risco.md`

---

## 0. Premissas transversais deste arquivo

### 0.1 Rotas assumidas

Os arquivos `03-ux-e-telas.md` e `04-camada-llm.md` ainda não existem no momento desta escrita. As rotas abaixo
são as **assumidas** por esta spec; se o `03` definir nomes diferentes, **o `03` prevalece** e quem implementar
esta spec faz a substituição mecânica.

| Rota | Tela | Papel nesta spec |
|---|---|---|
| `/carteira` | Carteira (lista dos 18 clientes, score, rating, tendência) | Destino do redirecionamento de `/` (D11.8) |
| `/clientes/[id]` | Página do cliente (gauge, dimensões, red flags, garantias, timeline, recomendação, copiloto) | Onde a maioria das etapas do pipeline "aparece" |
| `/clientes/[id]/parecer` | **Parecer de Risco** imprimível | Parte 3 |
| `/alertas` | Central de alertas | Etapa "Monitoramento contínuo" |
| `/due-diligence` | Consulta de prospect por CPF/CNPJ (fluxo A) | Etapa "Fontes / Coleta" |
| `/auditoria` | Trilha de decisões do analista | Etapa "Analista" |
| `/metodologia` | Pesos, fórmulas, curvas de PD, catálogo de fatores | Referência cruzada do bloco 4 do Canvas |
| `/arquitetura` | Pipeline conceitual | Parte 2 |
| `/canvas` | Project Canvas | Parte 1 |

### 0.2 Regras que valem para as três superfícies

1. **Banner global** `DADOS SIMULADOS — protótipo demonstrativo` permanece visível em tela (D11.7). Em impressão,
   é reproduzido no cabeçalho de **toda** página gerada.
2. **Nenhuma menção** a fornecedores de nuvem/IA de terceiros como parte da arquitetura conceitual, e **zero
   menção** ao ecossistema do parceiro tecnológico citado no documento de desafio (ferramentas e agentes
   nomeados na §1 e na §6 daquele documento) em qualquer ponto (D6). Quando for preciso nomear o modelo de linguagem, usar
   "modelo de linguagem via API, intercambiável" — o nome do modelo pode aparecer **apenas** no contador de custo
   já previsto em D5, nunca nestas três superfícies.
3. **Nomes oficiais**: "Krill Tech" (duas palavras), "Lastro", "Parecer de Risco" na UI e "Relatório Padronizado
   de Risco de Crédito e Alerta Precoce de RJ/Insolvência" como título formal do documento impresso (D2).
4. Cores de risco (verde/âmbar/laranja/vermelho) são exclusivas de A/B/C/D e de severidade. Toda ocorrência de
   cor vem acompanhada de rótulo textual (D9).
5. **Impressão em fundo claro.** A aplicação é dark-only em tela (D9), mas o `@media print` de `/canvas` e do
   parecer usa fundo branco, texto `#111`, e mantém as cores semânticas de risco em tons imprimíveis. Isso não é
   "tema claro" — é print stylesheet, e só existe nestas duas rotas.
6. Toda exportação em PDF é `window.print()` sobre print stylesheet (D11.4). Zero biblioteca de PDF.

### 0.3 Valores dinâmicos no Canvas

O Canvas é renderizado pela própria aplicação, então alguns números **vêm do motor**, não de texto fixo. Sintaxe
nesta spec: `{{token}}`. Cada token tem fallback textual para o caso improvável de falha do repositório.

| Token | Origem | Fallback |
|---|---|---|
| `{{carteira.total}}` | `listarClientes().length` | `18` |
| `{{carteira.emCouD}}` | clientes com `ratingFinal ∈ {C, D}` | `—` |
| `{{carteira.exposicaoEmRiscoEmRJ}}` | `Σ exposicao.exposicaoEmRiscoEmRJ` em BRL compacto (ex.: `R$ 7,4 mi`) | `—` |
| `{{carteira.comVeto}}` | clientes com `vetosAtivos.length > 0` | `—` |
| `{{carteira.rjEmCurso}}` | clientes com `estado === 'RJ_EM_CURSO'` | `—` |
| `{{data.hoje}}` | data de referência da aplicação, `dd/mm/aaaa` | data do build |

---

# PARTE 1 — Project Canvas (`/canvas`)

## 1.1 Propósito e postura

O Canvas é o entregável oficial (D1). É lido em três situações: (a) projetado durante o pitch, a 4–6 metros,
(b) impresso em A4 paisagem e entregue à banca, (c) aberto na tela pelo jurado que quiser conferir. O texto abaixo
é o texto final. Nenhum bloco depende do LLM. Nenhum bloco espera rede.

## 1.2 Cabeçalho da página (texto final)

```
LASTRO                                                     DADOS SIMULADOS — protótipo demonstrativo
Inteligência de risco de crédito e alerta precoce de RJ no agronegócio
Project Canvas · Hackathon PMI-DF 2026 · Edital 01/2026 · Desafio Krill Tech · {{data.hoje}}
```

Tagline (exibida sob o título, itálico, legível a distância):

> **Saber antes do calote. Proteger antes da RJ.**

Botões no canto superior direito (somente tela, ocultos na impressão): `Modo apresentação` · `Exportar PDF (A4 paisagem)` · `Abrir protótipo →` (link para `/carteira`).

## 1.3 Os dez blocos — texto final

Cada bloco tem: **numeral + título** (caixa alta), uma **manchete** (uma frase em negrito, o que precisa ser lido a
distância) e o **corpo**. O corpo usa itens curtos; onde houver "→", é uma relação causa/efeito que a UI pode
renderizar como seta.

---

### Bloco 1 · PROBLEMA & DIAGNÓSTICO

**Manchete:** A Krill Tech descobre a RJ do cliente quando já é tarde: o crédito anterior ao pedido entra no plano com deságio severo e prazo de anos.

Corpo:

- **A dor (Desafio §2):** elevação acentuada da inadimplência, pedidos **repentinos** de Recuperação Judicial e quebra de produtores rurais e agroindústrias na carteira. Quando o cliente entra em RJ, o fluxo de caixa é severamente comprometido e a recuperação do capital vira um processo demorado e complexo.
- **Causa 1 — marco legal:** a Lei nº 14.112/2020 estendeu a RJ ao **produtor rural pessoa física** com apenas 2 anos de atividade comprovada (Livro Caixa Digital ou inscrição estadual) → escalada de pedidos formais de RJ no campo.
- **Causa 2 — margem estrangulada:** El Niño/La Niña e quebra de safra + fertilizantes e insumos caros + soja e milho em queda → liquidez de médios e grandes produtores esgotada.
- **Causa 3 — efeito cascata:** o calote do produtor contamina distribuidores, revendas, tradings, indústria de equipamentos e **fornecedores de tecnologia e serviços — a Krill Tech está no fim da cadeia, é atingida por último e sem visibilidade.**
- **Agravante jurídico (Desafio §4):** deferida a RJ, o **Stay Period de 180 dias** (prorrogáveis) impede executar garantias e protestar. Penhor entra no plano com deságio; só a alienação fiduciária sobrevive (crédito extraconcursal).
- **Diagnóstico:** o problema não é falta de dado. São **14 fontes públicas dispersas**, sem cruzamento, sem antecedência e sem tradução em decisão de limite, prazo e garantia. A análise hoje reage ao **atraso**; precisa reagir ao **sinal** — a inadimplência técnica vem antes da financeira.
- *Na carteira demonstrativa:* {{carteira.emCouD}} de {{carteira.total}} clientes em C ou D · {{carteira.exposicaoEmRiscoEmRJ}} de exposição sem proteção efetiva em cenário de RJ · {{carteira.rjEmCurso}} RJ em curso.

---

### Bloco 2 · PÚBLICO-ALVO / BENEFICIÁRIOS

**Manchete:** O usuário é o analista de crédito da Krill Tech. O beneficiário é o caixa da empresa — e, na ponta, o produtor saudável que deixa de pagar pelo risco dos outros.

Corpo:

- **Usuário direto:** analista de crédito e cobrança da Krill Tech. Decide limite, prazo e garantia em venda a prazo, barter e CPR. Recebe score, parecer e alertas; **mantém a decisão final** e registra justificativa.
- **Usuários secundários:** gestor de crédito / CFO (visão de carteira, exposição em risco em RJ, provisão) · comercial (consulta pré-venda de prospect por CPF/CNPJ) · jurídico (Stay Period, natureza concursal × extraconcursal das garantias).
- **Beneficiários indiretos:** a Krill Tech (caixa preservado, menor provisão, capital de giro liberado) · o produtor rural adimplente (crédito mais rápido e barato porque o risco é discriminado, não generalizado por safra ou região) · a cadeia agro B2B — revendas, cooperativas, distribuidores — clientes futuros da plataforma · o mercado de crédito agro, com menos contaminação em cascata.
- **Quem não é usuário nesta versão:** o produtor. Seus dados são tratados exclusivamente para análise de crédito, sob base legal de proteção ao crédito (LGPD, art. 7º, X) e com fonte pública identificada.

---

### Bloco 3 · LÓGICA DE FUNCIONAMENTO DA SOLUÇÃO

**Manchete:** Quatro agentes, um contrato: máquina calcula, linguagem explica, analista decide.

Corpo (fluxo numerado; a UI renderiza como cadeia horizontal com os 4 agentes destacados):

1. **Entrada** — CPF/CNPJ de um prospect (fluxo A: due diligence) ou carteira já cadastrada (fluxo B: monitoramento).
2. **Agente Coletor & Parser** — consulta 14 fontes públicas + dados internos da Krill Tech; faz parsing de publicações de Diários de Justiça e de certidões em PDF; normaliza tudo em **fatos com fonte, data e evidência**.
3. **Agente de Risco Agro & Climático** — cruza a localização do imóvel (CAR) com o zoneamento ZARC, a quebra de safra regional, a precipitação (INMET) e a produtividade (CONAB); **liga o clima ao dinheiro exposto** em barter e CPR.
4. **Motor de Decisão & Scoring** *(ML quantitativo, proprietário)* — 7 dimensões → score 0–1000 → rating A–D; PD em 6, 12 e 24 meses; **índice de RJ separado**; regras de veto; red flags; recomendação parametrizada. Determinístico e auditável: **a soma dos fatores reconstrói o score.**
5. **Agente Sintetizador & Gerador de Relatórios** *(LLM)* — recebe os números prontos e redige o parecer, o "por que este score" e a recomendação em linguagem natural, citando evidências. **Nunca inventa nem altera um número.**
6. **Analista decide** — aprova, restringe ou suspende, com trilha de auditoria. O monitoramento contínuo recalcula quando um novo evento é identificado e o ciclo recomeça.

Rodapé do bloco: *Stack próprio da equipe: motor de risco e camada de linguagem em Python (serviço de API), interface web em TypeScript, orçamento de LLM controlado e fallback determinístico. Ver aba Arquitetura.*

---

### Bloco 4 · SCORE & CLASSIFICAÇÃO DE RATING

**Manchete:** Nota de 0 a 1000, quatro faixas, sete dimensões — e um risco de RJ medido em separado, porque inadimplência e RJ não são o mesmo evento.

Corpo:

**Faixas** (renderizar como barra horizontal segmentada, cores semânticas, rótulo dentro do segmento):

| Rating | Faixa | Rótulo | PD 12m aproximada |
|---|---|---|---|
| **A** | 750–1000 | Baixo risco | ≤ 5,6% |
| **B** | 600–749 | Risco moderado | 5,6% – 17,6% |
| **C** | 400–599 | Risco elevado | 17,6% – 44% |
| **D** | 0–399 | Risco crítico / Alerta de RJ | > 44% |

**Sete dimensões e pesos:** Comportamental / histórico interno **22%** · Jurídico & processual **20%** · Agro & climático **15%** · Fiscal & trabalhista **14%** · Cadastral & societário **10%** · Garantias & exposição **10%** · Ambiental **9%**.

- Cada dimensão parte de 1000 e sofre penalidades e bônus por fatores com pontos explícitos; o score é a média ponderada. Todo ponto tem fonte e evidência.
- **PD 12m** por curva logística calibrada sobre o score (ex.: 604 → 17,1%); **PD 6m e 24m** derivadas por hazard ajustado à tendência — PD6 < PD12 < PD24 por construção.
- **Risco de RJ** é indicador próprio (índice 0–100 → probabilidade), alimentado por sinais de insolvência coletiva: pluralidade de credores, dívida judicializada, PGFN, falência requerida. Considera **elegibilidade pela Lei 14.112/2020** — PF sem 2 anos comprovados não tem via de RJ.
- **Veto acima do score:** RJ, falência, embargo sobre bem em garantia, cadastro inapto, lista suja e fraude forçam **D**; execução fiscal > 50% da exposição ou CNDT relevante limitam a **C**. O score calculado **permanece visível** ao lado da classificação final, com o motivo nomeado.

---

### Bloco 5 · MATRIZ DE RED FLAGS

**Manchete:** Toda red flag nasce do mesmo fato que penaliza o score — carrega pontos, fonte, data e evidência, e nunca diverge da nota.

Corpo (renderizar como quatro faixas empilhadas, da CRÍTICA à BAIXA, com ícone + rótulo + cor):

- **CRÍTICA — veto imediato:** RJ ajuizada ou deferida · pedido de falência · embargo do IBAMA sobre bem dado em garantia · inclusão na lista suja (trabalho análogo ao escravo) · fraude confirmada.
- **ALTA — agir em até 7 dias:** ≥ 2 execuções de título em 90 dias · protestos recorrentes (≥ 3 em 12 meses) · dívida ativa PGFN crescente · **covenant contratual rompido (inadimplência técnica)** · queda de score > 80 pontos em 90 dias · CNDT positiva.
- **MÉDIA — revisar em 30 dias:** alteração societária relevante · saída de sócio majoritário · ZARC elevado para alto/crítico · quebra de safra regional > 20% · certidão vencida · endividamento crescente · CAR irregular.
- **BAIXA / INFORMATIVA:** alteração de endereço ou CNAE · nova filial · atualização cadastral · variação climática dentro do esperado.

Destaque final: *Sinal-assinatura de RJ: **três ou mais credores distintos executando** — não é disputa bilateral, é crise de liquidez generalizada, o precursor clássico do pedido.*

---

### Bloco 6 · RECOMENDAÇÃO DE DECISÃO OPERACIONAL

**Manchete:** A regra escolhe a decisão e calcula os números; o LLM apenas redige; o analista assina.

Corpo:

**Escala de recomendação** (renderizar como degraus, do verde ao vermelho): APROVAR → APROVAR COM REVISÃO DE LIMITE → APROVAR COM MONITORAMENTO INTENSIVO → APROVAR COM RESTRIÇÕES → SUSPENDER NOVA EXPOSIÇÃO A PRAZO → SUSPENDER EXPOSIÇÃO.

**Ações parametrizadas com os números do cliente** (exemplos reais do motor):
- "Reduzir limite aprovado de R$ 5.000.000 para R$ 3.500.000 (−30%)"
- "Reduzir prazo de pagamento de 120 para 60 dias"
- "Exigir garantia adicional de R$ 1.480.000 para cobrir a exposição desprotegida"
- "Converter penhor de safra (R$ 900.000) em alienação fiduciária para blindar o crédito em cenário de RJ"
- "Exigir pagamento à vista" · "Bloquear aumento de limite" · "Acionar garantia extraconcursal"
- "Reavaliar em 30 dias" — prazo por rating: A 180 d · B 90 d · C 30 d · D 7 d

**Por rating:** **A** mantém limite e prazo (revisa limite se utilização > 90%) · **B** mantém com monitoramento; restringe se a exposição em risco em RJ passar de 40% · **C** reduz limite e prazo, exige garantia extraconcursal; suspende novo prazo se a deterioração for acelerada · **D** suspende exposição e aciona garantias extraconcursais.

Rodapé obrigatório do bloco: **Decisão final sujeita à avaliação do analista responsável.** Toda decisão fica registrada com justificativa e marca de divergência em relação à recomendação.

---

### Bloco 7 · MONITORAMENTO CONTÍNUO / EARLY WARNING SYSTEM

**Manchete:** Monitoramento contínuo com recálculo automático: cada evento relevante identificado move o score e diz, ponto a ponto, por que mudou.

Corpo:

- **Eventos monitorados:** nova execução de título · novo protesto · inscrição em dívida ativa · distribuição ou deferimento de RJ · pedido de falência · embargo ambiental · alteração societária · covenant rompido · deterioração climática regional · atraso de pagamento · alteração cadastral.
- **Cadência honesta:** fontes públicas varridas em ciclos próprios (diário a semanal, conforme a fonte); dados internos a cada fechamento; **nenhuma fonte é assumida como tempo real** — toda evidência exibe a data da consulta.
- **Recálculo com explicação:** ao capturar um evento, o motor atualiza os fatos, recalcula e produz o delta por fator. Exemplo: **712 → 604 (−108)** — 2 novas execuções de título −42 · nova inscrição em dívida ativa −31 · deterioração climática regional −18 · atraso médio (3 d → 11 d) −17.
- **Alertas:** por severidade, com impacto em pontos, ação recomendada e prazo; central de alertas + timeline do cliente. Alerta CRÍTICO abre recomendação de suspensão. Tendência em 90 dias (melhorando · estável · deteriorando · deterioração acelerada) alimenta a PD e a recomendação.
- **Demonstrável ao vivo:** o controle "Simular evento de monitoramento" injeta um evento em um cliente e o recálculo acontece diante da banca.

---

### Bloco 8 · ARQUITETURA DE NEGÓCIOS & CUSTOS

**Manchete:** Cerca de R$ 555 mil por ano para 500 clientes monitorados. Uma única RJ antecipada preserva cerca de R$ 1 milhão. A primeira RJ paga o ano; a segunda é resultado.

Corpo:

**Modelo de sustentação em dois estágios:**
- **Estágio 1 — ferramenta interna da Krill Tech:** custo alocado ao centro de crédito; retorno medido em perda evitada e provisão reduzida.
- **Estágio 2 — plataforma SaaS para a cadeia agro B2B** (revendas, cooperativas, distribuidores): assinatura por cliente monitorado **R$ 60 a 120/mês** por faixa de exposição + **due diligence avulsa R$ 180** + relatório de carteira para comitê. Ponto de equilíbrio com ≈ 3 carteiras do porte da Krill Tech.

**Premissas de custo:** 500 clientes monitorados · 150 due diligences/ano · recálculo por evento + ciclo semanal · custos em R$, valores de 2026, mão de obra com encargos.

**Implementação (única, 6 meses): ≈ R$ 480 mil** — equipe de 4 (2 engenheiros, 1 cientista de dados, 1 especialista de crédito atuando como PM), integrações reais, backtesting e homologação.

**Operação anual recorrente:**

| Item | R$/ano | Nota |
|---|---|---|
| Coleta de dados | 55 mil | Cartórios de protesto ≈ 15 mil (consulta paga por documento) · agregador processual/DJE ≈ 36 mil · Receita, PGFN, TST, CRF, DataJud, SICAR, IBAMA, CONAB, ZARC, INMET: gratuitos |
| Infraestrutura | 48 mil | Aplicação, processamento, armazenamento de evidências, filas de revarredura |
| Inferência do LLM | 12 mil | ≈ US$ 0,02 por parecer; parsing assistido de publicações. **O LLM não é o custo relevante.** |
| Time de sustentação | 360 mil | 1 engenheiro + 0,5 cientista de dados + jurídico consultivo |
| Validação de modelo e auditoria | 30 mil | Backtesting semestral, revisão de pesos, relatório de disparidade |
| Contingência (10%) | 50 mil | |
| **Total** | **≈ 555 mil** | **≈ R$ 92 por cliente monitorado por mês** |

**Caso de retorno:** cliente com exposição de **R$ 2 milhões** entra em RJ sem garantia extraconcursal → crédito quirografário entra no plano com deságio severo e prazo de vários anos (Desafio §4); recuperação típica de 20 a 40% → **perda de R$ 1,2 a 1,6 milhão**, mais o custo financeiro do prazo. Uma RJ **antecipada em 90 dias** — redução de limite, encurtamento de prazo e conversão de penhor em alienação fiduciária — preserva **≈ R$ 1 milhão**. Retorno ≈ 1,8× o custo anual com **um** caso.

---

### Bloco 9 · PREMISSAS, RESTRIÇÕES E RISCOS

**Manchete:** Esta versão é 100% simulada, e diz isso em toda tela. Os riscos que importam são falso negativo, parsing ruim e automação sem supervisão — cada um tem tratamento nomeado.

Corpo:

**Premissas:** dados desta versão são simulados e nenhuma integração real é feita ou insinuada · as fontes públicas da §5 do desafio existem e são acessíveis · o analista permanece o decisor · a Krill Tech fornece histórico interno de pagamento para a fase de piloto.

**Restrições:** prazo do hackathon · sem backend persistente nesta versão · LLM com orçamento limitado e fallback determinístico · coeficientes calibrados por especialista, não treinados em histórico real.

**Riscos e tratamento:**

| Risco | Como a equipe lida |
|---|---|
| Disponibilidade e latência das bases públicas | Cache por fonte com data de consulta visível; dado indisponível **não zera** a dimensão — mantém o último valor com selo de defasagem e gera red flag informativa |
| Qualidade do parsing de Diários de Justiça e certidões em PDF | Dupla via (regras + extrator de linguagem), nível de confiança por evidência; evidência de baixa confiança vai para fila de validação humana **antes** de penalizar o score |
| Falso negativo do modelo (cliente ruim classificado como bom) | Regras de veto por fato jurídico acima do score; red flags independentes da nota; tendência em 90 dias como gatilho; backtesting em carteira histórica com métrica de recall em RJ |
| Viés por região, porte ou tipo de pessoa | Pesos configuráveis e publicados na aba Metodologia; veto só por fato jurídico, nunca por segmento; relatório semestral de disparidade por UF, cultura e PF/PJ |
| Automação sem supervisão | Decisão sempre do analista; trilha de auditoria com justificativa; divergência em relação à recomendação destacada e revisada |
| Alucinação do modelo de linguagem | LLM só redige a partir do JSON de números e evidências; validador rejeita qualquer valor numérico ausente da entrada; degradação para texto determinístico |
| LGPD e uso de dado público | Base legal: proteção ao crédito (art. 7º, X) e legítimo interesse (art. 7º, IX); minimização; dados de PF só com finalidade de crédito; retenção definida; sem comercialização de dado; direito de revisão de decisão automatizada (art. 20) atendido pela decisão humana obrigatória |

---

### Bloco 10 · PRÓXIMOS PASSOS

**Manchete:** Do protótipo ao piloto real em 3 meses; à produção em 6; à plataforma de cadeia em 12.

Corpo (renderizar como linha do tempo horizontal com 5 marcos):

- **Fase 0 · Hackathon (hoje):** protótipo funcional — motor determinístico auditável, {{carteira.total}} clientes simulados, parecer imprimível, monitoramento demonstrável, Canvas e arquitetura dentro da aplicação.
- **Fase 1 · Piloto (0–3 meses):** integrações reais com Receita Federal, PGFN, TST/CNDT, Caixa/CRF e DataJud; ingestão do histórico interno da Krill Tech; validação com 50 clientes reais e 3 analistas; backtesting em 24 meses de histórico para calibrar pesos e curvas.
- **Fase 2 · Produção (3–6 meses):** parsing de DJEs e cartórios de protesto; SICAR, IBAMA, ZARC, CONAB e INMET; modelo estatístico **treinado sobre histórico real** substitui os coeficientes calibrados à mão, **mantendo a decomposição por fator**; alertas por e-mail e mensageria; SLA de recálculo.
- **Fase 3 · Escala (6–12 meses):** oferta SaaS para revendas, cooperativas e distribuidores; API para ERPs; módulo de barter com acompanhamento de safra; relatório de carteira para comitê de crédito.
- **Fase 4 · Rede (12+ meses):** consórcio de dados de inadimplência técnica da cadeia agro, com consentimento; score de cadeia — quem fornece para quem, e onde a cascata começa.

---

## 1.4 Layout visual do Canvas

### 1.4.1 Princípio

Uma única folha. Três linhas de leitura, de cima para baixo: **POR QUÊ** (problema, público, lógica) →
**O QUÊ** (score, red flags, recomendação, monitoramento) → **COMO SE SUSTENTA** (negócio, riscos, próximos passos).
A banca lê a primeira linha e a coluna das manchetes em 30 segundos (D1).

### 1.4.2 Grade

Grade de **12 colunas × 3 linhas** sobre a área útil. Alturas das linhas: 30% · 38% · 32%.

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ LASTRO · tagline                                   Project Canvas · PMI-DF 2026 · SIMULADO │
├────────────────────────┬────────────────┬────────────────────────────────────────────┤
│ 1 PROBLEMA &           │ 2 PÚBLICO-ALVO │ 3 LÓGICA DE FUNCIONAMENTO                  │
│   DIAGNÓSTICO          │   BENEFICIÁRIOS│   [Coletor]→[Agro]→[Motor ML]→[LLM]→[Analista]│
│   (cols 1–4)           │   (cols 5–7)   │   (cols 8–12)                              │
├──────────────┬─────────┴──────┬─────────┴──────────┬─────────────────────────────────┤
│ 4 SCORE &    │ 5 MATRIZ DE    │ 6 RECOMENDAÇÃO     │ 7 MONITORAMENTO CONTÍNUO        │
│   RATING     │   RED FLAGS    │   OPERACIONAL      │   EARLY WARNING SYSTEM          │
│ [A][B][C][D] │ CRÍT/ALTA/MÉD/ │ degraus verde→verm.│ 712 → 604 (−108) …              │
│ 7 dimensões  │ BAIXA          │ ações c/ números   │ eventos · cadência · alertas    │
│ (cols 1–3)   │ (cols 4–6)     │ (cols 7–9)         │ (cols 10–12)                    │
├──────────────┴─────────┬──────┴────────────────────┬────────────────────────────────┤
│ 8 ARQUITETURA DE       │ 9 PREMISSAS, RESTRIÇÕES   │ 10 PRÓXIMOS PASSOS             │
│   NEGÓCIOS & CUSTOS    │   E RISCOS                │   F0 ─ F1 ─ F2 ─ F3 ─ F4       │
│   R$ 555 mil/ano ×     │   tabela risco→tratamento │   linha do tempo               │
│   R$ 1 mi por RJ       │                           │                                │
│   (cols 1–4)           │   (cols 5–8)              │   (cols 9–12)                  │
└────────────────────────┴───────────────────────────┴────────────────────────────────┘
```

### 1.4.3 Hierarquia tipográfica (impressão A4 paisagem, 297 × 210 mm, margens 8 mm)

| Elemento | Tamanho | Peso | Observação |
|---|---|---|---|
| "LASTRO" | 22 pt | 800 | Acento de marca (azul-aço) |
| Tagline | 11 pt | 500 itálico | |
| Linha de contexto do cabeçalho | 7 pt | 400 | Cinza |
| Numeral + título do bloco | 8,5 pt | 700, caixa alta, tracking +4% | Numeral em círculo com o acento de marca |
| Manchete do bloco | 8 pt | 700 | **Sempre a primeira linha do corpo. É o que se lê a distância.** |
| Corpo | 6,4 pt / entrelinha 1,3 | 400 | Itens com marcador fino |
| Tabelas internas | 6 pt | | Linhas separadoras 0,25 pt |
| Rodapé obrigatório (bloco 6) | 6,4 pt | 700 | |
| Badge SIMULADO | 7 pt | 700, caixa alta | Fundo âmbar claro, texto escuro, borda 0,5 pt |

Elementos gráficos obrigatórios (legíveis a distância, sem depender de texto pequeno):

1. **Bloco 3:** cadeia de 5 pastilhas com setas — `Coletor & Parser` → `Risco Agro & Climático` → `Motor de Decisão & Scoring` → `Sintetizador (LLM)` → `Analista`. As duas pastilhas de ML têm borda sólida no acento de marca; a do LLM tem borda tracejada e um pequeno rótulo "linguagem"; a do Analista tem ícone de pessoa.
2. **Bloco 4:** barra segmentada A/B/C/D com as faixas numéricas dentro; abaixo, barra de pesos das 7 dimensões (proporcional, rótulo com percentual).
3. **Bloco 5:** quatro faixas empilhadas com cor de severidade + ícone (triângulo para CRÍTICA, exclamação para ALTA, círculo para MÉDIA, info para BAIXA).
4. **Bloco 6:** seis degraus da recomendação com gradiente semântico verde → vermelho.
5. **Bloco 7:** o exemplo `712 → 604 (−108)` em fonte 11 pt, como mini-gráfico de cascata de 4 barras.
6. **Bloco 8:** dois números grandes lado a lado: **R$ 555 mil/ano** e **≈ R$ 1 mi por RJ antecipada**, com um "×1,8" entre eles.
7. **Bloco 10:** linha do tempo com 5 marcos e rótulos de horizonte.

### 1.4.4 Comportamento em tela

- Container com `aspect-ratio: 297 / 210`, largura máxima `min(100vw − 48px, 1600px)`, centralizado; a folha inteira cabe em viewport ≥ 1280 × 720 **sem rolagem**. Abaixo disso, rola verticalmente mantendo a grade.
- Tela é dark-only (D9): fundo do palco `--bg-canvas`, folha com fundo `--surface-1`, texto `--fg-1`. As cores semânticas de risco são as mesmas do resto da aplicação.
- **Hover** em um bloco: leve elevação e borda no acento de marca. **Clique**: abre o bloco em sobreposição ampliada (largura 900 px), com o mesmo texto em 15–16 px — é o modo de leitura do jurado que quer conferir um bloco. `Esc` fecha. Setas ← → navegam entre blocos.
- **Modo apresentação**: `Fullscreen API`; oculta cabeçalho da aplicação e banner (o badge SIMULADO da própria folha continua visível); atalhos `1`…`0` abrem os blocos 1…10 ampliados, `Esc` volta à folha inteira.
- Tokens `{{…}}` resolvem no servidor (RSC) a partir do repositório; se falhar, exibem o fallback e um `title` "valor indisponível nesta sessão".
- Links internos (Bloco 3 → `/arquitetura`; Bloco 4 → `/metodologia`) só em tela; em impressão viram texto simples.

### 1.4.5 Impressão

```css
@page { size: A4 landscape; margin: 8mm; }
```

- Fundo branco, texto `#111`, folha sem sombra; cores de risco em versão imprimível (verde `#1f7a3a`, âmbar `#b26b00`, laranja `#c2410c`, vermelho `#b91c1c`).
- `break-inside: avoid` em cada bloco; a folha inteira é **uma página** — se o conteúdo exceder, o corpo reduz para 6 pt via `@media print` antes de qualquer quebra. Teste de aceite: impressão em Chromium gera exatamente 1 página.
- Cabeçalho da folha reproduz o badge `DADOS SIMULADOS — protótipo demonstrativo` (D11.7).
- Botões, banner global da aplicação e navegação: `display: none`.
- `Exportar PDF (A4 paisagem)` = `window.print()`; antes, define `document.title = "Lastro_Project-Canvas_PMI-DF-2026"` para nomear o arquivo e restaura no `afterprint`.

---

# PARTE 2 — Aba Arquitetura (`/arquitetura`)

## 2.1 Propósito

Mostrar o pipeline conceitual **e** provar quatro coisas em uma tela: (1) o fluxo reproduz os quatro agentes de
referência da §6 do desafio com implementação própria; (2) **ML quantitativo e LLM são camadas distintas com
fronteira explícita** — números só saem do motor, texto só sai do LLM; (3) cada etapa tem um lugar concreto no
produto que está rodando ao lado; (4) **o diagrama descreve o que está de fato em execução na máquina durante o
pitch** — dois serviços reais (Python/Flask e Next.js), não uma ilustração. Nada aqui depende de biblioteca de
diagramação: é grid CSS + SVG autoral para conectores.

### 2.1.1 Topologia real de execução (D3)

```
Browser ──HTTP──► web/  Next.js 15 (porta 3000)        ──HTTP interno──► api/  Flask · Python 3.13 (porta 5001)
                  interface + proxy server-side                            Motor de Decisão & Scoring
                  não recalcula nada                                       Agente Sintetizador (LLM, streaming)
                                                                           dataset simulado em api/data/
```

- O browser **nunca** fala com o Flask. Route handlers em `web/app/api/*` fazem apenas proxy, inclusive do
  stream de texto, sem bufferizar.
- A chave do provedor de LLM vive só no Flask. A interface não contém lógica de risco.
- O contrato entre os dois é o `01-modelo-de-dados.md`: tipos TypeScript no `web/`, modelos pydantic espelhados
  no `api/`, teste de contrato comparando o JSON real.

## 2.2 Cabeçalho da página (texto final)

```
Arquitetura da solução
Pipeline de referência do desafio (§6), implementação própria da equipe — e é isto que está rodando agora.
```

Faixa de estado logo abaixo, quatro pastilhas de fatos:

`0 integrações reais nesta versão` · `14 fontes mapeadas` · `{{carteira.total}} clientes simulados` · `2 serviços em execução: Python/Flask (motor + IA) e Next.js (interface)`

A quarta pastilha é **viva**: o Next consulta `GET /api/saude` (proxy para o `health` do Flask) ao montar a
página e exibe `Flask · Python 3.13 · respondeu em {ms} ms` em verde-neutro (não é cor de risco: usar o acento de
marca) ou `Flask indisponível` em cinza com ícone de alerta. É a prova, em tela, de que o motor é um processo real.

**Nota fixa na página** (caixa discreta sob o cabeçalho, texto final):

> **Este diagrama não é ilustrativo.** Cada card das camadas ML e LLM aponta para código Python em execução no
> serviço `api/` (Flask); cada card de interface aponta para a aplicação Next.js que você está usando agora.
> Os números que aparecem nas telas foram calculados pelo motor deste diagrama, nesta máquina, nesta sessão.

Legenda fixa (canto superior direito, sempre visível):

- ▰ borda sólida azul-aço — **ML quantitativo / regras determinísticas**: estima probabilidades, gera score. Produz números.
- ▱ borda tracejada roxa-acinzentada (`--accent-llm`, tom neutro, não é cor de risco) — **LLM**: sintetiza evidências, explica, redige. Produz texto. **Nunca produz número.**
- ◌ borda pontilhada cinza — **fonte externa simulada**: nenhuma chamada é feita.
- ● círculo com ícone de pessoa — **humano no circuito**.

## 2.3 As onze etapas

Cada etapa é um **card** com: número, nome, agente de referência (pílula), camada (ML / LLM / Dados / Humano),
"o que entra → o que sai", fontes, **serviço + tecnologia** (onde o código realmente roda) e **"Onde aparece no
produto"** (link). O texto abaixo é o texto final do card e do painel lateral que abre ao clicar.

Convenção da coluna "Serviço · Tecnologia": `api/` = Flask, Python 3.13 (motor, LLM, dados); `web/` = Next.js 15,
TypeScript (interface e proxy). Cada card exibe uma **pílula de serviço** com o logotipo textual `PY` (fundo
`--surface-3`, borda sólida) ou `TS` (fundo `--surface-3`, borda fina no acento de marca) — a banca vê de relance
que motor e LLM vivem no serviço Python e que a interface não calcula.

| # | Etapa | Agente de referência (§6) | Camada | Entra → Sai | Fontes | Serviço · Tecnologia (stack próprio) | Onde aparece no produto |
|---|---|---|---|---|---|---|---|
| 1 | **FONTES** | Agente Coletor & Parser | Dados (externo, simulado) | CPF/CNPJ → documentos, certidões, publicações, séries | As 14 fontes da §2.5 | `api/` **PY** — conectores por fonte como contrato; nesta versão, dataset simulado em `api/data/` (Python/JSON) | `/due-diligence` (busca por documento) · `/clientes/[id]` › seção **Evidências consultadas** |
| 2 | **COLETA / INGESTÃO** | Agente Coletor & Parser | Dados | Documentos brutos → `Evidencia[]` com fonte, data de consulta, tipo | Todas | `api/` **PY** — camada de repositório do Flask (`api/repository/`), fronteira para integração real; exposta ao `web/` por rota HTTP e consumida via proxy `web/app/api/*` | `/clientes/[id]` › Evidências (selo "consulta simulada" + data) |
| 3 | **NORMALIZAÇÃO** | Agente Coletor & Parser | Dados | Evidências heterogêneas → `FatosDoCliente` tipado (interno, jurídico, fiscal, agro, cadastral, ambiental, operações, garantias) | Todas | `api/` **PY** — modelos pydantic v2 espelhando `types/` do `web/` (contrato da API); parsing de PDF/DJE por regras + extrator de linguagem (fase 2) | `/clientes/[id]` › cabeçalho e painéis de fatos; `/metodologia` › "Do fato ao fator" |
| 4 | **FEATURE ENGINEERING** | Agente Coletor & Parser **+** Agente de Risco Agro & Climático | ML | `FatosDoCliente` → `FatorCalculado[]` por dimensão (pontos, direção, evidência) | Interno, DataJud/DJE, cartórios, PGFN, TST, CRF, SICAR, IBAMA, CONAB, ZARC, INMET, RFB | `api/` **PY** — featurizers puros, um por dimensão, em `api/scoring/`; o Agente Agro cruza CAR × ZARC × quebra de safra × precipitação × produtividade | `/clientes/[id]` › **Decomposição por dimensão** (fatores com pontos e fonte) |
| 5 | **MOTOR PREDITIVO** | Motor de Decisão & Scoring | ML | Fatores → score por dimensão → score 0–1000 → PD 6/12/24 m → índice e probabilidade de RJ | — (consome a etapa 4) | `api/` **PY** — motor determinístico proprietário em Python: média ponderada, curva logística de PD, hazard por tendência, índice de RJ com elegibilidade (Lei 14.112/2020); coeficientes em `api/scoring/config.py` | `/carteira` › coluna Score/Rating · `/clientes/[id]` › **gauge de score, PD nos três horizontes, Risco de RJ** |
| 6 | **REGRAS E RED FLAGS** | Motor de Decisão & Scoring | ML / regras | Fatos + score → vetos (força D / teto C) → red flags por severidade → rating final | — | `api/` **PY** — tabela de gatilhos em `api/scoring/config.py`; red flags derivadas dos mesmos fatos | `/clientes/[id]` › **Score calculado × Classificação final após regras**, lista de red flags · `/alertas` |
| 7 | **SCORE / PD / RJ** | Motor de Decisão & Scoring | ML | Saída consolidada `AvaliacaoDeRisco` com auditoria de fechamento (`diferenca = 0`) | — | `api/` **PY** — função pura `calcular_risco(fatos, config)`; invariantes I1–I6 em `pytest` (`api/tests/`); JSON devolvido ao `web/` bate campo a campo com o tipo TypeScript | `/carteira` · `/clientes/[id]` · `/metodologia` › **Auditoria de fechamento** ("a soma dos fatores reconstrói o score") |
| — | **FRONTEIRA** | — | — | **Só números e evidências passam para a direita. Só texto volta para a esquerda.** | — | `api/` **PY** — contrato JSON de entrada do LLM montado a partir de `AvaliacaoDeRisco`; validador de saída rejeita números ausentes da entrada | Visível na própria aba como faixa vertical entre 7 e 8 |
| 8 | **CAMADA DE EXPLICAÇÃO** | Agente Sintetizador & Gerador de Relatórios | LLM | `AvaliacaoDeRisco` + evidências → texto "por que este score", "por que mudou", resumo executivo | — | `api/` **PY** — modelo de linguagem via API (SDK Python), prompts e guardas próprios; **streaming** repassado pelo proxy do `web/` sem bufferizar; timeout 25 s; teto de orçamento; fallback determinístico (D5) | `/clientes/[id]` › **Por que este score** · **Por que mudou** · Copiloto "Pergunte sobre este cliente" |
| 9 | **RECOMENDAÇÃO** | Motor de Decisão & Scoring (decide) **+** Agente Sintetizador (redige) | ML **→** LLM | Regra escolhe código e ações parametrizadas → LLM redige a justificativa | — | `api/` **PY** — tabela de decisão da §12 do motor; o LLM recebe as ações prontas no mesmo serviço | `/clientes/[id]` › card **Recomendação operacional** · `/clientes/[id]/parecer` |
| 10 | **ANALISTA** | — (humano no circuito) | Humano | Recomendação → decisão (aprovar, restringir, revisar, suspender, recusar) + justificativa | — | `web/` **TS** — formulário de decisão e `RegistroAuditoria` em `localStorage` (D11.3); enviado ao Flask junto da requisição quando altera o cálculo | `/clientes/[id]` › **Registrar decisão** · `/auditoria` |
| 11 | **MONITORAMENTO CONTÍNUO** | Agente Coletor & Parser (revarredura) **+** Motor (recálculo) | Dados → ML | Novo evento → novos fatos → recálculo → delta por fator → alerta | Todas, em ciclos por fonte | `api/` **PY** — rota `simular_evento` no Flask injeta o evento e recalcula; snapshots recalculados; Σ deltas = Δ score (I6). `web/` **TS** — dispara e exibe | `/alertas` › central · `/clientes/[id]` › **timeline** e "Por que mudou" · botão **Simular evento de monitoramento** |
| ◦ | **INTERFACE** (transversal) | — | Apresentação | JSON do Flask → telas; stream de texto → prosa token a token | — | `web/` **TS** — Next.js 15, React 19, Tailwind v4, Recharts, SVG autoral do gauge; route handlers só fazem proxy; **não recalcula nada** | Todas as rotas; renderizada como faixa fina sob o trilho, ver §2.4.2 |

Texto do painel lateral que abre em qualquer card de camada LLM (8, 9 à direita), sempre presente:

> **O que o LLM faz aqui:** recebe o JSON com score, rating, PD, risco de RJ, fatores, red flags, garantias e
> evidências já calculados e escreve texto em português, citando a evidência de cada afirmação.
> **O que o LLM não faz:** não calcula, não arredonda, não estima, não escolhe a recomendação. Qualquer número no
> texto que não exista na entrada é rejeitado pelo validador e o bloco cai para o texto determinístico.

Texto do painel lateral dos cards de camada ML (4–7, 9 à esquerda):

> **O que o modelo quantitativo faz aqui:** transforma fatos em pontos, pontos em score, score em probabilidade.
> Determinístico: a mesma entrada produz sempre a mesma saída, e a soma das contribuições reconstrói o resultado.
> **O que ele não faz:** não escreve texto. Toda frase que a banca lê vem da etapa 8 ou 9.

## 2.4 Representação visual

### 2.4.1 Esboço em ASCII (referência de composição)

```
AGENTES (§6)   ├──── Agente Coletor & Parser ────┤├─ Agro & Climático ─┤├──── Motor de Decisão & Scoring ────┤├── Sintetizador ──┤  humano   ├ Coletor + Motor ┤
                                                        (participa da 4)

CAMADA          DADOS (simulado) ───────────────────►  ML QUANTITATIVO ─────────────────────────►│FRONTEIRA│► LLM ──────────► HUMANO ──► LOOP

              ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐  ║  ┌ ─ ─ ─ ─┐   ┌────┬ ─ ─┐   ┌────────┐   ┌────────┐
              │ 1      │   │ 2      │   │ 3      │   │ 4      │   │ 5      │   │ 6      │   │ 7      │  ║  │ 8      │   │ 9  │    │   │ 10     │   │ 11     │
              │ FONTES │──►│ COLETA │──►│ NORMA- │──►│FEATURE │──►│ MOTOR  │──►│ REGRAS │──►│ SCORE  │══╬═►│EXPLICA-│──►│REC.│    │──►│ANALISTA│──►│MONITOR.│
              │ (14)   │   │INGESTÃO│   │LIZAÇÃO │   │ ENG.   │   │PREDIT. │   │RED FLAG│   │PD · RJ │  ║  │ÇÃO     │   │regra│LLM │   │  ●     │   │CONTÍNUO│
              └ ─ ─ ─ ─┘   └────────┘   └────────┘   └────────┘   └────────┘   └────────┘   └────────┘  ║  └ ─ ─ ─ ─┘   └────┴ ─ ─┘   └────────┘   └───┬────┘
               pontilhado    sólido       sólido       sólido       sólido       sólido       sólido    ║   tracejado    meio/meio     círculo         │
                                                                                                        ║                                               │
              "Só números e evidências passam" ─────────────────────────────────────────────────────────╨── "Só texto volta"                            │
                                                                                                                                                        │
              ◄─────────────────────────────────── novo evento → revarredura → recálculo → delta por fator → alerta ────────────────────────────────────┘

SERVIÇO       ├──────────────────────── api/  Flask · Python 3.13  (motor + LLM + dados) ─────────────────────────────────────────────────┤  web/ TS  ├ api/ PY + web/ TS ┤

TELA          due-diligence  cliente›Evid. cliente›Fatos  cliente›Dimens. carteira·gauge cliente›Regras  metodologia›Aud.  cliente›Por quê  cliente›Recom.  auditoria     alertas·timeline

              ═══════════════════════════════ web/  Next.js 15 · interface + proxy server-side · não recalcula nada ══════════════════════════════════════════
```

### 2.4.2 Especificação para implementação (grid + SVG, sem biblioteca)

**Estrutura vertical (de cima para baixo):**

1. **Faixa de agentes** — 4 (+1) spans horizontais alinhados às colunas das etapas que cada agente cobre:
   Coletor & Parser cobre 1–3 e participa de 4 e 11; Agro & Climático cobre 4 (span parcial, empilhado sob o do
   Coletor); Motor de Decisão & Scoring cobre 5–7 e a metade esquerda de 9; Sintenizador cobre 8 e a metade direita
   de 9; "Humano no circuito" cobre 10. Spans com fundo `--surface-2`, texto 12 px caixa alta, cantos 4 px.
2. **Faixa de camadas** — 5 spans coloridos por camada: `DADOS (simulado)` cinza · `ML QUANTITATIVO` azul-aço ·
   `FRONTEIRA` (largura fixa 56 px) · `LLM` roxo-acinzentado · `HUMANO` neutro · `LOOP` cinza. Estes spans
   são a separação visual inequívoca exigida: **não** dependem só de cor — trazem rótulo textual e o
   pictograma da legenda (▰ ▱ ◌ ●). Nota: ML e LLM são camadas **conceituais** distintas que vivem no **mesmo
   serviço** (`api/`, Python); a distinção de camada é sobre o que cada uma produz (número × texto), a distinção de
   serviço (faixa do item 7) é sobre onde o código roda. As duas faixas coexistem sem se confundir.
3. **Trilho de etapas** — `display: grid; grid-template-columns: repeat(7, 1fr) 56px repeat(4, 1fr)`; cada card
   `min-width: 150px`; altura 168 px; conteúdo: numeral (20 px, 800), nome (13 px, 700, caixa alta), pílula do
   agente (10 px), linha "entra → sai" (11 px, 2 linhas máx., `text-overflow: ellipsis`), e rodapé com o link
   "Onde aparece →" (11 px, acento de marca). Bordas por camada: sólida 1,5 px (ML), tracejada 1,5 px (LLM),
   pontilhada 1,5 px (fonte simulada), sólida 1 px + avatar circular (humano). O card 9 é **bipartido**: metade
   esquerda com borda sólida e rótulo "regra decide", metade direita com borda tracejada e rótulo "LLM redige".
4. **Coluna FRONTEIRA** — faixa vertical de 56 px de largura, altura de todo o trilho, fundo hachurado
   (`repeating-linear-gradient` 45°, 2 px), com texto rotacionado 90°: `SÓ NÚMEROS E EVIDÊNCIAS →` na parte
   superior e `← SÓ TEXTO` na inferior. Tooltip/painel ao clicar: o texto da §2.3 sobre validador.
5. **Conectores** — um único `<svg>` absoluto sobre o trilho, `pointer-events: none`, com `<line>` + `<marker>` de
   seta entre cards adjacentes (1 px, `--fg-3`). A seta 7→8 atravessa a FRONTEIRA como linha dupla (duas linhas
   paralelas a 3 px), para indicar contrato. O **loop** 11→2 é um `<path>` em U por baixo do trilho (raio 12 px),
   com rótulo no meio: `novo evento → revarredura → recálculo → delta por fator → alerta`. Coordenadas obtidas por
   `getBoundingClientRect()` dos cards após layout e em `ResizeObserver`; nada fixo em pixel absoluto.
6. **Faixa "onde aparece"** — sob cada card, chip com o nome da tela (`/carteira`, `cliente › Por que este score`,
   etc.), clicável, cor do acento de marca. Este é o elo entre a arquitetura e o produto rodando: o jurado clica e
   cai na tela correspondente do cliente atualmente em foco (parâmetro `?cliente=[id]`, padrão: primeiro cliente
   com rating C).
7. **Faixa de serviço** — imediatamente acima da faixa "onde aparece": dois spans com rótulo textual e pílula
   `PY`/`TS`. `api/ · Flask · Python 3.13 — motor, LLM e dados` cobre as etapas 1–9 e 11; `web/ · Next.js 15 —
   interface e proxy` cobre a etapa 10 e a faixa transversal de INTERFACE. Sob todo o trilho, uma barra contínua
   com borda dupla: `web/ Next.js 15 · interface + proxy server-side · não recalcula nada`, com uma seta vertical
   única rotulada `HTTP interno (proxy)` ligando-a ao span `api/`. Isso materializa a topologia de D3 no próprio
   diagrama: o browser toca só a barra de baixo; a barra de baixo toca o Flask.
8. **Painel lateral** (380 px, à direita, `position: sticky`) — abre ao clicar em qualquer card, com todas as
   colunas da tabela §2.3 em formato de ficha, o texto de camada (ML ou LLM) correspondente e uma linha
   `Executa em: api/ (Flask, Python 3.13)` ou `Executa em: web/ (Next.js 15, TypeScript)`.

**Responsividade:** abaixo de 1280 px de largura útil, o trilho vira um container `overflow-x: auto` com
`scroll-snap-type: x mandatory`; faixas de agentes e camadas rolam junto (mesmo container). Painel lateral vira
folha inferior.

**Acessibilidade:** cada card é `<button aria-expanded>`; a distinção ML/LLM está no texto do card (pílula de
camada), não só na borda.

## 2.5 Mapeamento das fontes

Seção abaixo do pipeline, título: **"De onde vêm os fatos — e o que cada fonte move no score"**.
Grid de 14 cards (4 colunas), cada um com borda pontilhada, badge `SIMULADO — sem integração` no canto e o texto
final abaixo. Ordem = ordem da §5 do desafio, com dados internos por último.

| Fonte (`FonteId`) | Dimensão do desafio (§5) | O que fornece | Dimensão do score que alimenta | Fatores que move |
|---|---|---|---|---|
| **Receita Federal — CNPJ Abertos** (`RECEITA_FEDERAL`) | Cadastral & Societário | Situação cadastral, QSA, capital social, CNAE, filiais, data de abertura | Cadastral & societário (10%) | `situacao_cadastral`, `tempo_atividade`, `capital_vs_exposicao`, `cnae_incompativel`, `qsa_estavel` · **veto** `VETO_CADASTRO_INAPTO` |
| **Redesim** (`REDESIM`) | Cadastral & Societário | Alterações societárias, entrada/saída de sócios, mudança de administrador | Cadastral & societário (10%) | `alteracao_societaria`, `saida_socio_majoritario` · sinal de RJ "alteração de administrador em crise" |
| **DataJud — CNJ** (`DATAJUD_CNJ`) | Processual & Jurídico | Distribuição de execuções de título, pedidos de falência, RJ, partes e valores | Jurídico & processual (20%) | `execucoes_titulo`, `materialidade_execucao`, `aceleracao_judicial`, `pluralidade_credores`, `pedido_falencia`, `rj_distribuida` · **vetos** `VETO_RJ`, `VETO_FALENCIA` · índice de RJ |
| **Diários de Justiça Eletrônicos** (`DJE`) | Processual & Jurídico | Publicações: citações, deferimento de RJ, decisões de stay, editais | Jurídico & processual (20%) | Confirma e data os fatores acima; alimenta `dataDeferimento` do **Stay Period** |
| **Jusbrasil / Escavador** (agregadores; nesta versão representados sob `DJE`, sem `FonteId` próprio) | Processual & Jurídico | Consolidação de publicações e processos por nome/documento, inclusive em tribunais sem API | Jurídico & processual (20%) | Mesmos fatores; reduz latência de captura de novos processos |
| **Cartórios de protesto** (`CARTORIO_PROTESTO`) | Processual & Jurídico | Protestos ativos, quantidade em 12 m, credores protestantes | Jurídico & processual (20%) | `protestos`, `protesto_recorrente` · sinal de RJ "protestos de credores distintos" |
| **PGFN — Dívida Ativa** (`PGFN`) | Fiscal & Trabalhista | Inscrições em dívida ativa, valor, evolução, parcelamentos e rompimentos, execuções fiscais | Fiscal & trabalhista (14%) | `divida_ativa`, `divida_ativa_crescente`, `parcelamento_rompido` · **teto** `TETO_EXEC_FISCAL` · índice de RJ |
| **TST — CNDT** (`TST_CNDT`) | Fiscal & Trabalhista | Certidão Negativa de Débitos Trabalhistas; débitos com trânsito em julgado | Fiscal & trabalhista (14%) e Jurídico (20%) | `cndt_positiva`, `trabalhistas` · **teto** `TETO_CNDT` |
| **Caixa — CRF/FGTS** (`CAIXA_CRF_FGTS`) | Fiscal & Trabalhista | Regularidade do FGTS | Fiscal & trabalhista (14%) | `fgts_irregular`, `certidoes_negativas` |
| **SICAR** (`SICAR`) | Territorial & Ambiental | Situação do CAR, área consolidada, reserva legal, APP, localização do imóvel | Ambiental (9%) e Agro & climático (15%) | `car_ausente`, `car_irregular`, `sobreposicao_app`, `car_regular` · fornece a **localização** que o Agente Agro cruza com ZARC/INMET |
| **IBAMA** (`IBAMA`) | Territorial & Ambiental | Embargos vigentes, autos de infração | Ambiental (9%) | `embargo_ibama`, `auto_infracao` · **veto** `VETO_EMBARGO_GARANTIA` quando o bem embargado está em garantia |
| **CONAB** (`CONAB`) | Agronômico & Climático | Produtividade média regional por cultura e safra; quebra de safra | Agro & climático (15%) | `quebra_safra_regional`, `produtividade_abaixo` · sinal de RJ "quebra > 25%" |
| **MAPA — ZARC** (`MAPA_ZARC`) | Agronômico & Climático | Risco climático da cultura por município e janela de plantio | Agro & climático (15%) | `zarc_risco` · sinal de RJ "ZARC alto/crítico" |
| **INMET** (`INMET`) | Agronômico & Climático | Séries históricas de precipitação e temperatura; desvio vs. normal | Agro & climático (15%) | `desvio_precipitacao` · evento `MUDANCA_CLIMATICA` no monitoramento |
| **Dados internos da Krill Tech** (`INTERNO_KRILLTECH`) | — (interno) | Histórico de pagamento, atrasos, renegociações, covenants, operações (venda a prazo, barter, CPR), garantias e limites | Comportamental (22%) e Garantias & exposição (10%) | `atraso_medio`, `pior_atraso`, `pontualidade`, `renegociacoes`, **`inadimplencia_tecnica`**, `tendencia_atraso`, `relacionamento`, `historico_limpo`, `descoberto_extraconcursal`, `descoberto_total`, `utilizacao_limite`, `barter_sem_lastro` |

Rodapé da seção (texto final):

> Nesta versão, **nenhuma destas fontes é consultada**. Os fatos vêm de um conjunto de dados fictício em
> `api/data/`, com documentos gerados e razões sociais inventadas, e toda evidência na aplicação traz o selo
> "consulta simulada" com a data. A camada de repositório do serviço Python já é a fronteira para integração real:
> trocar o dataset por conectores não altera nenhuma tela do Next.js.

## 2.6 Marcação de "nenhuma integração real"

Regras visuais, todas obrigatórias e simultâneas (não depender de uma só):

1. Card 1 (FONTES) e todos os 14 cards de fonte: borda **pontilhada** + badge `SIMULADO — sem integração`.
2. Conector 1→2 desenhado tracejado (os demais são sólidos), com rótulo `dataset simulado em api/data/`.
3. Faixa de estado no topo: `0 integrações reais nesta versão`.
4. Banner global da aplicação (D11.7) permanece visível.
5. Painel lateral do card 1 abre com a frase: *"Nenhuma chamada a órgão público é feita por esta aplicação. Os
   conectores existem como contrato na camada de repositório do serviço Python, não como implementação. A única
   chamada externa do sistema é a do modelo de linguagem, feita pelo Flask, com orçamento controlado."*

## 2.7 Honestidade do diagrama — o que está rodando de fato

Seção final da página, título **"O que está em execução agora"**. Três colunas, texto final:

| Componente | Estado nesta versão | Como o jurado confere |
|---|---|---|
| **Motor de Decisão & Scoring** — `api/scoring/` (Python) | **Real.** Função pura, determinística, com testes de invariantes (a soma dos fatores reconstrói o score). Coeficientes calibrados por especialista; treinamento estatístico sobre histórico real é Fase 2. | Aba Metodologia › Auditoria de fechamento mostra `diferença = 0` para cada cliente; pastilha viva `Flask · respondeu em {ms} ms` nesta página |
| **Agente Sintetizador** — `api/llm/` (Python) | **Real.** Chamada ao vivo ao modelo de linguagem via API, com streaming, timeout e teto de orçamento; fallback determinístico. | Página do cliente › "Por que este score" chega token a token; contador de custo acumulado visível na interface |
| **Agente Coletor & Parser** e **Agente de Risco Agro & Climático** — `api/repository/`, `api/scoring/agro.py` | **Parcial.** A lógica de normalização e de cruzamento (CAR × ZARC × safra × clima) roda de verdade sobre fatos simulados; os conectores às fontes públicas são contrato, não implementação. | Evidências com selo "consulta simulada"; cards de fonte com badge `SIMULADO — sem integração` |
| **Interface** — `web/` (Next.js 15) | **Real.** Consome exclusivamente o JSON do Flask via proxy server-side; não recalcula nada. | Desligar o Flask: a interface exibe estado de erro identificado, nunca números — porque não tem como produzi-los |

Frase de encerramento da página (texto final):

> A diferença entre este diagrama e um slide é que ele pode ser desligado: pare o serviço Python e nenhum número
> aparece em tela nenhuma.

---

# PARTE 3 — Parecer de Risco imprimível (`/clientes/[id]/parecer`)

## 3.1 Identidade do documento

- **Título formal** (impresso no topo da página 1): *Relatório Padronizado de Risco de Crédito e Alerta Precoce de RJ/Insolvência*
- **Nome curto** (UI, botões, abas): *Parecer de Risco*
- **Identificador**: `LSTR-{clienteId}-{AAAAMMDD}-{hash6}`, onde `hash6` são os 6 primeiros hex do SHA-256 do JSON
  canônico de `AvaliacaoDeRisco` (sem os campos de prosa). Mesma avaliação → mesmo identificador. Impresso no
  cabeçalho de toda página.
- **Ação de origem**: botão `Gerar parecer` na página do cliente (`/clientes/[id]`), que navega para esta rota.

## 3.2 Rota e comportamento em tela

- Rota: `/clientes/[id]/parecer`. Sem layout da aplicação (sem barra lateral); mantém apenas uma **barra de
  ferramentas fixa** no topo (oculta na impressão) com: `← Voltar ao cliente` · identificador · estado da geração
  de texto · `Exportar relatório`.
- Em tela, o documento é exibido como **páginas A4 retrato** sobre fundo escuro do palco (páginas em fundo branco
  já em tela — o parecer é um documento, não uma tela de trabalho; isso é consistente com a regra 0.2.5).
- Números e tabelas renderizam de imediato (motor). Blocos de prosa chegam por streaming com skeleton rotulado
  `gerando texto…` (D5). Se `LASTRO_LLM_ENABLED=false`, orçamento esgotado ou timeout, o texto determinístico
  ocupa o lugar e o bloco recebe a etiqueta `texto padrão (sem IA)`.

## 3.3 Layout de página para impressão

```css
@page { size: A4 portrait; margin: 0; }
.pagina { width: 210mm; height: 297mm; padding: 22mm 16mm 20mm 16mm; page-break-after: always; position: relative; }
.pagina:last-child { page-break-after: auto; }
```

- **Paginação manual e determinística**: o documento é uma sequência de contêineres `.pagina` de altura fixa,
  cada um com o próprio cabeçalho e rodapé. Isso permite `Página X de Y` correto em Chromium (que não expõe
  contadores de página para elementos arbitrários) e evita cortes de seção.
- Tipografia: corpo 10 pt / entrelinha 1,4; títulos de seção 12 pt caixa alta com tracking; números-chave 22–28 pt.
  Fonte do sistema (sans) — nenhuma dependência externa.
- Cores de risco em versão imprimível (mesmas da §1.4.5). Nenhum fundo escuro grande em impressão.
- Toda seção tem `break-inside: avoid`. Listas longas (evidências, red flags) são fatiadas por contagem
  (ver §3.6).

## 3.4 Cabeçalho e rodapé (todas as páginas)

**Cabeçalho (altura 14 mm):**

```
LASTRO · Parecer de Risco                                  DADOS SIMULADOS — protótipo demonstrativo
{razaoSocial} · {documento formatado} (simulado)           {identificador}
```

**Rodapé (altura 12 mm):**

```
Gerado em {dd/mm/aaaa HH:mm} · Analista responsável: {nome do analista} · Krill Tech        Página {X} de {Y}
Análise automatizada de apoio à decisão. Avaliação final sob responsabilidade do analista responsável.
```

**Marcação de dados simulados em toda página** (obrigatória, tripla):

1. Badge âmbar `DADOS SIMULADOS — protótipo demonstrativo` no cabeçalho de toda página.
2. Marca d'água diagonal `SIMULADO`, cinza a 7% de opacidade, 64 pt, centrada em cada `.pagina`
   (`position: absolute; transform: rotate(-30deg); pointer-events: none`). Deve **imprimir** — testar com
   `print-color-adjust: exact`.
3. Sufixo `(simulado)` após todo CPF/CNPJ e após toda fonte na seção de evidências.

## 3.5 Estrutura e ordem das seções

A ordem é fixa. A coluna "Origem" define quem produz o conteúdo: **MOTOR** (determinístico, instantâneo) ou
**LLM** (prosa, streaming, com fallback determinístico). Nenhuma seção mistura origem sem marcação.

| # | Seção | Origem | Conteúdo |
|---|---|---|---|
| 1 | **Identificação do cliente** | MOTOR | Razão social, nome fantasia, CPF/CNPJ (simulado), tipo de pessoa, município/UF, atividade, CNAE, culturas, início do relacionamento, estado atual (`ATIVO`, `EM_OBSERVACAO`, `SUSPENSO`, `RJ_EM_CURSO`, `FALENCIA`), origem (carteira/prospect). Safra de referência. |
| 2 | **Data e responsável** | MOTOR | Data de referência dos fatos (`dataReferencia`), data/hora de geração, analista responsável (persona fixa do cabeçalho, D11.1), identificador do documento, versão dos parâmetros do motor (`config` hash curto). |
| 3 | **Score, rating e classificação final** | MOTOR | Bloco de destaque: **SCORE CALCULADO** (número grande + gauge SVG simplificado) · **RATING CALCULADO** · **CLASSIFICAÇÃO FINAL APÓS REGRAS DE NEGÓCIO** · tendência 90 d com seta e rótulo. Se houver veto: caixa vermelha com borda `VETO ATIVO — {rotulo}` e a justificativa; se houver teto: caixa laranja `TETO APLICADO — {rotulo}`. Texto fixo sob o bloco: *"O score calculado permanece exibido mesmo quando a classificação final é rebaixada por regra de negócio."* |
| 4 | **Probabilidade de inadimplência (PD)** | MOTOR | Três colunas: **6 meses · 12 meses · 24 meses**, percentuais com 1 decimal, mini-barra por coluna. Linha de método (`pd.metodo`) em 8 pt. |
| 5 | **Risco de Recuperação Judicial** | MOTOR | Se `eventoJaOcorrido`: rótulo `RJ EM CURSO — evento ocorrido`, data de distribuição/deferimento, painel **Stay Period** (dias decorridos, dias restantes, lista "impedido" e lista "permanece possível"). Caso contrário: probabilidade 12 m, índice (efetivo/bruto), elegibilidade pela Lei 14.112/2020 com motivo de inelegibilidade quando houver, e tabela dos sinais com pontos. Texto fixo: *"Inadimplência e Recuperação Judicial são eventos distintos e medidos separadamente."* |
| 6 | **Resumo executivo** | **LLM** (fallback MOTOR) | 4 a 7 frases, máx. 900 caracteres: situação, principais motivos do rating, o que muda em relação ao último snapshot, o que se recomenda. Toda frase com número cita o campo de origem. Etiqueta ao pé: `Texto gerado por IA a partir dos dados deste parecer` ou `Texto padrão (sem IA)`. |
| 7 | **Principais riscos** | MOTOR (lista) + **LLM** (leitura) | Lista das red flags ordenadas por severidade e depois por `impactoEmPontos`: severidade (badge + rótulo), título, data, fonte (simulado), impacto em pontos, status. Máx. 8 na página; excedente vai para anexo. Abaixo da lista, parágrafo LLM "Leitura dos riscos" (máx. 700 caracteres) — interpreta a combinação (ex.: pluralidade de credores + PGFN crescente = pressão de liquidez), sem introduzir fato novo. |
| 8 | **Fatores mitigadores** | MOTOR (lista) + **LLM** (leitura) | Fatores com `direcao: 'protecao'` (rótulo, pontos, fonte) e garantias extraconcursais relevantes. Se não houver nenhum: texto fixo *"Nenhum fator de proteção materializado na data de referência."* Parágrafo LLM opcional (máx. 400 caracteres). |
| 9 | **Análise de exposição e garantias** | MOTOR | Tabela de operações por tipo (`VENDA_A_PRAZO`, `BARTER`, `CPR`) com saldo, a vencer em 90 d, em atraso; utilização do limite. Tabela de garantias com **duas seções separadas por natureza**: **EXTRACONCURSAL** (alienação fiduciária, CPR financeira registrada) e **CONCURSAL** (CPR física, penhor, hipoteca, aval/fiança), cada uma com valor declarado, haircut, valor atualizado, registrada, bem embargado. Indicadores: cobertura extraconcursal, cobertura total, exposição protegida, exposição em risco e, em destaque próprio com borda, **`Exposição em risco em cenário de RJ`** com o texto fixo *"Quanto a Krill Tech perde de proteção efetiva se este cliente pedir RJ: garantias concursais entram no plano; apenas as extraconcursais permanecem executáveis."* Barter sem CPR vinculada é listado nominalmente. |
| 10 | **Recomendação operacional** | MOTOR (código + ações) + **LLM** (justificativa) | Código da recomendação em destaque (`rotulo`), prazo de reavaliação, lista numerada de ações parametrizadas com prioridade (1 = imediata). Abaixo, parágrafo LLM "Justificativa" (máx. 600 caracteres) que conecta ações a riscos e mitigadores. Caixa fixa, não dispensável: **Decisão final sujeita à avaliação do analista responsável.** Área de decisão: se já houver `RegistroAuditoria` para este cliente, imprime a decisão, data e justificativa e a marca `divergiu da recomendação` quando aplicável; se não, imprime linhas em branco rotuladas "Decisão do analista", "Justificativa", "Data / assinatura". |
| 11 | **Evidências consultadas** | MOTOR | Tabela: nº, fonte (rótulo humano + `(simulado)`), tipo, título, data do documento, **data da consulta**, fatores relacionados (ids em fonte mono, 8 pt). Ordenada por fonte e data. 14 linhas por página; excedente em páginas adicionais do anexo. |
| 12 | **Metodologia e auditoria de fechamento** | MOTOR | Pesos das 7 dimensões, score por dimensão, contribuição ponderada, e a linha de auditoria: `Σ impactos = {somaImpactos} · score reconstruído = {scoreReconstruido} · diferença = {diferenca}`. Uma frase fixa: *"A soma das contribuições dos fatores reconstrói exatamente o score. Detalhe completo na aba Metodologia da aplicação."* |
| 13 | **Aviso obrigatório** | fixo | Ver §3.7. Sempre a última seção da última página, nunca separado dela. |

### 3.5.1 Alocação padrão de páginas

| Página | Seções |
|---|---|
| 1 | 1, 2, 3, 4, 5, 6 (a página 1 é a que a banca vê primeiro: identificação, números-chave e resumo) |
| 2 | 7, 8 |
| 3 | 9, 10 |
| 4 | 11 (até 14 evidências), 12, 13 |
| 5+ (anexo) | red flags excedentes (>8), evidências excedentes (>14), cada página com 14 linhas; o aviso (13) migra para a última página |

Se o cliente estiver em `RJ_EM_CURSO`, a seção 5 cresce (Stay Period) e a seção 6 desce para a página 2; o
alocador trata isso movendo a seção 8 para a página 3. Regra geral do alocador: preencher em ordem, nunca dividir
uma seção, exceto as duas listas fatiáveis (7 e 11).

## 3.6 Limites de conteúdo (para paginação previsível)

| Bloco | Limite |
|---|---|
| Resumo executivo (LLM) | 900 caracteres; o prompt pede 4–7 frases; excedente é truncado em fronteira de frase com "…" e o fato é registrado no console de desenvolvimento |
| Leitura dos riscos (LLM) | 700 caracteres |
| Leitura dos mitigadores (LLM) | 400 caracteres |
| Justificativa da recomendação (LLM) | 600 caracteres |
| Red flags na página 2 | 8; excedente em anexo |
| Ações recomendadas | todas (o motor emite no máximo 8) |
| Evidências por página | 14 |
| Garantias por seção de natureza | 6 por página; excedente em anexo, mantendo os totais na página 3 |

## 3.7 Aviso obrigatório (texto final)

Caixa com borda 1 pt, fundo cinza-claro imprimível, 9 pt:

> **Aviso.** Este relatório foi gerado de forma automatizada pela plataforma Lastro e constitui **instrumento de
> apoio à decisão**. Os valores de score, rating, probabilidade de inadimplência e risco de recuperação judicial
> resultam de modelo quantitativo determinístico aplicado a evidências com fonte e data identificadas; os textos
> assinalados como gerados por IA foram redigidos por modelo de linguagem exclusivamente a partir desses valores
> e evidências, sem produzir ou alterar qualquer número. **A avaliação final e a decisão de crédito são de
> responsabilidade do analista responsável**, que deve considerar informações adicionais não capturadas por
> este instrumento. Nesta versão, todos os dados são **simulados** e nenhuma base pública foi consultada; nomes,
> documentos e valores são fictícios. Documento {identificador}, parâmetros do motor {hash de config}.

## 3.8 O que vem do motor e o que vem do LLM — resumo de fronteira

| Vem do MOTOR (nunca do LLM) | Vem do LLM (sempre marcado, sempre com fallback) |
|---|---|
| Todo número: score, rating, classificação final, vetos e tetos, PD 6/12/24 m, índice e probabilidade de RJ, elegibilidade, Stay Period, exposições, coberturas, haircuts, deltas, impacto em pontos | Resumo executivo (seção 6) |
| Toda lista: red flags, fatores de proteção, ações recomendadas, evidências, garantias, sinais de RJ | Leitura dos riscos (parágrafo da seção 7) |
| O **código** da recomendação e o prazo de reavaliação | Leitura dos mitigadores (parágrafo da seção 8) |
| Todo texto fixo de interface e o aviso obrigatório | Justificativa da recomendação (parágrafo da seção 10) |
| Identificador, hash, datas, responsável | — |

Validador de saída do LLM (aplicado antes de renderizar qualquer parágrafo): extrai todos os tokens numéricos e
monetários do texto; cada um deve corresponder — após normalização de formatação — a um valor presente no JSON de
entrada. Falha → parágrafo substituído pelo texto determinístico e etiqueta `texto padrão (sem IA)`.

Texto determinístico de fallback (gerado por template em código, não por LLM) para cada um dos quatro blocos
existe obrigatoriamente e é o que aparece em teste automatizado (D5: fixtures, sem chamada ao vivo).

## 3.9 Botão "Exportar relatório"

Local: barra de ferramentas fixa da rota (oculta na impressão). Estados e comportamento:

| Estado | Rótulo e aparência | Comportamento ao clicar |
|---|---|---|
| Pronto (todos os blocos de prosa concluídos ou em fallback) | `Exportar relatório` — botão primário | Executa a sequência de exportação abaixo |
| Gerando texto (streaming em curso) | `Exportar relatório` com contador `texto {n}/4` e spinner; botão secundário ao lado: `Exportar agora com texto padrão` | Primário: aguarda conclusão (máx. 25 s, o timeout de D5) e então exporta. Secundário: substitui os blocos pendentes pelo texto determinístico, marca-os `texto padrão (sem IA)` e exporta imediatamente |
| LLM desativado ou orçamento esgotado | `Exportar relatório` com nota `texto padrão (sem IA)` | Exporta imediatamente |
| Falha de repositório (sem avaliação) | Desabilitado, `Sem dados para exportar` | — |

Sequência de exportação:

1. Confirma que o alocador de páginas concluiu e que `Página X de Y` está preenchido em todos os rodapés.
2. `document.title = "Lastro_Parecer_{slug da razão social}_{AAAA-MM-DD}"` (sugere o nome do arquivo no diálogo do navegador).
3. `window.print()`. Com `@page size: A4 portrait; margin: 0`, cabeçalho e rodapé do navegador ficam vazios e o
   PDF sai com o cabeçalho/rodapé próprios do documento.
4. No `afterprint`, restaura `document.title` para `"Parecer de Risco — {razaoSocial} · Lastro"`.
5. Grava na sessão (`localStorage`, chave `lastro:sessao:v1`, campo `pareceresExportados[]`) o par
   `{identificador, dataHora}` — sem criar tipo novo em `types/`; é anotação de sessão, exibida na timeline do
   cliente como entrada informativa `Parecer {identificador} exportado`.
6. Não há download programático além do diálogo de impressão do navegador. Nenhuma biblioteca de PDF.

Atalho: `Ctrl/Cmd + P` na rota dispara a mesma sequência (interceptado para aplicar o título e as verificações).

## 3.10 Critérios de aceite do parecer

1. Impressão em Chromium de um cliente A sem RJ gera exatamente 4 páginas; de um cliente em `RJ_EM_CURSO` com
   ≥ 9 red flags e ≥ 15 evidências gera 5 ou 6, com o aviso na última.
2. Em toda página impressa aparecem: badge `DADOS SIMULADOS`, marca d'água, identificador, `Página X de Y`,
   linha de responsabilidade do analista.
3. Com `LASTRO_LLM_ENABLED=false`, o documento é completo e todos os quatro blocos de prosa exibem
   `texto padrão (sem IA)`.
4. Nenhum número presente em parágrafo LLM falta no JSON de entrada (teste com fixtures gravadas).
5. A seção 9 nunca soma extraconcursal e concursal sem exibir as duas parcelas separadamente antes do total.
6. O score calculado aparece na seção 3 mesmo quando há veto de força D.
