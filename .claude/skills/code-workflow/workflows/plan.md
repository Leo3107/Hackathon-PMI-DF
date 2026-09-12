# Fase PLAN — plano particionado em workstreams paralelizáveis

Autônoma (sem checkpoint). **Apenas planejar — não implementar.** Usar **`/ultraplan`** para o planejamento profundo, e **`/ultrathink`** nas decisões de arquitetura mais difíceis.

**Modelo:** se a política de modelo por fase estiver ativa (opt-in no setup §0.6), a escrita/decisão do plano é do `fable` (maestro); subagentes de **pesquisa de código** preferem `opus` (4.8) — o Fable orienta o que investigar e planeja em cima do que voltou. Fallback: modelo da sessão. Ver SKILL.md §Modelo por fase.

## Processo

1. Estudar o **código real** de cada camada (subagentes de pesquisa em paralelo) e comparar contra as specs. **Não assumir que algo falta — confirmar com busca.**
2. Tratar as libs compartilhadas do repo (`*/lib/*`, `packages/*`, `common/*` — o que o repo usar) como bibliotecas padrão; preferir consolidar lá.
3. Quebrar o trabalho em **workstreams independentes** — esse é o ponto-chave para o build paralelo. Cada workstream:
   - tem **fronteira de dono** clara (arquivos/módulos que só ele toca) para minimizar conflito entre subagentes;
   - cita a **spec de origem** e o **loop de feedback** que o valida (da fase anterior);
   - declara **dependências** de outros workstreams (o que precisa estar pronto antes).
   - workstreams que tocam árvore compartilhada → marcar para **git worktree** no build.

## Artefato único: o plan ativo

Um só arquivo: **`plans/PLAN_AAAA-MM-DD_<slug>.md`** desta sessão. Ele **é** o plan ativo — editado continuamente durante o build (marcar done, adicionar itens descobertos, limpar concluídos quando crescer). **Não há plan ativo fora de `plans/`.** Plans de sessões antigas são history — não editar; sessão que retoma cria novo arquivo referenciando o antigo no topo.

## Detalhar ao máximo (hierarquia)

O plano tem de ser **bem detalhado**: cada workstream se quebra em **itens**, itens em **subitens** e, quando preciso, **sub-subitens** — até cada folha ser uma unidade pequena, acionável e validável por um feedback. Quanto mais granular, melhor o paralelismo e o espelhamento no Linear (uma task por nó — ver `linear.md`). Não deixar item vago tipo "implementar o módulo X"; quebrar no que de fato vira commit.

Cada **feature** (em geral um workstream ou item de topo) carrega sua **matriz de feedback** inline (vinda da fase anterior) — várias dimensões, cada uma com limiar; a feature só fecha quando todas passam.

Estrutura (ver convenções no `SKILL.md`):
```markdown
# Plan — <título>
Data: AAAA-MM-DD · Escopo: <frase> · Parent Linear: <id>
## Workstreams
- WS1 <nome> · dono: src/api/foo/* · dep: —
- WS2 <nome> · dono: src/frontend/bar/* · dep: WS1
## Itens (hierárquicos, granulares)
- [ ] (WS1) Item 1 — spec: specs/x.md §2
  - [ ] 1.1 subitem — spec: §2.1
    - [ ] 1.1.1 sub-subitem (folha acionável)
  - [ ] 1.2 subitem
- [ ] (WS1) Item 2
## Feedback matrix (por feature)
### WS1 — feedback matrix
- [auto] unit · limiar: verde
- [auto] lint/typecheck · limiar: 0 erro
- [auto] adversarial edge-case · limiar: 0 quebra
### WS2 — feedback matrix
- [auto] E2E · [auto] diff visual · [auto] qualidade-IA (rubrica §4) · [gated] aceite humano
## Decisões da sessão
## Execution log
```

## Espelhar no Linear

Ao terminar o plano, **disparar subagente Linear** (`linear.md`) para criar as sub-issues dos workstreams/itens sob a parent da sessão. Não-bloqueante — seguir para BUILD enquanto o subagente escreve.

Sem checkpoint humano — seguir direto para BUILD.
