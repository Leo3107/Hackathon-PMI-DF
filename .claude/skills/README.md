# Skills do Claude Code

Cópia das skills pessoais usadas localmente, versionadas aqui para uso em outras máquinas.

## Skills incluídas

| Skill | Para quê |
|---|---|
| `agent-browser` | Automação de browser via CLI (navegar, preencher forms, screenshots, scraping, QA). |
| `clone-website` | Engenharia reversa / clone pixel-perfect de sites, com builders em paralelo. |
| `code-workflow` | Orquestrador spec-driven: SPECS → FEEDBACK → PLAN → BUILD ⇄ FEEDBACK → REVIEW. |
| `design-taste-frontend` | Frontend anti-slop para landing pages, portfólios e redesigns. |
| `llm-council` | Conselho de 5 advisors que analisam, revisam entre si e sintetizam um veredito. |
| `thermo-nuclear-code-quality-review` | Review de manutenibilidade extremamente rigoroso. |

## Usar em outra máquina

**Só neste projeto** — já funciona: o Claude Code lê `.claude/skills/` do repositório.

**Globalmente (todos os projetos)** — copie para o diretório de skills do usuário:

```bash
# Linux / macOS
cp -r .claude/skills/* ~/.claude/skills/

# Windows (PowerShell)
Copy-Item .claude\skills\* $HOME\.claude\skills\ -Recurse
```

Reinicie o Claude Code e confirme com `/skills`.

## Não estão aqui (e por quê)

- **`code-review` e `security-review`** — são skills *built-in* do Claude Code, compiladas no binário. Já vêm instaladas em qualquer máquina, não há arquivo para copiar.
- **`frontend-design`** — vem do plugin oficial. Instale com:
  ```
  /plugin install frontend-design@claude-plugins-official
  ```
- **`caveman`** — plugin de terceiros (tem hooks, não funciona só copiando arquivo):
  ```
  /plugin marketplace add https://github.com/juliusbrussee/caveman.git
  /plugin install caveman@caveman
  ```
