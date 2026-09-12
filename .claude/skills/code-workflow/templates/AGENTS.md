# AGENTS.md

> Operacional **durável** deste repo: como rodar, testar, acessar, contribuir. Lido por todo agente antes de trabalhar. **Enxuto** — status e progresso moram no plan ativo (`plans/PLAN_*.md`), não aqui. Capturar o **porquê** quando ajudar.

## Build & Run
- Instalar deps: `<comando>`
- Subir o projeto: `<comando>` (portas, serviços)
- Variáveis de ambiente necessárias: `<...>`

## Validation / Tests
- Testes da unidade alterada: `<comando>` (preferir alvo específico — suíte inteira costuma ser lenta)
- Lint / typecheck: `<comando>`
- E2E: `<comando>` (e pré-requisitos)
- Quirks conhecidos / ruído de baseline: `<...>`

## Acessos
- Auth necessária antes de rodar (ex.: cloud login): `<...>`
- Credenciais / segredos: onde ficam (nunca commitar)

## PR & Branch
- Branch a partir de: `<main/dev>` · nunca commitar na padrão
- Convenção de nome de branch: `<...>`
- Como abrir PR: `<...>` · contra qual base

## Codebase patterns
- Libs padrão (consolidar aqui): `<*/lib/*, packages/*>`
- Convenções de modelo/API/teste: `<...>`
