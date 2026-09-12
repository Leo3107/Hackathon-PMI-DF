# Orquestração — o symphony de subagentes

Regras de como o maestro fan-out e integra. Vale para todas as fases (specs, plan, build, feedback, review).

## Princípio

O maestro **nunca bloqueia** no que pode ser delegado. Ele decompõe, dispara subagentes, e integra os retornos.

**Maximizar o paralelismo é o default, não uma otimização.** A cada turno, buscar o **maior número de subagentes rodando ao mesmo tempo** em trabalho que **não conflita** (donos de arquivo/módulo distintos — ver §Evitar conflito). Disparar todos juntos (vários numa só mensagem, ou via Workflow), não um de cada vez. Sequenciar **só** quando há dependência real (`dep:`) ou escrita concorrente na mesma árvore; fora disso, serializar é desperdício. Se um subagente roda sozinho enquanto há trabalho não-conflitante parado, **encher os slots ociosos** — com o próximo workstream independente ou com pesquisa/arquitetura adiantada do que vem a seguir.

## Quando disparar subagentes

- **Workstreams independentes** do plan (um subagente por workstream).
- **Pesquisa/arquitetura adiantada** — mapear código, estudar libs, projetar algo que outro subagente vai executar depois.
- **Feedback caro** — e2e completo, diff visual, adversarial, benchmark: roda em subagente para o maestro seguir (não-bloqueante).
- **Linear** — atualização de sub-issues sempre em subagente (`linear.md`).
- **Review** — passe adversarial/code-review (`review.md`).

## Evitar conflito entre subagentes paralelos

1. **Fronteira de dono**: cada subagente só escreve nos arquivos/módulos do seu workstream (definido no plan). Dois subagentes nunca editam o mesmo arquivo no mesmo lote.
2. **git worktree** (`isolation: "worktree"` no Agent/Workflow) quando escritas concorrentes tocariam a mesma árvore — cada um na sua cópia; o maestro mescla. Custa setup; usar só quando há conflito real.
3. **Ordenar por dependência**: workstream com `dep:` só dispara quando o de cima integrou.

## Contrato do subagente

Todo subagente recebe:
- **Objetivo** claro e fechado (o que entregar, critério de pronto).
- **Fatia relevante** de spec + item do plan.
- **`CONTEXT.md` + `AGENTS.md`** (ler antes de começar — memória compartilhada).
- Instrução de **retorno estruturado** (o que mudou, o que aprendeu, estado do feedback, o que ficou pendente).
- **Ferramentas deferred** que vá usar (MCP: Linear, Playwright, etc.) — instruí-lo a carregá-las com `ToolSearch` antes de chamar (causa comum de subagente "ignorar" uma integração).
- **Modelo preferido da fase** (`model:` no Agent/Workflow) — **só se a política estiver ativa** (opt-in no setup §0.6); ver SKILL.md §Modelo por fase. Se o modelo pedido não estiver disponível na conta, cair pro default da sessão sem bloquear o disparo.

Subagentes **podem recursar**: rodar seu próprio mini plan → build → feedback para entregar o que o maestro pediu. Bounded — não viram sessões infinitas.

## Integração (responsabilidade do maestro)

- Mesclar branches/worktrees; resolver conflitos.
- **Re-rodar o feedback no todo integrado** — paralelismo pode introduzir regressão invisível por-workstream.
- Coletar aprendizados dos retornos → promover pra `CONTEXT.md` (durável) / `AGENTS.md` (operacional).

## Ferramenta

Preferir o **Workflow tool** quando o fan-out é determinístico (pipeline por workstream, fan-out da matriz de feedback, loop-until-dry) — requer opt-in do usuário para multi-agente em escala. Caso contrário, **Agent tool** (vários numa só mensagem para rodar concorrente). Para feedback adversarial (qualidade-IA, edge-case), ver os padrões de verify/judge do Workflow.

**Sob `ultracode`** o opt-in está dado: autorar e rodar um **Workflow** vira o default do BUILD — script com pipeline por workstream + fan-out da matriz de feedback + verificação adversarial das entregas, buscando cobertura exaustiva (custo de token não é restrição). Fases de clareza (specs/feedback/plan) e edits triviais continuam solo. Se a política de modelo por fase estiver ativa (opt-in no setup §0.6), setar `opts.model` de cada `agent()` conforme a fase daquele estágio do pipeline (implementação e **execução mecânica** de feedback/adversarial → `opus`; **vivência como usuário** — agent-browser/E2E vivencial simulando o humano → `fable`; **análise** do compilado de evidências → `fable`) — ver SKILL.md §Modelo por fase.

## Memória (setup §0.3)

- `AGENTS.md` — operacional durável (rodar, testar, acessos, PR/branch, padrões). Um na raiz. Criar de `templates/AGENTS.md` se faltar.
- `CONTEXT.md` — aprendizados/decisões/armadilhas entre sessões. **Por escopo:** um na raiz e, quando útil, um dentro de uma pasta/app específico (info que só faz sentido ali). Criar de `templates/CONTEXT.md` se faltar. **Toda promoção de aprendizado durável vai pra cá** (no escopo certo); é o que faz o sistema se retroalimentar.
- `tmp-context.md` — aprendizado útil só **dentro da sessão**, que não vale guardar no repo. Não commitar (adicionar a `.gitignore` se necessário). Some ao fim da sessão.
- Todo subagente lê o(s) `CONTEXT.md` do escopo em que trabalha + o da raiz + `AGENTS.md` antes de começar.
