# REVIEW — passe adversarial / code-review

Roda ao fim do build (ou sob demanda como um dos loops de feedback). É um "agente" extra: tenta **provar que o trabalho está errado**, não confirmá-lo. Usar **`/ultrathink`** no julgamento adversarial dos achados.

**Modelo (dois tempos):** se a política de modelo por fase estiver ativa (opt-in no setup §0.6), a **execução** — lentes de review, verificação adversarial (refutar/reproduzir achados) — prefere `opus` (4.8). A **análise/julgamento** do compilado de achados (o que é real, severidade, o que vira item de plano) é do `fable`. Fallback: modelo da sessão. Ver SKILL.md §Modelo por fase.

## Como

1. Disparar subagentes de review em paralelo — usar `feature-dev:code-reviewer` para qualidade/bugs/segurança, e/ou subagentes adversariais com lentes distintas (correção, segurança, regra de negócio vs. spec, edge cases, reprodução).
2. Para achado de alta confiança, **verificar adversarialmente**: 2-3 subagentes tentam refutar o achado; maioria refuta → descartar. Sobrevive → é real.
3. **Filtrar por confiança** — reportar só o que importa (alta prioridade), não ruído.

## Saída

- Achados confirmados → **novos itens no plan ativo** (com severidade + spec violada), realimentando o loop BUILD.
- Padrão recorrente / armadilha → `CONTEXT.md`.
- Se o repo tem convenção de bugs (`bugs/`), seguir ela; senão, plano.

## Não

- Não "aprovar" sozinho trabalho que viola spec. Divergência da spec é achado, não detalhe.
- Não corrigir e revisar no mesmo subagente (quem escreveu não é juiz imparcial) — review é independente de quem buildou.
