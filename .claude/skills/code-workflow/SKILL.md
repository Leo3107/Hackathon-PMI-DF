---
name: code-workflow
description: Orquestrador de desenvolvimento agêntico spec-driven, feedback-first e paralelo, aplicável a qualquer repositório. Use quando o usuário disser "/code-workflow", "rodar o workflow", "seguir o fluxo specs/feedback/plan/build", "workflow este repo", ou pedir desenvolvimento guiado por especificação com feedback fechado e execução paralela por subagentes. Conduz SPECS → FEEDBACK-DESIGN → PLAN → (BUILD ⇄ FEEDBACK) → REVIEW, com checkpoints humanos só no início (aprovar specs + sim/não nos feedbacks) e o resto autônomo. Usa ultracode (Workflow tool) para maximizar paralelismo — builds paralelizáveis entre si e feedbacks rodando ENQUANTO builds acontecem, nunca fase ociosa.
---

# /code-workflow — maestro do fluxo specs → feedback → plan → build

Orquestrador de desenvolvimento. Sempre que o usuário invocar `/code-workflow` (ou "rodar o workflow", "seguir o fluxo", "workflow este repo"), carregue e siga este arquivo do início.

**Princípio:** desenvolvimento é spec-driven, feedback-first e paralelo. Você é o **maestro** — não executa trabalho pesado sozinho, você **fan-out → integra**. **Paralelo por default (lembre do `ultracode`):** sempre buscar o máximo de subagentes em trabalho não-conflitante ao mesmo tempo — builds paralelizáveis entre si, **feedbacks rodando enquanto builds estão em voo**, pesquisa adiantada do próximo workstream; sequencial só sob dependência ou conflito de arquivos (ver `orchestration.md`). Genérico: nada aqui é específico de um projeto; o específico mora no repo (`AGENTS.md`, `CONTEXT.md`, `specs/`).

Detalhe de cada fase nos arquivos de `workflows/` — **leia o arquivo da fase ao entrar nela**.

## O loop

```
SPECS  →  FEEDBACK-DESIGN  →  PLAN  →  ┌─ BUILD ⇄ FEEDBACK ─┐  →  (REVIEW)
 ▲ único checkpoint humano           └────── loop ─────────┘
```

**Política de checkpoint:** dois toques humanos, ambos no início. (1) **aprovação das SPECS**; (2) **sim/não no conjunto de feedbacks proposto** para a sessão (leve — já sondado durante as specs). PLAN, BUILD e REVIEW rodam **autônomos** — você decide arquitetura e fecha os loops sozinho, confiando nos feedbacks confirmados. Só volte ao humano se descobrir um gap que invalida as specs aprovadas.

## Skills integrantes

Este workflow **orquestra outras skills** nos pontos certos — invoque-as como parte do fluxo, não como alternativas a ele:

- **`/goal`** — no setup, para fixar/clarear o **objetivo** da sessão antes de tudo (alimenta o escopo/slug do §0.4).
- **`/grilling`** — na fase **SPECS**, para a entrevista implacável até clareza total.
- **`/ultraplan`** — na fase **PLAN**, para o planejamento profundo e hierárquico.
- **`/ultrathink`** — em **qualquer decisão difícil**: desenho do feedback, arquitetura no plan, conflito de integração no build, julgamento adversarial no review.
- **`ultracode`** — no **BUILD e nos FEEDBACKs**, para orquestração multi-agente em escala via **Workflow tool**: fan-out determinístico dos workstreams (pipeline/parallel), feedbacks disparados assim que cada entrega retorna (sem esperar o lote), verificação adversarial e cobertura exaustiva. Usar quando o trabalho justifica muitos subagentes em paralelo e o custo de token não é a restrição. Ver `orchestration.md` §Ferramenta.

## 0. Setup da sessão (uma vez)

### 0.1 Detectar o layout do repo
Não assumir. Descobrir: raiz git (`git rev-parse --show-toplevel`), repos aninhados/submódulos/workspaces (`git submodule status`, `.gitmodules`, workspaces de `package.json`, múltiplos `.git`), onde fica o código de cada camada (ler a árvore real), branch(es) padrão. Registrar quantos repos versionados existem — todo commit/push/PR depois considera todos.

### 0.1b Partir da main atualizada
**Default:** dar checkout na branch padrão + `pull` em **todos** os repos detectados, e criar uma **branch descritiva própria** a partir dela **antes de qualquer escrita** (inclusive specs). Só não fazer se o usuário pedir explicitamente (trabalhar na branch atual / não criar branch).

### 0.2 Ler contexto (em paralelo, ignorar ausentes)
`README.md`, `AGENTS.md`, `CONTEXT.md` (raiz e de pastas relevantes), `CLAUDE.md`, `CONTRIBUTING.md`; `specs/README.md` + specs relevantes; `plans/PLAN_*.md` recentes (e `IMPLEMENTATION_PLAN.md` se o repo tiver um legado).

### 0.3 Bootstrap dos docs de memória
Se faltarem, criar a partir de `templates/`: `AGENTS.md` (operacional, na raiz) e `CONTEXT.md` (aprendizados duráveis). `CONTEXT.md` é **por escopo**: pode haver um na raiz e outros dentro de pastas/apps específicos (info que só faz sentido ali). Garantir que `plans/` exista. Ver `workflows/orchestration.md` §memória.

### 0.4 Objetivo e escopo da sessão
Usar **`/goal`** para fixar/clarear o objetivo da sessão. Daí derivar o escopo (uma frase) → vira o **slug** do plan (kebab-case curto).

### 0.5 Parent issue do Linear
Perguntar a parent issue da sessão. Se o usuário não tiver, **criar uma** (ver `workflows/linear.md`). Todo o trabalho da sessão vira sub-issues dentro dela. As ferramentas `mcp__linear-server__*` são **deferred** — carregar com `ToolSearch` aqui no setup para o Linear não ser ignorado depois.

### 0.6 Política de modelo por fase (perguntar sempre)
Antes de entrar em SPECS, perguntar ao usuário via `AskUserQuestion` se quer aplicar a **política de modelo por fase** desta sessão (ver §Modelo por fase) — opção recomendada: sim. **Sim** → aplicar a tabela ao disparar subagentes (e o maestro, se ele próprio for um subagente) pelo resto da sessão. **Não** → omitir `model` em toda chamada de Agent/Workflow (herda o default do harness) e não repetir a pergunta na sessão.

### 0.7 Entrada
Default: começar em **SPECS**. Se specs já existem e estão aprovadas, pode entrar direto em FEEDBACK-DESIGN/PLAN. Ler o arquivo da fase e entrar.

## Fases (resumo — detalhe em `workflows/`)

1. **SPECS** → `workflows/specs.md`. Discovery implacável (estilo grill) até clareza total: regras de negócio, JTBD, pontos de implementação. Pode disparar subagentes de pesquisa no código em paralelo. Escreve `specs/<topic>.md`. **Checkpoint humano obrigatório** — único do fluxo.
2. **FEEDBACK-DESIGN** → `workflows/feedback.md`. Montar a **matriz de feedback por feature** — cada feature tem várias dimensões (E2E, qualidade-IA via judge+rubrica, edge-case adversarial, diff visual, lint, **vivência como usuário**...), cada uma com limiar; a feature só fecha quando todas passam. **Propor + pedir sim/não ao usuário.** Automatizáveis rodam a cada incremento; gated ao fechar a feature. Matriz registrada inline no plan ativo. **Regra não-negociável:** toda mudança que afeta a UX final — inclusive backend que muda o que o usuário percebe — exige **entrar no sistema vivo e testar como o usuário** (`/agent-browser` p/ web; dirigir a interface real p/ TUI/CLI/mobile), simulando o gesto real e analisando a tela. Ver `feedback.md` §Regra não-negociável.
3. **PLAN** → `workflows/plan.md`. Plano **bem detalhado e hierárquico** (workstreams → itens → subitens → sub-subitens), particionado em **workstreams independentes** (mínimo conflito), cada nó citando spec de origem + feedback que o valida. **Artefato único:** `plans/PLAN_AAAA-MM-DD_<slug>.md` desta sessão — o **plan ativo**, editado continuamente. Dispara subagente Linear pra espelhar **a hierarquia inteira** — uma issue por nó (no mínimo uma por item).
4. **BUILD ⇄ FEEDBACK** → `workflows/build.md`. Maestro dispara subagentes em paralelo pelos workstreams; cada incremento roda a matriz de feedback da feature (via subagentes, não-bloqueante) → atualiza o plan ativo + CONTEXT → commit em branch. **Todo turno reconcilia o Linear** (subagente dedicado, mecânico, sem depender de o maestro lembrar — ver `workflows/linear.md` §Reconciliação). **Todo achado de feedback retroalimenta o plan ativo como item novo.** **Ponto de ajuste que o usuário propõe testando um ambiente vivo (mock/preview/staging) NÃO vai direto pro build — reentra por um mini-ciclo SPECS→PLAN via subagents** que ajusta a spec relevante e expande o plan ativo antes de virar item (ver `workflows/build.md §Feedback de teste manual`). O loop só para quando o plano está **inteiramente fechado** — todos os workstreams, todos os itens, e todos os itens nascidos de feedback/review implementados e validados.
5. **REVIEW** → `workflows/review.md`. Passe adversarial/code-review; achados viram itens novos de plano.

## Modelo por fase (opcional — perguntar no setup §0.6)

**Opt-in.** Só se aplica se o usuário confirmou "sim" na pergunta do setup (§0.6). Se ele disse "não" (ou não foi perguntado ainda), **não aplicar** — omitir `model` nas chamadas e usar o default do harness.

Confirmado o opt-in: cada fase/papel tem um modelo preferido — aplicar ao **spawnar subagentes** (Agent tool `model:` ou Workflow tool `agent(..., {model})`) e, quando a própria sessão do maestro puder escolher modelo (ex. maestro disparado como subagente por outra sessão), à sessão do maestro também. **"Se disponível"** = tentar o preferido primeiro; se a conta/harness não tiver acesso a ele (erro de modelo indisponível), **cair pro modelo default da sessão sem bloquear a fase** — indisponibilidade de modelo nunca trava o fluxo.

| Fase / papel | Modelo preferido | Fallback |
|---|---|---|
| **Maestro (orquestrador)** | `fable` | modelo da sessão atual |
| **SPECS** — grill, discussão e escrita das specs | `fable` | modelo da sessão atual |
| **SPECS/PLAN** — subagentes de pesquisa de código | `opus` (4.8) | modelo da sessão atual |
| **FEEDBACK-DESIGN** — desenho da matriz por feature | `fable` | modelo da sessão atual |
| **PLAN** — escrita do plano | `fable` | modelo da sessão atual |
| **BUILD** — subagentes de workstream, implementação | `opus` (4.8) | modelo da sessão atual |
| **FEEDBACK — execução vivencial** (entrar no sistema vivo — `/agent-browser` p/ web, interface real p/ TUI/mobile — navegar, analisar o que a tela retorna, E2E ponta a ponta **simulando o próprio usuário**) | `fable` | modelo da sessão atual |
| **FEEDBACK — execução mecânica** (rodar testes/lint, juízes de qualidade-IA, adversarial, benchmarks, coletar evidências) | `opus` (4.8) | modelo da sessão atual |
| **FEEDBACK — análise** (ler o compilado de evidências que o executor trouxe → propor próximos passos no plan/build) | `fable` | modelo da sessão atual |
| **REVIEW — execução das lentes** (code-review, refutação, reprodução) | `opus` (4.8) | modelo da sessão atual |
| **REVIEW — análise/julgamento** (consolidar achados → itens de plano) | `fable` | modelo da sessão atual |

**Na prática — dois papéis:** **Fable = engenheiro sênior que orienta e vivencia**: entra na fase inicial (discussão, specs, feedback-design, plan), volta a cada momento de feedback para **analisar as evidências compiladas** e propor os próximos passos — e **executa ele mesmo o feedback vivencial**: no teste de entrar no sistema vivo (agent-browser etc.), o Fable faz o trabalho que o humano faria no loop — navega, olha o que o sistema retorna, julga a experiência ponta a ponta simulando o próprio usuário. **Opus = executor mecânico**: implementa, roda testes/juízes/adversarial e compila as evidências. Todo momento de feedback tem os dois tempos: **executor executa e compila → Fable analisa e propõe.**

Como passar: Agent tool aceita `model: "fable" | "opus" | "sonnet" | "haiku"`; Workflow tool aceita o mesmo valor em `opts.model` de cada `agent()`. Omitir o campo = herdar o modelo da sessão — é o fallback seguro quando o preferido não está disponível.

## Orquestração (o symphony)

Leia `workflows/orchestration.md`. Núcleo: o maestro fan-out e integra; nunca bloqueia. Subagentes para workstreams independentes, pesquisa adiantada, feedback, Linear, review. Particionar por dono de arquivo/módulo; usar git worktree (isolation:worktree) quando há escrita concorrente em árvore compartilhada. Subagentes recebem: objetivo claro, fatia de spec/plan, `CONTEXT.md` + `AGENTS.md`, e retorno estruturado — e podem recursar (mini plan/build/feedback).

## Memória que se retroalimenta

- Todo subagente lê o(s) `CONTEXT.md` relevante(s) + `AGENTS.md` antes de trabalhar.
- Aprendizado durável (decisão, armadilha, padrão) → promover pra `CONTEXT.md` do escopo certo (raiz ou pasta específica). Descoberta operacional (comando certo de rodar/testar) → `AGENTS.md`, enxuto. Aprendizado que só vale dentro da sessão → `tmp-context.md` (não commitado).
- O **plan ativo** é o `plans/PLAN_AAAA-MM-DD_<slug>.md` da sessão — carrega o estado vivo e é editado continuamente. **Não existe plan ativo fora de `plans/`.** Plans de sessões antigas não são editados (são history).

## Convenções de plans

Pasta `plans/`. Naming `PLAN_AAAA-MM-DD_<slug>.md`. Cada plan **é** um implementation plan; o da sessão atual é o **plan ativo**, editado continuamente durante o build. Estrutura mínima:
```markdown
# Plan — <título>
Data: AAAA-MM-DD · Escopo: <uma frase> · Parent Linear: <id>
Specs relevantes: [...] · Feedback loops: [...]
## Objetivos
## Workstreams (independentes)
## Itens priorizados
## Decisões da sessão
## Execution log
```
Sessão futura que retoma um plan cria **novo arquivo** referenciando o antigo no topo — nunca sobrescreve.

## Nunca

- Commitar na branch padrão (branch descritiva sempre).
- Avançar de SPECS sem aprovação humana.
- Bloquear o maestro com feedback/Linear que poderiam rodar em subagente.
- Inflar `AGENTS.md` com status (status mora no plan ativo).
- Tocar issues do Linear fora da parent da sessão.
- **Parar o loop com o plan ativo ainda aberto, ou descartar achado de feedback sem virar item do plano.** Cortar escopo é decisão humana explícita, nunca silenciosa.
- **Dar por fechada uma feature que mexe na UX sem ter entrado no sistema vivo e vivenciado como o usuário** (`/agent-browser` ou dirigindo a interface real). Vale mesmo quando a mudança é "só backend" mas o usuário percebe.
