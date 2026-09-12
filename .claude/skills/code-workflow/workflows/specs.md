# Fase SPECS — clareza total antes de qualquer código

Objetivo: extrair **tudo** que é preciso para construção clara e completa — regras de negócio, Jobs to Be Done, restrições, e pontos concretos de implementação. Esta é a fase mais importante do fluxo 1-shot: o que não ficar claro aqui vira retrabalho depois.

**Modelo:** se a política de modelo por fase estiver ativa (opt-in no setup §0.6), o grill/discussão/escrita da spec é do `fable` (maestro); subagentes de **pesquisa de código** desta fase preferem `opus` (4.8) — o Fable orienta o que buscar e analisa o que voltou. Fallback: modelo da sessão. Ver SKILL.md §Modelo por fase.

## Conduta

1. **Grill implacável e EXTENSO** (usar **`/grilling`**) — esta é a alma da fase. Entrevistar o usuário descendo **cada ramo** da árvore de decisão, resolvendo dependências uma a uma, até **clareza total**. Isso são **VÁRIAS RODADAS** de `AskUserQuestion` em **múltiplos turnos** — não pare na primeira rodada. **Priorizar profundidade:** quando uma decisão tem dependências (a resposta muda as próximas perguntas), fazer **uma pergunta por vez** e esperar; só compilar (até 4) perguntas **ortogonais** entre si, que não dependem uma da resposta da outra. Na dúvida entre profundidade e velocidade, escolher profundidade. Para cada pergunta, **ofereça sua resposta recomendada**. Cobrir todas as dimensões: **produto, UX/UI, regras de negócio, dados/contratos, edge cases, não-objetivos, sequência/escopo**.
   - **Anti-padrão (proibido):** escrever as specs após pouquíssimas perguntas assumindo o resto. Descoberta no código **substitui** perguntas *factuais* (o que existe, contratos, reuso), **não** substitui os **forks de produto/decisão** — esses são do usuário. Se você se pegar escrevendo uma seção "Suposições" longa, **cada suposição não-trivial era uma pergunta que você deixou de fazer** — volte e pergunte.
   - **Caçar gaps ativamente:** antes de fechar, liste o que ainda está ambíguo/faltando (produto, UX, técnico, edge case) e **pergunte** — não pare enquanto houver decisão do usuário em aberto. Regra prática: só saia do grill quando a próxima pergunta seria respondível por você sozinho sem risco de retrabalho.
   - **Não empurrar o escopo de volta é um erro:** se o pedido é grande, **questione o fatiamento/sequência** explicitamente em vez de assumir "faço tudo".
2. **Pergunta respondível pelo código → não pergunte: investigue.** Disparar subagentes de pesquisa (read-only, em paralelo) para mapear o código existente, padrões, libs e o que já está implementado. Não assumir que algo falta — confirmar com busca. Ver `orchestration.md`.
3. **JTBD, não implementação atual.** Focar no que o usuário precisa alcançar, não em como está hoje.
4. **Resumir entendimento** e **analisar criticamente os gaps** — de produto **e** de UX/UI — antes de escrever.
5. **Quebrar em Topics of Concern atômicos** → escrever/atualizar `specs/<topic>.md`. Se o repo não tem `specs/`, criar a pasta + `specs/README.md` (índice).
6. **Sondar o feedback.** Ao longo do discovery, ir mapeando — a partir dos critérios de aceite — quais tipos de feedback (ver `feedback.md`) fazem sentido para esta sessão e quais claramente **não** fazem, para já chegar na fase FEEDBACK-DESIGN com uma proposta pronta para o sim/não do usuário.

## O que cada spec captura

- **Regras de negócio** e invariantes (o que sempre tem de valer).
- **JTBD / fluxos** do usuário.
- **Critérios de aceite** — como saber que está pronto e correto (isso alimenta direto a fase FEEDBACK-DESIGN).
- **Pontos de implementação** conhecidos: integrações, contratos de dados, libs, restrições técnicas.
- **Decisões em aberto e suposições** assumidas.

## Checkpoint obrigatório (único do fluxo)

**Antes de escrever as specs, auto-check:** *"Fiz rodadas suficientes de grill? Sobrou alguma decisão de produto que assumi em vez de perguntar?"* Se sim → **volte a perguntar** antes de escrever. Specs escritas cedo demais, com poucas perguntas, são o erro mais caro do fluxo.

Após escrever/atualizar, **PARAR** e apresentar:
1. **Lista dos arquivos** criados/modificados em `specs/` (caminho completo).
2. **Resumo por arquivo** — 2-3 bullets.
3. **Pontos de atenção** — decisões em aberto, suposições, conflitos com specs existentes.
4. `AskUserQuestion`: "Specs prontas para revisão. Como prosseguir?"
   - **Aprovado, seguir para FEEDBACK-DESIGN**
   - **Ajustar pontos específicos**
   - **Revisar agora** (usuário lê e volta — aguardar)
   - **Voltar à entrevista** (faltou algo)

**NUNCA** avançar sem aprovação explícita. Aplicar ajustes e voltar ao checkpoint até aprovar. Depois deste ponto, o fluxo é autônomo.
