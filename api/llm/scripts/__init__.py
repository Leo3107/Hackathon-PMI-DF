"""Scripts operacionais da camada de linguagem — `04-camada-llm.md` §6.2 e §7.5.

⚠️  **Estes dois módulos são os únicos do repositório que gastam cota real.**
Nenhum deles roda em `pytest`, nenhum roda no CI, e nenhum foi executado na
sessão em que a camada foi escrita: as fixtures de `tests/fixtures/llm/` foram
redigidas à mão, no formato da spec, exatamente para preservar o saldo.

| Script | O que faz | Custo estimado |
|---|---|---|
| `gravar_fixtures` | grava respostas reais em `tests/fixtures/llm/` | ≈ US$ 0,04 (17 chamadas) |
| `avaliar_pareceres` | gera 10 pareceres e os submete ao juiz (§7) | ≈ US$ 0,05 (20 chamadas) |

A spec os localiza em `api/scripts/`; aqui vivem sob `api/llm/scripts/` porque
a fronteira de arquivo deste workstream é `api/llm/**`.
"""
