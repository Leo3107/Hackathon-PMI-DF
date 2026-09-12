# 00 — Decisões da sessão (registro autoritativo)

> Toda decisão abaixo foi **confirmada pelo usuário** ou é decisão de engenharia tomada sob
> prazo e registrada explicitamente. Nenhum subagente pode contrariar este arquivo.
> Em caso de conflito entre specs, **este arquivo vence**.

Data: 2026-09-12 · Produto: **Lastro** · Cliente-caso: **Krill Tech** · Evento: Hackathon PMI-DF 2026 (Edital 01/2026)

---

## D1 · Natureza do entregável

O Hackathon **não exige implementação funcional em código** (Documento de Desafio, §6, parágrafo final).
Os entregáveis oficiais são **Project Canvas (1 página)** e **pitch** perante a banca.

**Consequência:** o protótipo funcional é um *diferencial competitivo*, não o requisito.
Ele existe para **sustentar o pitch** e provar que a lógica do Canvas é real e executável.
Toda dúvida de escopo se resolve perguntando: *isso ajuda a banca a entender e acreditar em 30 segundos?*

O **Project Canvas é entregue dentro da própria aplicação**, na rota `/canvas`, com os 10 blocos
exigidos pela §7.1 do documento de desafio e exportação em PDF via print stylesheet.

## D2 · Grafia e nomenclatura

| Item | Grafia correta |
|---|---|
| Empresa parceira | **Krill Tech** (duas palavras — conforme o PDF oficial) |
| Produto | **Lastro** |
| Artefato de saída | **Relatório Padronizado de Risco de Crédito e Alerta Precoce de RJ/Insolvência** (nome oficial, §2 do desafio); na UI, abreviado para **"Parecer de Risco"** |
| Idioma | Português do Brasil, integralmente |

## D3 · Stack técnico — Next.js (interface) + Flask (motor e IA)

**Revisado em 2026-09-12 a pedido do usuário.** Arquitetura de dois serviços.

```
Browser ──HTTP──> Next.js (porta 3000)          ──HTTP interno──> Flask (porta 5001)
                  interface + proxy server-side                    motor + LLM + dados
```

O **browser nunca fala com o Flask diretamente.** Toda chamada passa por um route handler do
Next que faz proxy. Consequências desejadas: a `OPENAI_API_KEY` vive só no Flask, não há CORS a
resolver em produção, e a origem pública é uma só.

### `api/` — Flask (Python 3.13)

Implementa o **Motor de Decisão & Scoring** e o **Agente Sintetizador** da §6 do desafio.

- **Flask 3** + **pydantic v2** (modelos e validação) + **python-dotenv**
- **openai** (SDK oficial Python) para a camada de linguagem, com **streaming**
- **pytest** para o motor — o motor é função pura e é a parte com testes obrigatórios
- **flask-cors** apenas para o modo de desenvolvimento
- Sem banco de dados. Dataset simulado em arquivos Python/JSON sob `api/data/`
- Servidor de desenvolvimento: `flask --app app run --port 5001 --debug`

**Por que Python:** é onde a matemática de crédito e o ferramental preditivo pertencem, e é o
que a banca espera ver por trás de um "motor preditivo". Torna a aba `/arquitetura` honesta em
vez de ilustrativa.

### `web/` — Next.js 15 (App Router) + React 19 + TypeScript strict

- **Tailwind CSS v4** com tokens semânticos próprios
- **Recharts** para séries e distribuições; **SVG autoral** para o gauge de score
- **lucide-react** para ícones
- **npm** (Node 22 já instalado)
- **Playwright** para smoke E2E
- Sem lógica de risco. A interface **não recalcula nada** — consome o que o Flask devolve.
- Route handlers em `web/app/api/*` fazem **apenas proxy** para o Flask, inclusive repassando o
  stream de texto sem bufferizar.

### Contrato entre os dois

`specs/01-modelo-de-dados.md` define os tipos em TypeScript — eles são o **contrato da API**.
O Flask espelha os mesmos campos, com os mesmos nomes (em português), via modelos pydantic.
Divergência entre os dois lados é bug: um teste de contrato compara o JSON real devolvido pelo
Flask contra o tipo TypeScript esperado.

### Execução conjunta

Um `package.json` na raiz orquestra os dois processos com `concurrently`:
`npm run dev` sobe Flask e Next juntos. O Next exibe um estado de erro claro e identificável
se o Flask não estiver de pé — nunca uma tela branca.

### Estado de sessão

Decisões do analista, status de red flag e eventos simulados vivem em `localStorage` no
navegador (ver D11.3) e são enviados ao Flask junto da requisição quando alteram o cálculo.
Nenhuma persistência no servidor.

## D4 · Motor de risco — determinístico e real

**Confirmado pelo usuário.** Todos os números (score, decomposição, PD, risco de RJ, coberturas,
deltas) são **calculados** a partir de fatos brutos por cliente, nunca escritos à mão.

Invariante inegociável: **a soma das contribuições dos fatores reconstrói exatamente o score**,
e **a soma dos deltas por fator reconstrói exatamente a variação do score** entre dois instantes.
Se um jurado somar os componentes na tela, tem de fechar. Detalhe em `02-motor-de-risco.md`.

**O LLM nunca produz, altera ou recalcula um número.** Recebe os números já calculados e escreve texto.

## D5 · Camada de linguagem natural — LLM real

**Confirmado pelo usuário.** Provedor **OpenAI**, modelo **`gpt-5.4-mini`** (verificado como
disponível na conta em 2026-09-12; teste real: 604 tokens de entrada / 863 de saída, 0 tokens de
raciocínio, 6,4s de latência, qualidade de prosa aprovada).

Atua em **dois pontos**:
1. **Agente Sintetizador** — parecer, explicação do "por que este score", recomendação operacional.
2. **Copiloto de Análise** — caixa "Pergunte sobre este cliente", ancorada exclusivamente nas
   evidências e números daquele cliente, com citação de fonte e recusa explícita fora do escopo.

**Modo de chamada: sempre ao vivo** (decisão do usuário — sem pré-geração versionada, **sem cache de resposta**).

**Latência tratada por streaming** (decisão do usuário):
- Score, rating, PD, RJ, decomposição, red flags, garantias, exposição e timeline renderizam
  **instantaneamente** — vêm do motor determinístico, custo zero, sem rede.
- Apenas blocos de **prosa** chegam por streaming token a token, com skeleton identificado.
- **Nenhum número na tela jamais espera pelo LLM.** Falha ou timeout degrada só a prosa.

**Guardas obrigatórias** (mesmo sem cache):
- `LASTRO_LLM_ENABLED=false` → gerador determinístico de narrativa assume; app 100% funcional.
- `LASTRO_LLM_BUDGET_USD` → teto rígido de gasto acumulado; ao atingir, desliga a chamada e cai no determinístico.
- Contador de custo acumulado visível na interface (tokens e US$ estimado).
- Timeout de 25s por chamada, com degradação para o determinístico.
- A chave vive **apenas no servidor**. Jamais em variável `NEXT_PUBLIC_*`.

**Nos testes automatizados: fixtures gravadas**, não chamadas ao vivo (decisão do usuário) — para
que centenas de execuções de subagente não consumam o saldo de US$ 10. A avaliação de qualidade
do parecer (juiz) roda com orçamento contado, poucas dezenas de chamadas reais.

## D6 · Arquitetura conceitual — pipeline do desafio, stack próprio

**Confirmado pelo usuário:** reproduzir o **pipeline de 4 agentes** da §6 do documento de desafio,
mas **sem vincular ao ecossistema IBM**. A narrativa é de **motor proprietário da equipe**:
modelo de scoring próprio + LLM próprio na camada de síntese.

Agentes (nomes do desafio, implementação própria):
1. **Agente Coletor & Parser** — ingestão e parsing das fontes públicas
2. **Agente de Risco Agro & Climático** — cruza CAR × ZARC × histórico de quebra de safra
3. **Motor de Decisão & Scoring** — modelo preditivo próprio: score, PD 6/12/24m, risco de RJ
4. **Agente Sintetizador & Gerador de Relatórios** — LLM que compila achados em recomendação

A aba `/arquitetura` mostra o pipeline **e mapeia qual tela da app consome qual agente**,
separando visualmente o que é **ML quantitativo** do que é **LLM de linguagem**.

## D7 · Profundidade jurídica — institutos como funcionalidade de primeira classe

**Confirmado pelo usuário: incorporar tudo.** Não são tooltips decorativos; entram no cálculo.

| Instituto | Como entra no produto |
|---|---|
| **Stay Period** (180 dias, Lei 11.101/2005) | Cliente com RJ deferida exibe contagem regressiva do período de suspensão e bloqueio explícito de execução de garantia e de protesto. Painel dedicado na página do cliente. |
| **Alienação fiduciária = EXTRACONCURSAL** | Garantia que sobrevive à RJ. Indicador próprio de cobertura. |
| **Penhor = CONCURSAL** | Entra no plano de RJ com deságio. Indicador separado, nunca somado ao anterior sem distinção. |
| **Inadimplência TÉCNICA vs FINANCEIRA** | Quebra de covenant contratual detectada **antes** do atraso. Red flag antecipatória de categoria própria e penalidade na dimensão comportamental. É o coração do "agir antes do calote". |
| **Lei 14.112/2020** | Produtor rural **pessoa física** com ≥2 anos de atividade comprovada (Livro Caixa Digital ou inscrição estadual) é **elegível a pedir RJ**. Entra como fator do índice de propensão a RJ. PF não elegível tem risco de RJ fortemente reduzido. |
| **CPR física vs financeira** | Instrumento de lastro, classificado quanto à natureza e ao registro. |
| **Barter** | Operação de troca insumo × safra futura. Exige monitoramento de produtividade, clima e integridade da área plantada — conecta a dimensão agroclimática ao dinheiro exposto. |

## D8 · Tipos de operação modelados na exposição

**Confirmado:** `VENDA_A_PRAZO` (core B2B da Krill Tech), `BARTER`, `CPR`.

## D9 · Design

- **Dark-only.** Sem toggle de tema. Decisão de prazo e de densidade.
- **Design system próprio**: tokens semânticos em Tailwind v4 + primitivos autorais.
  Sem shadcn/ui, sem biblioteca de componentes de terceiros.
- **Acento de marca: azul-aço / ciano técnico.** Reservado a navegação, foco, marca e ações.
- **Verde, âmbar, laranja e vermelho são exclusivos da semântica de risco.** Nunca decorativos.
- Nunca depender só de cor: todo estado de risco carrega **rótulo textual + ícone + badge**.
- Desktop-first, responsivo até ~1280px de largura útil. Densidade alta, hierarquia tipográfica forte.

## D10 · Demo ao vivo

**Confirmado:** controle **"Simular evento de monitoramento"**, visivelmente rotulado como demo.
Injeta um evento real (nova execução, pedido de RJ, embargo do IBAMA, quebra de covenant) num cliente:
o motor **recalcula de fato**, o delta aparece no "por que mudou", um alerta entra na central e a
timeline ganha a entrada. Prova o monitoramento contínuo diante do jurado em segundos.

## D11 · Decisões de engenharia tomadas sob prazo (não perguntadas)

Registradas aqui para revisão explícita no checkpoint.

1. **Sem tela de login.** Um gate de autenticação atrasa o jurado sem agregar. A identidade do
   analista fica fixa no cabeçalho (persona de demonstração) e alimenta a trilha de auditoria.
2. **18 clientes** no dataset (faixa pedida: 15–20).
3. **Decisões do analista persistem em `localStorage`**, com botão "Restaurar dados da demonstração".
   Sobrevive a refresh durante o pitch sem exigir backend.
4. **Exportação de relatório e do Canvas por print stylesheet + `window.print()`** → PDF real do
   navegador, zero dependência e zero risco de build.
5. **Dados sintéticos e claramente fictícios**: razões sociais inventadas; municípios reais
   (informação pública e inócua); CPF/CNPJ gerados com dígito verificador válido, porém marcados
   como simulados em toda a interface.
6. **Nenhuma integração real com órgão público** é feita ou insinuada. Toda evidência exibe
   "consulta simulada" junto da data.
7. **Banner global permanente `DADOS SIMULADOS — protótipo demonstrativo`**, visível em todas as
   rotas e reproduzido no cabeçalho de todo PDF exportado.
8. **Rota inicial `/` redireciona para `/carteira`** — o jurado cai direto no "onde está o risco".

## D12 · Fora de escopo (não construir)

- Autenticação, multiusuário, permissões.
- Backend persistente, banco de dados, filas.
- Integração real com Receita Federal, DataJud, PGFN, TST, SICAR, IBAMA, CONAB, MAPA, INMET.
- Tema claro.
- Internacionalização.
- Treinamento real de modelo de ML (o "modelo preditivo" é o motor determinístico documentado).
- Qualquer funcionalidade não rastreável a uma seção do prompt do usuário ou do documento de desafio.
