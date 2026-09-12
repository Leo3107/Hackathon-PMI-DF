# Lastro

**Inteligência de risco de crédito e prevenção à inadimplência no agronegócio.**

Protótipo funcional desenvolvido para o **Hackathon PMI-DF 2026** (Edital 01/2026), em resposta ao
desafio proposto pela empresa parceira **Krill Tech**: conceber um sistema inteligente capaz de
realizar due diligence automatizada, triagem cadastral, monitoramento processual e financeiro, e
gerar um Relatório Padronizado de Risco de Crédito com alerta precoce de Recuperação Judicial.

> ### ⚠ DADOS SIMULADOS — protótipo demonstrativo
> Nenhuma integração real com órgão público é realizada. Todos os clientes, documentos, processos
> e evidências são fictícios, gerados para demonstração. Empresas e CPF/CNPJ não correspondem a
> pessoas ou entidades reais.

---

## A tese

Um birô de crédito entrega uma nota. O Lastro entrega o risco, a causa, a evidência e a ação.

> **NÃO ENTREGAMOS APENAS UMA NOTA.
> ENTREGAMOS O RISCO, A CAUSA, A EVIDÊNCIA E A AÇÃO RECOMENDADA.**

Toda tela existe para o analista de crédito responder rápido a cinco perguntas:

1. Qual é o risco?
2. Por que este cliente recebeu essa classificação?
3. O que mudou?
4. Qual é a evidência?
5. O que a Krill Tech deveria fazer agora?

## O que o diferencia

| | |
|---|---|
| **Inadimplência técnica** | Detecta quebra de covenant contratual **antes** do primeiro atraso. É o único sinal que chega a tempo de agir. |
| **Risco de RJ separado do risco de calote** | Inadimplência e Recuperação Judicial não são o mesmo evento. Um cliente pode pagar em dia e ainda assim pedir RJ sob pressão de outros credores. Os dois eixos são modelados e exibidos separadamente. |
| **Garantia que sobrevive à RJ** | Alienação fiduciária é extraconcursal; penhor entra no plano com deságio. O sistema calcula quanto da exposição continuaria protegida **se o cliente pedisse RJ amanhã**. |
| **Stay Period** | Cliente com RJ deferida exibe a contagem dos 180 dias em que a cobrança está legalmente suspensa, e o que ainda é possível executar. |
| **Score que se decompõe e fecha** | A soma das contribuições dos fatores reconstrói o score exibido. A soma dos deltas reconstrói a variação. Dá para auditar na tela. |
| **Gatilho de veto transparente** | Quando uma regra de negócio rebaixa a classificação, o score calculado continua visível ao lado, com o motivo nomeado. O modelo não esconde a si mesmo. |
| **IA que não inventa número** | O motor determinístico calcula; o modelo de linguagem apenas redige. Separação explícita e verificada por teste. |

## Stack

```
web/   Next.js 16 · React 19 · TypeScript · Tailwind v4     interface e proxy server-side
api/   Flask 3 · pydantic 2 · OpenAI                        motor de risco e camada de linguagem
```

O navegador nunca fala com o Flask diretamente: o Next faz proxy no servidor, de modo que a chave
da API nunca sai do backend.

## Rodando

Pré-requisitos: Node 22+ e Python 3.13+.

```bash
# dependências
npm install
cd web && npm install && cd ..
python -m venv api/.venv
api/.venv/Scripts/python -m pip install -r api/requirements.txt   # Windows
# api/.venv/bin/python -m pip install -r api/requirements.txt     # Linux/macOS

# configuração
cp .env.example .env        # preencha OPENAI_API_KEY

# subir os dois serviços juntos
npm run dev                 # web em :3000, api em :5001
```

A aplicação funciona integralmente **sem** chave da OpenAI: basta `LASTRO_LLM_ENABLED=false`,
e a camada de linguagem cai num gerador determinístico.

## Testes

```bash
npm test          # motor de risco (pytest) + typecheck e lint do frontend
npm run e2e       # Playwright
```

## Documentação

- [`specs/README.md`](specs/README.md) — índice das especificações e invariantes do produto
- [`specs/02-motor-de-risco.md`](specs/02-motor-de-risco.md) — a matemática completa do score, PD e risco de RJ
- [`specs/_desafio-pdf.txt`](specs/_desafio-pdf.txt) — documento oficial do desafio
- Dentro da aplicação: `/canvas` (Project Canvas do edital) e `/arquitetura` (pipeline da solução)

## Aviso

Análise automatizada de **apoio à decisão**. A avaliação final é de responsabilidade do analista
de crédito. O sistema não substitui o julgamento humano e não opera como decisor autônomo.
