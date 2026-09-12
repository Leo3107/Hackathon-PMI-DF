# Linear — subagente de progresso (sub-issues sob uma parent)

O Linear é o espaço onde o trabalho aparece e dá sensação de progresso. **Faz parte do fluxo — não é opcional.** **Sempre atualizado por subagente dedicado** — nunca pelo maestro diretamente (não travar o fluxo principal).

**Cadência: reconciliação a cada turno do BUILD** (ver `build.md` §Ciclo do maestro, passo 5) — não pontos fixos que dependem de o maestro lembrar. Ver §Reconciliação abaixo.

> **Causa comum de o Linear ser ignorado:** as ferramentas `mcp__linear-server__*` são **deferred** — o subagente precisa carregá-las com `ToolSearch` (`select:list_teams,list_issues,save_issue,save_comment,get_issue,list_comments`) **antes** de chamar. Carregar no setup e em cada subagente de Linear.

## Reconciliação (modo principal — todo turno do BUILD)

Um subagente, disparado **sempre**, sem condição prévia (não é "se algo relevante aconteceu" — o próprio subagente decide isso lendo o estado). Objetivo: ao final do turno, **Linear e plan ativo estão em paridade 1:1**. Prompt do subagente cobre:

1. Carregar as ferramentas `mcp__linear-server__*` via `ToolSearch`.
2. Ler o **plan ativo** inteiro (fonte da verdade) e a árvore de issues existentes sob a parent (`list_issues` recursivo).
3. Para cada nó do plano sem issue correspondente → **criar** (título = nó, `parentId` = issue do nó-pai; de cima para baixo).
4. Para cada nó cujo status mudou desde a última reconciliação (novo done, novo bloqueio, item reaberto por feedback) → **atualizar estado** (`Todo`/`In Progress`/`Done`) e **comentar** o que mudou (o que foi feito, branch, estado das dimensões de feedback, ou motivo do bloqueio).
5. Para nó removido do plano (escopo cortado) → fechar/cancelar a issue correspondente, comentando o motivo.
6. Se nada mudou desde o turno anterior: **não fazer nenhuma chamada de escrita** — só confirmar (retorno curto tipo "sem diff"). Barato, então não há motivo pra pular o turno "achando que não vale a pena checar".
7. Retornar ao maestro um resumo curto: quantas issues criadas/atualizadas/fechadas, e qualquer inconsistência que o subagente não conseguiu resolver sozinho (ex. issue duplicada, parent sumida) — isso vira item do plano se for bloqueante.

Como o subagente é sempre disparado (não gated por "o maestro lembrou"), a paridade não depende de nenhum humano ou do maestro identificar o evento certo — é aritmética de diff, todo turno.

## Escopo (regra dura)

- Toda sessão tem **1 parent issue** (definida no setup §0.5; usuário passa ou o maestro cria).
- O subagente cria/atualiza **somente sub-issues dentro dessa parent**. **Nunca** toca em issues fora desse escopo.
- Se a parent não existe: criar uma issue de escopo da sessão (título = escopo, descrição = link pras specs + objetivo) no time correto e usá-la como parent.

## Campos obrigatórios (regra dura)

Toda issue **criada ou atualizada** pelo workflow DEVE ter preenchidos: **estimate (pontuação), assignee (dono), project, milestone e cycle**. Derivação:
- **project / milestone** → herdar da parent issue da sessão.
- **cycle** → o cycle ativo do time.
- **assignee** → o usuário da sessão (dono do trabalho), salvo instrução contrária.
- **estimate** → heurística de esforço: S = 1–2, M = 3, L = 5–8 pontos.

Campo sem valor derivável **não fica vazio** — perguntar ao maestro/usuário antes de salvar.

Além dos campos, **toda issue criada ou atualizada DEVE ter uma descrição boa e completa** (não só título): **o que é**, **por que** existe, **critério de aceite / definition of done** (como saber que fechou) e **referência à spec de origem** quando houver (`specs/x.md §N`). Título isolado, sem descrição, não passa. Detalhe do formato em §Conteúdo de cada issue.

## Granularidade (regra)

**Criar o maior número possível de tasks** — no **mínimo uma por item** do plan ativo. Como o plano é hierárquico (workstreams → itens → subitens → sub-subitens; ver `plan.md`), **espelhar a hierarquia inteira** no Linear: cada nó vira uma issue, aninhada via `parentId` sob seu nó-pai.

```
parent da sessão
└─ WS1 (issue)
   └─ Item 1 (issue)
      ├─ 1.1 subitem (issue)
      │  └─ 1.1.1 sub-subitem (issue)
      └─ 1.2 subitem (issue)
```

Não agrupar itens distintos numa só task. Cada folha acionável do plano tem a sua.

## Quando disparar o subagente

- **A cada turno do maestro durante o BUILD** (`build.md` §Ciclo do maestro, passo 5) — a reconciliação acima. É o disparo **primário** e cobre todos os casos abaixo automaticamente, porque eles são só instâncias de "o plano mudou desde a última leitura":
  - fim do PLAN (primeira reconciliação: cria a hierarquia inteira);
  - item novo nascido de feedback/review;
  - item concluído (`Todo`→`In Progress`→`Done` + comentário de progresso);
  - bloqueio (comentário na issue);
  - item removido do plano (fecha/cancela a issue).
- Fora do BUILD (SPECS/FEEDBACK-DESIGN/PLAN/REVIEW), disparar pontualmente quando o evento acontece (ex. criar a parent no setup §0.5; espelhar a hierarquia ao fechar o PLAN) — esses momentos não têm o loop por turno do BUILD para carregar a reconciliação automaticamente.

## Como

Ferramentas `mcp__linear-server__*` (carregar via ToolSearch quando subagente). Fluxo, dentro da reconciliação (ou de um disparo pontual fora do BUILD):
1. `list_teams` / `get_issue` para localizar a parent e o time.
2. `list_issues` percorrendo a árvore (parent e descendentes) para ler issues existentes — **idempotente**: casar por título/caminho do nó, não duplicar; complementar/atualizar a que já existe.
3. `save_issue` com `parentId` para criar cada issue aninhada (criar de cima para baixo — pai antes do filho, para ter o `parentId`); `save_issue` para mudar estado; `save_comment`/`list_comments` para progresso.

## Conteúdo de cada issue

- **Título**: o nó do plan (curto, acionável).
- **Descrição**: spec de origem (`specs/x.md §N`), workstream, loop de feedback associado.
- **Comentários**: log de progresso por incremento — sinal sobre ruído, não copiar diff inteiro.

Mandar conteúdo direto, sem escapes (`\n` literal não — newline real).
