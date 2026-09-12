# Fase BUILD — loop fechado, execução paralela

Autônoma, em loop, até o **plan ativo** esvaziar. O maestro **fan-out → integra** (ver `orchestration.md`); não implementa workstream grande sozinho quando pode paralelizar.

**Modelo:** se a política de modelo por fase estiver ativa (opt-in no setup §0.6), subagentes de **implementação** de workstream preferem `opus` (4.8), e os de **execução de feedback** dentro do loop (matriz da feature, adversarial, navegação, testes) **também `opus`** — Opus roda e compila as evidências. O **`fable`** entra depois, no papel de engenheiro sênior: analisa o compilado de evidências de cada rodada e **propõe os próximos passos no plan/build** (itens novos, reaberturas, ajustes de rota). Fallback em ambos: modelo da sessão. Ver SKILL.md §Modelo por fase.

**Pipeline, não batch.** Nunca esperar todos os subagentes de build terminarem para começar a validar. **Assim que um workstream retorna, disparar imediatamente seus agentes de feedback sobre aquela entrega** — enquanto os outros workstreams ainda estão construindo. A meta é manter a fila sempre cheia: a todo momento, **uns agentes implementando e outros validando em paralelo**, nunca uma fase ociosa esperando a outra. (Workflow tool: `pipeline()`, sem barreira entre os estágios build→feedback — ver `orchestration.md §Ferramenta`.)

## Ciclo do maestro

1. Ler o **plan ativo** (`plans/PLAN_*.md` da sessão), `CONTEXT.md`, `AGENTS.md`. Selecionar os workstreams **prontos** (dependências satisfeitas).
2. **Despachar subagentes em paralelo** — um por workstream independente (worktree se tocam árvore compartilhada). Adiantar pesquisa/arquitetura do que vem a seguir com outros subagentes enquanto estes constroem.
3. Cada subagente entrega o workstream pelo **ciclo fechado**:
   implementar → **rodar a matriz de feedback da feature** (dimensões `[auto]` em paralelo a cada incremento; corrigir até cada uma passar o limiar) → atualizar o **plan ativo** (done + novos itens descobertos) → commit em branch descritiva. A feature só fecha quando **todas** as dimensões da matriz passam (as `[gated]`, ao fechar a feature). O subagente **não** mexe no Linear diretamente — isso é responsabilidade do passo 5, centralizado.
4. **Integrar à medida que cada workstream fecha** (não em lote): resolver conflitos, mesclar branches/worktrees, e **re-rodar o feedback no todo integrado** (subagente) — paralelismo pode introduzir regressão que o feedback por-workstream não pega. O feedback de um workstream que já retornou roda em paralelo à implementação dos que ainda estão em curso.
5. **Reconciliar Linear — mecânico, todo turno, sem exceção** (ver `linear.md` §Reconciliação): disparar **um** subagente de Linear que compara o **plan ativo pós-integração** contra a árvore de issues sob a parent e resolve o diff inteiro numa passada (cria nó novo, move estado, comenta progresso/bloqueio). Não-bloqueante — o maestro segue pro passo 6 sem esperar a confirmação, mas **dispara sempre**, mesmo quando "nada mudou" neste turno (o subagente confirma isso rápido e barato). Isso substitui depender do maestro lembrar de disparar em eventos pontuais — a cadência é o próprio turno do loop.
6. Promover aprendizado durável → `CONTEXT.md` do escopo certo; operacional → `AGENTS.md` (enxuto); intra-sessão → `tmp-context.md` (não commitado). Atualizar o `## Execution log` do plan ativo.
7. Repetir até o plan ativo estar **inteiramente fechado** (zero itens acionáveis). Então rodar **REVIEW** (`review.md`) — e os achados do review viram novos itens, que também entram no loop. **Antes de encerrar a sessão**, garantir uma última reconciliação (passo 5) com o plano no estado final.

## Condição de parada (regra dura)

A iteração só para quando o plan ativo está **completamente fechado** — **todos** os workstreams, **todos** os itens, e **todos** os itens que surgiram via feedback/review implementados e validados. Não parar com plano pela metade.

- **Todo achado de feedback retroalimenta o plano.** Falha de teste, divergência de diff visual, métrica abaixo do alvo, refutação adversarial, achado de review, bug colateral — vira **item novo no plan ativo** (não some, não fica só "anotado"). Itens novos têm de ser implementados e revalidados como qualquer outro.
- Um item só é marcado done quando seu **loop de feedback passou o limiar**. Limiar não batido → reabrir o item, não fechar.
- Implementar **tudo**, completo — nada de placeholder/stub/"fica pra depois". Se o escopo for grande demais para uma sessão, isso é decisão humana explícita (voltar ao usuário), não um corte silencioso do loop.

## Feedback de teste manual → reentra por SPECS+PLAN (nunca direto no build)

Quando o usuário está **testando um ambiente vivo** (mock/preview/staging que o maestro sobe pra ele) e propõe **pontos de ajuste** (mudança de comportamento, UX, regra, copy), esses pontos **não viram item de build direto**. Cada ponto reentra pelo início do fluxo — um **mini-ciclo SPECS→PLAN rodado via subagents** — antes de virar trabalho. Isso preserva a rastreabilidade `spec → plan → build → feedback` e evita que ajuste dito no calor do teste vire código sem spec.

Protocolo por ponto (ou por lote de pontos disjuntos — compilar quando possível):

1. **Capturar verbatim** o ponto do usuário (no repo/arquivo de feedback verbatim ligado à spec — rastreabilidade).
2. **Subagente SPECS** (prefere `fable` se a política estiver ativa): discovery mínimo do ponto (grill enxuto **só** se ambíguo — senão não incomodar o usuário), localiza a spec relevante em `specs/` e **ajusta/expande a spec existente** com o novo requisito + critério de aceite. Só cria spec nova se o ponto não couber em nenhuma. Retorno: qual spec mudou e o quê.
3. **Subagente PLAN** (prefere `fable`): traduz o requisito ajustado na spec em **itens novos no plan ativo** (workstream/item/subitem), cada nó citando a **spec de origem** + a **dimensão de feedback** que o valida; particiona pra **não conflitar** com workstreams em voo (worktree se preciso). Retorno: itens adicionados ao plan.
4. Só então o item entra no **loop de BUILD** normal (fan-out → matriz de feedback → integra).

Pontos que tocam specs/áreas **disjuntas** disparam seus mini-ciclos **em paralelo**. Um ponto que **invalida uma spec aprovada** (não só refina) é o único caso que volta ao usuário como decisão, não como ajuste. O maestro não bloqueia: enquanto os subagents de spec/plan rodam por um ponto, os workstreams de build já despachados seguem.

## Linear (obrigatório — mecânico, não depende de lembrar)

O Linear **faz parte do ciclo**, não é opcional. Modelo antigo (disparar em "pontos fixos" que o maestro precisa lembrar) falha na prática — itens ficam sem sub-issue, dones sem mover de coluna. Modelo atual: **passo 5 do ciclo do maestro dispara a reconciliação a cada turno**, incondicionalmente — não é um checklist de eventos, é parte estrutural do loop. Detalhe do que a reconciliação cobre em `linear.md` §Reconciliação.

**As ferramentas `mcp__linear-server__*` são deferred** — o subagente de reconciliação precisa carregá-las com `ToolSearch` (`select:list_teams,list_issues,save_issue,save_comment,get_issue,list_comments`) antes de chamar. Não pular o Linear por elas não estarem à mão: carregue-as. Se o maestro perceber que um turno passou sem disparar o passo 5, isso é uma falha do ciclo — reconciliar imediatamente antes de seguir, não esperar o próximo turno.

## Regras de cada incremento (do subagente)

- Implementar pelo item de **maior prioridade** do seu workstream. Antes de declarar "não implementado", **buscar no código**.
- **Feedback é obrigatório**: rodar as dimensões da **matriz da feature** (do plan ativo); corrigir até cada uma passar o limiar. Só pular se o usuário pedir explicitamente (registrar verificação pendente no plano).
- Rodar **feedback não-bloqueante em subagente** quando for caro (e2e completo, diff visual, adversarial) para o maestro seguir; bloquear só no que é barato e local (unit/lint).
- Seguir convenções de teste/lint do repo (`AGENTS.md`). Para endpoint/feature novo, escrever testes.
- **Single source of truth, sem migrations/adapters paralelos.** Se teste alheio quebrar por causa do incremento, resolver como parte dele.
- **Implementar completo** — nada de placeholder/stub. Deletar código morto.
- **Nunca commitar na branch padrão.** Trabalhar na branch descritiva criada no setup (a partir da main atualizada) → commit → push. Criar tag (patch +1; começar `0.0.1`) quando build/tests passarem. Considerar **todos** os repos detectados no setup.

## Documentação

- **Plan ativo** sempre atual (futuro trabalho depende disso para não duplicar).
- Ao aprender a rodar/testar algo (comando que custou acertar) → `AGENTS.md`, breve.
- `AGENTS.md` operacional only — status mora no plan ativo. Inflar `AGENTS.md` polui todo loop futuro.
- Capturar o **porquê** ao documentar (teste e importância da implementação).
