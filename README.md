# Lastro

**Inteligência de risco de crédito e prevenção à inadimplência no agronegócio.**

Protótipo funcional desenvolvido para o **Hackathon PMI-DF 2026** (Edital 01/2026), em resposta ao
desafio proposto pela empresa parceira **Krill Tech**: conceber um sistema inteligente capaz de
realizar due diligence automatizada, triagem cadastral, monitoramento processual e financeiro, e
gerar um Relatório Padronizado de Risco de Crédito com alerta precoce de Recuperação Judicial.

> ### ⚠ A carteira de demonstração usa DADOS SIMULADOS
> Os 18 clientes da carteira, seus processos, garantias e evidências são fictícios, criados para
> demonstração — empresas e CPF/CNPJ não correspondem a entidades reais.
>
> A camada de coleta (`coleta/`) é a exceção: ela consulta **fontes públicas de verdade**
> (Receita Federal, PGFN, IBAMA, IBGE/SIDRA, BCB, clima e protestos). A interface identifica
> sempre qual das duas origens sustenta cada número.

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
web/      Next.js 16 · React 19 · TypeScript · Tailwind v4   interface e proxy server-side
api/      Flask 3 · pydantic 2 · OpenAI                      motor de risco e camada de linguagem
coleta/   Python · DuckDB · httpx · polars                   ingestão real das fontes públicas
```

O navegador nunca fala com o Flask diretamente: o Next faz proxy no servidor, de modo que a chave
da API nunca sai do backend.

### As três camadas e os quatro agentes do desafio

| Camada | Agente da §6 do desafio | O que faz |
|---|---|---|
| `coleta/` | **Agente Coletor & Parser** e **Agente de Risco Agro & Climático** | Baixa e normaliza as fontes públicas num warehouse DuckDB e monta o dicionário de features de um documento |
| `api/scoring/` | **Motor de Decisão & Scoring** | Transforma fatos em score, PD, risco de RJ, red flags e recomendação, de forma determinística e auditável |
| `api/llm/` | **Agente Sintetizador & Gerador de Relatórios** | Redige parecer, explicação e recomendação em linguagem natural, **sem nunca produzir um número** |

A fronteira entre a coleta e o motor é o contrato `Features → FatosDoCliente`, em
[`api/adaptadores/`](api/adaptadores/): é o que permite a mesma análise rodar sobre um cliente
simulado da carteira ou sobre um CNPJ real consultado na hora.

## Rodando com Docker (recomendado)

Único pré-requisito: Docker.

```bash
docker compose up --build
```

Interface em **http://localhost:3000** · API em **http://localhost:5001**.

A aplicação funciona **integralmente sem chave da OpenAI**: sem ela, a camada de linguagem cai
num gerador determinístico e nenhum número desaparece da tela. Para ligar o modelo de verdade,
exporte a chave antes de subir (ou deixe-a num `.env`, que o compose lê):

```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

Para desligar o modelo mesmo tendo chave — útil para ensaiar o pitch sem depender de rede:

```bash
LASTRO_LLM_ENABLED=false docker compose up
```

Derrubar tudo: `docker compose down`. Apagar também o warehouse da coleta: `docker compose down -v`.

## Rodando sem Docker

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
- [`coleta/README.md`](coleta/README.md) — a camada de ingestão: fontes, warehouse, CLI e API
- Dentro da aplicação: `/canvas` (Project Canvas do edital) e `/arquitetura` (pipeline da solução)

## Aviso

Análise automatizada de **apoio à decisão**. A avaliação final é de responsabilidade do analista
de crédito. O sistema não substitui o julgamento humano e não opera como decisor autônomo.
