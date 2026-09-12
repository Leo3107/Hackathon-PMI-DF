# 02 — Motor de risco (determinístico)

> Especificação matemática completa. **Esta é a fonte de verdade numérica do produto.**
> Implementação em `lib/scoring/`. Zero aleatoriedade: mesma entrada, mesma saída, sempre.
> O LLM nunca toca nestes números.

Referências: prompt do usuário §4, §5, §6, §8, §10, §11 · Documento de Desafio §4 (glossário), §6 (Motor de Decisão & Scoring)

---

## 1. Princípio de arquitetura: fatos → fatores → dimensões → score

```
FatosDoCliente (dados brutos, mock)
      │  featurizers puros, um por dimensão
      ▼
FatorCalculado[]   { id, dimensao, rotulo, pontos, direcao, fonte, evidenciaId }
      │  agregação por dimensão
      ▼
DimensaoAvaliada[] { dimensao, score 0-1000, peso, fatores[], tendencia }
      │  média ponderada
      ▼
scoreCalculado 0-1000  →  ratingCalculado A|B|C|D
      │  regras de veto (determinísticas, fora do score)
      ▼
ratingFinal  +  vetoAtivo?  +  motivoDoVeto
```

**Cada fator carrega seus próprios pontos.** Isso é o que permite explicar, decompor e
comparar dois instantes no tempo sem nenhuma heurística de apresentação.

---

## 2. Dimensões e pesos

Definidos em `lib/scoring/config.ts` como constante exportada e **configurável**.

| # | Dimensão | Chave | Peso |
|---|---|---|---|
| D1 | Comportamental / histórico interno | `comportamental` | **22%** |
| D2 | Jurídico & processual | `juridico` | **20%** |
| D3 | Fiscal & trabalhista | `fiscal` | **14%** |
| D4 | Agro & climático | `agroclimatico` | **15%** |
| D5 | Cadastral & societário | `cadastral` | **10%** |
| D6 | Ambiental | `ambiental` | **9%** |
| D7 | Garantias & exposição | `garantias` | **10%** |
| | | **Σ** | **100%** |

**Invariante I1:** a soma dos pesos é exatamente 1,00. Teste unitário obrigatório.

**Justificativa dos pesos** (para o pitch e para a aba de metodologia):
comportamental lidera porque dado interno de pagamento é o preditor mais direto e menos ruidoso
que a Krill Tech possui; jurídico vem logo atrás porque execução ajuizada é o sinal público mais
antecedente de insolvência; agroclimático pesa acima do usual em crédito por ser o setor de
atuação e a causa macro apontada nas §3 do desafio (El Niño/La Niña, quebra de safra).

---

## 3. Cálculo de uma dimensão

Cada dimensão parte de **1000 (risco nulo)** e sofre penalidades e bônus:

```
scoreDimensao = clamp( 1000 - Σ penalidades + Σ bonus , 0 , 1000 )
```

- **Penalidade**: fator com `direcao: 'risco'`, `pontos` positivo.
- **Bônus**: fator com `direcao: 'protecao'`, `pontos` positivo (subtraído da penalidade total).
- Todo fator só é emitido quando **materializado** (pontos > 0). Fator zerado não polui a tela.

### Contribuição de um fator ao score final

```
impactoGlobal(fator) = peso(dimensao) × pontos(fator) × sinal
                       sinal = -1 para 'risco', +1 para 'protecao'
```

**Invariante I2 (a que o jurado pode auditar):**

```
scoreCalculado = 1000 + Σ_todos_os_fatores impactoGlobal(fator)
```

Só vale enquanto nenhuma dimensão satura no clamp. Quando satura, o motor **redistribui o
excedente**: os fatores da dimensão saturada têm seus `impactoGlobal` reescalados
proporcionalmente para que a soma feche. O campo `impactoGlobalAjustado` é o que a UI exibe,
e `lib/scoring/audit.ts` expõe `verificarFechamento()` que retorna a diferença — que deve ser 0.
**Teste unitário obrigatório para os 18 clientes.**

---

## 4. Catálogo de fatores por dimensão

Todos os coeficientes vivem em `lib/scoring/config.ts`. Nenhum número mágico no corpo das funções.

### D1 · Comportamental (peso 22%) — fonte: dados internos Krill Tech

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `atraso_medio` | atraso médio de pagamento em 12m | `min(250, atrasoMedioDias × 12)` | risco |
| `pior_atraso` | pior atraso registrado em 12m | `min(200, piorAtrasoDias × 5)` | risco |
| `pontualidade` | fração de títulos pagos em dia em 12m | `(1 - pctPagosEmDia) × 300` | risco |
| `renegociacoes` | renegociações nos últimos 12m | `min(180, nRenegociacoes × 60)` | risco |
| `inadimplencia_tecnica` | **covenants contratuais rompidos e vigentes** | `min(240, nCovenantsRompidos × 120)` | risco |
| `tendencia_atraso` | atraso médio dos últimos 90d > atraso médio dos 12m anteriores | `min(120, (atraso90 - atraso12m) × 10)` | risco |
| `relacionamento` | tempo de relacionamento | `min(120, anosRelacionamento × 15)` | proteção |
| `historico_limpo` | nenhum atraso > 5 dias em 24m | `80` | proteção |

> `inadimplencia_tecnica` é o fator-assinatura do produto: dispara **antes** de qualquer atraso.
> Ver `00-decisoes.md` D7. Sempre gera também uma red flag de severidade ALTA.

### D2 · Jurídico & processual (peso 20%) — fonte: DataJud/CNJ, DJEs, cartórios de protesto

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `execucoes_titulo` | execuções de título ajuizadas em 12m | `min(300, nExecucoes12m × 70)` | risco |
| `materialidade_execucao` | valor total em execução ÷ exposição total | `min(200, razao × 400)` | risco |
| `aceleracao_judicial` | ≥2 execuções nos últimos 90 dias | `100` | risco |
| `protestos` | protestos ativos | `min(180, nProtestos × 45)` | risco |
| `protesto_recorrente` | ≥3 protestos em 12m | `80` | risco |
| `pedido_falencia` | pedido de falência distribuído contra o cliente | `400` | risco |
| `rj_distribuida` | RJ ajuizada ou deferida | `900` | risco |
| `trabalhistas` | reclamações com trânsito em julgado | `min(100, nAcoes × 25)` | risco |
| `pluralidade_credores` | nº de credores **distintos** executando ≥ 3 | `120` | risco |
| `sem_litigio` | nenhuma ação em 36m | `60` | proteção |

> `pluralidade_credores` é deliberadamente separado de `execucoes_titulo`: três execuções de um
> mesmo credor indica disputa bilateral; três execuções de credores distintos indica **crise de
> liquidez generalizada** — o precursor clássico de RJ. Entra também no índice de RJ (§6).

### D3 · Fiscal & trabalhista (peso 14%) — fonte: PGFN, TST/CNDT, Caixa/CRF-FGTS

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `divida_ativa` | dívida ativa PGFN ÷ exposição total | `min(320, razao × 500)` | risco |
| `divida_ativa_crescente` | dívida ativa cresceu nos últimos 90d | `90` | risco |
| `cndt_positiva` | CNDT positiva (débito trabalhista com trânsito em julgado) | `200` | risco |
| `fgts_irregular` | CRF-FGTS irregular | `120` | risco |
| `parcelamento_rompido` | parcelamento fiscal rompido em 12m | `150` | risco |
| `certidoes_negativas` | todas as certidões negativas e vigentes | `80` | proteção |

### D4 · Agro & climático (peso 15%) — fonte: MAPA/ZARC, CONAB, INMET, SICAR

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `zarc_risco` | risco ZARC da cultura na região | `baixo 0 · moderado 90 · alto 200 · critico 320` | risco |
| `quebra_safra_regional` | quebra de safra regional no último ciclo (%) | `min(200, quebraPct × 6)` | risco |
| `desvio_precipitacao` | desvio da precipitação acumulada vs. normal climatológica | `min(150, abs(desvioPct) × 3)` | risco |
| `monocultura` | cultura única, sem diversificação | `60` | risco |
| `produtividade_abaixo` | produtividade do cliente abaixo da média regional (%) | `min(120, deficitPct × 4)` | risco |
| `barter_sem_lastro` | operação barter sem CPR registrada cobrindo-a | `100` | risco |
| `irrigacao_ou_seguro` | área irrigada relevante **ou** seguro agrícola vigente | `100` | proteção |
| `diversificacao` | ≥3 culturas distintas | `60` | proteção |

### D5 · Cadastral & societário (peso 10%) — fonte: Receita Federal/CNPJ Abertos, Redesim

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `situacao_cadastral` | situação RFB diferente de ATIVA | `400` | risco |
| `tempo_atividade` | <3 anos → 200 · 3–5 anos → 100 · >5 anos → 0 | conforme faixa | risco |
| `alteracao_societaria` | alteração societária relevante em 180d | `120` | risco |
| `saida_socio_majoritario` | saída de sócio majoritário em 12m | `100` | risco |
| `capital_vs_exposicao` | capital social ÷ exposição: <0,5 → 150 · <1,0 → 80 · ≥1,0 → 0 | conforme faixa | risco |
| `cnae_incompativel` | CNAE principal incompatível com a atividade declarada | `80` | risco |
| `qsa_estavel` | quadro societário estável há ≥5 anos | `80` | proteção |

### D6 · Ambiental (peso 9%) — fonte: SICAR, IBAMA

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `embargo_ibama` | embargo do IBAMA vigente sobre imóvel do cliente | `500` | risco |
| `auto_infracao` | auto de infração ambiental não quitado | `200` | risco |
| `car_ausente` | imóvel sem CAR | `300` | risco |
| `car_irregular` | CAR em situação pendente/irregular | `150` | risco |
| `sobreposicao_app` | sobreposição com reserva legal ou APP | `180` | risco |
| `car_regular` | CAR ativo e regular | `60` | proteção |

### D7 · Garantias & exposição (peso 10%)

| id | Condição | Pontos | Direção |
|---|---|---|---|
| `descoberto_extraconcursal` | `(1 - coberturaExtraconcursal) × 400`, coberturas limitadas a 1,0 no cálculo | fórmula | risco |
| `descoberto_total` | `(1 - coberturaTotal) × 250` | fórmula | risco |
| `utilizacao_limite` | utilização do limite >85% → 120; >95% → +80 (acumula, teto 200) | conforme faixa | risco |
| `concentracao_patrimonial` | exposição total > 2× patrimônio declarado | `150` | risco |
| `vencimento_concentrado` | >50% do a vencer concentrado em 90 dias | `80` | risco |
| `sobrecolateral` | cobertura extraconcursal ≥ 100% | `120` | proteção |

---

## 5. Rating e faixas

`lib/scoring/config.ts`, configurável:

| Rating | Faixa | Rótulo |
|---|---|---|
| **A** | 750–1000 | Baixo risco |
| **B** | 600–749 | Risco moderado |
| **C** | 400–599 | Risco elevado |
| **D** | 0–399 | Risco crítico / Alerta de RJ |

Rótulo de D alinhado à §7.1 do documento de desafio.

---

## 6. Probabilidade de inadimplência (PD)

### PD 12 meses — curva logística sobre o score

```
PD12(score) = L / (1 + exp((score - s0) / k))
onde  L = 0,62   s0 = 500   k = 108
```

Calibração escolhida para ancorar nos valores ilustrativos do briefing
(score 604 → PD12 ≈ 17,1%) e produzir uma curva monotonicamente decrescente e suave:

| Score | PD 12m |
|---|---|
| 1000 | 0,60% |
| 900 | 1,49% |
| 800 | 3,63% |
| 750 (piso A) | 5,57% |
| 700 | 8,41% |
| 650 | 12,37% |
| 600 (piso B) | 17,59% |
| 550 | 23,95% |
| 500 | 31,00% |
| 400 (piso C) | 44,41% |
| 300 | 53,59% |
| 150 | 59,67% |

Valores conferidos numericamente em 2026-09-12. **Invariante I3:** PD12 é estritamente
decrescente em `score` — verificado por varredura de 0 a 1000, zero violações.

### PD 6m e PD 24m — consistência de hazard

Derivadas de PD12 por hazard constante ajustado pela **tendência**, o que garante por construção
`PD6 < PD12 < PD24` sem nenhum ajuste manual:

```
PD6  = 1 - (1 - PD12) ^ (0,5 × ψ)
PD24 = 1 - (1 - PD12) ^ (2,0 × θ)
```

| Tendência do score | ψ (curto prazo) | θ (longo prazo) |
|---|---|---|
| `melhorando` | 0,85 | 0,80 |
| `estavel` | 1,00 | 0,92 |
| `deteriorando` | 1,15 | 1,10 |
| `deterioracao_acelerada` | 1,30 | 1,25 |

Verificação para score 604 (PD12 = 17,13%), conferida numericamente em 2026-09-12:

| Tendência | PD 6m | PD 12m | PD 24m |
|---|---|---|---|
| `melhorando` | 7,67% | 17,13% | 25,96% |
| `estavel` | 8,97% | 17,13% | 29,23% |
| `deteriorando` | 10,24% | 17,13% | 33,86% |
| `deterioracao_acelerada` | 11,50% | 17,13% | 37,48% |

Ordem de grandeza coerente com os valores ilustrativos do briefing (9,4% / 17,3% / 26,8%).

**Invariante I4:** `PD6 < PD12 < PD24` para toda combinação de score e tendência — verificado
por varredura de 0 a 1000 nas quatro tendências, zero violações.

---

## 7. Risco de Recuperação Judicial — indicador SEPARADO

> **Inadimplência e RJ não são o mesmo evento** (exigência explícita do briefing §5).
> Um cliente pode pagar a Krill Tech em dia e ainda assim entrar em RJ por pressão de outros
> credores; e pode ficar inadimplente sem nunca pedir RJ. O motor modela os dois caminhos
> separadamente e a UI **nunca** os apresenta como escala única.

### Índice de propensão a RJ (`rjIndex`, 0–100)

Somatório de sinais **específicos de insolvência coletiva**, não de atraso bilateral:

| Sinal | Pontos |
|---|---|
| Pluralidade de credores executando (≥3 credores distintos) | 20 |
| Endividamento judicializado ÷ exposição total | até 25 (`min(25, razao × 50)`) |
| Protestos de credores distintos em 180d | até 12 (`min(12, nCredoresProtestantes × 4)`) |
| Dívida ativa PGFN ÷ faturamento estimado | até 10 (`min(10, razao × 40)`) |
| Risco ZARC alto/crítico **ou** quebra de safra > 25% | até 12 |
| Pedido de falência distribuído (RJ defensiva é resposta comum) | 15 |
| Parcelamento fiscal rompido | 6 |
| Covenant rompido (inadimplência técnica) | 8 |
| Alteração de administrador em período de crise | 5 |
| **Redutor:** patrimônio líquido ≥ 3× exposição e zero execuções | −15 |

### Elegibilidade legal (Lei 14.112/2020)

```
elegivelRJ =
  tipoPessoa === 'PJ'
  || (tipoPessoa === 'PF' && anosAtividadeComprovada >= 2
      && (possuiLivroCaixaDigital || possuiInscricaoEstadual))
```

Produtor rural **PF não elegível** não tem via de RJ: tende a execução individual e falência
patrimonial. Aplica-se fator de atenuação:

```
se (!elegivelRJ) rjIndexEfetivo = rjIndex × 0,15
```

A UI explicita o motivo: *"Não elegível a RJ — produtor rural PF sem 2 anos de atividade
comprovada (Lei 14.112/2020). Risco migra para execução individual."*

### Conversão em probabilidade

```
RJ12 = 0,45 / (1 + exp(-(rjIndexEfetivo - 55) / 9))
```

| rjIndexEfetivo | Risco de RJ 12m |
|---|---|
| 10 | 0,30% |
| 20 | 0,90% |
| 30 | 2,63% |
| 40 | 7,15% |
| 45 | 11,14% |
| 50 | 16,41% |
| 55 | 22,50% |
| 60 | 28,59% |
| 70 | 37,85% |
| 80 | 42,37% |

Valores conferidos numericamente em 2026-09-12.

**Caso especial:** com RJ já ajuizada ou deferida, `RJ12 = 100%` e o estado do cliente passa a
`RJ_EM_CURSO` — o indicador deixa de ser probabilidade e vira **evento ocorrido**, com rótulo
distinto na UI e ativação do painel de Stay Period (§9).

**Invariante I5:** existe ao menos um cliente no dataset com **PD moderado e RJ alto** e ao menos
um com **PD alto e RJ baixo**, para provar visualmente que os eixos são independentes.

---

## 8. Gatilhos de veto — regras determinísticas acima do score

> Exigência do briefing §10. O score é estatístico; certos eventos são **eliminatórios por
> natureza jurídica**, independentemente da nota. A UI exibe sempre os dois valores lado a lado:
> **SCORE CALCULADO** e **CLASSIFICAÇÃO FINAL APÓS REGRAS DE NEGÓCIO**, com o motivo do veto
> nomeado. **Nunca esconder o motivo.**

| id | Condição | Efeito | Justificativa exibida |
|---|---|---|---|
| `VETO_RJ` | RJ ajuizada ou deferida | força **D** | Crédito anterior ao pedido entra no plano com deságio severo. Stay Period suspende execuções. |
| `VETO_FALENCIA` | Pedido de falência distribuído | força **D** | Risco iminente de liquidação do devedor. |
| `VETO_EMBARGO_GARANTIA` | Embargo do IBAMA vigente sobre imóvel **oferecido em garantia** | força **D** | Garantia juridicamente comprometida: bem embargado tem excussão inviabilizada. |
| `VETO_CADASTRO_INAPTO` | Situação cadastral RFB inapta, suspensa ou baixada | força **D** | Impedimento cadastral para operar a prazo. |
| `VETO_LISTA_SUJA` | Inclusão no Cadastro de Empregadores (trabalho análogo ao escravo) | força **D** | Risco reputacional e de cadeia; vedação de política de crédito. |
| `VETO_FRAUDE` | Indício de fraude ou irregularidade grave confirmada | força **D** | Quebra de confiança; caso para análise especializada. |
| `TETO_EXEC_FISCAL` | Execuções fiscais somadas > 50% da exposição total | teto em **C** | Concorrência de crédito com preferência fiscal. |
| `TETO_CNDT` | CNDT positiva com débito > 15% do patrimônio declarado | teto em **C** | Passivo trabalhista com preferência sobre quirografários. |

Regra de composição: aplicam-se todos os gatilhos; **o resultado é o rating mais severo**
entre o calculado e os impostos. Um veto de `força D` sempre prevalece sobre um `teto C`.

**Importante:** o veto **não altera o `scoreCalculado`**, que continua visível. Isso preserva a
honestidade do modelo — o analista vê que o quantitativo dizia 520 e que a regra de negócio
rebaixou para D, e por quê.

---

## 9. Stay Period (Lei 11.101/2005)

Ativo quando o cliente está em `RJ_EM_CURSO` com data de deferimento conhecida.

```
diasDecorridos  = hoje - dataDeferimento
diasRestantes   = max(0, 180 + diasProrrogados - diasDecorridos)
stayPeriodAtivo = diasRestantes > 0
```

Enquanto ativo, a página do cliente exibe painel dedicado com contagem regressiva e a lista
explícita do que a Krill Tech **está legalmente impedida de fazer**: executar garantias,
protestar títulos, cobrar judicialmente. E o que **permanece possível**: excutir garantia com
**alienação fiduciária** (crédito extraconcursal, fora dos efeitos da RJ — §4 do desafio).

Essa distinção é o ponto em que a modelagem de garantias paga o investimento: em RJ, cobertura
extraconcursal é a única que realmente protege.

---

## 10. Exposição, garantias e coberturas

```
exposicaoTotal      = Σ operacoes.saldoDevedor
aVencer90d          = Σ operacoes.parcelas[vencimento <= hoje+90].valor
limiteUtilizadoPct  = exposicaoTotal ÷ limiteAprovado

valorExtraconcursal = Σ garantias[natureza = 'EXTRACONCURSAL'].valorAtualizado
valorConcursal      = Σ garantias[natureza = 'CONCURSAL'].valorAtualizado

coberturaExtraconcursal = valorExtraconcursal ÷ exposicaoTotal
coberturaTotal          = (valorExtraconcursal + valorConcursal) ÷ exposicaoTotal

exposicaoProtegida   = min(exposicaoTotal, valorExtraconcursal + valorConcursal)
exposicaoEmRisco     = exposicaoTotal - exposicaoProtegida
exposicaoEmRiscoEmRJ = max(0, exposicaoTotal - valorExtraconcursal)
```

`exposicaoEmRiscoEmRJ` é o número que ninguém mais mostra: **quanto a Krill Tech perde de
proteção efetiva se este cliente pedir RJ amanhã**, porque o penhor entra no plano e a
alienação fiduciária não. Deve aparecer com destaque próprio na seção de garantias.

### Classificação das garantias

| Tipo | Natureza | Base |
|---|---|---|
| Alienação fiduciária | **EXTRACONCURSAL** | Propriedade resolúvel transferida ao credor; fora dos efeitos da RJ (§4 do desafio) |
| CPR financeira **registrada** | **EXTRACONCURSAL** | Título com garantia registrada e vinculação específica |
| CPR física | **CONCURSAL** | Obrigação de entrega; sujeita ao plano |
| Penhor (safra, máquina) | **CONCURSAL** | Vincula o bem, mas entra no concurso de credores |
| Aval / fiança | **CONCURSAL** | Garantia pessoal, sem separação patrimonial |
| Hipoteca | **CONCURSAL** | Direito real de garantia sujeito ao plano |

`haircut` por tipo (deságio aplicado ao valor declarado para obter `valorAtualizado`),
configurável em `config.ts`: alienação fiduciária de máquina 20% · CPR financeira 10% ·
CPR física 25% · penhor de safra 40% · hipoteca 30% · aval 60%.

---

## 11. Tendência e "por que o score mudou"

O dataset guarda, por cliente, uma série de **snapshots** de `FatosDoCliente` em datas passadas.
O motor recalcula cada snapshot — nada é armazenado pré-calculado.

```
delta(fator) = impactoGlobal_t1(fator) - impactoGlobal_t0(fator)
```

Fatores que existem só em t1 entram com `impactoGlobal_t0 = 0` (e vice-versa).

**Invariante I6:**

```
score_t1 - score_t0 = Σ_todos_os_fatores delta(fator)
```

A UI ordena por `|delta|` e mostra os maiores contribuintes com o sinal explícito, exatamente
no formato pedido pelo briefing §6:

```
712 → 604   (-108 pontos)
  2 novas execuções de título ................ -42
  nova inscrição em dívida ativa ............. -31
  deterioração climática regional ............ -18
  atraso médio de pagamento (3d → 11d) ....... -17
```

**Teste unitário obrigatório:** para todo par de snapshots consecutivos dos 18 clientes,
a soma dos deltas deve igualar a diferença de score com tolerância `< 0,5 ponto`.

### Classificação da tendência

Sobre a variação do score nos últimos 90 dias:

| Variação em 90d | Tendência |
|---|---|
| ≥ +25 | `melhorando` |
| entre −24 e +24 | `estavel` |
| entre −25 e −79 | `deteriorando` |
| ≤ −80 | `deterioracao_acelerada` |

---

## 12. Recomendação operacional (determinística)

> O **texto** da recomendação é escrito pelo LLM, mas **qual recomendação** e **quais ações**
> são decididas por regra. O LLM não escolhe a decisão de crédito. Ver `04-camada-llm.md`.

| Condição (avaliada em ordem, primeira que casar vence) | Recomendação |
|---|---|
| Veto de força D ativo | `SUSPENDER_EXPOSICAO` |
| Rating final D | `SUSPENDER_EXPOSICAO` |
| Rating C **e** tendência `deterioracao_acelerada` | `SUSPENDER_NOVA_EXPOSICAO_A_PRAZO` |
| Rating C | `APROVAR_COM_RESTRICOES` |
| Rating B **e** `exposicaoEmRiscoEmRJ` > 40% da exposição | `APROVAR_COM_RESTRICOES` |
| Rating B **e** tendência deteriorando | `APROVAR_COM_MONITORAMENTO_INTENSIVO` |
| Rating B | `APROVAR` |
| Rating A **e** utilização de limite > 90% | `APROVAR_COM_REVISAO_DE_LIMITE` |
| Rating A | `APROVAR` |

Cada recomendação carrega um **conjunto de ações concretas parametrizadas pelos números do
cliente** — não texto genérico. Exemplos gerados por regra:

- `reduzir_limite`: *"Reduzir limite aprovado de R$ 5.000.000 para R$ 3.500.000 (−30%)"* —
  o percentual vem de tabela por rating e tendência.
- `exigir_garantia_adicional`: *"Exigir garantia adicional de R$ 1.480.000 para cobrir a
  exposição desprotegida"* — valor = `exposicaoEmRisco`.
- `reduzir_prazo`: *"Reduzir prazo de pagamento de 120 para 60 dias"*.
- `converter_para_extraconcursal`: *"Converter penhor de safra (R$ 900.000) em alienação
  fiduciária para blindar o crédito em cenário de RJ"* — só emitida quando há garantia concursal relevante.
- `reavaliar_em`: *"Reavaliar em 30 dias"* — prazo por severidade (A 180d · B 90d · C 30d · D 7d).
- `monitoramento_intensivo`, `bloquear_aumento_limite`, `exigir_pagamento_a_vista`,
  `encaminhar_analise_especializada`, `acionar_garantia`.

**Toda tela que exibe recomendação exibe também, de forma não dispensável:**
*"Decisão final sujeita à avaliação do analista responsável."*

---

## 13. Red flags — derivação automática

Red flags **não são escritas à mão**: são derivadas dos mesmos fatos, por regra, para que nunca
divirjam do score. Cada uma com `severidade`, `data`, `fonte`, `descricao`, `impactoEmPontos`
(= `impactoGlobal` do fator correspondente) e `status` (`nova` | `analisada` | `resolvida`).

| Severidade | Gatilhos |
|---|---|
| **CRÍTICA** | RJ ajuizada/deferida · pedido de falência · fraude confirmada · embargo do IBAMA sobre garantia · lista suja |
| **ALTA** | ≥2 execuções em 90d · protestos recorrentes · dívida ativa crescente · **covenant rompido (inadimplência técnica)** · queda de score > 80 pontos em 90d · CNDT positiva |
| **MÉDIA** | Alteração societária relevante · saída de sócio majoritário · ZARC elevado para alto/crítico · quebra de safra regional > 20% · certidão vencida · endividamento crescente · CAR irregular |
| **BAIXA / INFORMATIVA** | Alteração de endereço ou CNAE · nova filial · atualização cadastral · variação climática dentro do esperado |

---

## 14. Contrato de saída do motor

> **Implementação: Python, dentro do serviço Flask** (`api/`), conforme `00-decisoes.md` §D3.
> Os nomes de campo são os mesmos de `01-modelo-de-dados.md`, em português — aquele arquivo é o
> **contrato da API** e o JSON devolvido pelo Flask tem de bater campo a campo com ele.
> Convenção interna do Python em `snake_case`; a serialização para JSON usa **exatamente as
> chaves em camelCase do contrato TypeScript** (alias pydantic), sem exceção.

```python
def calcular_risco(fatos: FatosDoCliente, config: ScoringConfig | None = None) -> AvaliacaoDeRisco: ...
```

`AvaliacaoDeRisco` contém: `scoreCalculado`, `ratingCalculado`, `ratingFinal`, `vetosAtivos[]`,
`dimensoes[]` (com fatores), `pd` (`6m`/`12m`/`24m`), `riscoRJ`, `exposicao`, `stayPeriod?`,
`tendencia`, `redFlags[]`, `recomendacao` (código + ações parametrizadas), `evidencias[]`,
`auditoria` (fechamento das somas).

**Função pura, síncrona, sem I/O, sem leitura de relógio, sem aleatoriedade** — a data de
referência é parâmetro explícito, para que os testes sejam determinísticos e os snapshots
históricos recalculáveis. Coeficientes em `api/scoring/config.py`, nunca no corpo das funções.

### Testes obrigatórios (`pytest`, em `api/tests/`)

| Teste | Verifica |
|---|---|
| `test_pesos_somam_um` | Invariante I1 |
| `test_fechamento_de_soma` | Invariante I2 para os 18 clientes e todos os snapshots |
| `test_pd_monotonica` | Invariante I3 por varredura de 0 a 1000 |
| `test_ordem_das_pds` | Invariante I4 nas quatro tendências |
| `test_eixos_independentes` | Invariante I5 no dataset |
| `test_fechamento_de_deltas` | Invariante I6 em todo par de snapshots consecutivos |
| `test_determinismo` | Mesma entrada devolve saída idêntica em execuções repetidas |
| `test_vetos` | Cada gatilho força o rating correto e preserva `scoreCalculado` |
| `test_coberturas` | Extraconcursal nunca somada a concursal sem distinção |
| `test_contrato_json` | Chaves do JSON batem com os tipos de `01-modelo-de-dados.md` |
