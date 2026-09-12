# 03 — UX, arquitetura de informação e telas

> **Escopo deste arquivo.** Define *quais* telas existem, *o que* cada uma contém, em *que ordem*,
> com *que interações* e em *que estados*. É prescritivo: outro agente implementa a partir daqui sem
> poder perguntar nada.
>
> **Fora do escopo deste arquivo:** tokens, cores, tipografia, geometria de componentes e
> formatadores — tudo isso está em [`05-design-system.md`](05-design-system.md) e **não é redefinido
> aqui**. Quando este documento escreve `KpiTile`, `DataTable`, `ScoreGauge`, `FactorBar`,
> `StackedBar`, `Timeline`, `EvidenceCard`, `AlertRow`, `Drawer`, `Termo`, `StreamingText`,
> `ErrorState`, `EmptyState`, `CostCounter`, `SimulatedDataBanner`, está invocando o primitivo já
> especificado na 05, com as props de lá.
>
> Em conflito com [`00-decisoes.md`](00-decisoes.md), **a 00 vence**.
> Os dados citados vêm de [`01-modelo-de-dados.md`](01-modelo-de-dados.md); o significado de cada
> número vem de [`02-motor-de-risco.md`](02-motor-de-risco.md); a prosa e o streaming vêm de
> [`04-camada-llm.md`](04-camada-llm.md); Canvas, arquitetura e parecer vêm de
> [`07-canvas-arquitetura-parecer.md`](07-canvas-arquitetura-parecer.md).

Data de referência do protótipo: **2026-09-12**. Idioma: **português do Brasil**, integralmente.

---

## 0. Premissas de produto que governam toda decisão de tela

### 0.1 O usuário

**Analista de crédito da Krill Tech.** Não é executivo, não é cientista de dados, não é advogado.
Opera venda a prazo, barter e CPR para produtores rurais e trading agrícolas. Decide limite, prazo e
garantia. **Mantém a decisão final** e responde por ela.

### 0.2 As cinco perguntas

Toda tela existe para responder rápido a uma ou mais destas cinco perguntas. Um bloco que não
responda a nenhuma delas **não entra**.

| # | Pergunta | Onde é respondida com prioridade |
|---|---|---|
| P1 | **Qual é o risco?** | `ScoreGauge`, rating, PD 6/12/24m, risco de RJ, exposição em risco |
| P2 | **Por que essa classificação?** | "Por que este score", decomposição por dimensão, vetos, red flags |
| P3 | **O que mudou?** | Tendência, variação em 90 dias, Σ deltas por fator, linha do tempo, alertas |
| P4 | **Qual a evidência?** | Fontes e evidências, selo "consulta simulada", link fator → evidência |
| P5 | **O que a Krill Tech deve fazer agora?** | Recomendação operacional com ações parametrizadas e prazo |

### 0.3 Os dois fluxos

| | **Fluxo A — Novo cliente** | **Fluxo B — Cliente existente** |
|---|---|---|
| Pergunta de negócio | "Posso conceder crédito a este CPF/CNPJ?" | "O que mudou na minha carteira desde ontem?" |
| Porta de entrada | `/nova-analise` | `/carteira` |
| Dado de origem | `Cliente.origem = 'PROSPECT'` | `Cliente.origem = 'CARTEIRA'` |
| Natureza | Pontual, sob demanda, orientada a decisão de concessão | Contínua, orientada a alerta e a delta |
| Saída | Parecer + decisão de concessão | Alerta + reavaliação + ação de mitigação |
| Diferença visual | Pipeline animado de coleta; sem histórico, sem timeline, sem carteira | Sem pipeline; histórico, deltas, alertas e exposição real |

O prospect **não tem** exposição, garantias, histórico interno, snapshots, timeline nem alertas. A
página do cliente detecta `origem` e suprime esses blocos (§4.13), em vez de mostrar cards vazios.

### 0.4 Regras de interface não negociáveis (derivadas das invariantes I7–I10)

| Regra | Consequência prática |
|---|---|
| **R1** | Nenhum número em tela espera o LLM. Números renderizam no primeiro paint; só prosa faz streaming. |
| **R2** | Nenhum estado de risco é comunicado só por cor — sempre **rótulo textual + ícone + badge** (I8). |
| **R3** | Toda tela que exibe recomendação exibe, de forma não dispensável, *"Decisão final sujeita à avaliação do analista responsável."* (I9). |
| **R4** | `SimulatedDataBanner` em toda rota, inclusive nas de impressão (I10). |
| **R5** | Todo número exibido tem origem rastreável: fator → evidência → fonte → data de consulta. |
| **R6** | A interface **não calcula nada**. Se um número não veio do Flask, ele não existe. Proibido somar, dividir ou arredondar no cliente; usar `lib/format.ts`. |
| **R7** | Erro nunca é tela branca. Todo estado de falha tem causa nomeada, consequência e ação (§9). |

---

## 1. Arquitetura de informação e rotas

### 1.1 Mapa de rotas

| # | Rota | Nome na navegação | Shell | Responde | Origem dos dados |
|---|---|---|---|---|---|
| 1 | `/` | — | — | — | **Redirect 308 permanente para `/carteira`** (D11.8). Não renderiza nada. |
| 2 | `/carteira` | Carteira | sim | P1, P3 no agregado | `listarClientes` + avaliação de cada cliente |
| 3 | `/clientes` | Clientes | sim | P1 comparativo | `listarClientes` + avaliações |
| 4 | `/clientes/[id]` | *(breadcrumb: razão social)* | sim | P1–P5 | `obterCliente`, `obterFatosAtuais`, `obterHistorico`, `obterEventos` |
| 5 | `/clientes/[id]/parecer` | *(botão "Gerar parecer")* | **não** | P1–P5 em documento | idem + narrativa LLM. Especificado na **07 §Parte 3**. |
| 6 | `/nova-analise` | Nova análise | sim | P1–P2, P4–P5 (fluxo A) | `consultarDocumento` |
| 7 | `/alertas` | Alertas | sim | P3, P5 | `listarAlertas` |
| 8 | `/auditoria` | Auditoria | sim | governança | `listarAuditoria` |
| 9 | `/arquitetura` | Arquitetura | sim | credibilidade técnica | estático. Especificada na **07 §Parte 2**. |
| 10 | `/canvas` | Project Canvas | **não** | entregável do edital | estático + agregados. Especificado na **07 §Parte 1**. |

Rotas 5 e 10 renderizam **sem sidebar e sem topbar**, com apenas uma barra de ferramentas própria
(voltar / imprimir), porque são documentos e não telas de trabalho. Mantêm o
`SimulatedDataBanner` na variante `impressao`.

**Nenhuma outra rota existe.** Não criar `/configuracoes`, `/perfil`, `/login`, `/relatorios`,
`/dashboard` (o dashboard **é** `/carteira`) nem qualquer rota não listada acima.

### 1.2 Decisão: a lista de clientes é rota própria (`/clientes`), não seção da carteira

**Decisão: rota própria.** Justificativa, nesta ordem de peso:

1. **São duas perguntas diferentes.** `/carteira` responde *"onde está o risco do meu portfólio?"* —
   é agregada, visual e de leitura em segundos. `/clientes` responde *"qual cliente atende a este
   critério?"* — é um instrumento de busca e triagem, com 13 colunas, 8 filtros e 5 ordenações. Empilhar
   uma tabela larga e filtrável embaixo de uma faixa de KPIs e quatro gráficos produz uma página de
   rolagem longa em que nenhuma das duas perguntas é respondida bem.
2. **Estado de filtro precisa de URL.** Filtros, busca e ordenação de `/clientes` são serializados em
   query string (§3.6) para serem compartilháveis e sobreviverem a refresh durante o pitch. Fazer isso
   dentro da carteira poluiria a URL da tela de abertura, que precisa ser limpa: `/carteira`.
3. **O drill-down precisa de destino.** Todo clique em KPI e em gráfico da carteira navega para
   `/clientes` com filtro pré-aplicado (§2.7). Sem rota própria, não há para onde navegar, e o drill-down
   viraria "rolar a página até a tabela", que é a pior forma de drill-down.
4. **Custo de não fazer é alto no pitch.** O jurado que abre a app vê agregados; o analista que
   trabalha vive na tabela. Separar deixa cada superfície otimizada para o seu uso.

**Contrapartida assumida:** a carteira perde a visão nominal imediata. Compensada por dois elementos
dentro de `/carteira`: a **faixa de atenção imediata** (§2.2, até 3 clientes nominados) e a tabela
**"Onde está o dinheiro em risco"** (§2.6, 8 linhas, somente leitura, com link "Ver todos os
clientes →"). Nenhuma das duas é filtrável — quem quer filtrar vai para `/clientes`.

### 1.3 Navegação persistente

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ ⚗ DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público│ 28px
├──────────────┬────────────────────────────────────────────────────────────────────┤
│ LASTRO       │ Carteira › Fazenda Vale do Araguaia   [busca]  US$0,42/10  ⚡ M.R. │ 48px
│ ──────────── ├────────────────────────────────────────────────────────────────────┤
│ ▣ Carteira   │                                                                    │
│ ▤ Clientes   │  conteúdo · padding 24px · max-width 1440px · grid 12 col · gap 16 │
│ ⊕ Nova análise│                                                                   │
│ △ Alertas  ③ │                                                                    │
│ ✓ Auditoria  │                                                                    │
│ ──────────── │                                                                    │
│ ⚙ Arquitetura│                                                                    │
│ ▦ Canvas     │                                                                    │
│              │                                                                    │
│ ─────────────│                                                                    │
│ Restaurar    │                                                                    │
│ demonstração │                                                                    │
└──────────────┴────────────────────────────────────────────────────────────────────┘
```

**Sidebar — 240px, colapsa para 56px abaixo de 1280px** (05 §5.2). Ordem fixa, agrupada em dois
blocos separados por divisória:

| Grupo | Itens | Racional da ordem |
|---|---|---|
| **Operação** | Carteira · Clientes · Nova análise · Alertas · Auditoria | Segue o dia do analista: panorama → triagem → concessão → reação → registro |
| **Documentação** | Arquitetura · Project Canvas | Superfícies de banca, não de trabalho. Sempre por último, visualmente atenuadas (`fg-tertiary`). |

- **Badge em "Alertas"**: contagem de alertas **não lidos**, com o número. Se houver ao menos um
  `CRITICA` não lido, o badge usa a cor semântica de crítico **e** o ícone `TriangleAlert` (R2). Zero
  não lidos = sem badge, jamais "0".
- Item ativo: borda esquerda 2px `accent-400`, fundo `accent-tint`, rótulo `fg-primary`.
- Colapsada: só ícone, com `Tooltip` à direita contendo o rótulo. O badge de alertas vira ponto de 6px.
- Rodapé fixo da sidebar: botão-texto **"Restaurar dados da demonstração"** (D11.3) — abre `Modal` de
  confirmação ("Isto apaga decisões registradas, eventos simulados e marcações de leitura desta
  sessão. Os dados voltam ao estado inicial.") com ações `Restaurar` / `Cancelar`. Limpa a chave
  `lastro:sessao:v1` e recarrega a rota atual.

**Topbar — 48px.** Da esquerda para a direita:

| Slot | Conteúdo | Comportamento |
|---|---|---|
| 1 | **Breadcrumb** | `Carteira` · `Clientes › Fazenda Vale do Araguaia` · `Clientes › Fazenda Vale do Araguaia › Parecer`. Cada nível anterior é link. Nível atual em `fg-primary`, não clicável. Trunca com reticências no meio, preservando o fim. |
| 2 | **Busca global** (`SearchInput`, 280px) | Atalho `/` e `Ctrl/Cmd+K`. Busca por razão social, nome fantasia, documento e município. Popover com até 8 resultados agrupados em "Clientes" e "Prospects", cada linha com nome, documento, município/UF e `RatingBadge`. `Enter` navega para `/clientes/[id]`. Sem resultado: "Nenhum cliente ou prospect corresponde a «X»." + ação "Analisar este documento em Nova análise" quando o texto tem forma de CPF/CNPJ. |
| 3 | *(espaçador flexível)* | |
| 4 | **`CostCounter`** | Exatamente como na 05 §6.24. Sempre visível, em todas as rotas com shell. Consulta `GET /api/llm/custo` ao montar e após cada stream concluído. É a defesa visível contra gasto silencioso. |
| 5 | **Controle de simulação de evento** | Botão `Simular evento` com ícone `Zap` e rótulo `DEMO` em `Badge` neutro. Abre popover (§1.5). |
| 6 | **Identidade do analista** | Avatar de iniciais 24px + nome. Popover ao clicar: nome completo, cargo, empresa e a frase *"Perfil de demonstração. O Lastro não tem autenticação nesta versão (ver `00-decisoes.md` D11.1)."* Sem "sair", sem troca de usuário. |

**Persona fixa de demonstração** (usada no cabeçalho e gravada em `RegistroAuditoria.analista`):

```
Marina Rezende · Analista de Crédito Sênior · Krill Tech
```

**Banner de dados simulados.** Fixo no topo absoluto do viewport, 28px, acima da sidebar e da topbar,
largura total, não fechável (05 §6.23). Nas rotas 5 e 10 aparece na variante `impressao`, dentro do
cabeçalho do documento, e **imprime**.

### 1.4 Gramática de navegação

| Ação | Comportamento |
|---|---|
| Clique em linha de cliente (qualquer tabela) | Navega para `/clientes/[id]`. A linha inteira é alvo; o nome é o *link* semântico para leitores de tela. |
| Clique em KPI ou gráfico da carteira | Navega para `/clientes?<filtro>` (§2.7). Nunca abre modal. |
| Clique em alerta | Navega para `/clientes/[id]#red-flags` e marca o alerta como lido. |
| Clique em registro de auditoria | Navega para `/clientes/[id]#decisao`. |
| Clique em evidência | Abre `Drawer` lateral **na mesma rota** (§4.11). Evidência nunca é rota. |
| Clique em fator | Abre `Drawer` de detalhe do fator (§4.6). |
| Voltar do navegador | Restaura filtros, ordenação e posição de rolagem em `/clientes` e `/alertas` (estado em query string). |
| `Esc` | Fecha, na ordem: popover → drawer → modal. Devolve o foco ao elemento que abriu. |

### 1.5 Controle de simulação de evento (D10)

Vive na **topbar**, disponível em todas as rotas com shell, porque o pitch pode precisar dele de
qualquer lugar. Popover de 360px, rotulado no topo: **`MODO DEMONSTRAÇÃO · injeta um evento e
recalcula o risco de verdade`**.

| Campo | Conteúdo |
|---|---|
| Cliente | Select com os clientes da carteira. **Pré-preenchido com o cliente da rota atual**, quando houver. |
| Evento | Rádio com 4 opções: `Nova execução de título` · `Pedido de Recuperação Judicial` · `Embargo do IBAMA sobre imóvel em garantia` · `Quebra de covenant (inadimplência técnica)`. Cada opção com uma linha de efeito esperado, em `fg-secondary`, ex.: *"Aciona `VETO_EMBARGO_GARANTIA` — força rating D."* |
| Ação | Botão primário `Simular evento`. |

Ao confirmar: chama `simularEvento(clienteId, tipo)`, recebe os fatos recalculados, e **navega para
`/clientes/[id]`** se ainda não estiver lá. Na chegada, em sequência e com as durações da 05 §9:

1. O `ScoreGauge` anima do score anterior para o novo (05 §7.6) e exibe o delta no mesmo elemento.
2. O card **"O que mudou"** (§4.5) entra no topo do fluxo principal, expandido, com a decomposição
   dos deltas.
3. A `Timeline` ganha a entrada nova, destacada por 4s com anel `accent-400`.
4. O badge de Alertas na sidebar incrementa.
5. Um `Toast` de 5s: *"Evento simulado. Score recalculado pelo motor: 712 → 604 (−108)."*

**Reversível:** o popover passa a exibir, abaixo, a linha `Evento simulado em <cliente> · <hora>` com
ação `Desfazer`, que remove o evento da sessão e recalcula de volta. "Restaurar dados da demonstração"
também remove todos.

---

## 2. `/carteira` — onde está o risco da carteira

Pergunta única: **"onde está o risco da minha carteira agora?"**. Tela de abertura da aplicação e do
pitch. Deve ser legível sem rolagem em 1440×900.

### 2.1 Wireframe

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║ ⚗ DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público        ║
╠══════════╦════════════════════════════════════════════════════════════════════════════════╣
║ LASTRO   ║ Carteira            [🔍 buscar cliente…]   US$0,42/10,00 ▪▪▫ ⚡Simular  M.Rezende║
║          ╠════════════════════════════════════════════════════════════════════════════════╣
║ ▣Carteira║ ┌── ATENÇÃO IMEDIATA ─────────────────────────────────────────────────────────┐║
║ ▤Clientes║ │ ⛔ VETO ATIVO         │ ↓ MAIOR QUEDA 90d      │ ⚠ ALERTA CRÍTICO + RECENTE  │║
║ ⊕Nova    ║ │ Agro Serra Azul Ltda │ Fazenda Vale Araguaia  │ Cerrado Grãos S/A           │║
║ △Alertas③║ │ Embargo IBAMA sobre  │ 712 → 604  (−108 pts)  │ RJ deferida em 04/09/2026   │║
║ ✓Auditor.║ │ imóvel em garantia   │ B → C · deterioração   │ Stay Period: 173 dias rest. │║
║ ─────────║ │ R$ 4,82 mi expostos  │ acelerada              │ R$ 9,10 mi em risco em RJ   │║
║ ⚙Arquit. ║ │ [Abrir cliente →]    │ [Ver o que mudou →]    │ [Abrir cliente →]           │║
║ ▦Canvas  ║ └─────────────────────────────────────────────────────────────────────────────┘║
║          ║                                                                                ║
║          ║ ┌─ EXPOSIÇÃO ─────┬─ EM RISCO ──────┬─ CRÍTICA ───────┬─ COBERTURA ──────────┐ ║
║          ║ │ R$ 184,3 mi     │ R$ 41,7 mi      │ R$ 22,6 mi      │ Extraconcursal  38%  │ ║
║          ║ │ a prazo · 18 cl.│ 22,6% do total  │ 4 clientes D/veto│ ▰▰▰▱▱▱▱▱▱▱          │ ║
║          ║ │ ▸ 90d: R$ 61,2mi│ ▸ em RJ: 63,9mi │ ▸ 12,3% do total│ Total           71%  │ ║
║          ║ │                 │                 │                 │ ▰▰▰▰▰▰▰▱▱▱          │ ║
║          ║ ├─ CLIENTES ──────┼─ ALERTAS 30d ───┼─ DETERIORAÇÃO ──┼──────────────────────┤ ║
║          ║ │ 18 na carteira  │ 11 no período   │ 5 clientes       │                     │ ║
║          ║ │ 12 ativos       │ 2 críticos      │ queda ≥ 25 pts   │                     │ ║
║          ║ │ 3 observação    │ 4 altos         │ em 90 dias       │                     │ ║
║          ║ │ 2 suspensos     │ 3 médios        │ ▸ 2 acelerada    │                     │ ║
║          ║ │ 1 RJ em curso   │ 2 informativos  │                  │                     │ ║
║          ║ └─────────────────┴─────────────────┴──────────────────┴─────────────────────┘ ║
║          ║                                                                                ║
║          ║ ┌── MATRIZ DE RISCO DA CARTEIRA ───────────┬── EXPOSIÇÃO POR RATING ─────────┐ ║
║          ║ │ R$ em risco em RJ                         │ A ▰▰▰▰▰▰▰▰▰ R$ 71,2mi   5 cli. │ ║
║          ║ │ 12│              ●D                       │ B ▰▰▰▰▰▰▰   R$ 58,4mi   6 cli. │ ║
║          ║ │  9│        ●C         ●D                  │ C ▰▰▰▰      R$ 32,1mi   4 cli. │ ║
║          ║ │  6│   ●B      ●C   ●C                     │ D ▰▰▰       R$ 22,6mi   3 cli. │ ║
║          ║ │  3│ ●A ●B ●B    ●B                        ├── CONCENTRAÇÃO ────────────────┤ ║
║          ║ │  0└─●A─●A─────────────────────── PD 12m   │ Soja      ▰▰▰▰▰▰▰▰ R$ 78,9mi  │ ║
║          ║ │    0%   10%   20%   30%   40%   50%       │ Milho     ▰▰▰▰▰    R$ 41,0mi  │ ║
║          ║ │ ○ tamanho = exposição total                │ Algodão   ▰▰▰▰     R$ 33,2mi  │ ║
║          ║ └───────────────────────────────────────────┴────────────────────────────────┘ ║
║          ║                                                                                ║
║          ║ ┌── ONDE ESTÁ O DINHEIRO EM RISCO ────────────────────────────────────────────┐║
║          ║ │ Cliente                  UF  Exp. total  Em risco  Em risco RJ  Rating  Tend.│║
║          ║ │ Cerrado Grãos S/A        GO  R$ 14,2 mi  R$ 9,1mi  R$ 9,1 mi    ⛔ D    ↓↓  │║
║          ║ │ Agro Serra Azul Ltda     BA  R$  4,8 mi  R$ 3,9mi  R$ 4,8 mi    ⛔ D    ↓   │║
║          ║ │ … 6 linhas …                                                                 │║
║          ║ │                                                [Ver todos os clientes →]     │║
║          ║ └──────────────────────────────────────────────────────────────────────────────┘║
╚══════════╩════════════════════════════════════════════════════════════════════════════════╝
```

### 2.2 Faixa de atenção imediata (topo, 12 colunas, altura fixa 132px)

Até **três** cartões lado a lado (4 colunas cada), selecionados por regra determinística, avaliada
nesta ordem, sem repetir cliente:

| Slot | Regra de seleção | Se não houver candidato |
|---|---|---|
| 1 | Cliente com **veto de força D** ativo, de maior `exposicaoEmRiscoEmRJ`. | Cliente de maior `exposicaoEmRiscoEmRJ` com rating D. |
| 2 | Cliente com **maior queda de score em 90 dias** (mais negativo), desde que ≤ −25. | Cliente com tendência `deterioracao_acelerada`. Se nenhum, o slot **é omitido** e os demais se redistribuem. |
| 3 | Alerta `CRITICA` **não lido** mais recente. | Alerta `ALTA` não lido mais recente. |

Se nenhum dos três tiver candidato, a faixa inteira é substituída por uma barra de 44px, em cor
neutra, com texto: *"Nenhuma ocorrência crítica na carteira nas últimas 24h. Última varredura:
12/09/2026 06:00."* — **nunca** um espaço vazio.

Conteúdo de cada cartão: ícone + eyebrow do motivo · razão social (link) · uma linha de causa nomeada
· uma linha com o número financeiro relevante · botão-texto de ação. Borda esquerda 3px na cor
semântica **e** ícone **e** eyebrow textual (R2).

### 2.3 Faixa de KPIs (grid 4×2, `KpiTile`)

| # | Título | Valor principal | Linhas de apoio | Fonte do dado |
|---|---|---|---|---|
| K1 | Exposição total a prazo | Σ `exposicao.exposicaoTotal` | `18 clientes` · `A vencer em 90 dias: R$ X` | motor |
| K2 | Exposição em risco | Σ `exposicao.exposicaoEmRisco` | `% da exposição total` · **`Em cenário de RJ: R$ Y`** (Σ `exposicaoEmRiscoEmRJ`) | motor |
| K3 | Exposição crítica | Σ exposição de clientes com `ratingFinal='D'` ou veto ativo | `N clientes` · `% do total` | motor |
| K4 | Cobertura por garantia | **dois** `ProgressBar` rotulados: `Extraconcursal N%` e `Total M%` | `Termo` EXTRACONCURSAL e CONCURSAL nos rótulos | motor |
| K5 | Clientes | contagem total | quebra por `EstadoCliente`: ativos · em observação · suspensos · RJ em curso · falência (omitida se 0) | `Cliente.estado` |
| K6 | Alertas em 30 dias | contagem | quebra pelas 4 severidades, com rótulo textual de cada | `listarAlertas` |
| K7 | Deterioração relevante | nº de clientes com Δscore 90d ≤ −25 | `▸ N em deterioração acelerada` | motor |
| K8 | *(célula ocupada por K4, que tem altura dupla)* | — | — | — |

**K4 nunca soma extraconcursal com total sem distinção** — são duas barras, dois rótulos, dois
números, com tooltips do glossário. É a materialização visual de D7 na tela de abertura.

### 2.4 Visualizações **aceitas**

Regra do briefing: **gráfico decorativo é proibido**. Cada gráfico abaixo existe porque responde a uma
pergunta que uma tabela responderia pior.

| ID | Pergunta que responde | Marca | Eixo X | Eixo Y | Codificações extras | Drill-down ao clicar |
|---|---|---|---|---|---|---|
| **V1 · Matriz de risco da carteira** (6 col) | *"Quais clientes combinam alta probabilidade de calote com muito dinheiro desprotegido?"* | Dispersão (scatter) | `pd.pd12m`, 0–60%, eixo linear, rótulos em % | `exposicao.exposicaoEmRiscoEmRJ`, em R$ mi | Raio ∝ √`exposicaoTotal` (6–18px); cor = `ratingFinal`; **letra do rating impressa dentro do ponto** (R2); ponto com veto ganha anel tracejado | Navega para `/clientes/[id]` |
| **V2 · Exposição por rating** (3 col) | *"Quanto do meu dinheiro está em cada faixa de risco?"* — não quantos clientes, quanto **dinheiro** | Barras horizontais, uma por rating, ordem A→D fixa | R$ | rating | Rótulo à direita com R$ **e** contagem de clientes | `/clientes?rating=D` |
| **V3 · Concentração por cultura** (3 col) | *"Se a soja quebrar, quanto da carteira é atingido?"* | Barras horizontais ordenadas por valor, top 5 + `Outras` | R$ exposição | cultura | Barra da cultura com maior ZARC médio recebe marcador `▲` + tooltip *"Risco climático médio alto nesta cultura"* | `/clientes?cultura=Soja` |
| **V4 · Concentração geográfica** (3 col) | *"Minha carteira está concentrada em qual UF?"* | Barras horizontais ordenadas, top 6 + `Outras` | R$ exposição | UF (sigla + nome) | Segmento interno em cor semântica mostra a parcela em risco daquela UF | `/clientes?uf=MT` |

V3 e V4 **compartilham um card** com duas abas (`Cultura` | `UF`), na mesma coluna de V2, para
economizar altura vertical e manter a tela sem rolagem.

### 2.5 Visualizações **recusadas** — e por quê

| Recusado | Motivo da recusa |
|---|---|
| **Mapa coroplético do Brasil** | Área geográfica não é proporcional a exposição; o Mato Grosso pareceria dominante por tamanho, não por dinheiro. Custo de implementação (topojson, projeção) alto e precisão de leitura menor que a de uma barra ordenada. **V4 responde melhor com 1/10 do esforço.** |
| **Pizza / rosca de distribuição de rating** | Comparação de ângulos é menos precisa que a de comprimentos, e a rosca só carrega quatro valores — cabe numa barra com os números escritos. Proibida também pela 05 §8.2. |
| **Medidor (gauge) de "saúde da carteira"** | Agrega sete dimensões e 18 clientes num único número que ninguém consegue defender numa arguição. O `ScoreGauge` existe **por cliente**, onde há decomposição auditável por trás. Carteira não tem score. |
| **Radar das sete dimensões no agregado** | A área do polígono muda com a ordem dos eixos, o que a torna manipulável e não comparável. Decomposição por dimensão é apresentada como barras, e só na página do cliente. |
| **Treemap de exposição** | Retângulos aninhados são difíceis de comparar e péssimos com 18 itens de ordens de grandeza próximas. A tabela §2.6 responde melhor. |
| **Sparkline decorativo dentro de KPI** | Sem eixo e sem escala, uma linha de 40px comunica "tem tendência" sem dizer qual. Se a tendência importa, ela é um número com sinal (K7) ou um `TrendIndicator` rotulado. |
| **Série temporal do score médio da carteira** | Média de score entre clientes de exposições muito diferentes é um número sem significado econômico. O que importa é *quanto dinheiro* migrou de faixa — e isso o card "O que mudou" do cliente responde com precisão. |
| **Contador animado (count-up) nos KPIs** | Movimento sem informação; proibido pela 05 §9.3. Números aparecem no valor final. |

### 2.6 Tabela "Onde está o dinheiro em risco" (12 col, rodapé da carteira)

`DataTable` densa, **8 linhas fixas**, ordenada por `exposicaoEmRiscoEmRJ` decrescente, **sem filtros,
sem paginação, sem ordenação interativa**. Colunas: Cliente · UF · Exposição total · Em risco · **Em
risco em RJ** · Rating · Tendência. Rodapé com link `Ver todos os clientes →` para `/clientes?ordem=risco_rj`.
A coluna "Em risco em RJ" é a destacada tipograficamente — é o número que ninguém mais mostra (02 §10).

### 2.7 Contrato de drill-down

| Origem | Destino |
|---|---|
| K1 | `/clientes?ordem=exposicao` |
| K2 | `/clientes?filtro=alta-exposicao&ordem=risco_rj` |
| K3 | `/clientes?filtro=veto&ordem=exposicao` |
| K4 | `/clientes?ordem=cobertura` |
| K5 | `/clientes` |
| K6 | `/alertas?periodo=30d` |
| K7 | `/clientes?filtro=deterioracao&ordem=variacao` |
| V1 (ponto) | `/clientes/[id]` |
| V2 (barra) | `/clientes?rating=<A\|B\|C\|D>` |
| V3 (barra) | `/clientes?cultura=<cultura>` |
| V4 (barra) | `/clientes?uf=<UF>` |

Todo KPI clicável tem `role="link"`, `cursor: pointer`, foco visível e a affordance `→` no canto
inferior direito ao hover. KPI não clicável não recebe hover.

---

## 3. `/clientes` — lista de clientes

### 3.1 Colunas

| # | Coluna | Alinh. | Largura | Conteúdo e formatação |
|---|---|---|---|---|
| 1 | **Cliente** | esq. | 240px, **fixa ao rolar** | Razão social em `fg-primary` (1 linha, truncada com tooltip); abaixo, nome fantasia em `fg-tertiary` 11px, quando houver. Ícone `Sprout` para PF produtor rural. |
| 2 | CPF/CNPJ | esq. | 150px | `type-mono` 12px, formatado (`formatarDocumento`). |
| 3 | Município/UF | esq. | 150px | `Município · UF`, UF em `fg-secondary`. |
| 4 | Tipo | centro | 56px | `Badge` neutro `PF` ou `PJ`. |
| 5 | Cultura | esq. | 140px | Primeira cultura + `+N` com tooltip listando as demais. |
| 6 | Exposição | dir. | 120px | `formatarMoedaCompacta` (R$ 14,2 mi). Tooltip com valor integral. |
| 7 | Próx. vencimento | dir. | 120px | Data `dd/MM/yyyy` + linha inferior `em N dias` / **`vencido há N dias`** em cor semântica + ícone. |
| 8 | **Score** | dir. | 88px | Número 15px `type-mono` `fg-primary`, **com veto** exibe `604` riscado? **Não** — ver §3.4. |
| 9 | Rating | centro | 48px | `RatingBadge` (letra + cor + rótulo em tooltip). |
| 10 | PD 12m | dir. | 80px | `formatarPercentual(pd12m, 1)`. Cabeçalho com `Termo sigla="PD"`. |
| 11 | Risco de RJ | dir. | 96px | Percentual + `Badge` textual de faixa (`baixo`/`moderado`/`alto`/`ocorrido`). Cabeçalho com `Termo sigla="RJ"`. |
| 12 | Tendência | centro | 72px | `TrendIndicator`: seta + `Δ −108` em `type-mono` 11px. |
| 13 | Alertas | centro | 64px | Contagem; a pastilha assume a cor da **maior severidade** presente e imprime a inicial dela (`C`/`A`/`M`/`I`). Zero = `—` em `fg-tertiary`. |

Largura total ≈ 1424px; abaixo de 1280px, as colunas 3 e 5 colapsam para um `Drawer` de detalhe
acessível pelo botão `⋯` ao fim da linha. Coluna 1 permanece fixa com sombra à direita.

### 3.2 Score + rating + tendência numa célula sem poluir

**Decisão: três colunas adjacentes, não uma célula composta.** Score (num.), Rating (badge) e
Tendência (seta + delta) ocupam as colunas 8, 9 e 12, com Rating imediatamente à direita do Score,
formando um grupo visual sem borda. Racional: comprimir os três num único campo produz uma célula de
três alturas que quebra a densidade de 36px (05 §5.3) e impede ordenar por cada um separadamente.

Regras de renderização:

- O número do score é sempre `scoreCalculado`.
- Quando há veto (`ratingFinal ≠ ratingCalculado`), o `RatingBadge` mostra **o rating final** e ganha
  um ícone `ShieldAlert` de 10px sobreposto ao canto, com tooltip: *"Rating rebaixado por veto:
  <rótulo do veto>. Score calculado: 604 (rating C)."* O score **não** é riscado — riscar sugere que
  o número é inválido, e ele não é; ele é o número auditável que o veto sobrepõe.
- `TrendIndicator` com Δ exibe o sinal sempre (`+31`, `−108`), nunca o valor absoluto sozinho.
- Quando não há snapshot anterior (prospect ou cliente novo), a célula de tendência mostra `—` com
  tooltip *"Sem histórico suficiente para calcular variação."*

### 3.3 Filtros

`FilterChips` numa única linha acima da tabela. **Seletor único e exclusivo** (rádio, não
multi-seleção) — com 18 clientes, combinar filtros produz conjuntos vazios com mais frequência do que
resultados úteis, e a simplicidade vale mais no pitch. Cada chip traz a contagem entre parênteses;
chip com contagem 0 fica desabilitado, com tooltip *"Nenhum cliente neste critério."*

| Chip | Predicado |
|---|---|
| `Todos (18)` | padrão |
| `Rating A (5)` | `ratingFinal === 'A'` |
| `Rating B (6)` | `ratingFinal === 'B'` |
| `Rating C (4)` | `ratingFinal === 'C'` |
| `Rating D (3)` | `ratingFinal === 'D'` |
| `Com alerta (7)` | ≥1 alerta não lido |
| `Com gatilho de veto (2)` | `vetosAtivos.length > 0` |
| `Deterioração recente (5)` | Δscore 90d ≤ −25 |
| `Alta exposição (6)` | `exposicaoTotal` no quartil superior da carteira |

Chips de rating exibem a cor semântica **apenas na borda inferior de 2px**, nunca como fundo, para não
competir com os `RatingBadge` das linhas.

### 3.4 Busca

`SearchInput` de 320px à esquerda dos chips. Casa, sem diferenciar acento ou caixa, contra: razão
social, nome fantasia, documento (com e sem máscara) e município. Debounce de 200ms. Combina com o
filtro ativo por **E** lógico. Botão `×` limpa. Contador à direita: `7 de 18 clientes`.

### 3.5 Ordenação

Clique no cabeçalho alterna asc/desc; `Shift` não acumula (ordenação única). Colunas ordenáveis e
direção padrão ao primeiro clique:

| Coluna | Padrão | Chave da URL |
|---|---|---|
| Score | crescente (pior primeiro) | `ordem=score` |
| Exposição | decrescente | `ordem=exposicao` |
| PD 12m | decrescente | `ordem=pd` |
| Variação do score | crescente (queda maior primeiro) | `ordem=variacao` |
| Alertas | decrescente | `ordem=alertas` |
| *(extras usados por drill-down)* | — | `ordem=risco_rj`, `ordem=cobertura` |

**Ordenação inicial da rota sem parâmetros: `ordem=score` crescente** — o pior cliente no topo. A
tela responde "onde está o risco" antes de qualquer interação. Cabeçalho ativo com seta e
`aria-sort`.

### 3.6 Estado na URL

`/clientes?filtro=deterioracao&busca=serra&ordem=variacao&dir=asc`. Todos os parâmetros são opcionais
e o estado é integralmente reconstruível a partir deles. Mudança de filtro usa `router.replace`
(não empilha histórico); navegação para um cliente usa `push`.

### 3.7 Estados vazios

| Situação | Título | Texto | Ação |
|---|---|---|---|
| Filtro sem resultado | `Nenhum cliente neste filtro` | *"O filtro «Com gatilho de veto» não retornou clientes."* | `Limpar filtro` |
| Busca sem resultado | `Nenhum resultado para «serrinha»` | *"Verifique a grafia ou busque por documento ou município."* | `Limpar busca` · `Analisar novo documento` |
| Filtro + busca sem resultado | `Nenhum resultado` | *"«serrinha» não retorna clientes dentro do filtro «Rating A»."* | `Manter busca e ver todos os ratings` · `Limpar tudo` |
| Carteira vazia (só após "Restaurar" falhar) | `Carteira sem clientes` | *"Nenhum cliente carregado. Verifique se o serviço de dados está ativo."* | `Recarregar` |

---

## 4. `/clientes/[id]` — página do cliente

A maior superfície do produto. Responde às cinco perguntas na ordem em que o analista as faz.

### 4.1 Layout e dobra

Grid de 12 colunas. **Cabeçalho ocupa 12.** Em seguida, duas colunas:
**principal = 8** (rolagem normal) e **lateral direita = 4** (`position: sticky; top: 76px`, contendo
score, PD/RJ e recomendação — as respostas de P1 e P5 ficam visíveis durante toda a rolagem).

Faixas de largura total (12 colunas), quando presentes, entram **entre** o cabeçalho e as duas
colunas, nesta ordem: (a) banda de veto ativo; (b) painel de Stay Period; (c) card "O que mudou"
após simulação de evento.

**Acima da dobra em 1440×900** (viewport útil ≈ 824px após banner 28 + topbar 48): cabeçalho completo,
banda de veto e/ou Stay Period se existirem, o `ScoreGauge` inteiro com rating e variação, o card de
PD e risco de RJ completo, o título e a primeira ação da recomendação, e o título do bloco "Por que
este score". Nada mais precisa estar acima da dobra.

**Vai para `Drawer`, nunca para a página:** detalhe de um fator, detalhe de uma evidência, comparação
entre dois snapshots, lista completa de operações e de parcelas, lista completa de processos, e o
histórico completo de decisões do analista (a página mostra as 3 últimas).

### 4.2 Wireframe

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║ ⚗ DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público        ║
╠══════════╦════════════════════════════════════════════════════════════════════════════════╣
║ sidebar  ║ Clientes › Fazenda Vale do Araguaia    [🔍]  US$0,42/10 ⚡Simular  M.Rezende    ║
║          ╠════════════════════════════════════════════════════════════════════════════════╣
║ ▣Carteira║ FAZENDA VALE DO ARAGUAIA LTDA                       [Gerar parecer] [⚡Simular] ║
║ ▤Clientes║ 12.345.678/0001-90 · Querência/MT · Soja, Milho safrinha · PJ                   ║
║ ⊕Nova    ║ Cliente desde 03/2019 · EM OBSERVAÇÃO · Última varredura 12/09/2026 06:00      ║
║ △Alertas③╠════════════════════════════════════════════════════════════════════════════════╣
║ ✓Auditor.║ ┌── PRINCIPAL (8 col) ───────────────────────┐┌── LATERAL (4 col · sticky) ───┐║
║          ║ │                                            ││        ┌───────────┐          │║
║          ║ │ ⚠ POR QUE ESTE SCORE            [streaming]││        │    604    │  ▼ −108  │║
║          ║ │ ┌ Fatores de risco ─────────────────────┐  ││        │  ▰▰▰▱▱▱▱  │  em 90d  │║
║          ║ │ │ 2 execuções de título      ▇▇▇▇▇ −42  │  ││        └───────────┘          │║
║          ║ │ │ Dívida ativa PGFN          ▇▇▇▇  −31  │  ││   RATING C · Risco elevado    │║
║          ║ │ │ Deterioração climática     ▇▇▇   −18  │  ││   ▼ deterioração acelerada    │║
║          ║ │ │ Atraso médio 3d → 11d      ▇▇▇   −17  │  ││                               │║
║          ║ │ └───────────────────────────────────────┘  ││ ── PROBABILIDADES ──────────  │║
║          ║ │ ┌ Fatores de proteção ──────────────────┐  ││ PD 6m   10,2%  ▰▰▱▱▱▱▱▱▱▱    │║
║          ║ │ │ Alienação fiduciária  +38  ▇▇▇        │  ││ PD 12m  17,1%  ▰▰▰▱▱▱▱▱▱▱    │║
║          ║ │ │ Relacionamento 7 anos +18  ▇▇         │  ││ PD 24m  33,9%  ▰▰▰▰▰▱▱▱▱▱    │║
║          ║ │ └───────────────────────────────────────┘  ││ ────────────────────────────  │║
║          ║ │ » A queda concentra-se na dimensão juríd…  ││ RISCO DE RJ 12m               │║
║          ║ │                                            ││ 22,5%  ALTO   índice 55/100   │║
║          ║ │ ▤ DECOMPOSIÇÃO POR DIMENSÃO                ││ ▲ escala própria — não é PD    │║
║          ║ │ Comportamental 22% ▰▰▰▰▰▰▱▱▱▱ 612  ▼      ││                               │║
║          ║ │ Jurídico       20% ▰▰▰▱▱▱▱▱▱▱ 318  ▼▼     ││ ── RECOMENDAÇÃO ───────────   │║
║          ║ │ Fiscal         14% ▰▰▰▰▰▱▱▱▱▱ 502  ▬      ││ APROVAR COM RESTRIÇÕES        │║
║          ║ │ Agroclimático  15% ▰▰▰▰▱▱▱▱▱▱ 441  ▼      ││ Reavaliar em 30 dias          │║
║          ║ │ Cadastral      10% ▰▰▰▰▰▰▰▰▱▱ 790  ▬      ││ 1 Reduzir limite de R$ 5,0 mi │║
║          ║ │ Ambiental       9% ▰▰▰▰▰▰▰▱▱▱ 710  ▬      ││   para R$ 3,5 mi (−30%)       │║
║          ║ │ Garantias      10% ▰▰▰▰▰▱▱▱▱▱ 540  ▼      ││ 2 Exigir garantia adicional   │║
║          ║ │ Σ contribuições = 604  ✓ fecha com o score ││   de R$ 1,48 mi               │║
║          ║ │                                            ││ 3 Converter penhor de safra   │║
║          ║ │ ⚑ RED FLAGS (4)      [nova 2][analisada 1] ││   em alienação fiduciária     │║
║          ║ │ ⛔ CRÍTICA  Covenant rompido …      −38 pts ││ » Justificativa: o rebaixa…   │║
║          ║ │ ⚠ ALTA     2 execuções em 90 dias  −42 pts ││ ┌───────────────────────────┐ │║
║          ║ │ ⚠ ALTA     Dívida ativa crescente  −31 pts ││ │ Decisão final sujeita à   │ │║
║          ║ │ ◐ MÉDIA    ZARC elevado p/ alto    −18 pts ││ │ avaliação do analista     │ │║
║          ║ │                                            ││ │ responsável.              │ │║
║          ║ │ ⛁ EXPOSIÇÃO E GARANTIAS                    ││ └───────────────────────────┘ │║
║          ║ │ Exposição total       R$ 14.200.000        │└───────────────────────────────┘║
║          ║ │ ▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱  protegida 71% | risco  │                                ║
║          ║ │ Extraconcursal  R$ 5.396.000   38%   ▰▰▰▱▱ │                                ║
║          ║ │ Concursal       R$ 4.686.000   33%   ▰▰▰▱▱ │                                ║
║          ║ │ ┌──────────────────────────────────────┐   │                                ║
║          ║ │ │ EM RISCO SE PEDIR RJ AMANHÃ          │   │                                ║
║          ║ │ │ R$ 8.804.000  ·  62% da exposição    │   │                                ║
║          ║ │ │ o penhor entra no plano; a alienação │   │                                ║
║          ║ │ │ fiduciária, não.                     │   │                                ║
║          ║ │ └──────────────────────────────────────┘   │                                ║
║          ║ │                                            │                                ║
║          ║ │ ⏱ LINHA DO TEMPO — 12 meses                │                                ║
║          ║ │ 712 ─────●───╮                             │                                ║
║          ║ │ 650        ╰──●──╮                         │                                ║
║          ║ │ 604              ╰───●                     │                                ║
║          ║ │  jun    jul    ago    set                  │                                ║
║          ║ │ ● 04/07 2 execuções de título     −42  →   │                                ║
║          ║ │ ● 19/08 Inscrição em dívida ativa −31  →   │                                ║
║          ║ │ ● 02/09 Covenant rompido          −38  →   │                                ║
║          ║ │                                            │                                ║
║          ║ │ ⛓ FONTES E EVIDÊNCIAS (14 fontes · 23 doc) │                                ║
║          ║ │ [DataJud][PGFN][TST][SICAR][IBAMA][+9]     │                                ║
║          ║ │ ▸ Execução nº 1009…/2026 · DataJud · 11/09 │                                ║
║          ║ │   consulta simulada                    →   │                                ║
║          ║ │                                            │                                ║
║          ║ │ ✦ COPILOTO DE ANÁLISE                      │                                ║
║          ║ │ [Pergunte sobre este cliente…        ] [↵] │                                ║
║          ║ │ Sugestões: Por que o score caiu? · Qual    │                                ║
║          ║ │ garantia protege em RJ? · O que mudou?     │                                ║
║          ║ │                                            │                                ║
║          ║ │ ✎ DECISÃO DO ANALISTA                      │                                ║
║          ║ │ ( )Aprovar (•)Aprovar c/ restrições ( )Rev.│                                ║
║          ║ │ ( )Suspender ( )Recusar                    │                                ║
║          ║ │ [Justificativa (obrigatória)…           ]  │                                ║
║          ║ │ ⚠ Sua decisão diverge da recomendação? não │                                ║
║          ║ │                        [Registrar decisão] │                                ║
║          ║ └────────────────────────────────────────────┘                                ║
╚══════════╩════════════════════════════════════════════════════════════════════════════════╝
```

### 4.3 Cabeçalho (12 col)

| Linha | Conteúdo |
|---|---|
| 1 | **Razão social** em `type-title` · à direita: `Gerar parecer` (primário), `Simular evento` (secundário, com `Badge` DEMO), `⋯` (menu: `Copiar documento`, `Ver na lista`) |
| 2 | Documento (`type-mono`) · Município/UF · Culturas · `Badge` PF/PJ · CNAE em tooltip |
| 3 | `Cliente desde MM/AAAA` · `Badge` de `EstadoCliente` com rótulo textual · `Última varredura: dd/MM/aaaa HH:mm` |

Para `origem = 'PROSPECT'`, a linha 3 é substituída por `Badge` **`PROSPECT — sem relacionamento
comercial`** + `Consulta realizada em dd/MM/aaaa HH:mm`, e o botão `Simular evento` não aparece.

### 4.4 Score, veto, PD e risco de RJ (lateral, 4 col)

**Card 1 — Score.** `ScoreGauge` (05 §7) com o número grande, `RatingBadge` com rótulo textual
("Risco elevado"), `TrendIndicator` com a variação em 90 dias (`▼ −108 em 90 dias`), e a data do
snapshot de comparação em `fg-tertiary`.

**Modo veto** — quando `vetosAtivos.length > 0`, o card apresenta **lado a lado, com pesos
tipográficos diferentes**, e o gauge entra no modo veto da 05 §7.7:

```
┌──────────────────────────────────────────────┐
│ SCORE CALCULADO        CLASSIFICAÇÃO FINAL   │
│      604                      D              │
│   rating C                Risco crítico      │
│   (pelo motor)            (por veto)         │
├──────────────────────────────────────────────┤
│ ⛔ VETO: Embargo do IBAMA sobre imóvel        │
│    oferecido em garantia                     │
│    Garantia juridicamente comprometida: bem  │
│    embargado tem excussão inviabilizada.     │
│    Fonte: IBAMA · 08/09/2026  [Ver evidência]│
└──────────────────────────────────────────────┘
```

O **motivo é nomeado**, com `VetoAtivo.rotulo` e `VetoAtivo.justificativa` literais do motor, efeito
declarado (`força D` / `teto C`) e link para a evidência. Havendo mais de um veto, listam-se todos;
o efeito exibido é o mais severo. Além do card, uma **banda de largura total** entra logo abaixo do
cabeçalho com o mesmo rótulo, para que o veto seja impossível de não ver.

**Card 2 — Probabilidades.** Três linhas: `PD 6m`, `PD 12m`, `PD 24m`, cada uma com percentual e
`ProgressBar` **na mesma escala 0–60%**, para que a progressão entre horizontes seja visível. Rodapé
com `ProbabilidadeDeDefault.metodo` em `Tooltip` e `Termo sigla="PD"` no título.

**Card 3 — Risco de RJ.** Separado visualmente por divisória espessa e por um rótulo explícito:
**`Escala própria — não comparável à PD`**. Conteúdo: probabilidade em 12m, faixa textual
(`baixo` < 5% · `moderado` 5–15% · `alto` 15–30% · `crítico` > 30% · `ocorrido` quando
`eventoJaOcorrido`), `rjIndex`/100, e a lista de `sinais` com pontos. Quando `elegivel = false`,
substitui a probabilidade por:

```
NÃO ELEGÍVEL A RJ
Produtor rural pessoa física sem comprovação de 2 anos
de atividade (Lei 14.112/2020). Risco de RJ reduzido
por inelegibilidade legal — ver motivo.
```

**Proibição dura:** PD e risco de RJ nunca compartilham eixo, barra, escala de cor, card ou legenda.
São perguntas diferentes — "vai atrasar?" e "vai pedir recuperação judicial?" — e a invariante I5 do
dataset existe exatamente para provar que andam separados.

**Card 4 — Recomendação.** `Recomendacao.rotulo` em destaque, com ícone e cor semântica derivada do
código; `Reavaliar em N dias`; lista **numerada** de `acoes` ordenada por `prioridade` (1 = imediata),
cada uma com o texto já parametrizado pelo motor; abaixo, o parágrafo de justificativa em
`StreamingText` (tarefa `recomendacao`); e, ao pé, a caixa **não dispensável** com
*"Decisão final sujeita à avaliação do analista responsável."* (R3, I9).

### 4.5 "Por que este score" e "O que mudou"

**Bloco "Por que este score"** (principal, primeiro). Duas listas em cards irmãos:

| Lista | Conteúdo | Ordenação |
|---|---|---|
| **Fatores de risco** | `FactorBar` divergente por fator com `direcao='risco'`: rótulo, detalhe, `impactoGlobalAjustado` com sinal, barra proporcional | `|impacto|` decrescente, top 6 + `Ver todos os N fatores` |
| **Fatores de proteção** | idem para `direcao='protecao'` | idem, top 4 |

Abaixo das duas listas, o parágrafo do LLM em `StreamingText` (tarefa `score`), precedido do rótulo
`Análise` e do marcador de origem (05 §6.20). **As barras e os números renderizam antes do texto**
(R1). Clique em um fator abre `Drawer` com: fórmula aplicada em texto ("atraso médio de 11 dias × 12,
limitado a 250"), pontos brutos, peso da dimensão, impacto global, evidências que o sustentam e
histórico do fator nos últimos snapshots.

**Bloco "O que mudou"** (principal, aparece **acima** de "Por que este score") — presente quando há
snapshot anterior e a variação é diferente de zero; sempre presente após simulação de evento. Formato
literal exigido pela 02 §11:

```
712 → 604   (−108 pontos)   ·   06/07/2026 → 12/09/2026
  2 novas execuções de título ................ −42
  nova inscrição em dívida ativa ............. −31
  deterioração climática regional ............ −18
  atraso médio de pagamento (3d → 11d) ....... −17
  ─────────────────────────────────────────────────
  Σ dos deltas ............................... −108  ✓ fecha
```

Linha de fechamento **obrigatória e visível** (I6). Seletor de período no cabeçalho do card:
`30 dias` · `90 dias` (padrão) · `12 meses` · `Desde o início`.

### 4.6 Decomposição por dimensão

Sete linhas na ordem fixa de peso decrescente da 02 §2 (comportamental 22% → jurídico 20% → agro 15% →
fiscal 14% → cadastral 10% → garantias 10% → ambiental 9%). Cada linha: rótulo · peso · `ProgressBar`
0–1000 · score da dimensão · `TrendIndicator` · ícone `AlertOctagon` quando `saturou = true`, com
tooltip *"Dimensão saturada: o excedente foi redistribuído. O impacto real é maior que o exibido nesta barra."*

Rodapé **obrigatório** do card, sempre visível (materializa I2):

```
Σ contribuições = 604,0   ·   score exibido = 604   ·   diferença 0,0 ✓
```

Se `auditoria.diferenca > 0,5` — o que não deve acontecer —, a linha vira estado de erro com
*"Inconsistência de fechamento detectada. Não utilize este parecer."*, e o botão `Gerar parecer` é
desabilitado.

Cada linha é expansível (`chevron`) e revela os fatores daquela dimensão e as `fontes` consultadas.

### 4.7 Red flags

Lista ordenada por severidade (CRÍTICA → BAIXA) e, dentro da severidade, por data decrescente. Cada
item: ícone + rótulo textual de severidade + título + descrição + fonte + data + `impactoEmPontos` com
sinal + `Badge` de `status`. Filtro de status em `FilterChips` no cabeçalho do card:
`Todas` · `Novas` · `Analisadas` · `Resolvidas`.

Ação por item: menu `⋯` com `Marcar como analisada` / `Marcar como resolvida` / `Ver evidência`. A
mudança de status persiste em `localStorage` (D11.3) e **não altera o score** — a interface exibe, ao
lado do controle, a nota *"Marcar como analisada não altera o cálculo; é registro de triagem."*

Card vazio: `EmptyState` com *"Nenhuma red flag ativa. A varredura de 12/09/2026 não encontrou
ocorrências."*

### 4.8 Exposição e garantias

| Sub-bloco | Conteúdo |
|---|---|
| Linha de números | Exposição total · Limite aprovado · Utilização do limite (% com `ProgressBar`, cor semântica acima de 85%) · A vencer em 90 dias · Em atraso |
| `StackedBar` de proteção | Barra única de largura total: `exposicaoProtegida` vs `exposicaoEmRisco`, com rótulos e valores dentro ou acima dos segmentos |
| Coberturas | Duas linhas separadas — **Extraconcursal** (valor, % e barra) e **Concursal** (valor, % e barra) —, cada uma com `Termo` do glossário. **Proibido apresentar uma soma única "cobertura" sem a separação.** |
| **Caixa "Em risco se pedir RJ amanhã"** | Card destacado com `exposicaoEmRiscoEmRJ` em número grande, percentual da exposição, e a frase fixa: *"O penhor entra no plano de recuperação com deságio; a alienação fiduciária, não."* É o diferencial do produto e recebe o maior peso tipográfico do bloco depois da exposição total. |
| Tabela de garantias | `DataTable` compacta: Tipo · **Natureza** (`Badge` EXTRACONCURSAL/CONCURSAL) · Descrição · Valor declarado · `Termo sigla="HAIRCUT"` aplicado · Valor atualizado · Registrada (✓/✗ com rótulo) · Embargada (só aparece a coluna se houver ao menos uma `bemEmbargado`) |
| Operações | Resumo por `TipoOperacao` (venda a prazo, barter, CPR) com valores; link `Ver todas as N operações e parcelas →` que abre `Drawer` com a tabela completa de `Operacao` e `Parcela`. Operação barter exibe cultura, sacas prometidas, preço de referência e, quando `cprVinculadaId` ausente, o aviso *"Barter sem CPR registrada cobrindo a operação."* |

### 4.9 Painel de Stay Period

Renderiza **apenas** quando `stayPeriod.ativo === true`. Faixa de largura total (12 col),
imediatamente abaixo do cabeçalho (e da banda de veto, quando houver), porque é a informação que
muda o que o analista pode legalmente fazer hoje.

```
┌── STAY PERIOD ATIVO ─────────────────────────────────────────────────────────────┐
│ RJ deferida em 04/09/2026 · decorridos 8 de 180 dias                             │
│ ▰▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱  173 dias restantes   (prorrogável uma vez, art. 6º L.11.101)│
│                                                                                  │
│ A KRILL TECH NÃO PODE          │ A KRILL TECH AINDA PODE                        │
│ ✗ Executar garantias concursais│ ✓ Excutir alienação fiduciária (extraconcursal) │
│ ✗ Protestar títulos            │ ✓ Habilitar crédito no quadro-geral            │
│ ✗ Cobrar judicialmente         │ ✓ Suspender novo fornecimento a prazo          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

As duas listas vêm literalmente de `stayPeriod.bloqueios` e `stayPeriod.permitido`. Nunca inventar
item. O termo `STAY_PERIOD` no título carrega o `Tooltip` do glossário. A contagem regressiva é
número calculado pelo motor, **não** um timer de JavaScript.

### 4.10 Ordem definitiva dos blocos

| Ordem | Bloco | Coluna | Condição de exibição |
|---|---|---|---|
| 1 | Cabeçalho | 12 | sempre |
| 2 | Banda de veto | 12 | `vetosAtivos.length > 0` |
| 3 | Painel de Stay Period | 12 | `stayPeriod.ativo` |
| 4 | O que mudou | 8 | há snapshot anterior com Δ ≠ 0 |
| 5 | Por que este score | 8 | sempre |
| 6 | Decomposição por dimensão | 8 | sempre |
| 7 | Red flags | 8 | sempre (com estado vazio) |
| 8 | Exposição e garantias | 8 | `origem = 'CARTEIRA'` |
| 9 | Linha do tempo | 8 | `origem = 'CARTEIRA'` e ≥2 snapshots |
| 10 | Fontes e evidências | 8 | sempre |
| 11 | Copiloto de análise | 8 | sempre |
| 12 | Decisão do analista | 8 | sempre |
| L1 | Score / veto | 4 sticky | sempre |
| L2 | PD | 4 sticky | sempre |
| L3 | Risco de RJ | 4 sticky | sempre |
| L4 | Recomendação | 4 sticky | sempre |

Âncoras de URL para navegação externa: `#mudou`, `#por-que`, `#dimensoes`, `#red-flags`,
`#exposicao`, `#stay-period`, `#timeline`, `#evidencias`, `#copiloto`, `#decisao`. O alvo recebe
`scroll-margin-top: 88px` e um anel `accent-400` por 2s.

### 4.11 Fontes e evidências

Cabeçalho do card: `N fontes consultadas · M documentos`. Abaixo, `FilterChips` com as fontes
efetivamente presentes (rótulo humano: `DataJud — CNJ`, `PGFN`, `TST/CNDT`, `SICAR`, `IBAMA`,
`MAPA/ZARC`, `CONAB`, `INMET`, `Receita Federal`, `Redesim`, `Cartório de protesto`,
`Caixa — CRF/FGTS`, `DJE`, `Interno Krill Tech`). Lista de `EvidenceCard`, ordenada por
`dataConsulta` decrescente, com título, tipo, resumo de uma linha, fonte, data e o selo
**`consulta simulada`** (obrigatório em toda evidência, D11.6).

Clique abre `Drawer` de 480px com: fonte e `urlFicticia` desabilitada (com tooltip *"Endereço
ilustrativo — nenhuma consulta real foi realizada"*), tipo, data do documento, data de consulta,
resumo integral, e a seção **"Sustenta os fatores"**, listando `fatoresRelacionados` como links que
rolam até o fator correspondente em "Por que este score". Esse laço evidência↔fator é o que responde
P4 e precisa funcionar nos dois sentidos.

### 4.12 Copiloto de análise

Card ancorado no fluxo principal (não é widget flutuante, não é chat global). Componentes:

1. Campo de pergunta com placeholder `Pergunte sobre este cliente…`, envio por `Enter`,
   `Shift+Enter` quebra linha, limite de 300 caracteres com contador a partir de 250.
2. Três sugestões clicáveis, fixas: `Por que o score caiu?` · `Qual garantia protege em cenário de RJ?`
   · `O que mudou nos últimos 90 dias?`
3. Histórico da conversa (máx. 6 mensagens visíveis, 04 §…), pergunta à direita, resposta à esquerda.
4. Resposta em `StreamingText`, com as fontes citadas renderizadas como chips clicáveis ao final,
   que abrem o `Drawer` de evidência.
5. Rodapé fixo do card: *"O copiloto responde apenas com base nos dados desta avaliação. Não consulta
   internet nem bases externas."*
6. Botão `Expandir` que move a conversa para um `Drawer` de 520px, mantendo a página utilizável ao lado.

Recusa fora de escopo: a resposta do modelo já vem no formato definido na 04; a interface apenas a
renderiza, com ícone `Info` e sem tratá-la como erro.

### 4.13 Prospect — o que some

Com `origem = 'PROSPECT'`, os blocos 8 (exposição e garantias), 9 (linha do tempo) e 4 (o que mudou)
**não renderizam**, e no lugar do bloco 8 entra um card único:

```
SEM EXPOSIÇÃO ATUAL
Este documento não possui operações com a Krill Tech. A avaliação
considera apenas fontes externas e a simulação de limite abaixo.

Limite pretendido:  [ R$ 3.000.000    ]  [Recalcular cobertura]
Garantias oferecidas: nenhuma informada
```

O campo de limite pretendido é enviado ao motor como exposição hipotética e a recomendação é
recalculada. A decisão do analista, nesse fluxo, é de **concessão**, e o rótulo do bloco 12 muda para
`Decisão de concessão`.

---

## 5. Linha do tempo

Vive dentro de `/clientes/[id]` (§4.10 bloco 9). Objetivo: **tornar a deterioração impossível de não
ver** — não listar eventos.

### 5.1 Construção

Componente composto por duas camadas verticalmente empilhadas e **compartilhando o mesmo eixo X**
(datas, 12 meses até a data de referência):

| Camada | Altura | Conteúdo |
|---|---|---|
| **Superior — série do score** | 160px | Linha em degraus (`stepAfter`) ligando o score recalculado de cada `SnapshotHistorico`. Eixo Y 0–1000 com **faixas de rating ao fundo**, em tinta muito baixa, rotuladas à direita (A/B/C/D) — a travessia de faixa fica visível sem tooltip. Ponto em cada snapshot. |
| **Inferior — eventos** | lista | Marcadores no eixo, um por `EventoDeRisco`, com forma por severidade (não só cor) e linha guia pontilhada subindo até a série. |

**Por que degraus, não curva suave:** o score não varia continuamente entre varreduras; ele muda
quando um fato novo entra. Curva suave inventa valores intermediários que o motor nunca calculou.

### 5.2 Lista de eventos (abaixo do gráfico)

`Timeline` (05 §6.14), ordem cronológica **decrescente** (mais recente primeiro), uma linha por evento:

```
● 02/09/2026  ⛔ CRÍTICA   Covenant de endividamento rompido
              Interno Krill Tech · inadimplência técnica sem atraso financeiro
              Score após: 604   Δ −38                    [Ver evidência →]
```

Colunas lógicas: data · marcador de severidade (forma + rótulo) · título · descrição de uma linha ·
fonte · `scoreApos` · `deltaScore` com sinal · ação.

### 5.3 Interações

| Interação | Resultado |
|---|---|
| Hover em ponto da série | `ChartTooltip`: data, score, rating naquele momento, e "N eventos nesta data". |
| Clique em ponto da série | Abre `Drawer` **"Comparar com hoje"**: duas colunas com score, rating, PD 12m, risco de RJ, exposição, e a decomposição de deltas por fator entre aquele snapshot e o atual, com a linha de fechamento Σ. |
| Clique em marcador de evento | Rola a lista até a entrada correspondente e a destaca por 2s. |
| Clique em `Ver evidência` | Abre o `Drawer` de evidência (§4.11) com as `evidenciaIds` do evento. |
| Teclado | O gráfico é `tabbable`; `←`/`→` percorrem os pontos, `Enter` abre o drawer de comparação. O gráfico tem `role="img"` com `aria-label` descrevendo a trajetória: *"Score de 712 em junho para 604 em setembro, queda de 108 pontos, travessia da faixa B para a faixa C."* |
| Seletor de período | `90 dias` · `6 meses` · `12 meses` (padrão) — muda a janela do eixo X. |

### 5.4 Estado insuficiente

Com menos de 2 snapshots: card com `EmptyState` *"Histórico insuficiente para série temporal. Este
cliente tem 1 varredura registrada (12/09/2026)."* e a lista de eventos, se houver, renderizada sozinha.

---

## 6. `/nova-analise` — due diligence de novo cliente

Fluxo A. Três etapas na **mesma rota**, com transição de estado (sem navegação, sem query string):
`entrada` → `pipeline` → `resultado`.

### 6.1 Wireframe — etapa 1 (entrada)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          NOVA ANÁLISE DE CRÉDITO                               │
│      Consulte um CPF ou CNPJ antes de conceder crédito a prazo, barter ou CPR. │
│                                                                                │
│            ┌──────────────────────────────────────────────┐                    │
│            │  CPF ou CNPJ                                 │  [ Consultar ]     │
│            │  12.345.678/0001-90                          │                    │
│            └──────────────────────────────────────────────┘                    │
│              ✓ CNPJ válido                                                     │
│                                                                                │
│  PERFIS DEMONSTRATIVOS — clique para analisar                                  │
│  ┌──────────────────────┬──────────────────────┬──────────────────────────────┐│
│  │ Agropecuária Boa Vis…│ Sementes Alto Rio Lt…│ Comercial Dois Irmãos ME     ││
│  │ 11.222.333/0001-44   │ 44.555.666/0001-77   │ 77.888.999/0001-22           ││
│  │ Rio Verde/GO · Soja  │ Luís Eduardo Mag./BA │ Sorriso/MT · Milho           ││
│  │ Perfil: aprovável    │ Perfil: limítrofe    │ Perfil: recusável            ││
│  └──────────────────────┴──────────────────────┴──────────────────────────────┘│
│                                                                                │
│  ℹ Nenhuma consulta real é feita a órgão público. Os dados são simulados.      │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Validação do documento

| Estado | Gatilho | Feedback |
|---|---|---|
| Neutro | campo vazio | placeholder `000.000.000-00 ou 00.000.000/0000-00` |
| Máscara | digitação | aplica máscara de CPF até 11 dígitos, converte para CNPJ a partir do 12º |
| Incompleto | 1–10 ou 12–13 dígitos | `fg-tertiary`: *"Continue digitando — 11 dígitos para CPF, 14 para CNPJ."* Botão desabilitado. |
| **Inválido** | 11 ou 14 dígitos com DV incorreto | ícone + *"Dígito verificador inválido. Confira o número digitado."* Botão desabilitado. |
| Válido | DV correto | ✓ + `CPF válido` / `CNPJ válido`. Botão habilitado. `Enter` consulta. |
| Já na carteira | documento pertence a `origem='CARTEIRA'` | Não roda o pipeline. Card: *"Este documento já pertence a um cliente da carteira: **Fazenda Vale do Araguaia Ltda**."* + botões `Abrir cliente` (primário) e `Reanalisar mesmo assim` (secundário, roda o pipeline e termina em `/clientes/[id]`). |
| **Não encontrado** | DV válido, `consultarDocumento` retorna `null` | Ver §6.5. |

A validação de DV é a **única** operação de cálculo permitida no frontend (é validação de formulário,
não de risco) e vive em `lib/validacao/documento.ts`.

### 6.3 Wireframe — etapa 2 (pipeline)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ANALISANDO 11.222.333/0001-44                                      [Cancelar]  │
│ AGROPECUÁRIA BOA VISTA LTDA · Rio Verde/GO                                     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ✓ CADASTRAL ──── ✓ JURÍDICO ──── ✓ FISCAL ──── ◐ AMBIENTAL ──── ○ AGROCLIM.   │
│  Receita Federal  DataJud/CNJ     PGFN          SICAR            MAPA/ZARC     │
│  Redesim          DJE · Cartórios TST · Caixa   IBAMA            CONAB · INMET │
│  3 documentos     7 documentos    4 documentos  consultando…     —             │
│       │                                                                        │
│       └──── ○ INTERNO ──── ○ SCORE ──── ○ RELATÓRIO                            │
│             Krill Tech     Motor de     Agente                                 │
│             histórico      Decisão      Sintetizador                           │
│             —              —            —                                      │
│                                                                                │
│  ┌── REGISTRO DA COLETA ────────────────────────────────────────────────────┐  │
│  │ 14:32:07  CADASTRAL   Receita Federal · situação ATIVA desde 12/03/2014  │  │
│  │ 14:32:07  CADASTRAL   Redesim · quadro societário estável há 6 anos      │  │
│  │ 14:32:08  JURÍDICO    DataJud · 1 ação trabalhista arquivada             │  │
│  │ 14:32:08  JURÍDICO    Cartórios · nenhum protesto ativo                  │  │
│  │ 14:32:09  FISCAL      PGFN · sem inscrição em dívida ativa               │  │
│  │ 14:32:09  AMBIENTAL   SICAR · consultando CAR do imóvel…                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ⚗ Simulação de coleta. Nenhuma consulta real a órgão público é realizada.     │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 6.4 Semântica da animação — ela reflete estágios reais

**Regra dura:** a animação não é decorativa nem temporizada por `setTimeout` arbitrário. Cada estágio
só é marcado como concluído quando o dado correspondente **existe na resposta do motor**.

| Estágio | Fontes exibidas | Concluído quando | Contador exibido |
|---|---|---|---|
| 1 · Cadastral | Receita Federal · Redesim | `dimensoes` contém `cadastral` | nº de `Evidencia` com essas fontes |
| 2 · Jurídico | DataJud/CNJ · DJE · Cartório de protesto | idem `juridico` | idem |
| 3 · Fiscal | PGFN · TST/CNDT · Caixa CRF-FGTS | idem `fiscal` | idem |
| 4 · Ambiental | SICAR · IBAMA | idem `ambiental` | idem |
| 5 · Agroclimático | MAPA/ZARC · CONAB · INMET | idem `agroclimatico` | idem |
| 6 · Interno | Interno Krill Tech | idem `comportamental` + `garantias` | idem |
| 7 · Score | Motor de Decisão & Scoring | `scoreCalculado` presente e `auditoria.diferenca` ≤ 0,5 | `— ponto(s)` |
| 8 · Relatório | Agente Sintetizador (LLM) | primeiro token da narrativa recebido | tokens recebidos |

Implementação: a chamada ao motor é única; os estágios 1–7 são revelados em sequência com
**intervalo mínimo de 280ms e máximo de 700ms cada** apenas para legibilidade, e o estágio 8 acompanha
o stream real. Se a resposta chegar antes, os estágios ainda percorrem o mínimo; se demorar, o estágio
corrente pulsa (`◐`) indefinidamente até chegar. **Nunca marcar concluído um estágio cujo dado não
chegou.** Duração total típica: 2,5s a 4s.

Estados por estágio: `○ pendente` (cinza) · `◐ consultando` (acento, pulsação da 05 §9) ·
`✓ concluído` · `⚠ sem dado` (fonte não retornou evidência — permitido, e o registro escreve
*"Nenhum registro encontrado"*, que é informação, não falha).

Botão `Cancelar` aborta o `fetch` e volta à etapa 1 sem registrar nada.

### 6.5 Documento não encontrado

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  ⃠  DOCUMENTO SEM REGISTRO NAS BASES SIMULADAS                                  │
│                                                                                │
│  99.888.777/0001-66 tem dígito verificador válido, mas não corresponde a       │
│  nenhum perfil do conjunto de dados demonstrativo do Lastro.                   │
│                                                                                │
│  Em produção, este resultado significaria um de três cenários, e cada um tem   │
│  tratamento diferente na política de crédito:                                  │
│    • CNPJ recém-constituído, sem histórico — exige garantia reforçada          │
│    • Documento inexistente ou digitado com erro — devolver ao comercial        │
│    • Pessoa física sem inscrição estadual — avaliar elegibilidade a prazo      │
│                                                                                │
│  [ Tentar outro documento ]   [ Ver perfis demonstrativos ]                    │
└────────────────────────────────────────────────────────────────────────────────┘
```

Esta tela é deliberadamente informativa: transforma um caminho de erro em demonstração de
conhecimento de domínio diante da banca.

### 6.6 Etapa 3 — resultado

Ao concluir o estágio 7, a rota **navega para `/clientes/[id]`** com o prospect carregado
(`origem='PROSPECT'`, §4.13), preservando `/nova-analise` no histórico para o botão voltar. Uma faixa
de 40px no topo da página do cliente indica: *"Resultado de análise iniciada em /nova-analise ·
documento consultado em 12/09/2026 14:32"* com ação `Gerar parecer`.

**Decisão:** não existe uma quarta tela de "relatório resumido". A página do cliente já é o relatório,
e duplicá-la criaria duas verdades. O artefato de saída documental é o `/clientes/[id]/parecer`.

### 6.7 Perfis demonstrativos

Três cards clicáveis, alimentados por `Cliente.origem === 'PROSPECT'` do dataset (06 §prospects),
rotulados `aprovável`, `limítrofe` e `recusável`. Clique preenche o campo e dispara a consulta
imediatamente. Existem para que o jurado não precise digitar 14 dígitos durante o pitch.

---

## 7. `/alertas` — central de alertas

Responde: *"o que mudou na carteira e o que eu faço a respeito?"*

### 7.1 Estrutura

| Faixa | Conteúdo |
|---|---|
| Cabeçalho | Título · contagem total · contagem de não lidos · ações `Marcar todos como lidos` e `Ver clientes afetados` |
| Resumo por severidade | Quatro `KpiTile` compactos, clicáveis, que filtram: `Crítico (2)` · `Alto (4)` · `Médio (3)` · `Informativo (2)`. Cada um com ícone e rótulo textual (R2). |
| Filtros | `FilterChips`: `Todos` · `Não lidos` · `Últimos 7 dias` · `Últimos 30 dias` · `Com ação pendente`. Combinam-se com o filtro de severidade por **E**. |
| Agrupamento | Select: **`Por data` (padrão)** · `Por cliente` · `Por severidade` |
| Lista | `AlertRow`, agrupada conforme o select, com cabeçalhos de grupo fixos ao rolar (`sticky`) |

**Agrupamento padrão por data**, em buckets nomeados: `Hoje` · `Ontem` · `Esta semana` ·
`Últimos 30 dias` · `Anteriores`. Racional: a pergunta que traz o analista à central é temporal
("o que aconteceu desde que saí ontem"), não nominal.

### 7.2 Anatomia de um alerta

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ⛔ CRÍTICO   ● não lido                                          02/09/2026 06:12 │
│ CERRADO GRÃOS S/A  ·  Goiânia/GO  ·  Rating D                                    │
│ Recuperação judicial deferida                                                    │
│ Descrição  RJ deferida pela 3ª Vara Empresarial. Stay Period em curso.           │
│ Impacto    R$ 9.100.000 de exposição, dos quais R$ 9.100.000 sem cobertura       │
│            extraconcursal. Score 512 → 180 (−332). Rating rebaixado a D por veto.│
│ Ação       Habilitar crédito no quadro-geral em até 15 dias. Suspender novo      │
│            fornecimento a prazo. Não executar garantias concursais.              │
│ Fonte      DJE · 02/09/2026 · consulta simulada                                  │
│                              [Abrir cliente →]  [Marcar como lido]  [Ver evidência]│
└──────────────────────────────────────────────────────────────────────────────────┘
```

Campos obrigatórios por alerta, todos vindos de `Alerta`: cliente (link), data, tipo/título,
severidade (ícone + rótulo + borda esquerda 3px), `descricao`, `impacto`, `acaoRecomendada`, fonte e
estado de leitura. Alerta não lido tem fundo `surface-raised` e ponto de 6px; lido fica em
`surface-base` com opacidade de texto reduzida — **nunca** desaparece.

### 7.3 Marcação de leitura

- Clique em `Marcar como lido` alterna o estado (a ação vira `Marcar como não lido`).
- Abrir o cliente pelo alerta marca como lido automaticamente.
- `Marcar todos como lidos` pede confirmação em `Modal` quando há ao menos um `CRITICA` não lido.
- Estado persiste em `localStorage` sob `lastro:sessao:v1`; `Restaurar dados da demonstração` reverte.

### 7.4 Navegação e estados vazios

Clique na linha → `/clientes/[id]#red-flags`. Clique em `Ver evidência` → `Drawer` de evidência na
própria rota de alertas.

| Situação | `EmptyState` |
|---|---|
| Sem alertas | *"Nenhum alerta na carteira. A última varredura foi em 12/09/2026 06:00."* |
| Filtro sem resultado | *"Nenhum alerta crítico não lido nos últimos 7 dias."* + `Limpar filtros` |
| Todos lidos, filtro `Não lidos` | *"Você está em dia. Nenhum alerta pendente de leitura."* + `Ver todos` |

---

## 8. `/auditoria` — trilha de decisão humana

Materializa o *human-in-the-loop* exigido pela §5 do desafio: a máquina recomenda, a pessoa decide, e
o registro fica.

### 8.1 Tabela

`DataTable` densa, ordenada por `dataHora` decrescente:

| Coluna | Conteúdo |
|---|---|
| Data/hora | `dd/MM/aaaa HH:mm` |
| Analista | nome (persona fixa) |
| Cliente | razão social (link) |
| Score no momento | número + `RatingBadge` do `ratingNoMomento` |
| Recomendação gerada | `Badge` com o rótulo do `CodigoRecomendacao` |
| Decisão do analista | `Badge` com o rótulo de `DecisaoAnalista` |
| **Divergência** | Quando `divergiuDaRecomendacao`: ícone `GitBranch` + rótulo `DIVERGENTE` em cor de atenção; caso contrário, `Alinhada` em `fg-tertiary` |
| Justificativa | Primeiras 80 caracteres + `⋯`; linha inteira expande ao clicar |

Filtros: `Todas` · `Divergentes` · `Por cliente` (select) · `Últimos 30 dias`. Contador de
divergência no cabeçalho: `3 de 14 decisões divergiram da recomendação (21%)`.

Linha expandida mostra a justificativa integral, a lista de ações recomendadas que estavam vigentes no
momento e um link `Ver estado do cliente na data →` que abre o `Drawer` de comparação de snapshot (§5.3).

### 8.2 Destaque de divergência

Divergência é o dado mais importante desta tela — é a prova de que a ferramenta não decide sozinha.
Tratamento: borda esquerda 2px em cor de atenção **+** ícone **+** a palavra `DIVERGENTE` **+**
uma linha extra abaixo da linha principal, sempre visível, no formato:

```
↳ Recomendado: SUSPENDER NOVA EXPOSIÇÃO A PRAZO  →  Decidido: APROVAR COM RESTRIÇÕES
```

### 8.3 Formulário de decisão (`#decisao`, dentro de `/clientes/[id]`)

O registro nasce aqui, não em `/auditoria`.

| Elemento | Especificação |
|---|---|
| Contexto | Linha fixa: `Recomendação do motor: APROVAR COM RESTRIÇÕES · Score 604 · Rating C` |
| Decisão | Cinco botões-rádio em linha: `Aprovar` · `Aprovar com restrições` · `Revisar` · `Suspender` · `Recusar`. Sem pré-seleção. |
| Aviso de divergência | Aparece **assim que** a seleção difere do recomendado: *"Sua decisão diverge da recomendação do motor. Descreva o fundamento — o registro ficará marcado como divergente na trilha de auditoria."* Não bloqueia. |
| Justificativa | `textarea` de 3 linhas, **obrigatória sempre**, mínimo 20 caracteres, contador de 500. Placeholder muda com a decisão (ex.: `Descreva as restrições impostas e o prazo`). |
| Ação | `Registrar decisão` — desabilitado até haver decisão e justificativa válida. |
| Após registrar | `Toast` *"Decisão registrada na trilha de auditoria."*; o card passa a exibir as **3 últimas decisões** deste cliente com data, decisão, justificativa e marca de divergência, mais `Ver trilha completa →`; o formulário volta ao estado inicial para uma nova decisão. |

Persistência em `localStorage` (D11.3). O registro grava `analista` com a persona fixa, `scoreNoMomento`,
`ratingNoMomento`, `recomendacaoGerada` e `divergiuDaRecomendacao` calculado pela tabela de
equivalência abaixo — que é **regra de interface**, não de risco:

| `CodigoRecomendacao` | Decisão considerada **alinhada** |
|---|---|
| `APROVAR` | `APROVAR` |
| `APROVAR_COM_MONITORAMENTO_INTENSIVO` | `APROVAR`, `APROVAR_COM_RESTRICOES` |
| `APROVAR_COM_REVISAO_DE_LIMITE` | `APROVAR_COM_RESTRICOES` |
| `APROVAR_COM_RESTRICOES` | `APROVAR_COM_RESTRICOES` |
| `SUSPENDER_NOVA_EXPOSICAO_A_PRAZO` | `SUSPENDER`, `REVISAR` |
| `SUSPENDER_EXPOSICAO` | `SUSPENDER`, `RECUSAR` |

Qualquer combinação fora desta tabela é divergência.

---

## 9. Estados por tela

### 9.1 Regras gerais

| Estado | Tratamento padrão |
|---|---|
| **Loading** | Skeleton com a **forma real** do conteúdo (mesma altura, mesmas colunas), nunca spinner de página inteira. Skeletons pulsam conforme 05 §9. Duração mínima 200ms para evitar flash. |
| **Vazio** | `EmptyState` com título, causa e ao menos uma ação. Nunca "Nenhum dado". Sempre diz **por que** está vazio. |
| **Erro** | `ErrorState` com: o que falhou, o que isso significa para a análise, e o que fazer. Sempre com `Tentar novamente`. |
| **Parcial** | Números do motor renderizados + bloco de prosa em erro próprio. **Nunca** derrubar a tela por falha de prosa. |

### 9.2 Matriz completa

| Tela | Loading | Vazio | Erro de dados | Observações |
|---|---|---|---|---|
| `/carteira` | Faixa de atenção como 3 blocos cinza 132px; 8 skeletons de KPI; 4 áreas de gráfico com eixos desenhados sem série; tabela com 8 linhas fantasma | "Carteira sem clientes" (§3.7) | `ErrorState` de largura total substitui o conteúdo, preservando shell | Nunca renderizar gráfico com zero série — exibir o estado vazio do gráfico com o texto da pergunta que ele responderia |
| `/clientes` | Cabeçalho e filtros reais (contagens em `—`) + 12 linhas fantasma | §3.7 | `ErrorState` no lugar da tabela; filtros ficam desabilitados | Filtros e busca permanecem operáveis durante loading de reordenação |
| `/clientes/[id]` | Cabeçalho real (nome vem da lista, já em cache) + skeleton do gauge + skeletons dos blocos na ordem final | Cliente inexistente → `ErrorState` "Cliente não encontrado" + `Ver todos os clientes` | Se o motor falhar: erro de largura total. Se só uma seção falhar: erro local naquele card | Blocos suprimidos por `origem='PROSPECT'` **não** mostram skeleton |
| `/nova-analise` | n/a na entrada; o pipeline **é** o loading | n/a | Falha no meio do pipeline: o estágio corrente vira `✗` vermelho, os seguintes ficam `○`, e um `ErrorState` aparece abaixo do registro com `Tentar novamente` | Documento não encontrado é estado próprio, não erro (§6.5) |
| `/alertas` | 6 `AlertRow` fantasma com cabeçalhos de grupo | §7.4 | `ErrorState` no lugar da lista | Resumo por severidade mostra `—` durante loading |
| `/auditoria` | 8 linhas fantasma | "Nenhuma decisão registrada nesta sessão. As decisões que você registrar na página do cliente aparecerão aqui." + `Ir para a carteira` | `ErrorState` | Trilha vazia é o estado **inicial normal** da demo; o texto precisa deixar isso claro |
| `/clientes/[id]/parecer` | Documento com números + skeletons nos blocos de prosa | n/a | Ver 07 §Parte 3 | Botão `Imprimir` desabilitado enquanto houver bloco em loading |

### 9.3 Estados específicos da camada de IA

| Estado | Gatilho | Interface |
|---|---|---|
| **Streaming em andamento** | stream aberto | Skeleton **identificado**: título do bloco fixo + 3 linhas pulsando + rótulo `Gerando análise…` com ícone `Sparkles`. Ao chegar o primeiro token, as linhas dão lugar ao texto, que cresce com cursor de bloco. O container tem `min-height` fixo para não deslocar o layout. `aria-live="polite"` só no **fim** do stream, para não tagarelar no leitor de tela. |
| **LLM desligado** (`LASTRO_LLM_ENABLED=false`) | flag do servidor | O bloco renderiza a **narrativa determinística** normalmente, com a etiqueta ao pé: `Texto padrão (sem IA)`. O `CostCounter` exibe `LLM desligado`. **Não é erro e não usa cor de erro.** |
| **Orçamento esgotado** | `custoUsd ≥ orcamentoUsd` | Idêntico ao anterior, com a etiqueta `Orçamento de IA atingido — texto padrão`. O `CostCounter` vira `Orçamento atingido — modo determinístico`. Tooltip explica que os números não são afetados. |
| **LLM indisponível / timeout** | erro de rede ou > 25s | O bloco mostra, no lugar do texto: ícone `Info` + *"A análise em linguagem natural não pôde ser gerada agora."* + `Tentar novamente` + o texto determinístico logo abaixo, sob a etiqueta `Texto padrão (sem IA)`. **Os números do bloco permanecem intactos.** |
| **Stream interrompido no meio** | conexão cai | O texto parcial é mantido, seguido de `— interrompido` em `fg-tertiary` e `Retomar`. Nunca apagar o que já foi lido. |
| **Copiloto fora de escopo** | resposta de recusa do modelo | Renderizada como mensagem normal com ícone `Info`. Não é erro. |

### 9.4 API Flask fora do ar — estado obrigatório

O Next é **só interface**: sem o Flask, não há score, PD, RJ, exposição, alerta nem auditoria. Este é
o estado de falha mais provável durante a demonstração e precisa ser o mais bem tratado.

**Detecção.** Todo route handler de proxy (`web/app/api/*`) que receber `ECONNREFUSED`, `ETIMEDOUT`,
`fetch failed` ou status ≥ 500 do Flask devolve `503` com o corpo:

```json
{ "erro": "MOTOR_INDISPONIVEL", "detalhe": "Sem resposta do serviço de cálculo em 127.0.0.1:5001" }
```

**Apresentação.** Dois níveis, simultâneos:

1. **Faixa global persistente**, 32px, logo abaixo do `SimulatedDataBanner`, presente em todas as
   rotas enquanto o serviço não responder:
   `⚠ Motor de risco indisponível — os valores exibidos podem estar desatualizados. Reconectando… (tentativa 3)`
   com botão `Tentar agora`. Repetição automática com backoff de 2s, 4s, 8s, 16s e depois 30s fixos.
   Ao voltar, a faixa some e um `Toast` confirma *"Motor de risco reconectado."*, revalidando a rota.
2. **`ErrorState` no conteúdo**, quando a rota não tem nenhum dado para mostrar:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ⚠  MOTOR DE RISCO INDISPONÍVEL                                              │
│                                                                              │
│  A interface do Lastro não calcula risco. Todos os scores, probabilidades,   │
│  coberturas e recomendações vêm do serviço de cálculo em Python, que não     │
│  está respondendo.                                                           │
│                                                                              │
│  O que fazer:                                                                │
│    1. Verifique se o serviço está de pé:  npm run dev                        │
│    2. Confirme a porta 5001 e a variável LASTRO_API_URL                      │
│    3. Consulte o terminal do serviço api/ para erros de inicialização        │
│                                                                              │
│  Última resposta bem-sucedida: 12/09/2026 14:28:51                           │
│                                                                              │
│  [ Tentar novamente ]     [ Ver arquitetura do sistema ]                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Regras:** nunca tela branca; nunca número em cache apresentado como atual sem a faixa de aviso; o
shell (sidebar, topbar, banner) **continua renderizando** — a navegação permanece utilizável;
`/canvas` e `/arquitetura` continuam funcionando integralmente, porque não dependem do motor, e a
faixa global explica que apenas as telas de dados estão afetadas.

---

## 10. Acessibilidade e microcópia

### 10.1 Glossário e tooltips

Todo termo técnico usa `<Termo sigla="…" />` da 05 §6.13, com o texto **literal** do glossário. Termos
obrigatórios e onde cada um deve aparecer ao menos uma vez:

| Termo | Onde é obrigatório |
|---|---|
| `PD` | cabeçalho da coluna PD 12m (`/clientes`), card de probabilidades, parecer |
| `RJ` | coluna Risco de RJ, card de risco de RJ, alertas de RJ, parecer |
| `CNDT` | fator `cndt_positiva`, red flag de CNDT, evidências do TST |
| `CAR` | fatores `car_ausente`/`car_irregular`/`car_regular`, evidências do SICAR |
| `ZARC` | fator `zarc_risco`, V3 da carteira, evidências do MAPA |
| `CPR` | tabela de garantias, resumo de operações |
| `EXTRACONCURSAL` | K4 da carteira, coberturas, tabela de garantias, Stay Period |
| `CONCURSAL` | idem |
| `STAY_PERIOD` | título do painel de Stay Period, alerta de RJ |
| `COVENANT` | red flag de inadimplência técnica, fator `inadimplencia_tecnica` |
| `PGFN`, `CRF_FGTS`, `BARTER`, `HAIRCUT` | onde a sigla aparecer pela primeira vez na tela |

**Inadimplência técnica** não é sigla e não entra no glossário de termos; recebe tratamento de
microcópia fixa, sempre que aparecer:

> *"Quebra de cláusula contratual detectada antes de qualquer atraso de pagamento. É o sinal mais
> antecipado disponível — e não aparece em nenhum bureau."*

Regra: um termo recebe tooltip **na primeira ocorrência por card**, não em todas — sublinhado pontilhado
repetido a cada linha polui a tabela.

### 10.2 Formatação (usar exclusivamente `lib/format.ts`, 05 §11)

| Tipo | Formato | Exemplo |
|---|---|---|
| Moeda | `R$ 14.200.000` (sem centavos acima de R$ 1.000) | `formatarMoeda` |
| Moeda compacta | `R$ 14,2 mi`, `R$ 820 mil` (tabelas e KPIs) | `formatarMoedaCompacta` |
| Percentual | `17,1%` (1 casa); `22,6%` | `formatarPercentual` |
| Score | inteiro, sem separador | `604` |
| Delta | sempre com sinal | `−108`, `+31` |
| Data | `dd/MM/aaaa` | `12/09/2026` |
| Data e hora | `dd/MM/aaaa HH:mm` | `12/09/2026 14:32` |
| Data relativa | `há 3 dias`, `em 12 dias`, `hoje`, `ontem` | apoio, nunca substitui a data absoluta |
| Documento | máscara pt-BR | `12.345.678/0001-90` |

Sinal negativo é o **minuto tipográfico** `−` (U+2212), não o hífen. Números em tabelas usam
`font-variant-numeric: tabular-nums` (05 §4.3).

### 10.3 Teclado

| Contexto | Comportamento exigido |
|---|---|
| Tabelas | `Tab` entra na tabela uma vez (roving tabindex); `↑`/`↓` navegam linhas; `Enter` abre o cliente; `Home`/`End` vão ao primeiro/último; `Tab` sai para o próximo controle. Cabeçalhos ordenáveis são `button` com `aria-sort`. |
| Filtros | `FilterChips` é `role="radiogroup"`; `←`/`→` percorrem; `Espaço` seleciona. |
| Drawer | Foco move para o título ao abrir; foco preso dentro; `Esc` fecha e devolve o foco ao gatilho. |
| Modal | Idem, com `aria-modal="true"` e overlay não clicável quando a ação for destrutiva. |
| Busca global | `/` e `Ctrl/Cmd+K` focam; `↑`/`↓` percorrem os resultados; `Esc` fecha sem navegar. |
| Gráficos | `tabbable` com `role="img"` e `aria-label` descritivo; séries com pontos navegáveis por `←`/`→`. |
| Formulário de decisão | Rádios como `radiogroup`; `Ctrl/Cmd+Enter` registra quando válido. |
| Atalho de rota | `g` seguido de `c` (carteira), `l` (clientes), `a` (alertas), `n` (nova análise). Indicado no popover da persona. |

Foco visível em **todo** elemento interativo: anel de 2px `accent-400` com offset de 2px, nunca
removido. `:focus-visible`, não `:focus`.

### 10.4 Redundância de canal (I8) — checklist verificável

| Elemento | Cor | Ícone | Texto |
|---|---|---|---|
| `RatingBadge` | ✓ | — | ✓ letra + rótulo em tooltip |
| Severidade de alerta/red flag | ✓ | ✓ forma distinta por nível | ✓ `CRÍTICO`/`ALTO`/`MÉDIO`/`INFORMATIVO` |
| `TrendIndicator` | ✓ | ✓ seta com inclinação distinta | ✓ delta numérico com sinal |
| Veto | ✓ | ✓ `ShieldAlert` | ✓ rótulo do veto + efeito |
| Natureza de garantia | ✓ | — | ✓ `EXTRACONCURSAL` / `CONCURSAL` escrito |
| Ponto da matriz V1 | ✓ | — | ✓ letra do rating impressa no ponto |
| Estágio do pipeline | ✓ | ✓ `○ ◐ ✓ ✗ ⚠` | ✓ nome do estágio + contador |
| Status de parcela | ✓ | ✓ | ✓ `A vencer` / `Paga` / `Em atraso` |

Teste de aceitação: um print em escala de cinza de cada tela deve permanecer integralmente
interpretável. Se algum estado desaparecer, a tela está errada.

### 10.5 Microcópia — frases fixas e literais

| Contexto | Texto exato |
|---|---|
| Aviso de decisão humana | `Decisão final sujeita à avaliação do analista responsável.` |
| Banner global | `DADOS SIMULADOS — protótipo demonstrativo · nenhuma consulta real a órgão público` |
| Selo de evidência | `consulta simulada` |
| Rodapé do copiloto | `O copiloto responde apenas com base nos dados desta avaliação. Não consulta internet nem bases externas.` |
| Prosa gerada por IA | `Texto gerado por IA a partir dos dados deste parecer` |
| Prosa determinística | `Texto padrão (sem IA)` |
| Separação PD × RJ | `Escala própria — não comparável à PD` |
| Fechamento de soma | `Σ contribuições = {score}  ·  score exibido = {score}  ·  diferença 0,0 ✓` |
| Exposição em cenário de RJ | `O penhor entra no plano de recuperação com deságio; a alienação fiduciária, não.` |
| Simulação de evento | `MODO DEMONSTRAÇÃO · injeta um evento e recalcula o risco de verdade` |

**Tom:** afirmativo, específico e sem hedge. Proibidos na interface: "talvez", "aproximadamente" em
número calculado, "inteligência artificial avançada", "revolucionário", "poderoso", exclamação e
emoji. Toda mensagem de erro nomeia a causa e oferece uma ação. Todo estado vazio explica o porquê.

---

## 11. Os 30 segundos do jurado

Cenário: o jurado recebe o notebook com a aplicação aberta em `/carteira`, em 1440×900, e ninguém
narra nada. Este é o caminho do olho que a tela precisa **forçar**, com o tempo aproximado:

| t | O olho vai para | Porque | O que ele conclui |
|---|---|---|---|
| 0–2s | Banner de dados simulados (topo, largura total, textura diagonal) | É o primeiro elemento e não compete com nada | *"É um protótipo honesto, não estão me vendendo dado falso como real."* |
| 2–5s | **Faixa de atenção imediata** — três cartões com nomes próprios, causas e valores em R$ | Maior contraste da tela, borda esquerda em cor semântica, nomes de empresa em `type-title` | *"Três clientes estão em apuros agora, e cada um por um motivo diferente e nomeado."* |
| 5–9s | **K1 e K2** — `R$ 184,3 mi` e `R$ 41,7 mi em risco · em RJ: R$ 63,9 mi` | Números maiores da tela, alinhados à esquerda no início da faixa de KPIs | *"Sabem exatamente quanto dinheiro está exposto e quanto está desprotegido — inclusive num cenário jurídico específico."* |
| 9–13s | **K4 — cobertura extraconcursal 38% vs total 71%** | Duas barras distintas onde todo concorrente mostra uma só | *"Isso não é um dashboard genérico; alguém entende de direito falimentar."* |
| 13–17s | **V1 — matriz de risco**, com os pontos D no alto à direita e a letra do rating impressa neles | Único gráfico de dispersão, com ponto grande e anel tracejado nos vetos | *"O risco não é uma nota só; é probabilidade cruzada com dinheiro desprotegido."* |
| 17–20s | Clique no ponto D mais alto → **`/clientes/[id]`** | O ponto tem cursor de link e o anel de veto chama o clique | — |
| 20–24s | **Coluna direita:** score `604` no gauge, ao lado da **classificação final D com o motivo do veto nomeado** | Maior elemento da página, com a assimetria "calculado vs final" | *"O sistema separa o que o modelo calculou do que a regra jurídica impôs — e diz qual regra."* |
| 24–27s | **Card "O que mudou": `712 → 604 (−108)` com quatro linhas que somam exatamente −108 e a marca ✓** | Alinhamento monoespaçado e a linha de fechamento | *"Eu posso somar na tela e fecha. Não é número inventado por um modelo de linguagem."* |
| 27–30s | **Card de recomendação:** `APROVAR COM RESTRIÇÕES`, três ações com valores em reais, `Reavaliar em 30 dias`, e a caixa `Decisão final sujeita à avaliação do analista responsável.` | Sticky, sempre visível, com a caixa de aviso emoldurada | *"Ele me diz o que fazer com números concretos — e admite que quem decide sou eu."* |

**As cinco perguntas, respondidas em 30 segundos, sem um clique além do primeiro:** P1 na faixa de
atenção e no gauge; P2 no veto nomeado e na decomposição; P3 no `712 → 604`; P4 no selo "consulta
simulada" e na fonte de cada evidência à distância de um clique; P5 na recomendação com ações
parametrizadas.

### 11.1 O que **não** pode acontecer nesses 30 segundos

| Proibição | Consequência se violada |
|---|---|
| Nenhum spinner ocupando a tela na abertura | O jurado conclui que é lento ou que depende de rede |
| Nenhum bloco de prosa acima da dobra na carteira | Streaming visível de imediato sugere que os números vêm do LLM (viola a leitura de I7) |
| Nenhuma animação de entrada além de fade de 120ms | Movimento gratuito consome o orçamento de atenção |
| Nenhum "0" ou "—" em KPI da abertura | Vazio na tela inicial lê-se como produto inacabado |
| Nenhuma tela branca se o Flask cair | §9.4 é a rede de segurança e precisa estar testada |
| Nenhum gráfico sem rótulo de eixo ou sem unidade | Gráfico ilegível vira gráfico decorativo, e decorativo é proibido |

### 11.2 Ensaio de aceitação da tela de abertura

Checklist a rodar antes da entrega, com os dois serviços de pé, em 1440×900:

- [ ] `/` redireciona para `/carteira` em menos de 300ms
- [ ] `/carteira` pinta números reais sem rolagem e sem spinner de página
- [ ] A faixa de atenção nomeia três clientes distintos, com três causas distintas
- [ ] K2 mostra, na mesma célula, exposição em risco **e** exposição em risco em cenário de RJ
- [ ] K4 mostra duas barras separadas, nunca uma soma
- [ ] V1 tem rótulo nos dois eixos, unidade em ambos e a letra do rating dentro de cada ponto
- [ ] Clicar em qualquer KPI ou barra leva a `/clientes` com o filtro correto pré-aplicado
- [ ] Um print em escala de cinza da carteira e da página do cliente continua interpretável
- [ ] Derrubar o Flask exibe a faixa §9.4 em até 5s, sem tela branca, com a navegação viva
- [ ] `LASTRO_LLM_ENABLED=false` mantém todos os números e todas as telas íntegros
