# Specs — Lastro

Plataforma de inteligência de risco de crédito e prevenção à inadimplência no agronegócio.
Protótipo funcional desenvolvido para o **Hackathon PMI-DF 2026** (Edital 01/2026), desafio
proposto pela empresa parceira **Krill Tech**.

> **Toda a aplicação opera sobre dados simulados.** Nenhuma integração real com órgão público
> é feita ou insinuada. Ver `00-decisoes.md` D11.

## Índice

| Arquivo | Conteúdo | Autoridade |
|---|---|---|
| [`00-decisoes.md`](00-decisoes.md) | Registro autoritativo de decisões da sessão. Em conflito entre specs, este vence. | **Máxima** |
| [`01-modelo-de-dados.md`](01-modelo-de-dados.md) | Contrato de tipos TypeScript. Separação entre fatos brutos e avaliação derivada. | Alta |
| [`02-motor-de-risco.md`](02-motor-de-risco.md) | Especificação matemática completa: fatores, dimensões, score, PD, risco de RJ, vetos, Stay Period, garantias, deltas. **Fonte de verdade numérica.** | Alta |
| [`03-ux-e-telas.md`](03-ux-e-telas.md) | Arquitetura de informação, rotas, cada tela, estados, acessibilidade. | Alta |
| [`04-camada-llm.md`](04-camada-llm.md) | Agente Sintetizador e Copiloto: prompts, endpoints, streaming, custo, rubrica de qualidade. | Alta |
| [`05-design-system.md`](05-design-system.md) | Tokens, paleta semântica de risco, tipografia, catálogo de primitivos, gráficos, impressão. | Alta |
| [`06-dados-simulados.md`](06-dados-simulados.md) | Dataset de 18 clientes + prospects: fatos brutos coerentes, snapshots, eventos, evidências. | Alta |
| [`07-canvas-arquitetura-parecer.md`](07-canvas-arquitetura-parecer.md) | Project Canvas (entregável oficial), aba Arquitetura e Parecer imprimível. | Alta |
| [`_desafio-pdf.txt`](_desafio-pdf.txt) | Texto integral do Documento de Desafio oficial. Referência primária. | Referência |

## Como ler, por papel

- **Implementando o motor?** `02` primeiro, `01` para os tipos, `06` para os dados de entrada.
- **Implementando tela?** `03` primeiro, `05` para os componentes, `01` para os tipos.
- **Implementando a camada de IA?** `04` primeiro, `02` para entender o que nunca pode ser alterado.
- **Preparando o pitch?** `07` e a seção final de `03` ("os 30 segundos do jurado").

## Invariantes do produto (não negociáveis)

| # | Invariante | Onde é testada |
|---|---|---|
| I1 | Os pesos das sete dimensões somam exatamente 1,00 | `02` §2 |
| I2 | A soma das contribuições dos fatores reconstrói o score exibido | `02` §3 |
| I3 | PD 12m é estritamente decrescente no score | `02` §6 |
| I4 | PD 6m < PD 12m < PD 24m para toda combinação | `02` §6 |
| I5 | O dataset contém casos que provam que PD e risco de RJ são eixos independentes | `02` §7, `06` |
| I6 | A soma dos deltas por fator reconstrói exatamente a variação do score | `02` §11 |
| I7 | O LLM nunca produz, altera ou recalcula um número | `04` |
| I8 | Nenhum estado de risco é comunicado apenas por cor | `05` |
| I9 | Toda tela com recomendação exibe o aviso de decisão humana | `02` §12, `03` |
| I10 | O aviso de dados simulados é visível em toda rota e em todo PDF exportado | `00` D11 |
