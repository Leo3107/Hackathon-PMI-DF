# Plan — Lastro · protótipo de inteligência de risco de crédito no agronegócio

Data: 2026-09-12 · Escopo: construir de ponta a ponta o protótipo funcional do Lastro para o
pitch do Hackathon PMI-DF 2026 (desafio Krill Tech) · Parent Linear: não usado (decisão do usuário)

Specs: [`specs/README.md`](../specs/README.md) · Modo de execução: **autônomo até a entrega**,
por decisão explícita do usuário — sem checkpoints intermediários; commit e push ao final.

---

## Objetivos

1. Uma aplicação que responde, em 30 segundos de olhar, **quem está em risco, quanto dinheiro
   está em risco, por quê, o que mudou, o que fazer e qual a evidência**.
2. Números que **fecham**: decomposição que soma, deltas que reconstroem a variação, PD coerente.
3. Camada de IA real, mas que **nunca inventa número** e nunca trava a interface.
4. O Project Canvas — entregável oficial do edital — vivo dentro do produto.
5. Rodar sem sobressalto no dia do pitch, mesmo com rede ruim ou API fora.

## Arquitetura

```
web/  Next.js 16 + React 19 + Tailwind v4   interface, proxy server-side, sem lógica de risco
api/  Flask 3 + pydantic 2 + openai         motor determinístico, dataset, camada de linguagem
```

## Workstreams

| WS | Nome | Dono (fronteira de escrita) | Depende de |
|---|---|---|---|
| **WS1** | Modelos + motor de risco + testes | `api/models/**`, `api/scoring/**`, `api/tests/**`, `web/types/**` | — |
| **WS2** | Dataset simulado dos 18 clientes | `api/data/**` | spec 06 · tipos do WS1 |
| **WS3** | API Flask: rotas, serialização, repositório | `api/app.py`, `api/routes/**`, `api/repository/**` | WS1, WS2 |
| **WS4** | Camada de linguagem: Sintetizador + Copiloto | `api/llm/**` | spec 04 · WS1 |
| **WS5** | Design system e formatadores | `web/app/globals.css`, `web/components/ui/**`, `web/lib/format.ts` | spec 05 |
| **WS6** | Shell, navegação, cliente de API, proxy | `web/app/layout.tsx`, `web/app/api/**`, `web/lib/api.ts`, `web/components/shell/**` | WS5 |
| **WS7** | Carteira e lista de clientes | `web/app/carteira/**`, `web/app/clientes/page.tsx`, `web/components/carteira/**` | WS5, WS6, WS3 |
| **WS8** | Página detalhada do cliente | `web/app/clientes/[id]/**`, `web/components/cliente/**` | WS5, WS6, WS3, WS4 |
| **WS9** | Nova análise, alertas, auditoria | `web/app/nova-analise/**`, `web/app/alertas/**`, `web/app/auditoria/**` | WS5, WS6, WS3 |
| **WS10** | Canvas, Arquitetura, Parecer imprimível | `web/app/canvas/**`, `web/app/arquitetura/**`, `web/app/parecer/**` | spec 07 · WS5 |

Nenhum par de workstreams escreve no mesmo arquivo. Por isso rodam em paralelo sem worktree.

## Ordem de disparo

```
onda 1  WS1 ────────────────────────────┐
onda 2  WS5 · WS2 · WS4 ────────────────┤ (assim que as specs 05/06/04 caírem)
onda 3  WS3 · WS6 ──────────────────────┤
onda 4  WS7 · WS8 · WS9 · WS10 ─────────┘
onda 5  integração, feedback vivencial, correção, commit, push
```

## Itens

### WS1 · Modelos + motor
- [ ] 1.1 Modelos pydantic espelhando `specs/01` com alias camelCase na serialização
- [ ] 1.2 Tipos TypeScript equivalentes em `web/types/`
- [ ] 1.3 `config.py` com todos os coeficientes — zero número mágico nas funções
- [ ] 1.4 Featurizers das 7 dimensões, todos os fatores da §4 da spec 02
- [ ] 1.5 Agregação por dimensão com clamp e marcação de saturação
- [ ] 1.6 Score ponderado, rating e redistribuição de saturação (fecha a invariante I2)
- [ ] 1.7 PD 6/12/24 e risco de RJ, incluindo elegibilidade da Lei 14.112/2020
- [ ] 1.8 Os oito gatilhos de veto, preservando `scoreCalculado`
- [ ] 1.9 Exposição, garantias, coberturas e `exposicaoEmRiscoEmRJ`
- [ ] 1.10 Stay Period
- [ ] 1.11 Red flags derivadas dos mesmos fatores
- [ ] 1.12 Árvore de recomendação com ações parametrizadas pelos números do cliente
- [ ] 1.13 Motor de delta ("por que o score mudou") — fecha a invariante I6
- [ ] 1.14 Suíte pytest cobrindo I1 a I6, determinismo, vetos, coberturas e contrato JSON

### WS2 · Dataset
- [ ] 2.1 Os 18 clientes com fatos brutos coerentes, cobrindo todas as personas exigidas
- [ ] 2.2 Invariante I5: caso de PD moderado com RJ alto e caso de PD alto com RJ baixo
- [ ] 2.3 Snapshots históricos por cliente, com a narrativa de queda 712 → 604 reproduzida
- [ ] 2.4 Eventos e alertas derivados, com as quatro severidades representadas
- [ ] 2.5 Evidências distribuídas pelas 14 fontes previstas, todas marcadas como simuladas
- [ ] 2.6 Prospects consultáveis pelo fluxo de due diligence
- [ ] 2.7 Varredura de contradições nos dados

### WS3 · API
- [ ] 3.1 Fábrica de aplicação Flask, blueprints, healthcheck
- [ ] 3.2 Repositório sobre o dataset, com a interface de `specs/01`
- [ ] 3.3 Rotas de clientes, carteira, avaliação, histórico, eventos, alertas, auditoria
- [ ] 3.4 Rota de due diligence por documento
- [ ] 3.5 Rota de simulação de evento (recálculo real)
- [ ] 3.6 Serialização com as chaves exatas do contrato TypeScript
- [ ] 3.7 Tratamento de erro uniforme e códigos de status corretos

### WS4 · Camada de linguagem
- [ ] 4.1 Interface `NarrativeEngine` e implementação determinística de fallback
- [ ] 4.2 Implementação OpenAI com streaming e `gpt-5.4-mini`
- [ ] 4.3 Serialização econômica do contexto de avaliação para o prompt
- [ ] 4.4 As quatro tarefas: parecer, explicação do score, explicação da recomendação, copiloto
- [ ] 4.5 Contabilização de tokens, custo acumulado e teto rígido
- [ ] 4.6 Kill switch por variável de ambiente e degradação por falha ou timeout
- [ ] 4.7 Fixtures para teste sem consumir cota
- [ ] 4.8 Guardas anti-alucinação e recusa fora de escopo no copiloto

### WS5 · Design system
- [ ] 5.1 Tokens de superfície, borda, texto e acento em `globals.css`
- [ ] 5.2 Paleta semântica de risco com contraste verificado ≥ 4.5:1
- [ ] 5.3 Escala tipográfica e numeração tabular nas colunas financeiras
- [ ] 5.4 Catálogo de primitivos
- [ ] 5.5 `ScoreGauge` autoral em SVG, com faixas de rating e tratamento de veto
- [ ] 5.6 Estilo de gráficos Recharts integrado ao sistema
- [ ] 5.7 Formatadores pt-BR de moeda, percentual, data e documento
- [ ] 5.8 Print stylesheet

### WS6 · Shell
- [ ] 6.1 Layout raiz, navegação persistente, banner de dados simulados
- [ ] 6.2 Cliente de API tipado e route handlers de proxy, inclusive repasse de stream
- [ ] 6.3 Identidade do analista e contador de custo do LLM
- [ ] 6.4 Estado de API indisponível, claro e acionável
- [ ] 6.5 Controle "Simular evento de monitoramento"
- [ ] 6.6 Persistência de sessão em `localStorage` e ação de restaurar a demonstração

### WS7 · Carteira e lista
- [ ] 7.1 KPIs de topo
- [ ] 7.2 Faixa de atenção imediata
- [ ] 7.3 Visualizações de concentração e distribuição por rating
- [ ] 7.4 Tabela de clientes com todas as colunas exigidas
- [ ] 7.5 Filtros, busca e ordenação
- [ ] 7.6 Estados de carregamento, vazio e erro

### WS8 · Página do cliente
- [ ] 8.1 Cabeçalho e identidade
- [ ] 8.2 Score, rating, tendência, variação e exibição de veto lado a lado
- [ ] 8.3 PD nos três horizontes e risco de RJ como indicador separado
- [ ] 8.4 Recomendação com ações e aviso de decisão humana
- [ ] 8.5 "Por que este score?" com fatores de risco e de proteção e seus impactos
- [ ] 8.6 Decomposição por dimensão
- [ ] 8.7 Red flags
- [ ] 8.8 Exposição e garantias, com extraconcursal versus concursal e exposição em risco em RJ
- [ ] 8.9 Painel de Stay Period quando aplicável
- [ ] 8.10 Linha do tempo com score e eventos
- [ ] 8.11 Fontes e evidências
- [ ] 8.12 Copiloto de análise
- [ ] 8.13 Decisão do analista com justificativa

### WS9 · Due diligence, alertas, auditoria
- [ ] 9.1 Fluxo de nova análise com pipeline visual dos estágios reais
- [ ] 9.2 Perfis demonstrativos e tratamento de documento desconhecido
- [ ] 9.3 Central de alertas por severidade
- [ ] 9.4 Trilha de auditoria com destaque de divergência entre recomendação e decisão

### WS10 · Canvas, arquitetura, parecer
- [ ] 10.1 Project Canvas com os 10 blocos do edital, em uma página
- [ ] 10.2 Aba de arquitetura separando ML quantitativo de LLM
- [ ] 10.3 Parecer imprimível e exportação em PDF

---

## Matriz de feedback por workstream

### WS1 — motor de risco
- [auto] pytest das invariantes I1–I6 · limiar: verde, zero falha
- [auto] determinismo — mesma entrada, saída idêntica · limiar: igualdade exata
- [auto] varredura numérica de monotonicidade de PD · limiar: zero violação
- [auto] adversarial — entradas limítrofes: exposição zero, divisão por zero, datas invertidas,
  valores negativos, cliente sem garantia, cliente sem operação · limiar: zero exceção não tratada
- fora: diff visual, vivência (não tem superfície de UX)

### WS2 — dataset
- [auto] validação pydantic de todos os registros · limiar: zero erro
- [auto] varredura de contradições lógicas (litígio versus `semLitigio36m`, CNDT versus certidões
  negativas, atraso versus pontualidade) · limiar: zero contradição
- [auto] plausibilidade financeira: exposição por hectare dentro de faixa, garantia compatível
  com o bem, patrimônio compatível com exposição · limiar: revisão aprovada por juiz
- [auto] cobertura de personas e invariante I5 · limiar: todas presentes

### WS3 — API
- [auto] teste de contrato: chaves do JSON batem com `web/types/` · limiar: zero divergência
- [auto] smoke de todas as rotas · limiar: 200 e corpo válido
- [auto] adversarial: id inexistente, documento malformado, payload vazio · limiar: erro tratado

### WS4 — camada de linguagem
- [auto] fidelidade numérica: juiz confere cada número do texto gerado contra a entrada ·
  limiar: zero número inventado ou alterado — **falha aqui é severidade máxima**
- [auto] qualidade do parecer: painel de juízes contra a rubrica da spec 04 · limiar: ≥ 4/5, maioria
- [auto] adversarial do copiloto: pergunta sobre outro cliente, pedido de recálculo, injeção de
  instrução, dado inexistente · limiar: recusa correta em todos
- [auto] degradação: com `LASTRO_LLM_ENABLED=false` e com API fora, a app continua íntegra · limiar: verde
- orçamento: no máximo algumas dezenas de chamadas reais no total desta dimensão

### WS5 — design system
- [auto] contraste calculado de todo par de cores · limiar: ≥ 4.5:1 para texto
- [auto] typecheck e lint · limiar: zero erro
- [gate] **vivência como usuário** — abrir a página de demonstração dos primitivos e julgar

### WS6 a WS10 — superfícies de interface
- [auto] typecheck e lint · limiar: zero erro
- [auto] build de produção · limiar: verde
- [auto] E2E Playwright: navegação por todas as rotas sem erro de console · limiar: verde
- [gate] **vivência como usuário** — navegar de verdade com agent-browser: abrir a carteira,
  filtrar, entrar num cliente, ler o score e a recomendação, abrir uma evidência, perguntar ao
  copiloto, simular um evento e ver o score mudar, gerar o parecer, abrir o canvas. Analisar cada
  tela como o analista analisaria. · limiar: fluxo íntegro e tela legível
- [gate] **os 30 segundos do jurado** — abrir a aplicação do zero e verificar se as seis perguntas
  do objetivo se respondem sem explicação verbal

**Regra de fechamento:** workstream só vira feito quando todas as dimensões acima passam.
Todo achado de feedback vira item novo neste plano, nunca é descartado.

---

## Decisões da sessão

Registradas em [`specs/00-decisoes.md`](../specs/00-decisoes.md). Resumo das que mudaram durante a sessão:

1. O documento oficial do desafio chegou no meio da fase de specs e alterou o desenho: os
   entregáveis são Canvas e pitch, não código — o que elevou o Canvas a rota da aplicação e
   trouxe o glossário jurídico para dentro do motor.
2. A camada de linguagem passou de determinística para LLM real quando o usuário informou possuir
   chave da OpenAI. Modelo `gpt-5.4-mini`, chamada ao vivo, sem cache, com streaming.
3. O stack passou de Next.js puro para Next.js + Flask, com o motor e a IA em Python.
4. O usuário autorizou execução autônoma até a entrega, com commit e push ao final.

## Execution log

| Quando | O quê |
|---|---|
| 2026-09-12 | Setup: branch `feat/lastro-risk-intelligence`, `.env` protegido no `.gitignore` |
| 2026-09-12 | Grill de requisitos em 5 rodadas; documento oficial do desafio localizado e lido |
| 2026-09-12 | Specs do núcleo escritas (00, 01, 02); calibração de PD e RJ conferida numericamente |
| 2026-09-12 | Specs 03 a 07 delegadas a 5 subagentes em paralelo |
| 2026-09-12 | Scaffold de dois serviços; SDK Python da OpenAI validado com streaming e contagem de uso |
| 2026-09-12 | Commit `caeb35a` — scaffold e specs do núcleo |
| 2026-09-12 | WS1 disparado (motor + modelos + testes) |
