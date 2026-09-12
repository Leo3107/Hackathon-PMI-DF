# CONTEXT.md

> Memória durável entre sessões: decisões, armadilhas e padrões aprendidos neste repositório.
> Todo subagente lê antes de começar. ≠ `AGENTS.md` (operacional) e ≠ plan ativo (estado vivo).

## Decisões de arquitetura

- **Fatos brutos separados de avaliação derivada** — o mock guarda apenas `FatosDoCliente`;
  score, PD, rating, coberturas, red flags e recomendação são sempre recalculados por função pura.
  *Por quê:* elimina por construção a possibilidade de o dado mockado discordar do motor. Era o
  risco número um do protótipo — um jurado somar os componentes na tela e não fechar. (2026-09-12)

- **O motor é determinístico; o LLM só escreve prosa** — a escolha da recomendação e todos os
  números vêm de regra. O LLM recebe valores prontos.
  *Por quê:* credibilidade técnica diante da banca e ausência de alucinação numérica. (2026-09-12)

- **Repositório assíncrono desde o mock** (`RepositorioLastro`) — assinatura já é `Promise`.
  *Por quê:* trocar mock por API real não deve tocar nenhum componente de tela. (2026-09-12)

- **Contribuição de fator como unidade de explicação** — cada fator carrega `pontos` e
  `impactoGlobal = peso × pontos × sinal`. Decomposição, explicação, delta histórico e red flags
  derivam todos da mesma estrutura.
  *Por quê:* uma única fonte para "qual é o risco", "por quê", "o que mudou" e "qual a evidência"
  — as quatro perguntas que o produto promete responder. (2026-09-12)

- **Inadimplência técnica como cidadã de primeira classe** — covenant rompido penaliza a dimensão
  comportamental e gera red flag ALTA mesmo sem nenhum atraso de pagamento.
  *Por quê:* é a tese do produto. Detectar antes do calote é o que diferencia de um birô de crédito. (2026-09-12)

- **Garantias classificadas em extraconcursal vs concursal** — alienação fiduciária sobrevive à RJ;
  penhor entra no plano com deságio (Lei 11.101/2005, glossário §4 do desafio).
  *Por quê:* permite calcular `exposicaoEmRiscoEmRJ`, que é o número que nenhum concorrente mostra:
  quanto a Krill Tech perde de proteção efetiva se o cliente pedir RJ amanhã. (2026-09-12)

- **PD e risco de RJ são eixos independentes** — inadimplência e recuperação judicial não são o
  mesmo evento e nunca compartilham escala na interface.
  *Por quê:* exigência explícita do briefing, e é verdade de domínio: quem tem muitos credores
  distintos executando pode pedir RJ mesmo pagando a Krill Tech em dia. (2026-09-12)

## Armadilhas / gotchas

- **`gpt-5.4-mini` exige `max_completion_tokens`**, não `max_tokens`, no endpoint
  `POST /v1/chat/completions`. Verificado na prática em 2026-09-12.
- **Latência medida do modelo: ~6,4s** para um parecer de ~860 tokens de saída. Qualquer tela que
  dependa disso de forma bloqueante fica inutilizável. Daí a regra: número nunca espera por LLM.
- **`create-next-app` recusa nome de projeto começando com ponto** (restrição de nomenclatura do npm).
- **Heredoc de markdown extenso quebra o parser do Git Bash neste ambiente Windows.** Use a
  ferramenta Write para arquivos grandes; heredoc só para conteúdo curto.
- **O remote deste repositório é público e o `.env` contém uma chave real da OpenAI.** Conferir
  `git check-ignore .env` antes de qualquer commit. Orçamento do usuário: US$ 10.

## Mapa mental do código

- `lib/scoring/` é o coração e a única parte com testes obrigatórios. Puro, sem I/O, sem relógio.
- `lib/scoring/config.ts` concentra todos os coeficientes — mudar comportamento do motor é mudar
  esse arquivo, nunca o corpo das funções.
- `lib/llm/` tem duas implementações intercambiáveis da mesma interface; a determinística precisa
  ser boa o bastante para a aplicação continuar apresentável sem rede.
- `components/ui/` é o design system próprio. Nada de biblioteca de terceiros.
- `data/` guarda fatos brutos por cliente, um arquivo por cliente.

## Questões em aberto

- Pesos das sete dimensões e calibração das curvas de PD e de RJ estão propostos com justificativa
  em `specs/02-motor-de-risco.md`, mas não foram validados por um analista de crédito real.

## Log de aprendizados por sessão

### 2026-09-12 — Especificação e construção do protótipo Lastro

- O documento oficial do desafio **não exige implementação em código** (§6). O protótipo funcional
  é diferencial competitivo, não requisito. Os entregáveis são Project Canvas e pitch — por isso o
  Canvas virou uma rota da própria aplicação.
- O glossário do §4 do desafio é uma mina de requisitos de produto, não decoração: Stay Period,
  extraconcursal vs concursal, inadimplência técnica vs financeira, Lei 14.112/2020, CPR e barter
  viraram todos funcionalidade calculada.
- O prompt inicial do usuário não mencionava o PDF do desafio; ele chegou no meio da fase de specs
  e mudou decisões já tomadas. Vale perguntar por documentos oficiais logo no início.
