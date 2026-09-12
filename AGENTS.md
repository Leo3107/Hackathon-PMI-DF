# AGENTS.md

> Operacional deste repositório. Todo agente lê antes de trabalhar.
> Status e progresso moram no plan ativo (`plans/PLAN_*.md`), **não aqui**.

## O que é este repo

**Lastro** — protótipo funcional de plataforma de inteligência de risco de crédito e prevenção
à inadimplência no agronegócio. Construído para o Hackathon PMI-DF 2026, desafio da **Krill Tech**.
Next.js 15 App Router + React 19 + TypeScript strict + Tailwind v4. Dados simulados.

**Antes de escrever qualquer código, leia `specs/README.md` e `specs/00-decisoes.md`.**
`00-decisoes.md` é autoritativo: em conflito entre specs, ele vence.

## Build & Run

- Instalar dependências: `npm install`
- Desenvolvimento: `npm run dev` → http://localhost:3000
- Build de produção: `npm run build`
- Servir o build: `npm start`

## Variáveis de ambiente

Copiar `.env.example` para `.env` e preencher. **`.env` está no `.gitignore` e nunca pode ser
versionado** — o remote deste repositório é público.

| Variável | Papel |
|---|---|
| `OPENAI_API_KEY` | Chave da camada LLM. **Lida apenas no servidor.** Jamais em `NEXT_PUBLIC_*`. |
| `LASTRO_LLM_MODEL` | Modelo. Padrão `gpt-5.4-mini`. |
| `LASTRO_LLM_ENABLED` | `false` desliga o LLM e cai no gerador determinístico. Kill switch de pitch. |
| `LASTRO_LLM_BUDGET_USD` | Teto rígido de gasto acumulado por processo. |

**Orçamento real do usuário: US$ 10.** Não gaste em testes automatizados — use as fixtures
descritas em `specs/04-camada-llm.md`. Chamada ao vivo é para a aplicação em uso, não para CI.

## Validação

- Typecheck: `npx tsc --noEmit`
- Lint: `npm run lint`
- Testes do motor de risco: `npx vitest run lib/scoring`
- Suíte completa: `npx vitest run`
- E2E: `npx playwright test`

Rodar sempre o alvo específico antes da suíte inteira.

## PR & Branch

- Branch a partir de `main`. **Nunca commitar direto na `main`.**
- Convenção: `feat/<escopo>`, `fix/<escopo>`.
- Remote público: `github.com/Leo3107/Hackathon-PMI-DF`. Nada de segredo em commit.

## Padrões de código

- **Idioma:** toda string de interface, rótulo, mensagem de erro e comentário em **português do Brasil**.
  Nomes de tipos, funções e variáveis também em português, conforme `specs/01-modelo-de-dados.md`.
- **`lib/scoring/` é função pura.** Sem I/O, sem `Date.now()`, sem `Math.random()`.
  A data de referência é sempre parâmetro explícito. É o que torna os testes determinísticos.
- **Nenhum número mágico.** Todo coeficiente do motor vive em `lib/scoring/config.ts`.
- **Nada de score, PD ou rating escrito à mão no mock.** O mock guarda só fatos brutos
  (`FatosDoCliente`); tudo o mais é derivado. Ver `specs/01-modelo-de-dados.md`.
- **O LLM nunca produz número.** Recebe valores já calculados e escreve prosa. Ver `specs/04-camada-llm.md`.
- Acesso a dado sempre via `RepositorioLastro` (assíncrono), nunca importando o mock direto na tela.
- Sem biblioteca de componentes de terceiros. O design system é próprio, em `components/ui/`.

## Estrutura

```
app/            rotas do App Router + route handlers da camada LLM
components/     ui/ (primitivos do design system) e por domínio
lib/
  scoring/      motor determinístico (puro, testado)
  llm/          NarrativeEngine: implementação OpenAI + fallback determinístico
  repository/   fronteira de dados, mock + localStorage de sessão
  format.ts     formatadores pt-BR de moeda, percentual, data, documento
data/           dataset simulado dos clientes
types/          contratos TypeScript
specs/          especificações — leia antes de codar
plans/          plan ativo da sessão
```
