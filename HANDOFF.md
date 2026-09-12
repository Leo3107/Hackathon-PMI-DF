# HANDOFF — projeto Lastro

> **Para o próximo agente.** Este arquivo é o ponto de retomada. Leia-o inteiro antes de
> qualquer coisa. Gerado em 2026-09-12, ao fim da sessão de especificação e início do build.
>
> Ordem de leitura recomendada: este arquivo → `specs/00-decisoes.md` → `AGENTS.md` →
> `CONTEXT.md` → `plans/PLAN_2026-09-12_lastro-risk-intelligence.md` → a spec do que você for tocar.

---

## 1. O que é

**Lastro** — protótipo funcional de plataforma de inteligência de risco de crédito e prevenção
à inadimplência no agronegócio. Construído para o **Hackathon PMI-DF 2026** (Edital 01/2026),
desafio da empresa parceira **Krill Tech**. Usuário-alvo: o **analista de crédito** da Krill Tech.

Tese do produto, que orienta toda decisão de escopo:

> Não entregamos apenas uma nota. Entregamos o risco, a causa, a evidência e a ação recomendada.

O documento oficial do desafio está em [`specs/_desafio-pdf.txt`](specs/_desafio-pdf.txt).
**Leia-o.** Ele contém o glossário jurídico que virou funcionalidade calculada do produto e
define os entregáveis oficiais: **Project Canvas de uma página + pitch**. Código funcional não é
exigido pelo edital — nosso protótipo é diferencial competitivo, não requisito.

## 2. Estado do repositório

- **Branch de trabalho:** `feat/lastro-risk-intelligence`, já publicada em
  `origin/Leo3107/Hackathon-PMI-DF`. **Nunca commitar na `main`.**
- **Último commit publicado:** `d79da95` (specs da camada de linguagem).
- **`.env` contém uma chave real da OpenAI e o remote é público.** Está no `.gitignore` e
  verificado com `git check-ignore .env`. **Confira isso antes de todo commit.**

### Commits até aqui

| Hash | Conteúdo |
|---|---|
| `caeb35a` | Scaffold dos dois serviços + specs do núcleo (00, 01, 02) |
| `de9b022` | README, plano ativo, harness de E2E, dependências do frontend |
| `18298e3` | Specs 05 (design system) e 07 (Canvas/Arquitetura/Parecer) |
| `d79da95` | Spec 04 (camada de linguagem) |

## 3. Decisões travadas com o usuário — **não reabra sem perguntar**

Todas estão em [`specs/00-decisoes.md`](specs/00-decisoes.md), que é **autoritativo**: em conflito
entre specs, ele vence. Resumo do que foi decidido pelo humano, não por inferência:

| # | Decisão |
|---|---|
| 1 | **Escopo completo** — as 12 prioridades do briefing, não um recorte |
| 2 | **Motor determinístico real** — nada de número escrito à mão no mock; tudo calculado |
| 3 | **LLM real da OpenAI**, modelo `gpt-5.4-mini`, para narrativa **e** copiloto de análise |
| 4 | **Chamada sempre ao vivo, sem cache e sem pré-geração** — o usuário recusou cache explicitamente |
| 5 | **Streaming**, com os números renderizando instantaneamente e só a prosa em stream |
| 6 | **Nos testes, fixtures gravadas** — nunca chamada real, para preservar o saldo |
| 7 | **Dark-only**, design system próprio, sem shadcn/ui nem biblioteca de componentes |
| 8 | **Acento azul-aço**; verde/âmbar/laranja/vermelho reservados à semântica de risco |
| 9 | **Controle de simulação de evento ao vivo** para o pitch |
| 10 | **Project Canvas como rota `/canvas`** da própria aplicação |
| 11 | **Pipeline de 4 agentes do edital, mas stack próprio** — proibido mencionar IBM/watsonx/IBM Bob |
| 12 | **Institutos jurídicos como funcionalidade de primeira classe**, não tooltip |
| 13 | **Exposição modela venda a prazo, barter e CPR** |
| 14 | **Next.js (interface) + Flask (motor e IA)** — mudança de stack pedida no meio da sessão |
| 15 | **Execução autônoma até a entrega**, com commit e push ao final |

### Autorizações e restrições operacionais dadas pelo usuário

- ✅ **Commitar e dar push** na branch de trabalho — autorizado explicitamente.
- ✅ **Desligar o computador ao final**, mas **somente após confirmar que o push chegou ao remote**.
- ⚠️ **Orçamento de US$ 10 na OpenAI.** Não gaste em teste automatizado. O usuário pediu
  explicitamente contenção de custo.
- ⚠️ **Usar Opus 5 nos subagentes** para reduzir consumo de tokens.
- ⚠️ O usuário está dormindo. Decisões pequenas são suas; só pare se algo invalidar uma das
  decisões acima.

## 4. Arquitetura

```
web/   Next.js 16.3.5 · React 19.2.8 · TypeScript strict · Tailwind v4   :3000
api/   Flask 3.1.3 · pydantic 2.13.5 · openai 3.13.0 · Python 3.13       :5001
```

O browser **nunca** fala com o Flask diretamente. Os route handlers do Next em `web/app/api/*`
fazem proxy server-side, de modo que a `OPENAI_API_KEY` nunca sai do backend e não há CORS em produção.

```bash
npm run dev        # sobe os dois com concurrently
npm test           # pytest do motor + typecheck e lint do frontend
npm run e2e        # Playwright
```

Interpretador Python no Windows/Git Bash: `api/.venv/Scripts/python`.

## 5. Specs — todas escritas

| Arquivo | Linhas | O que traz |
|---|---|---|
| `specs/00-decisoes.md` | — | **Autoritativo.** As 15 decisões acima, com justificativa |
| `specs/01-modelo-de-dados.md` | — | Contrato de tipos. Fatos brutos separados do derivado |
| `specs/02-motor-de-risco.md` | — | **A matemática completa.** Fatores, dimensões, score, PD, RJ, vetos, Stay Period, garantias, deltas |
| `specs/04-camada-llm.md` | ~1.560 | Prompts literais, protocolo NDJSON, verificador numérico, ledger, rubrica |
| `specs/05-design-system.md` | ~1.640 | Tokens, contrastes calculados, geometria do gauge, 15 formatadores |
| `specs/07-canvas-arquitetura-parecer.md` | ~780 | Os 10 blocos do Canvas com texto final, aba de arquitetura, parecer imprimível |

### ⚠️ As specs 03 e 06 estavam sendo escritas quando a sessão terminou

Se **`specs/03-ux-e-telas.md`** ou **`specs/06-dados-simulados.md`** não existirem no disco, os
subagentes que os escreviam foram interrompidos. **Você precisa escrevê-los antes de construir as
telas e o dataset.** Os briefings completos que eu havia passado a eles estão reproduzidos na
seção 9 deste documento — use-os como está.

## 6. Invariantes do produto — não negociáveis

Estas são a diferença entre um protótipo que sustenta uma arguição e um que desmonta na primeira
pergunta da banca. Todas devem estar cobertas por teste.

| # | Invariante |
|---|---|
| I1 | Os pesos das sete dimensões somam exatamente 1,00 |
| I2 | A soma das contribuições dos fatores **reconstrói o score exibido** |
| I3 | PD 12m é estritamente decrescente no score |
| I4 | PD 6m < PD 12m < PD 24m em toda combinação |
| I5 | O dataset contém caso de **PD moderado com RJ alto** e de **PD alto com RJ baixo** |
| I6 | A soma dos deltas por fator **reconstrói exatamente a variação do score** |
| I7 | **O LLM nunca produz, altera ou recalcula um número** |
| I8 | Nenhum estado de risco é comunicado apenas por cor |
| I9 | Toda tela com recomendação exibe o aviso de decisão humana |
| I10 | O aviso de dados simulados aparece em toda rota e em todo PDF |

I3 e I4 **já foram verificadas numericamente** por varredura de 0 a 1000: zero violação.
As tabelas de PD e de risco de RJ em `specs/02` contêm os valores conferidos, não estimados.

## 7. O que está pronto no código

### `api/models/` — ✅ completo
Modelos pydantic v2 espelhando `specs/01`. Campos internos em `snake_case`, serialização JSON com
as chaves camelCase do contrato TypeScript. Arquivos: `base`, `enums`, `cliente`, `fatos`,
`exposicao`, `avaliacao`, `eventos`, `tabelas`.

### `api/scoring/` — 🔶 parcial
Existem: `config.py`, `fatores.py`, `dimensoes.py`, `score.py`, `exposicao.py`, `formatacao.py`,
`util.py`. **Faltam** (conforme a spec 02): `probabilidades.py`, `vetos.py`, `stay_period.py`,
`red_flags.py`, `recomendacao.py`, `delta.py`, `audit.py` e o `__init__.py` que expõe
`calcular_risco(fatos, config=None, data_referencia=None)`.
**`api/tests/` ainda não existe.** A suíte de invariantes é o item mais importante em aberto.

### `web/` — 🔶 parcial
- `lib/format.ts` + `format.test.ts` — formatadores pt-BR
- `components/ui/` — `cn`, `fontes`, `glossario`, `risco`, `tipos-ui`, `gauge-geometry` (+ teste)
- `app/globals.css` — tokens em curso
- `app/canvas/` + `components/canvas/` — Project Canvas em curso
- **Faltam:** a maior parte dos primitivos, `web/types/`, shell, e todas as demais rotas

## 8. Plano de retomada — ordem sugerida

O plano completo, com workstreams e matriz de feedback, está em
[`plans/PLAN_2026-09-12_lastro-risk-intelligence.md`](plans/PLAN_2026-09-12_lastro-risk-intelligence.md).
Fronteiras de arquivo já definidas lá — **respeite-as para poder paralelizar sem conflito**.

```
1. Escrever specs 03 e 06 (se ausentes)          ← briefings na seção 9
2. Terminar api/scoring/ + api/tests/            ← caminho crítico, é o coração
3. api/data/ (18 clientes)                       ← depende da spec 06
4. api/llm/ (camada de linguagem)                ← spec 04, territorio api/llm/**
5. api/app.py + api/routes/ (Flask)              ← depende de 2 e 3
6. web/types/ + design system + shell            ← spec 05 e 03
7. Telas: carteira, cliente, nova análise,
   alertas, auditoria                            ← spec 03
8. Integração, E2E, vivência com navegador real,
   correções
9. Commit, push, e só então desligar a máquina
```

### Onde está o risco de prazo
A **página do cliente** (WS8) é a maior superfície: score com veto, PD, risco de RJ, recomendação,
"por que este score", decomposição, red flags, exposição e garantias, Stay Period, timeline,
evidências, copiloto e decisão do analista. Comece por ela assim que a API responder.

### Riscos técnicos já identificados
1. **Buffering do stream** em qualquer dos dois saltos mata o streaming silenciosamente.
   Mitigações na spec 04: `direct_passthrough`, `X-Accel-Buffering`, `force-dynamic`, proxy
   devolvendo `upstream.body` sem ler.
2. **Ledger de custo é por processo** — o Flask precisa rodar com worker único.
3. **Sem cache** significa 4–8s de latência por bloco de prosa a cada abertura. O contador de
   custo na interface é a defesa visível contra gasto silencioso.
4. O contexto do parecer ficou em ~4.500 tokens de entrada. Se o orçamento apertar, o primeiro
   corte é o campo `resumo` das evidências.

## 9. Briefings originais das specs 03 e 06

Reproduzidos na íntegra para você não precisar reconstruí-los. Dispare cada um como subagente
(modelo Opus), um arquivo por agente, sem sobreposição.

### 9.1 · `specs/03-ux-e-telas.md`

Papel: arquiteto de informação e Product Designer sênior. Ler antes: `00-decisoes.md`,
`01-modelo-de-dados.md`, `02-motor-de-risco.md`, `_desafio-pdf.txt`.

Conteúdo exigido:

1. **Arquitetura de informação e rotas.** Rotas obrigatórias: `/carteira` (para onde `/`
   redireciona), lista de clientes, `/clientes/[id]`, `/nova-analise`, `/alertas`, `/auditoria`,
   `/arquitetura`, `/canvas` e a rota de parecer imprimível. Decidir se a lista é rota própria ou
   seção da carteira, e justificar. Definir a navegação persistente e onde vivem o banner de dados
   simulados, a identidade do analista, o contador de custo do LLM e o controle de simulação de evento.
2. **Carteira.** Responde "onde está o risco da carteira?". KPIs: exposição total a prazo,
   exposição em risco, exposição crítica, cobertura por garantia separando extraconcursal de total,
   quantidade de clientes, clientes por rating, alertas em 30 dias, clientes com deterioração
   relevante, concentração geográfica e por cultura. **Dizer quais visualizações entram e quais são
   recusadas, e por quê** — o briefing proíbe gráfico decorativo. Para cada gráfico: pergunta que
   responde, tipo de marca, eixos, e o drill-down ao clicar. Definir a faixa de atenção imediata no topo.
3. **Lista de clientes.** Colunas: Cliente, CPF/CNPJ, Município/UF, Tipo, Cultura, Exposição,
   Próximo vencimento, Score, Rating, PD 12m, Risco de RJ, Tendência, Alertas. Filtros: Todos,
   Rating A/B/C/D, Com alerta, Com gatilho de veto, Deterioração recente, Alta exposição. Busca por
   cliente, documento e município. Ordenação por score, exposição, PD, variação do score e alertas.
   Especificar composição dos filtros, estado vazio, e como score+rating+tendência cabem numa célula
   sem poluir.
4. **Página do cliente.** Ordem e conteúdo de cada bloco: cabeçalho; score grande com rating,
   tendência, variação e — havendo veto — **score calculado vs classificação final lado a lado com o
   motivo nomeado**; PD 6/12/24 e risco de RJ **como indicador separado, jamais na mesma escala**;
   recomendação com ações e aviso de decisão humana; "por que este score" com fatores de risco e de
   proteção e o impacto de cada um; decomposição por dimensão; red flags; exposição e garantias com
   extraconcursal vs concursal e exposição em risco em cenário de RJ; painel de Stay Period; linha do
   tempo; fontes e evidências; copiloto; decisão do analista. Definir layout em colunas, o que fica
   acima da dobra e o que vai para drawer.
5. **Linha do tempo.** Data, score naquele momento, evento. Deve deixar a deterioração evidente.
   Definir como o score é plotado junto dos eventos e a interação de abrir a evidência.
6. **Nova análise.** CPF/CNPJ → consultar → pipeline visual com os estágios Cadastral, Jurídico,
   Fiscal, Ambiental, Agroclimático, Interno → Score → Relatório. Validação do documento, documento
   não encontrado, perfis demonstrativos clicáveis, e a animação refletindo estágios reais do motor.
7. **Central de alertas.** Crítico, Alto, Médio, Informativo. Cada alerta com cliente, data, tipo,
   severidade, impacto e ação recomendada. Agrupamento, filtros, marcação de lido, navegação.
8. **Auditoria.** Quem analisou, quando, qual score, qual recomendação e qual decisão humana.
   Campo de decisão com Aprovar, Aprovar com restrições, Revisar, Suspender, Recusar, mais
   justificativa. Destacar divergência entre recomendação e decisão.
9. **Estados.** Por tela: loading, vazio, erro, cliente selecionado, filtros ativos, busca sem
   resultado, streaming em andamento, LLM indisponível, orçamento esgotado, **e API Flask fora do ar**
   — com erro claro e acionável, nunca tela branca.
10. **Acessibilidade e microcópia.** Tooltips para PD, RJ, CNDT, CAR, ZARC, CPR, extraconcursal,
    concursal, Stay Period, inadimplência técnica. Moeda em R$ pt-BR, datas em pt-BR, navegação por
    teclado nas tabelas, foco visível, nunca só cor.
11. **Os 30 segundos do jurado.** Seção final descrevendo o caminho exato do olho ao abrir a app.

Formato: markdown denso, tabelas, wireframes em ASCII para carteira, cliente e nova análise.
Prescritivo — outro agente implementa sem poder perguntar. Sem código React.

### 9.2 · `specs/06-dados-simulados.md`

Papel: analista de crédito sênior do agronegócio + engenheiro de dados. Ler antes: `00-decisoes.md`,
`01-modelo-de-dados.md`, `02-motor-de-risco.md`, `_desafio-pdf.txt`.

**Regra central:** não escrever score, PD, rating nem red flag. Escrever apenas `FatosDoCliente`.
Calibrar os fatos para que o score resultante caia na faixa pretendida, **fazendo a conta à mão
pelas fórmulas da spec 02 e registrando-a**. Se não cair na faixa, ajustar os fatos, nunca o motor.

Personas obrigatórias entre os **18 clientes**: um excelente rating A; um moderado B; um em
deterioração que cai de B para C ao longo dos snapshots; um crítico D; um com **veto de embargo do
IBAMA sobre imóvel dado em garantia** (o briefing cita esse caso nominalmente); um com boa nota mas
risco jurídico recém-surgido; um com risco climático alto; um com muitas garantias e
sobrecolateralização; um de exposição elevada; um **em RJ em curso com Stay Period ativo**; um
**produtor rural PF não elegível a RJ** pela Lei 14.112/2020; um com **inadimplência técnica sem
nenhum atraso financeiro** — o caso que prova a tese do produto. E a **invariante I5**: um cliente
com PD moderado e RJ alto (paga a Krill Tech em dia mas tem muitos credores executando) e um com PD
alto e RJ baixo.

Coerência exigida: município, UF e cultura compatíveis com a realidade agrícola brasileira (soja e
milho no Matopiba, Centro-Oeste e Paraná; algodão na Bahia e no Mato Grosso; café em Minas; cana em
São Paulo e Goiás; arroz e soja no Rio Grande do Sul; fruticultura irrigada no Vale do São
Francisco), **usando municípios reais**. Exposição compatível com área e cultura, a partir de uma
razão documentada de R$ por hectare. Patrimônio, capital social e faturamento mutuamente
compatíveis. Garantia compatível com o bem. Atraso médio, pior atraso e pontualidade consistentes
entre si. Quem tem execuções não pode ter `semLitigio36m`; quem tem CNDT positiva não pode ter
`todasCertidoesNegativas` — **fazer e documentar uma varredura de contradições**. Razões sociais
fictícias, CPF/CNPJ com dígito verificador válido e marcados como simulados. Datas coerentes com o
calendário agrícola e com a data de referência **2026-09-12**.

Snapshots: 5 a 7 por cliente ao longo de 12 meses, especificando **o que muda entre um e outro**,
porque o delta é calculado da diferença. Para pelo menos um cliente, reproduzir a narrativa do
briefing: **queda de 712 para 604 em cerca de 60 dias**, decomposta em novas execuções, nova dívida
ativa, deterioração climática e piora do comportamento de pagamento.

Eventos e alertas derivados dos snapshots, com as quatro severidades representadas. Evidências
distribuídas pelas 14 fontes previstas, cada uma com fonte, data de consulta, tipo, resumo e os
fatores que sustenta, todas marcadas como consulta simulada. Mais 3 ou 4 **prospects** para o fluxo
de due diligence — um aprovável, um limítrofe, um recusável — e o tratamento de documento desconhecido.

Estrutura de arquivos sob `api/data/` em Python, um cliente por arquivo, snake_case. Ao final,
tabela consolidada dos 18 com nome, município/UF, cultura, tipo de pessoa, exposição, score
estimado, rating, PD 12m, risco de RJ e persona — e a exposição total da carteira, que deve ficar
na ordem de dezenas a poucas centenas de milhões de reais.

## 10. Armadilhas desta máquina

- **Heredoc de markdown extenso quebra o parser do Git Bash aqui.** Use a ferramenta Write para
  arquivos grandes.
- **`create-next-app` recusa nome de projeto começando com ponto.**
- **`gpt-5.4-mini` exige `max_completion_tokens`**, não `max_tokens`. Streaming funciona com
  `stream=True` e `stream_options={"include_usage": True}`; o `usage` chega no último chunk;
  `reasoning_tokens` vem 0; latência típica de 6,4s para ~860 tokens de saída. **Tudo isso já foi
  verificado na prática — não gaste cota confirmando de novo.**
- Git avisa sobre conversão LF→CRLF a cada commit. É ruído, não erro.

## 11. Definição de pronto

A aplicação está entregue quando:

- [ ] `npm test` verde — pytest do motor com as invariantes I1 a I6, typecheck e lint do frontend
- [ ] `npm run build` verde
- [ ] `npm run e2e` verde, sem erro de console
- [ ] Todas as rotas navegáveis com os dois serviços de pé
- [ ] **Vivência real com navegador**: abrir a carteira, filtrar, entrar num cliente, ler o score e
      a recomendação, abrir uma evidência, perguntar ao copiloto, simular um evento e ver o score
      mudar, gerar o parecer, abrir o Canvas
- [ ] Ensaio com `LASTRO_LLM_ENABLED=false` provando que a app continua íntegra sem rede
- [ ] Um jurado abrindo a aplicação entende em 30 segundos quem está em risco, quanto dinheiro
      está em risco, por quê, o que mudou, o que fazer e qual a evidência
- [ ] Commit e **push confirmado no remote**
- [ ] Só então: desligar a máquina, conforme o usuário autorizou
