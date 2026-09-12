# Fase FEEDBACK-DESIGN — desenhar a matriz de feedback por feature

Roda **antes** do PLAN. Pergunta central: *dado o que as specs pedem, o que prova que cada feature atingiu o nível de qualidade alvo?* Sem isso, o build 1-shot não tem como saber se chegou lá. Usar **`/ultrathink`** ao pesar as dimensões.

**Modelo (dois tempos):** se a política de modelo por fase estiver ativa (opt-in no setup §0.6): o **desenho da matriz** (esta fase) prefere `fable`. As dimensões **mecânicas executadas durante o build** (unit, juízes de qualidade-IA, adversarial, benchmarks — tudo que roda, coleta e compila evidência) preferem `opus` (4.8). A **vivência como usuário** (entrar no sistema vivo via `/agent-browser` ou interface real, navegar, analisar o que a tela retorna, E2E ponta a ponta) prefere `fable` — ele faz o trabalho que o humano faria no loop, simulando o próprio usuário. A **análise do compilado** — ler as evidências e propor os próximos passos no plan/build — é do `fable` (maestro ou subagente-analista). Fallback: modelo da sessão. Ver SKILL.md §Modelo por fase.

## Regra não-negociável: vivenciar como usuário toda mudança que afeta a UX

**Se a mudança toca a experiência do usuário final — inclusive mudança de backend que muda algo que o usuário vê/sente (resposta de API, texto, latência percebida, ordem, estado, comportamento) — é OBRIGATÓRIO entrar no sistema vivo e testar como o próprio usuário faria**, simulando exatamente o fluxo dele, antes de dar a feature/item como fechado. Não basta teste unitário, "o endpoint retorna 200" ou raciocínio sobre o diff: **entra na interface rodando, faz o que o usuário faz, observa o resultado real e analisa.** Muitos bugs de UX (título cortado, seleção que não anda, layout que colide, cópia confusa) só aparecem vivendo a tela — nunca no código.

- **Como entrar, por tipo de interface:**
  - **Web / Electron (app com UI navegável):** usar **`/agent-browser`** na stack real — abrir, clicar, digitar, navegar como o usuário, tirar screenshot, ler o estado. É o caminho default para qualquer UI de navegador.
  - **Outra interface (TUI/CLI interativo, terminal, mobile, etc.):** **dirigir a interface real** do jeito que o usuário dirige (ex.: pty enviando teclas + emulador de terminal pra ler os frames de verdade; device/simulador no mobile). O princípio é o mesmo do agent-browser: operar a coisa viva, não simular na cabeça.
- **Simular fielmente:** reproduzir o gesto do usuário (segurar tecla = rajada, colar, redimensionar a janela, caminho de erro), não só o caminho feliz digitado devagar.
- **Analisar, não só rodar:** olhar o frame/tela final como o usuário olharia e julgar legibilidade, clareza e se o que aconteceu é o esperado — o achado vira item novo no plano (ver `build.md`).
- Essa dimensão (**"Vivência como usuário"** na tabela abaixo) entra na matriz de **toda feature com superfície de UX** e é **gate de fechamento** — a feature não vira `done` sem ela.

## Modelo: matriz por feature

Uma **feature** (capacidade coerente — em geral um workstream ou item de topo) raramente é validada por um único loop. O fluxo E2E tem de funcionar, **e** a resposta de IA tem de ser boa, **e** não pode haver bug em caso específico, **e** o visual tem de bater, **e** vivê-la como usuário tem de ser boa. Por isso cada feature carrega **várias dimensões de feedback ao mesmo tempo**, cada uma com critério/limiar próprio. **A feature só fecha quando TODAS as dimensões passam.**

## Processo

1. Reler as specs (foco nos **critérios de aceite**) e o `CONTEXT.md`.
2. Para cada feature, montar sua **matriz**: quais dimensões do catálogo se aplicam e quais **explicitamente não** (e por quê). Para cada dimensão que entra: como rodar, **limiar**, e **auto vs gated**.
3. Onde a dimensão for subjetiva (qualidade de IA), definir **rubrica + golden examples** — idealmente já na spec, para o juiz ter contra o que medir.
4. **Propor ao usuário e pedir sim/não** (`AskUserQuestion`): apresentar a matriz por feature — dimensões que entram (com limiar/auto-gated), as que ficaram de fora e por quê. Opções: **Confirmar**, **Ajustar**, **Revisar**. É o segundo (e último) toque humano. Só seguir com confirmação.
5. Após o sim, registrar a matriz **inline no plan ativo**, por feature (criar `plans/PLAN_AAAA-MM-DD_<slug>.md`; a fase PLAN preenche o resto). Durável → `CONTEXT.md`.

## Catálogo de dimensões (com como rodar)

| Dimensão | Quando entra | Como rodar / limiar |
|---|---|---|
| **Unit** | Lógica pura, regras de negócio | Testes da unidade alterada. Feature nova → escrever. Limiar: verde. |
| **Integração / E2E** | Fluxos ponta-a-ponta, endpoints, UI navegável | Playwright determinístico (rápido) ou `/agent-browser` (stack real). Limiar: verde; distinguir regressão de drift de fixture. |
| **Vivência como usuário** ⭐ | **Toda mudança que afeta a UX final — inclusive backend que muda o que o usuário percebe** | Entrar no sistema vivo e operar como o usuário (`/agent-browser` p/ web/Electron; dirigir a interface real — ex. pty+emulador — p/ TUI/CLI/mobile). Simular o gesto real (rajada de tecla, colar, resize, caminho de erro). **Analisar o frame final como o usuário olharia.** Limiar: fluxo do usuário funciona e a tela está legível/clara. **Gate de fechamento.** Modelo preferido: `fable` (simula o próprio usuário). Ver §Regra não-negociável. |
| **Lint / typecheck / build** | Sempre (barato) | A cada incremento. Limiar: 0 erro. |
| **Qualidade de IA** | Saída de modelo que precisa ser **boa** (chat, geração, avaliação) | **LLM-as-judge**: subagente juiz pontua a saída contra **rubrica** (definida na spec) + golden examples. **SEMPRE rodar o juiz num subagente Claude** (Agent tool `subagent_type: "claude"` ou `model` Claude) — nunca outro modelo; preferir `model: "opus"` (execução de feedback). **Painel de 2-3 juízes com lentes distintas** (correção, tom, aderência à spec) pra reduzir falso-positivo. Limiar: ex. ≥4/5 e maioria do painel. O compilado dos veredictos vai pro `fable` analisar e decidir os próximos passos. Abaixo do limiar → reabre item. |
| **Edge-case adversarial** | Bug que só aparece em caso específico | Subagentes adversariais **geram casos extremos** (inputs ambíguos/maliciosos/limítrofes) a cada incremento + property/fuzz onde couber. Preferir `model: "opus"` (execução). Limiar: 0 quebra. Cada bug achado **vira item novo no plano**. |
| **Diff visual** | UI com alvo claro (Figma/mock/print) | Subagente de visão compara screenshot do implementado vs. alvo; reporta divergências (espaçamento, cor, layout). Limiar: diff aprovado. Iterar até casar. |
| **Maximização de métrica** | ML/ranking — maximizar algo | Harness de avaliação + **baseline** + **alvo**. Limiar: não regredir e tender ao alvo. |
| **Benchmark de performance** | Restrição de latência/throughput/custo | Medir contra limiar; regressão acima bloqueia. |
| **Aceitação manual** | Qualidade subjetiva que nenhum automático pega | **Gated**: apresentar evidência (screenshots/saída) ao humano ao fechar a feature. |

## Cadência (executa no build)

- **Dimensões automatizáveis** (unit, E2E, lint/typecheck, diff visual, qualidade-IA, adversarial/fuzz, métrica, benchmark) rodam **a cada incremento** da feature — via subagentes em paralelo, não-bloqueantes.
- **Vivência como usuário** roda ao **fechar cada feature com superfície de UX** (e sempre que um incremento mudar visivelmente a tela) — é gate obrigatório, não pode ser pulada porque "é só backend".
- **Dimensões gated** (aceite humano) rodam ao **fechar a feature**.
- **Feature só vira `done` quando todas as dimensões passam o limiar.** Qualquer falha → **item novo no plano ativo** (ver `build.md` §Condição de parada).

## Saída (inline no plan ativo, por feature)

```markdown
### WS2 · Chat de dúvida — feedback matrix
- [auto] E2E Playwright — abre/responde/persiste · limiar: verde
- [auto] qualidade-IA — judge vs rubrica specs/chat.md §4 · limiar: ≥4/5, painel 2/3
- [auto] adversarial edge-case — prompts ambíguos/limítrofes · limiar: 0 quebra
- [auto] lint/typecheck · limiar: 0 erro
- [gate] vivência como usuário — /agent-browser: abre o chat, manda dúvida real, lê a resposta na tela · limiar: fluxo ok + tela legível
- [gated] aceite humano — amostra ao fechar
- fora: diff visual (sem UI nova), métrica (não-ML)
Feature done = todas as [auto]+[gated] acima no limiar.
```

Confirmado o sim/não, seguir para PLAN.
