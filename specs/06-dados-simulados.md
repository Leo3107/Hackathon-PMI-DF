# 06 — Dados simulados

> Dataset de demonstração do Lastro: **18 clientes de carteira + 4 prospects**, com histórico,
> eventos, alertas, evidências e trilha de auditoria. Vive em `api/data/`.
>
> **Regra central, inegociável:** este documento **não escreve score, PD, rating, red flag,
> recomendação, cobertura, natureza de garantia nem valor atualizado de garantia.** Escreve
> exclusivamente `FatosDoCliente` (spec 01) e a identidade do `Cliente`. Todo o resto é derivado
> por `scoring.calcular_risco`. Os números de score que aparecem aqui são **verificações de
> calibração feitas à mão pelas fórmulas da spec 02** — servem de teste de aceitação do dataset,
> não de dado persistido.
>
> Referências: `00-decisoes.md` (autoritativo) · `01-modelo-de-dados.md` (contrato de campos) ·
> `02-motor-de-risco.md` (toda a matemática) · `_desafio-pdf.txt` · `api/models/` (forma real)

---

## 1. Invariantes que este dataset precisa sustentar

| # | Invariante | Como o dataset a satisfaz |
|---|---|---|
| I2 | Σ impactos reconstrói o score | Conferido cliente a cliente na §7 |
| I3/I4 | Monotonia das PDs | Propriedade do motor; o dataset só precisa cobrir a faixa 253–977 |
| **I5** | **PD moderado + RJ alto** e **PD alto + RJ baixo** | `ipanema-graos` (PD12 9,85% · RJ12 **40,60%**) e `joao-camargo` (PD12 **31,26%** · RJ12 0,14%) |
| I6 | Σ deltas reconstrói a variação | Conferido na §9 para o par 712 → 604 |
| I10 | Aviso de dados simulados | Todo documento e toda `Evidencia` carrega `simulada = true` |

Cobertura de gatilhos de veto (spec 02 §8) — **os oito gatilhos são exercidos pelo dataset**:

| Gatilho | Quem o dispara |
|---|---|
| `VETO_RJ` | `ponta-verde` |
| `VETO_FALENCIA` | `rio-formoso` |
| `VETO_EMBARGO_GARANTIA` | `barra-do-ipe` |
| `VETO_CADASTRO_INAPTO` | prospect `beira-rio` |
| `VETO_LISTA_SUJA` | prospect `santa-helena-norte` |
| `VETO_FRAUDE` | prospect `santa-helena-norte` (composição de dois vetos na mesma ficha) |
| `TETO_EXEC_FISCAL` | `santa-vitoria-arroz` (B calculado → **C** final) |
| `TETO_CNDT` | `coop-vale-do-ivai` (B calculado → **C** final) |

---

## 2. Data de referência e calendário agrícola

**`dataReferencia` de todos os fatos atuais: `2026-09-12`.** O motor nunca lê o relógio.

| Marco | Janela adotada |
|---|---|
| Safra 2025/26 | Plantio out–nov/2025 · colheita fev–mai/2026 · **ciclo encerrado** na data de referência |
| Safra 2026/27 | **Plantio em curso** (set–nov/2026) · colheita fev–mai/2027 |
| Milho safrinha 2026 | Plantio jan–mar/2026 · colheita jun–ago/2026 |
| Café (Patrocínio/MG) | Colheita mai–ago/2026 encerrada; florada da safra 2027 em set/2026 |
| Cana (Sertãozinho/SP) | Safra 2026/27 em moagem desde abr/2026 |
| Arroz irrigado (RS) | Colheita fev–abr/2026; plantio 2026/27 a partir de out/2026 |
| Fruticultura (Petrolina/PE) | Ciclos escalonados o ano inteiro; irrigação integral |

Consequências obrigatórias: `safraReferencia = "2026/27"` para grãos em plantio; parcelas de custeio
2026/27 vencem **após** a colheita (mar–jun/2027); saldos de 2025/26 vencem out–nov/2026.

---

## 3. Estrutura de arquivos — `api/data/`

Python puro, `snake_case`, **um cliente por arquivo**, sem I/O e sem dependência de rede.

```
api/data/
  __init__.py                 # API pública do pacote (ver abaixo)
  _base.py                    # helpers: parcelas(), evid(), garantia(), operacao()
  catalogo.py                 # CLIENTES: list[Cliente] · PROSPECTS: list[Cliente]
  fontes.py                   # ROTULOS_FONTE: dict[FonteId, str] (14 fontes)
  eventos.py                  # EVENTOS: list[EventoDeRisco] (sem scoreApos/deltaScore)
  alertas.py                  # ALERTAS: list[Alerta]
  auditoria.py                # REGISTROS: list[RegistroAuditoria]
  clientes/
    __init__.py               # agrega FATOS e SNAPSHOTS de todos os módulos
    santa_ines.py
    vale_do_piquiri.py
    cerrado_norte.py
    rio_formoso.py
    barra_do_ipe.py
    alto_paranaiba.py
    serra_do_urucui.py
    sao_bento_bioenergia.py
    chapadao_algodoeira.py
    ponta_verde.py
    joao_camargo.py
    tres_barras.py
    ipanema_graos.py
    frutivale.py
    santa_vitoria_arroz.py
    dois_irmaos.py
    maria_nogueira.py
    coop_vale_do_ivai.py
  prospects/
    __init__.py
    nova_alianca.py
    ribeirao_claro.py
    beira_rio.py
    santa_helena_norte.py
```

Cada módulo de cliente expõe **exatamente três nomes**:

```python
CLIENTE: Cliente                      # identidade
FATOS: FatosDoCliente                 # snapshot atual, dataReferencia = 2026-09-12
SNAPSHOTS: list[SnapshotHistorico]    # 6 snapshots, do mais antigo ao mais recente;
                                      # o último é idêntico a FATOS
```

`api/data/__init__.py` expõe:

```python
CLIENTES: list[Cliente]
PROSPECTS: list[Cliente]
FATOS_POR_CLIENTE: dict[str, FatosDoCliente]
SNAPSHOTS_POR_CLIENTE: dict[str, list[SnapshotHistorico]]
EVENTOS_POR_CLIENTE: dict[str, list[EventoDeRisco]]
ALERTAS: list[Alerta]
REGISTROS_AUDITORIA: list[RegistroAuditoria]
def por_documento(doc: str) -> Cliente | None   # normaliza pontuação antes de comparar
```

**Proibições no pacote `data/`:** importar de `scoring/`; escrever `score`, `pd`, `rating`,
`redFlags`, `recomendacao`, `natureza` de garantia, `valorAtualizado` de garantia, `scoreApos`
ou `deltaScore`. Os dois últimos campos de `EventoDeRisco` são preenchidos **em runtime** pela
camada de serviço, recalculando o snapshot correspondente.

---

## 4. Metodologia de calibração

### C1 · Razão documentada de R$ por hectare

Custo de custeio da safra (insumos + defensivos + sementes + corretivos), preços de referência
de **agosto/2026**, em R$/ha. A **exposição da Krill Tech é uma fração desse custo**, porque a
Krill é um entre vários fornecedores do produtor.

| Cultura | Custeio R$/ha | Fonte narrativa da referência |
|---|---:|---|
| Soja | 5.200 | Pacote tecnológico médio Cerrado/Sul |
| Milho safrinha | 3.400 | Pacote reduzido, 2ª safra |
| Milho verão | 3.400 | Idem |
| Algodão | 14.500 | Alta demanda de defensivos e colheita mecanizada |
| Café arábica (formação/tratos) | 18.000 | Adubação parcelada + colheita |
| Cana-de-açúcar (tratos + renovação) | 9.000 | Ciclo de soca |
| Arroz irrigado | 8.500 | Custo de irrigação e secagem |
| Trigo | 3.100 | Ciclo de inverno |
| Fruticultura irrigada (manga/uva) | 32.000 | Alta intensidade de capital e mão de obra |
| Feijão | 4.100 | Ciclo curto, alta demanda de fungicida |

```
exposicaoTotal ≈ Σ (área_da_cultura_ha × custeio_R$/ha) × fraçãoKrill
```

`fraçãoKrill` fica entre **21% e 59%** e está declarada na ficha de cada cliente. Nenhuma ficha
pode violar essa razão em mais de ±5%.

### C2 · Coerência de patrimônio, capital e faturamento

- `faturamentoEstimadoAnual ≥ 1,1 × exposicaoTotal` para todo cliente **exceto** os em crise
  (`rio-formoso`, `ponta-verde`), onde a exposição chega a se aproximar do faturamento.
- `patrimonioDeclarado` é **patrimônio líquido**, não ativo bruto — por isso `tres-barras`
  (alavancado) tem patrimônio menor que a exposição, e é exatamente essa a causa do covenant rompido.
- `capitalSocial` de PJ ≈ 20%–45% do patrimônio. **Para PF não existe capital social**: o campo
  recebe o **patrimônio rural declarado no IRPF afetado à atividade**, que é o que o fator
  `capital_vs_exposicao` mede economicamente. Convenção documentada, obrigatória para as duas PFs.

### C3 · Calibração do score

O procedimento aplicado a cada cliente, e que deve ser refeito por quem alterar um fato:

1. Escrever os fatos.
2. Calcular os pontos de cada fator pelas fórmulas da spec 02 §4.
3. Somar penalidades e bônus por dimensão: `bruto = 1000 − Σpen + Σbon`.
4. `score_dim = clamp(bruto, 0, 1000)`.
5. `score = Σ score_dim × peso`.
6. Se o score não cair na faixa da persona, **ajustar os fatos** — nunca o motor, nunca a config.

**Saturação.** O clamp atua nos dois sentidos e o dataset a exercita de propósito:

- **Saturação superior** (`bruto > 1000`) é *estrutural* para clientes limpos: `todasCertidoesNegativas`
  vale +80 em D3 e, por definição, convive com zero penalidade fiscal — D3 fecha em 1080 e é
  cortada para 1000. O mesmo vale para D6 com `CAR ativo e regular` (+60 sem penalidade possível).
  A UI mostra `saturou = true` e o motor reescala os impactos daqueles fatores para 0 — comportamento
  correto e honesto: *a dimensão já estava no teto, o bônus não tinha para onde subir*.
- **Saturação inferior** (`bruto < 0`) ocorre em `rio-formoso` (D2), `barra-do-ipe` (D6) e
  `ponta-verde` (D1 e D2). São os casos que exercitam a redistribuição de `impactoGlobalAjustado`.

A §7 marca, cliente a cliente, quais dimensões saturam e em que direção.

### C4 · Protesto **não** é litígio

`protestosAtivos > 0` **não contradiz** `semLitigio36m = true`: protesto é ato **extrajudicial**
lavrado em cartório, não ação judicial. Quatro clientes A usam essa combinação de propósito
(`santa-ines`, `sao-bento-bioenergia`, `frutivale`, `maria-nogueira`). O que contradiz
`semLitigio36m` é execução, ação trabalhista, falência ou RJ. Ver a varredura na §12.

### C5 · Tempo de relacionamento

`anos_de_relacionamento` é derivado pelo motor da **operação aberta mais antiga** (`api/scoring/fatores.py`),
porque `FatosDoCliente` não carrega `inicioRelacionamento`. Logo, **`inicioRelacionamento` do
`Cliente` e a data da operação mais antiga são campos distintos com propósitos distintos**: o
primeiro é rótulo de UI, o segundo alimenta o fator `relacionamento`. As fichas declaram os dois.

---

## 5. Tabela consolidada dos 18 clientes

Score, rating, PD e risco de RJ abaixo são **verificações de calibração**, recalculadas pelo motor
em runtime. A coluna `Rating` traz `calculado → final` quando há veto.

| # | id | Razão social | Município/UF | Culturas | PJ/PF | Exposição | Score | Rating | PD 12m | RJ 12m | Tendência | Persona |
|---|---|---|---|---|---|---:|---:|---|---:|---:|---|---|
| 1 | `santa-ines` | Fazenda Santa Inês Agropecuária Ltda | Sorriso/MT | Soja · Milho safrinha · Algodão | PJ | 14.000.000 | **917,9** | A | 1,27% | 0,10% | estável | **Excelente A** |
| 2 | `vale-do-piquiri` | Agropecuária Vale do Piquiri Ltda | Campo Mourão/PR | Soja · Milho safrinha | PJ | 8.600.000 | **745,2** | B | 5,80% | 0,27% | estável | **Moderado B** |
| 3 | `cerrado-norte` | Cerrado Norte Agronegócios S.A. | Balsas/MA | Soja · Milho | PJ | 22.400.000 | **604,0** | B | 17,13% | 9,99% | deterioração acelerada | **Deterioração 712→604** |
| 4 | `rio-formoso` | Grupo Rio Formoso Comércio de Grãos Ltda | Formosa do Rio Preto/BA | Soja · Algodão | PJ | 11.800.000 | **253,6** | D | 56,26% | 44,70% | deterioração acelerada | **Crítico D + falência** |
| 5 | `barra-do-ipe` | Fazenda Barra do Ipê Agrícola Ltda | Querência/MT | Soja | PJ | 9.200.000 | **571,6** | C → **D** | 21,08% | 1,21% | deteriorando | **Veto: embargo IBAMA sobre garantia** |
| 6 | `alto-paranaiba` | Sementes e Café Alto Paranaíba Ltda | Patrocínio/MG | Café arábica | PJ | 6.400.000 | **766,2** | A | 4,86% | 12,85% | deterioração acelerada | **Nota boa, risco jurídico novo** |
| 7 | `serra-do-urucui` | Agropecuária Serra do Uruçuí Ltda | Uruçuí/PI | Soja · Milho | PJ | 12.600.000 | **592,3** | C | 18,51% | 0,75% | deteriorando | **Risco climático alto** |
| 8 | `sao-bento-bioenergia` | Usina São Bento Bioenergia S.A. | Sertãozinho/SP | Cana-de-açúcar | PJ | 26.500.000 | **865,9** | A | 2,03% | 0,10% | estável | **Sobrecolateralizado** |
| 9 | `chapadao-algodoeira` | Algodoeira Chapadão Grande S.A. | Primavera do Leste/MT | Algodão · Soja · Milho safrinha | PJ | 41.000.000 | **724,9** | B | 6,87% | 0,33% | deteriorando | **Exposição elevada (maior da carteira)** |
| 10 | `ponta-verde` | Agroindustrial Ponta Verde S.A. | Rio Verde/GO | Milho · Soja | PJ | 18.300.000 | **325,5** | D | 51,72% | **100%** | deterioração acelerada | **RJ em curso · Stay Period ativo** |
| 11 | `joao-camargo` | João Batista Moreira Camargo | Cristalina/GO | Soja · Milho safrinha | **PF** | 3.900.000 | **498,2** | C | **31,26%** | **0,14%** | deteriorando | **PF inelegível a RJ · I5 (PD alto / RJ baixo)** |
| 12 | `tres-barras` | Fazenda Três Barras Agropecuária Ltda | Não-Me-Toque/RS | Soja · Trigo · Milho | PJ | 7.100.000 | **735,3** | B | 6,30% | 2,00% | deteriorando | **Inadimplência técnica sem nenhum atraso** |
| 13 | `ipanema-graos` | Agrícola Ipanema Ltda | Barreiras/BA | Soja · Milho safrinha | PJ | 15.800.000 | **680,0** | B | **9,85%** | **40,60%** | deteriorando | **I5 (PD moderado / RJ alto)** |
| 14 | `frutivale` | Frutivale Agrícola do Vale Ltda | Petrolina/PE | Manga · Uva de mesa | PJ | 5.600.000 | **942,8** | A | 1,01% | 0,10% | melhorando | **Fruticultura irrigada em recuperação** |
| 15 | `santa-vitoria-arroz` | Arrozeira Santa Vitória Ltda | Uruguaiana/RS | Arroz irrigado · Soja | PJ | 6.800.000 | **723,4** | B → **C** | 6,96% | 8,77% | estável | **Teto por execução fiscal** |
| 16 | `dois-irmaos` | Agropastoril Dois Irmãos Ltda | Rondonópolis/MT | Soja · Milho safrinha | PJ | 10.400.000 | **696,9** | B | 8,62% | 0,67% | deteriorando | **Ruptura societária** |
| 17 | `maria-nogueira` | Maria Aparecida Ferreira Nogueira | Luís Eduardo Magalhães/BA | Soja · Algodão | **PF** | 4.700.000 | **924,7** | A | 1,19% | 0,10% | melhorando | **PF elegível a RJ (contraste com o #11)** |
| 18 | `coop-vale-do-ivai` | Cooperativa Agroindustrial Vale do Ivaí | Cascavel/PR | Soja · Milho safrinha · Trigo | PJ | 19.200.000 | **718,5** | B → **C** | 7,24% | 0,31% | estável | **Teto por CNDT positiva** |

### Agregados da carteira

| Métrica | Valor |
|---|---:|
| **Exposição total** | **R$ 244.300.000,00** |
| A vencer em 90 dias | R$ 114.850.000,00 |
| Em atraso | R$ 15.450.000,00 |
| Garantias extraconcursais (valor atualizado) | R$ 104.390.000,00 |
| Garantias concursais (valor atualizado) | R$ 80.300.000,00 |
| Cobertura extraconcursal da carteira | 42,73% |
| Cobertura total da carteira | 75,60% |
| Exposição em risco (sem qualquer garantia) | R$ 76.840.000,00 · 31,45% |
| **Exposição em risco em cenário de RJ** | **R$ 143.260.000,00 · 58,64%** |
| Clientes por rating final | **A 5 · B 6 · C 4 · D 3** |
| Exposição por rating final | A 57,2 MM · B 105,3 MM · C 42,5 MM · **D 39,3 MM** |

Concentração geográfica (R$ milhões): MT 74,6 · BA 32,3 · PR 27,8 · SP 26,5 · MA 22,4 ·
GO 22,2 · RS 13,9 · PI 12,6 · MG 6,4 · PE 5,6.

Concentração por cultura, rateada igualmente entre as culturas de cada cliente (R$ milhões):
Soja 94,0 · Milho safrinha 44,1 · Milho 29,0 · Algodão 26,6 · Cana 26,5 · Trigo 8,8 ·
Café 6,4 · Arroz 3,4 · Manga 2,8 · Uva 2,8.

### Recomendação esperada (derivada pela spec 02 §12 — conferência, não dado)

| Recomendação | Clientes | Prazo de reavaliação |
|---|---|---:|
| `SUSPENDER_EXPOSICAO` | `rio-formoso`, `barra-do-ipe`, `ponta-verde` | 7 d |
| `APROVAR_COM_RESTRICOES` | `serra-do-urucui`, `joao-camargo`, `santa-vitoria-arroz`, `coop-vale-do-ivai` (rating C) · `vale-do-piquiri`, `cerrado-norte`, `chapadao-algodoeira`, `tres-barras`, `dois-irmaos` (B com exposiçãoEmRiscoEmRJ > 40%) | 30 d / 90 d |
| `APROVAR_COM_MONITORAMENTO_INTENSIVO` | `ipanema-graos` | 90 d |
| `APROVAR_COM_REVISAO_DE_LIMITE` | `alto-paranaiba`, `frutivale`, `maria-nogueira` (A com utilização > 90%) | 180 d |
| `APROVAR` | `santa-ines`, `sao-bento-bioenergia` | 180 d |

---

## 6. Convenções de preenchimento

### 6.1 · Padrões do modelo

As fichas da §7 declaram **apenas os campos que divergem do padrão** de `api/models/fatos.py`.
Todo campo não citado está no padrão abaixo, e isso é normativo:

| Bloco | Padrões |
|---|---|
| `interno` | `atrasoMedioDias12m` 0 · `atrasoMedioDias90d` 0 · `piorAtrasoDias12m` 0 · `pctTitulosPagosEmDia12m` **1.0** · `renegociacoes12m` 0 · `semAtrasoRelevante24m` **false** · `covenantsRompidos` `[]` |
| `juridico` | todos os contadores e valores 0 · `pedidoFalencia` false · `recuperacaoJudicial` **null** · `semLitigio36m` false · `fraudeConfirmada` false · `listaSujaTrabalhoEscravo` false |
| `fiscal` | valores 0 · `cndtPositiva` false · `crfFgtsRegular` **true** · `parcelamentoRompido12m` false · `todasCertidoesNegativas` **false** |
| `agro` | `riscoZarc` **"baixo"** · percentuais 0 · `areaIrrigadaHa` 0 · `seguroAgricolaVigente` false · `culturas` `[]` |
| `cadastral` | `situacaoRfb` **"ATIVA"** · numéricos 0 · flags false · `cnaeCompativel` **true** · `tipoPessoa` null |
| `ambiental` | flags false · `situacaoCar` **"ATIVO_REGULAR"** · `sobreposicaoAppOuReserva` false |

Três campos são **obrigatórios em toda ficha**, mesmo quando coincidem com o padrão, porque o
motor os usa em fallback: `agro.culturas`, `agro.safraReferencia`, `cadastral.tipoPessoa`.

### 6.2 · Operações e parcelas

Toda ficha tem **três operações** e o seguinte cronograma canônico. `saldoDevedor` de cada
operação é **exatamente a soma das suas parcelas em aberto**, de modo que
`Σ saldoDevedor = exposicaoTotal` por construção.

| Parcela | Vencimento | Status | Operação | Papel |
|---|---|---|---|---|
| P0 | `2026-09-12 − diasAtraso` | `EM_ATRASO` | OP-1 | Saldo vencido da safra 2025/26 |
| P1 | `2026-10-28` | `A_VENCER` | OP-1 | 60% do a vencer em 90 dias |
| P2 | `2026-11-27` | `A_VENCER` | OP-2 | 40% do a vencer em 90 dias |
| P3 | `2027-03-30` | `A_VENCER` | OP-2 | 55% do a vencer fora da janela |
| P4 | `2027-06-30` | `A_VENCER` | OP-3 | 45% do a vencer fora da janela |

| Operação | Tipo | Descrição-modelo | `dataContratacao` |
|---|---|---|---|
| OP-1 | `VENDA_A_PRAZO` | "Fornecimento de insumos — saldo da safra 2025/26" | `2025-10-15` |
| OP-2 | `BARTER` ou `CPR` (ver ficha) | "Custeio da safra 2026/27 — <cultura principal>" | `2026-08-18` |
| OP-3 | `VENDA_A_PRAZO` | "Investimento em máquinas e estrutura" | **data da ficha** (a mais antiga) |

Ids: `OP-<ID_CLIENTE>-1..3`, parcelas `PAR-<ID_CLIENTE>-<n>`. A `dataContratacao` de OP-3 é o
campo que determina o fator `relacionamento` (ver C5) e está destacado em cada ficha.

**Barter.** Quando OP-2 é `BARTER`, `barter.sacasPrometidas × barter.precoReferenciaSaca` deve
ficar a menos de 2% do `saldoDevedor` de OP-2. Preços de referência de agosto/2026:
soja R$ 128,50/sc · milho R$ 62,00/sc · algodão R$ 405,00/@ · café R$ 1.980,00/sc.
`cprVinculadaId` aponta para uma garantia de tipo CPR **registrada** do próprio cliente — quando
ausente, o fator `barter_sem_lastro` dispara (é o caso de `rio-formoso`, `serra-do-urucui` e
`ponta-verde`, e **só** deles).

### 6.3 · Valores das parcelas

| id | P0 (dias) | P1 `2026-10-28` | P2 `2026-11-27` | P3 `2027-03-30` | P4 `2027-06-30` | OP-1 | OP-2 | OP-3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `santa-ines` | — | 2.520.000 | 1.680.000 | 5.390.000 | 4.410.000 | 2.520.000 | 7.070.000 | 4.410.000 |
| `vale-do-piquiri` | 500.000 (18 d) | 2.340.000 | 1.560.000 | 2.310.000 | 1.890.000 | 2.840.000 | 3.870.000 | 1.890.000 |
| `cerrado-norte` | 1.500.000 (27 d) | 7.080.000 | 4.720.000 | 5.005.000 | 4.095.000 | 8.580.000 | 9.725.000 | 4.095.000 |
| `rio-formoso` | 2.700.000 (62 d) | 3.840.000 | 2.560.000 | 1.485.000 | 1.215.000 | 6.540.000 | 4.045.000 | 1.215.000 |
| `barra-do-ipe` | 600.000 (23 d) | 1.860.000 | 1.240.000 | 3.025.000 | 2.475.000 | 2.460.000 | 4.265.000 | 2.475.000 |
| `alto-paranaiba` | — | 1.230.000 | 820.000 | 2.392.000 | 1.958.000 | 1.230.000 | 3.212.000 | 1.958.000 |
| `serra-do-urucui` | 1.200.000 (34 d) | 4.260.000 | 2.840.000 | 2.365.000 | 1.935.000 | 5.460.000 | 5.205.000 | 1.935.000 |
| `sao-bento-bioenergia` | — | 4.740.000 | 3.160.000 | 10.230.000 | 8.370.000 | 4.740.000 | 13.390.000 | 8.370.000 |
| `chapadao-algodoeira` | 2.400.000 (19 d) | 14.100.000 | 9.400.000 | 8.305.000 | 6.795.000 | 16.500.000 | 17.705.000 | 6.795.000 |
| `ponta-verde` | 4.100.000 (74 d) | 7.740.000 | 5.160.000 | 715.000 | 585.000 | 11.840.000 | 5.875.000 | 585.000 |
| `joao-camargo` | 450.000 (58 d) | 1.440.000 | 960.000 | 578.000 | 472.000 | 1.890.000 | 1.538.000 | 472.000 |
| `tres-barras` | — | 2.580.000 | 1.720.000 | 1.540.000 | 1.260.000 | 2.580.000 | 3.260.000 | 1.260.000 |
| `ipanema-graos` | — | 3.060.000 | 2.040.000 | 5.885.000 | 4.815.000 | 3.060.000 | 7.925.000 | 4.815.000 |
| `frutivale` | — | 1.020.000 | 680.000 | 2.145.000 | 1.755.000 | 1.020.000 | 2.825.000 | 1.755.000 |
| `santa-vitoria-arroz` | 300.000 (14 d) | 1.560.000 | 1.040.000 | 2.145.000 | 1.755.000 | 1.860.000 | 3.185.000 | 1.755.000 |
| `dois-irmaos` | 600.000 (21 d) | 3.600.000 | 2.400.000 | 2.090.000 | 1.710.000 | 4.200.000 | 4.490.000 | 1.710.000 |
| `maria-nogueira` | — | 900.000 | 600.000 | 1.760.000 | 1.440.000 | 900.000 | 2.360.000 | 1.440.000 |
| `coop-vale-do-ivai` | 1.100.000 (16 d) | 5.040.000 | 3.360.000 | 5.335.000 | 4.365.000 | 6.140.000 | 8.695.000 | 4.365.000 |

### 6.4 · Garantias

Ids `GAR-<ID_CLIENTE>-<n>`. **Escrever somente `tipo`, `descricao`, `valorDeclarado`,
`registrada` e `dataAvaliacao`.** `natureza` e `valorAtualizado` são derivados por
`models.tabelas` / `scoring.exposicao` (haircuts: AF 20% · CPR financeira 10% · CPR física 25% ·
penhor de safra 40% · penhor de máquina 35% · hipoteca 30% · aval 60%). `bemEmbargado` só é
escrito quando `true`.

`dataAvaliacao` = `2026-07-31` para todas as garantias, exceto as de `barra-do-ipe`
(`2026-08-24`, reavaliação após o embargo).

### 6.5 · Documentos

CPF/CNPJ fictícios com **dígito verificador válido** (conferidos). Todo cliente carrega
`nomeFantasia` quando aplicável e a marcação de dado simulado vem do banner global da aplicação
e do selo por evidência.

| id | Documento | id | Documento |
|---|---|---|---|
| `santa-ines` | 47.480.012/0001-24 | `joao-camargo` | 482.910.573-97 |
| `vale-do-piquiri` | 31.890.245/0001-65 | `tres-barras` | 12.975.603/0001-98 |
| `cerrado-norte` | 20.561.738/0001-35 | `ipanema-graos` | 45.621.889/0001-62 |
| `rio-formoso` | 39.204.471/0001-57 | `frutivale` | 21.890.345/0001-38 |
| `barra-do-ipe` | 28.615.390/0001-23 | `santa-vitoria-arroz` | 07.456.231/0001-53 |
| `alto-paranaiba` | 15.432.987/0001-90 | `dois-irmaos` | 36.510.872/0001-47 |
| `serra-do-urucui` | 44.107.266/0001-03 | `maria-nogueira` | 317.604.928-50 |
| `sao-bento-bioenergia` | 09.381.524/0001-44 | `coop-vale-do-ivai` | 04.827.196/0001-43 |
| `chapadao-algodoeira` | 26.734.091/0001-82 | `nova-alianca` | 50.139.428/0001-98 |
| `ponta-verde` | 33.849.157/0001-45 | `ribeirao-claro` | 38.726.514/0001-00 |
| | | `beira-rio` | 29.471.863/0001-29 |
| | | `santa-helena-norte` | 17.605.342/0001-38 |

---

## 7. Fichas dos 18 clientes

Legenda da **conta do score**: `pen` = Σ penalidades · `bon` = Σ bônus ·
`bruto = 1000 − pen + bon` · `score = clamp(bruto,0,1000)` · `contrib = score × peso`.
`Σ contrib` é o `scoreCalculado`. Tolerância de conferência: 0,1 ponto.

---

### 7.1 · `santa-ines` — Fazenda Santa Inês Agropecuária Ltda

**Persona:** cliente excelente, rating A. É a referência superior da carteira.

**Identidade.** CNPJ 47.480.012/0001-24 · PJ · Sorriso/MT · atividade "Produtor rural — grãos e
fibras" · CNAE 0115-6/00 (cultivo de soja) · culturas `["Soja","Milho safrinha","Algodão"]` ·
`inicioRelacionamento` 2016-03-14 · `estado` `ATIVO` · `origem` `CARTEIRA` ·
`nomeFantasia` "Fazenda Santa Inês".

**Área e razão R$/ha.** Soja 6.200 ha + milho safrinha 5.400 ha (sobre a área da soja) +
algodão 900 ha. Custeio = 6.200×5.200 + 5.400×3.400 + 900×14.500 = **R$ 63.650.000**.
`fraçãoKrill` = 22,0% → **R$ 14.003.000 ≈ R$ 14.000.000**. ✔

**Fatos (divergências do padrão).**

| Bloco | Campos |
|---|---|
| `interno` | `atrasoMedioDias12m` 5 · `atrasoMedioDias90d` 6 · `piorAtrasoDias12m` 18 · `pctTitulosPagosEmDia12m` 0,92 |
| `juridico` | `protestosAtivos` 2 · `protestos12m` 2 · `credoresProtestantes180d` 1 · `semLitigio36m` **true** |
| `fiscal` | `todasCertidoesNegativas` **true** |
| `agro` | `riscoZarc` "moderado" · `quebraSafraRegionalPct` 11 · `desvioPrecipitacaoPct` −24 · `produtividadeVsMediaRegionalPct` −5 · `areaTotalHa` 7.100 · `seguroAgricolaVigente` **true** · `safraReferencia` "2026/27" |
| `cadastral` | `anosAtividade` 14 · `capitalSocial` 11.000.000 · `qsaEstavel5anos` **true** · `anosAtividadeComprovada` 14 · `possuiInscricaoEstadual` true · `tipoPessoa` "PJ" |
| `ambiental` | — (todos no padrão: CAR ativo e regular) |
| topo | `limiteAprovado` 16.000.000 · `patrimonioDeclarado` 96.000.000 · `faturamentoEstimadoAnual` 78.000.000 |

**Operações.** OP-1 `VENDA_A_PRAZO` 2.520.000 · OP-2 **`BARTER`** 7.070.000, soja
55.020 sc × R$ 128,50 = R$ 7.070.070, `cprVinculadaId` = `GAR-SANTA-INES-1` ·
**OP-3 `VENDA_A_PRAZO` 4.410.000, `dataContratacao` `2023-08-15`** (dita `relacionamento`).

**Garantias.** `GAR-…-1` CPR_FINANCEIRA registrada R$ 6.500.000 ("CPR financeira nº 2026/0114 —
55.020 sc de soja") · `GAR-…-2` ALIENACAO_FIDUCIARIA R$ 3.200.000 ("Colheitadeira e plantadeira,
2 unidades") · `GAR-…-3` PENHOR_SAFRA R$ 5.000.000 ("Penhor da safra de algodão 2026/27").

**Conta do score.**

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 184,0 | 46,2 | 862,2 | 862,2 | 0,22 | 189,675 |
| jurídico | 90,0 | 60,0 | 970,0 | 970,0 | 0,20 | 194,000 |
| fiscal | 0,0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,14 | 140,000 |
| agroclimático | 248,0 | 160,0 | 912,0 | 912,0 | 0,15 | 136,800 |
| cadastral | 80,0 | 80,0 | 1000,0 | 1000,0 | 0,10 | 100,000 |
| ambiental | 0,0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 326,0 | 0,0 | 674,0 | 674,0 | 0,10 | 67,404 |
| | | | | | **Σ** | **917,88 → 917,9 · A** |

Fatores materializados: `atraso_medio` 60 · `pior_atraso` 90 · `pontualidade` 24 ·
`tendencia_atraso` 10 · `relacionamento` +46,2 · `protestos` 90 · `sem_litigio` +60 ·
`certidoes_negativas` +80 · `zarc_risco` 90 · `quebra_safra_regional` 66 ·
`desvio_precipitacao` 72 · `produtividade_abaixo` 20 · `irrigacao_ou_seguro` +100 ·
`diversificacao` +60 · `capital_vs_exposicao` 80 · `qsa_estavel` +80 · `car_regular` +60 ·
`descoberto_extraconcursal` 159,7 · `descoberto_total` 46,3 · `utilizacao_limite` 120.

Derivados de conferência: PD 0,64% / 1,27% / 2,32% · rjIndex 0,0 → RJ12 0,10% ·
cobertura extra 60,07% · cobertura total 81,50% · em risco R$ 2.590.000 ·
**em risco em RJ R$ 5.590.000** · utilização 87,5%.

---

### 7.2 · `vale-do-piquiri` — Agropecuária Vale do Piquiri Ltda

**Persona:** risco moderado B, estável. O "meio da carteira".

**Identidade.** CNPJ 31.890.245/0001-65 · PJ · Campo Mourão/PR · CNAE 0115-6/00 ·
culturas `["Soja","Milho safrinha"]` · `inicioRelacionamento` 2019-08-02 · `ATIVO` · `CARTEIRA`.

**Área e razão.** Soja 2.100 ha + milho safrinha 1.900 ha → 10.920.000 + 6.460.000 =
**R$ 17.380.000**; `fraçãoKrill` 49,5% → **R$ 8.603.100 ≈ R$ 8.600.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | `atrasoMedioDias12m` 12 · `atrasoMedioDias90d` 16 · `piorAtrasoDias12m` 38 · `pctTitulosPagosEmDia12m` 0,80 · `renegociacoes12m` 1 |
| `juridico` | `execucoesTitulo12m` 1 · `valorTotalEmExecucao` 520.000 · `credoresDistintosExecutando` 1 · `protestosAtivos` 2 · `protestos12m` 2 · `credoresProtestantes180d` 1 |
| `fiscal` | `dividaAtivaPgfn` 900.000 · `dividaAtivaPgfn90dAtras` 600.000 |
| `agro` | ZARC "moderado" · quebra 15 · precipitação −30 · produtividade −10 · `areaTotalHa` 2.100 · seguro **true** · safra "2026/27" |
| `cadastral` | anos 11 · capital 3.000.000 · `qsaEstavel5anos` true · comprovada 11 · IE true · PJ |
| `ambiental` | `situacaoCar` **"PENDENTE"** |
| topo | limite 9.200.000 · patrimônio 21.000.000 · faturamento 19.400.000 |

**Operações.** OP-1 2.840.000 (P0 500.000 com 18 dias de atraso) · OP-2 **`BARTER`** 3.870.000,
soja 30.116 sc × R$ 128,50 = R$ 3.869.906, `cprVinculadaId` = `GAR-VALE-DO-PIQUIRI-1` ·
**OP-3 1.890.000, `dataContratacao` `2024-07-10`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 3.600.000 · PENHOR_SAFRA R$ 4.600.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 494,0 | 32,6 | 538,6 | 538,6 | 0,22 | 118,494 |
| jurídico | 184,2 | 0 | 815,8 | 815,8 | 0,20 | 163,163 |
| fiscal | 142,3 | 0 | 857,7 | 857,7 | 0,14 | 120,074 |
| agroclimático | 310,0 | 100,0 | 790,0 | 790,0 | 0,15 | 118,500 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 444,9 | 0 | 555,1 | 555,1 | 0,10 | 55,512 |
| | | | | | **Σ** | **745,24 → 745,2 · B** |

PD 2,94% / 5,80% / 10,41% · rjIndex 8,9 → RJ12 0,27% · cobertura extra 37,67% · total 69,77% ·
em risco R$ 2.600.000 · **em risco em RJ R$ 5.360.000 (62,3%)** · utilização 93,5%.
Nenhuma dimensão satura.

---

### 7.3 · `cerrado-norte` — Cerrado Norte Agronegócios S.A.

**Persona:** deterioração. É o cliente da narrativa **712 → 604 em 60 dias** (§9) e o caso de
demonstração ao vivo do pitch.

**Identidade.** CNPJ 20.561.738/0001-35 · PJ · Balsas/MA (Matopiba) · CNAE 0115-6/00 ·
culturas `["Soja","Milho"]` · `inicioRelacionamento` 2017-11-06 · `estado` **`EM_OBSERVACAO`** ·
`CARTEIRA`.

**Área e razão.** Soja 9.800 ha + milho 4.200 ha → 50.960.000 + 14.280.000 = **R$ 65.240.000**;
`fraçãoKrill` 34,3% → **R$ 22.377.320 ≈ R$ 22.400.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atrasoMédio12m **11** · atrasoMédio90d **19** · pior 44 · pontualidade 0,78 · renegociações 1 |
| `juridico` | `execucoesTitulo12m` **3** · `execucoesTitulo90d` **2** · `valorTotalEmExecucao` 2.900.000 · `credoresDistintosExecutando` **3** · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 2 |
| `fiscal` | `dividaAtivaPgfn` **1.950.000** · `dividaAtivaPgfn90dAtras` 1.150.000 |
| `agro` | ZARC **"alto"** · quebra 19 · precipitação −31 · produtividade −11 · área 9.800 · safra "2026/27" |
| `cadastral` | anos 16 · capital 9.000.000 · qsa estável true · comprovada 16 · IE true · PJ |
| `ambiental` | CAR **"PENDENTE"** |
| topo | limite 23.000.000 · patrimônio 48.000.000 · faturamento 63.000.000 |

**Operações.** OP-1 8.580.000 (P0 1.500.000, 27 dias) · OP-2 **`BARTER`** 9.725.000, soja
75.681 sc × R$ 128,50 = R$ 9.724.008, `cprVinculadaId` = `GAR-CERRADO-NORTE-1` ·
**OP-3 4.095.000, `dataContratacao` `2024-03-20`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 7.400.000 · PENHOR_SAFRA R$ 9.500.000 ·
AVAL_FIANCA R$ 6.000.000 ("Aval dos sócios-administradores").

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 538,0 | 37,2 | 499,2 | 499,2 | 0,22 | 109,826 |
| jurídico | 571,8 | 0 | 428,2 | 428,2 | 0,20 | 85,643 |
| fiscal | 133,5 | 0 | 866,5 | 866,5 | 0,14 | 121,306 |
| agroclimático | 451,0 | 0 | 549,0 | 549,0 | 0,15 | 82,350 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 646,3 | 0 | 353,7 | 353,7 | 0,10 | 35,366 |
| | | | | | **Σ** | **603,99 → 604,0 · B** |

PD 11,50% / **17,13%** / 37,49% — bate com o valor ilustrativo do briefing para score 604 ·
rjIndex 43,7 → RJ12 9,99% · cobertura extra 29,73% · total 65,89% ·
em risco R$ 7.640.000 · **em risco em RJ R$ 15.740.000 (70,3%)** · utilização 97,4%.

---

### 7.4 · `rio-formoso` — Grupo Rio Formoso Comércio de Grãos Ltda

**Persona:** crítico D, com pedido de falência distribuído. Pior score da carteira.

**Identidade.** CNPJ 39.204.471/0001-57 · PJ · Formosa do Rio Preto/BA · CNAE 4622-2/00
(comércio atacadista de soja) · atividade "Produção e comércio de grãos" ·
culturas `["Soja","Algodão"]` · `inicioRelacionamento` 2021-05-19 · `estado` **`SUSPENSO`** ·
`CARTEIRA`.

**Área e razão.** Soja 4.500 ha + algodão 1.600 ha → 23.400.000 + 23.200.000 = **R$ 46.600.000**;
`fraçãoKrill` 25,3% → **R$ 11.789.800 ≈ R$ 11.800.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 24 · atraso90d 34 · pior 84 · pontualidade 0,56 · renegociações 2 · **`covenantsRompidos`** 1 item: `COV-RF-1` "Endividamento total acima de 2,5× o patrimônio líquido", limite "2,5×", apurado "3,4×", detecção `2026-03-04` |
| `juridico` | execuções12m **6** · execuções90d **3** · valor 7.100.000 · credores distintos **5** · protestos ativos 5 · protestos12m 7 · credoresProtestantes180d 4 · trabalhistas transitadas 2 · **`pedidoFalencia` true** |
| `fiscal` | dívida ativa 3.400.000 (90 d atrás 2.200.000) · **CNDT positiva** · débito trabalhista 980.000 · **CRF-FGTS irregular** · **parcelamento rompido** · execuções fiscais 3 / R$ 2.600.000 |
| `agro` | ZARC "alto" · quebra 27 · precipitação −38 · produtividade −19 · área 6.100 · safra "2026/27" |
| `cadastral` | anos 9 · capital 2.500.000 · **alteração societária 180d** · **saída de sócio majoritário** · comprovada 9 · IE true · PJ |
| `ambiental` | **auto de infração não quitado** · CAR "PENDENTE" |
| topo | limite 12.000.000 · patrimônio 14.000.000 · faturamento 17.500.000 |

**Operações.** OP-1 6.540.000 (P0 2.700.000, 62 dias) · OP-2 **`BARTER` sem lastro** 4.045.000,
soja 31.478 sc × R$ 128,50, **`cprVinculadaId` ausente** → dispara `barter_sem_lastro` ·
**OP-3 1.215.000, `dataContratacao` `2024-09-05`.**

**Garantias.** PENHOR_SAFRA R$ 4.000.000 · AVAL_FIANCA R$ 3.000.000. **Zero extraconcursal.**

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 922,0 | 30,3 | 108,3 | 108,3 | 0,22 | 23,819 |
| jurídico | 1430,0 | 0 | −430,0 | **0,0** ⬇satura | 0,20 | 0,000 |
| fiscal | 704,1 | 0 | 295,9 | 295,9 | 0,14 | 41,431 |
| agroclimático | 652,0 | 0 | 348,0 | 348,0 | 0,15 | 52,200 |
| cadastral | 370,0 | 0 | 630,0 | 630,0 | 0,10 | 63,000 |
| ambiental | 350,0 | 0 | 650,0 | 650,0 | 0,09 | 58,500 |
| garantias | 853,7 | 0 | 146,3 | 146,3 | 0,10 | 14,627 |
| | | | | | **Σ** | **253,58 → 253,6 · D** |

**Veto:** `VETO_FALENCIA` (força D — já era D). Relevante: o `scoreCalculado` continua visível.
PD 41,57% / 56,26% / 87,34% · **rjIndex 100,0 (teto)** → RJ12 44,70% · cobertura extra **0%** ·
total 30,51% · em risco R$ 8.200.000 · **em risco em RJ R$ 11.800.000 (100%)** · utilização 98,3%.
D2 satura para baixo: a redistribuição reescala os impactos jurídicos até fechar I2.

---

### 7.5 · `barra-do-ipe` — Fazenda Barra do Ipê Agrícola Ltda

**Persona:** **veto por embargo do IBAMA sobre imóvel dado em garantia.** Score calculado C,
classificação final D. É o caso nominado no briefing.

**Identidade.** CNPJ 28.615.390/0001-23 · PJ · Querência/MT · CNAE 0115-6/00 ·
culturas `["Soja"]` (monocultura) · `inicioRelacionamento` 2022-02-11 · `estado`
**`EM_OBSERVACAO`** · `CARTEIRA`.

**Área e razão.** Soja 5.200 ha → **R$ 27.040.000**; `fraçãoKrill` 34,0% →
**R$ 9.193.600 ≈ R$ 9.200.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 14 · atraso90d 20 · pior 45 · pontualidade 0,76 · renegociações 1 |
| `juridico` | execuções12m 2 · valor 900.000 · credores distintos 2 · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 2 |
| `fiscal` | dívida ativa 700.000 (90 d atrás 440.000) |
| `agro` | ZARC "alto" · quebra 18 · precipitação −28 · produtividade −12 · área 5.200 · safra "2026/27" · **sem seguro** |
| `cadastral` | anos 8 · capital 3.600.000 · qsa estável true · comprovada 8 · IE true · PJ |
| `ambiental` | **`embargoIbamaVigente` true** · **`embargoSobreImovelEmGarantia` true** · **auto de infração não quitado** · `situacaoCar` **"IRREGULAR"** · **`sobreposicaoAppOuReserva` true** |
| topo | limite 9.600.000 · patrimônio 27.000.000 · faturamento 15.800.000 |

**Operações.** OP-1 2.460.000 (P0 600.000, 23 dias) · OP-2 **`CPR`** 4.265.000 (sem bloco
`barter`) · **OP-3 2.475.000, `dataContratacao` `2024-11-12`.**

**Garantias.** `GAR-BARRA-DO-IPE-1` **HIPOTECA R$ 7.000.000** — "Matrícula 14.702, Fazenda Barra
do Ipê, gleba de 1.860 ha", **`bemEmbargado: true`** (é o imóvel alcançado pelo Termo de Embargo
do IBAMA) · `GAR-…-2` PENHOR_SAFRA R$ 2.600.000. **Zero extraconcursal.**

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 560,0 | 27,5 | 467,5 | 467,5 | 0,22 | 102,844 |
| jurídico | 269,1 | 0 | 730,9 | 730,9 | 0,20 | 146,174 |
| fiscal | 128,0 | 0 | 872,0 | 872,0 | 0,14 | 122,074 |
| agroclimático | 500,0 | 0 | 500,0 | 500,0 | 0,15 | 75,000 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 1030,0 | 0 | −30,0 | **0,0** ⬇satura | 0,09 | 0,000 |
| garantias | 674,5 | 0 | 325,5 | 325,5 | 0,10 | 32,554 |
| | | | | | **Σ** | **571,65 → 571,6 · C calculado** |

**Veto `VETO_EMBARGO_GARANTIA` → rating final D.** Esta é a ficha que a UI usa para mostrar
**SCORE CALCULADO 571,6 (C)** ao lado de **CLASSIFICAÇÃO FINAL D — garantia juridicamente
comprometida**. PD 12,73% / 21,08% / 40,59% · rjIndex 22,7 → RJ12 1,21% ·
cobertura extra **0%** · total 70,22% · em risco R$ 2.740.000 ·
**em risco em RJ R$ 9.200.000 (100%)** · utilização 95,8%.

---

### 7.6 · `alto-paranaiba` — Sementes e Café Alto Paranaíba Ltda

**Persona:** nota boa, **risco jurídico recém-surgido**. Score A (766,2) com dimensão jurídica em
330 e risco de RJ de 12,85%. É o cliente que mostra por que um número só não basta.

**Identidade.** CNPJ 15.432.987/0001-90 · PJ · Patrocínio/MG · CNAE 0134-2/00 (cultivo de café) ·
culturas `["Café arábica"]` · `inicioRelacionamento` 2014-09-30 · `ATIVO` · `CARTEIRA`.

**Área e razão.** Café 1.180 ha × 18.000 = **R$ 21.240.000**; `fraçãoKrill` 30,1% →
**R$ 6.393.240 ≈ R$ 6.400.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 6 · atraso90d 9 · pior 20 · pontualidade 0,90 |
| `juridico` | **execuções12m 3 · execuções90d 2** · valor 2.400.000 · **credores distintos 3** · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 2 |
| `fiscal` | `todasCertidoesNegativas` **true** |
| `agro` | ZARC "moderado" · quebra 14 · precipitação −25 · produtividade −6 · área 1.180 · seguro true · safra "2026/27" |
| `cadastral` | anos 22 · capital 4.000.000 · qsa estável true · comprovada 22 · IE true · PJ |
| `ambiental` | — (CAR regular) |
| topo | limite 7.000.000 · patrimônio 39.000.000 · faturamento 28.000.000 |

**Operações.** OP-1 1.230.000 · OP-2 **`BARTER`** 3.212.000, café 1.622 sc × R$ 1.980,00 =
R$ 3.211.560, `cprVinculadaId` = `GAR-ALTO-PARANAIBA-1` ·
**OP-3 1.958.000, `dataContratacao` `2024-05-08`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 3.900.000 · ALIENACAO_FIDUCIARIA R$ 1.800.000
("Duas colhedoras de café automotrizes") · PENHOR_SAFRA R$ 2.200.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 232,0 | 35,2 | 803,2 | 803,2 | 0,22 | 176,703 |
| jurídico | 670,0 | 0 | 330,0 | 330,0 | 0,20 | 66,000 |
| fiscal | 0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,14 | 140,000 |
| agroclimático | 333,0 | 100,0 | 767,0 | 767,0 | 0,15 | 115,050 |
| cadastral | 80,0 | 80,0 | 1000,0 | 1000,0 | 0,10 | 100,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 215,7 | 0 | 784,3 | 784,3 | 0,10 | 78,430 |
| | | | | | **Σ** | **766,18 → 766,2 · A** |

PD 3,19% / 4,86% / 11,71% · **rjIndex 46,8 → RJ12 12,85%** · cobertura extra 77,34% ·
total 97,97% · em risco R$ 130.000 · em risco em RJ R$ 1.450.000 · utilização 91,4% →
recomendação `APROVAR_COM_REVISAO_DE_LIMITE`.

---

### 7.7 · `serra-do-urucui` — Agropecuária Serra do Uruçuí Ltda

**Persona:** **risco climático alto**. Dimensão agroclimática em 118/1000 — a mais baixa da carteira.

**Identidade.** CNPJ 44.107.266/0001-03 · PJ · Uruçuí/PI (Matopiba) · CNAE 0115-6/00 ·
culturas `["Soja","Milho"]` · `inicioRelacionamento` 2018-04-25 · **`EM_OBSERVACAO`** · `CARTEIRA`.

**Área e razão.** Soja 4.800 ha + milho 1.600 ha → 24.960.000 + 5.440.000 = **R$ 30.400.000**;
`fraçãoKrill` 41,4% → **R$ 12.585.600 ≈ R$ 12.600.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 18 · atraso90d 26 · pior 52 · pontualidade 0,72 · renegociações 2 |
| `juridico` | execuções12m 1 · valor 300.000 · credores distintos 1 · protestos ativos 1 · protestos12m 1 · credoresProtestantes180d 1 |
| `fiscal` | dívida ativa 520.000 (igual 90 d atrás — **não crescente**) |
| `agro` | **ZARC "critico"** · **quebra 34** · **precipitação −50** · **produtividade −28** · área 4.800 · sem irrigação · sem seguro · safra "2026/27" |
| `cadastral` | anos 12 · capital 4.000.000 · qsa estável true · comprovada 12 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 12.800.000 · patrimônio 22.000.000 · faturamento 19.000.000 |

**Operações.** OP-1 5.460.000 (P0 1.200.000, 34 dias) · OP-2 **`BARTER` sem lastro** 5.205.000,
soja 40.506 sc × R$ 128,50, **sem `cprVinculadaId`** (a CPR do cliente é **física**, não vinculada
à operação) · **OP-3 1.935.000, `dataContratacao` `2024-10-01`.**

**Garantias.** CPR_FISICA R$ 5.200.000 · PENHOR_SAFRA R$ 4.800.000. **Zero extraconcursal** —
a CPR física é concursal por natureza (spec 02 §10).

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 700,0 | 29,2 | 329,2 | 329,2 | 0,22 | 72,424 |
| jurídico | 124,5 | 0 | 875,5 | 875,5 | 0,20 | 175,095 |
| fiscal | 20,6 | 0 | 979,4 | 979,4 | 0,14 | 137,111 |
| agroclimático | 882,0 | 0 | 118,0 | 118,0 | 0,15 | 17,700 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 795,5 | 0 | 204,5 | 204,5 | 0,10 | 20,452 |
| | | | | | **Σ** | **592,28 → 592,3 · C** |

PD 11,10% / 18,51% / 36,25% · rjIndex 18,3 → RJ12 0,75% · cobertura extra **0%** · total 53,81% ·
em risco R$ 5.820.000 · **em risco em RJ R$ 12.600.000 (100%)** · utilização 98,4%.

---

### 7.8 · `sao-bento-bioenergia` — Usina São Bento Bioenergia S.A.

**Persona:** **muitas garantias e sobrecolateralização.** Cobertura extraconcursal de 112,6% —
o único cliente com `exposicaoEmRiscoEmRJ` igual a zero.

**Identidade.** CNPJ 09.381.524/0001-44 · PJ · Sertãozinho/SP · CNAE 0113-0/00 (cultivo de
cana-de-açúcar) · atividade "Usina sucroenergética — cana própria e de fornecedores" ·
culturas `["Cana-de-açúcar"]` · `inicioRelacionamento` 2012-06-08 · `ATIVO` · `CARTEIRA`.

**Área e razão.** Cana 14.000 ha × 9.000 = **R$ 126.000.000**; `fraçãoKrill` 21,0% →
**R$ 26.460.000 ≈ R$ 26.500.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 9 · atraso90d 12 · pior 30 · pontualidade 0,86 · renegociações 1 |
| `juridico` | protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 1 · **`acoesTrabalhistasTransitadas` 3** · `semLitigio36m` **true** (ver C4: protesto é extrajudicial; as trabalhistas transitaram antes da janela de 36 meses) |
| `fiscal` | `todasCertidoesNegativas` **true** |
| `agro` | ZARC "moderado" · quebra 14 · precipitação −26 · produtividade −8 · **área 14.000 · irrigada 4.200 (30%)** · safra "2026/27" |
| `cadastral` | anos 31 · capital 85.000.000 · qsa estável true · comprovada 31 · IE true · PJ |
| `ambiental` | — (CAR regular) |
| topo | limite 40.000.000 · patrimônio 310.000.000 · faturamento 268.000.000 |

> ⚠ **Ponto de atenção da varredura (§12, item V6):** `semLitigio36m = true` coexistindo com
> `acoesTrabalhistasTransitadas = 3` só é coerente sob a leitura de que o campo mede **ações
> ajuizadas** nos últimos 36 meses. As três reclamações foram ajuizadas em 2020–2021 e o trânsito
> em julgado ocorreu em 2023-02. Esta é a leitura adotada e deve constar do rótulo da UI.

**Operações.** OP-1 4.740.000 · OP-2 **`CPR`** 13.390.000 · **OP-3 8.370.000,
`dataContratacao` `2023-11-22`.**

**Garantias.** ALIENACAO_FIDUCIARIA R$ 21.000.000 ("Duas colhedoras de cana e frota de
transbordo — 11 unidades") · CPR_FINANCEIRA registrada R$ 14.500.000 ·
HIPOTECA R$ 12.000.000 · PENHOR_MAQUINA R$ 6.000.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 390,0 | 42,1 | 652,1 | 652,1 | 0,22 | 143,461 |
| jurídico | 165,0 | 60,0 | 895,0 | 895,0 | 0,20 | 179,000 |
| fiscal | 0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,14 | 140,000 |
| agroclimático | 344,0 | 100,0 | 756,0 | 756,0 | 0,15 | 113,400 |
| cadastral | 0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,10 | 100,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 0 | 120,0 | 1120,0 | **1000,0** ⬆satura | 0,10 | 100,000 |
| | | | | | **Σ** | **865,86 → 865,9 · A** |

PD 1,02% / 2,03% / 3,70% · rjIndex 0,0 (com o redutor de patrimônio forte) → RJ12 0,10% ·
**cobertura extra 112,64% · total 159,06%** · em risco R$ 0 · **em risco em RJ R$ 0** ·
utilização 66,3%. Quatro dimensões saturam para cima — é o cliente que exercita a redistribuição
de bônus.

---

### 7.9 · `chapadao-algodoeira` — Algodoeira Chapadão Grande S.A.

**Persona:** **exposição elevada** — R$ 41.000.000, a maior da carteira (16,8% do total) e
R$ 23.700.000 de exposição desprotegida em cenário de RJ.

**Identidade.** CNPJ 26.734.091/0001-82 · PJ · Primavera do Leste/MT · CNAE 0116-4/01 (cultivo
de algodão herbáceo) · culturas `["Algodão","Soja","Milho safrinha"]` ·
`inicioRelacionamento` 2015-01-22 · `ATIVO` · `CARTEIRA`.

**Área e razão.** Algodão 5.600 ha + soja 8.900 ha + milho safrinha 6.000 ha →
81.200.000 + 46.280.000 + 20.400.000 = **R$ 147.880.000**; `fraçãoKrill` 27,7% →
**R$ 40.962.760 ≈ R$ 41.000.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 11 · atraso90d 15 · pior 34 · pontualidade 0,82 · renegociações 1 |
| `juridico` | execuções12m 2 · valor 1.800.000 · credores distintos 2 · **protestos ativos 3 · protestos12m 3** · credoresProtestantes180d 2 |
| `fiscal` | dívida ativa 2.400.000 (90 d atrás 1.600.000) |
| `agro` | ZARC "moderado" · quebra 17 · precipitação −27 · produtividade −9 · área 14.500 · seguro true · safra "2026/27" |
| `cadastral` | anos 19 · capital 12.000.000 · qsa estável true · comprovada 19 · IE true · PJ |
| `ambiental` | — (CAR regular) |
| topo | limite 42.000.000 · patrimônio 124.000.000 · faturamento 186.000.000 |

**Operações.** OP-1 16.500.000 (P0 2.400.000, 19 dias) · OP-2 **`BARTER`** 17.705.000, algodão
43.716 @ × R$ 405,00 = R$ 17.704.980, `cprVinculadaId` = `GAR-CHAPADAO-ALGODOEIRA-1` ·
**OP-3 6.795.000, `dataContratacao` `2024-06-18`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 13.000.000 · ALIENACAO_FIDUCIARIA R$ 7.000.000
("Colhedora de algodão e prensa enfardadeira") · PENHOR_SAFRA R$ 11.000.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 456,0 | 33,5 | 577,5 | 577,5 | 0,22 | 127,052 |
| jurídico | 372,6 | 0 | 627,4 | 627,4 | 0,20 | 125,488 |
| fiscal | 119,3 | 0 | 880,7 | 880,7 | 0,14 | 123,302 |
| agroclimático | 309,0 | 160,0 | 851,0 | 851,0 | 0,15 | 127,650 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 615,5 | 0 | 384,5 | 384,5 | 0,10 | 38,451 |
| | | | | | **Σ** | **724,94 → 724,9 · B** |

PD 4,01% / 6,87% / 14,49% · rjIndex 10,7 → RJ12 0,33% · cobertura extra 42,20% · total 58,29% ·
em risco R$ 17.100.000 · **em risco em RJ R$ 23.700.000 (57,8%)** · utilização 97,6%.

---

### 7.10 · `ponta-verde` — Agroindustrial Ponta Verde S.A.

**Persona:** **RJ em curso, Stay Period ativo.** É a ficha que liga o painel de Stay Period.

**Identidade.** CNPJ 33.849.157/0001-45 · PJ · Rio Verde/GO · CNAE 0111-3/02 (cultivo de milho) ·
culturas `["Milho","Soja"]` · `inicioRelacionamento` 2013-03-27 · `estado` **`RJ_EM_CURSO`** ·
`CARTEIRA`.

**Área e razão.** Milho 4.100 ha + soja 5.300 ha → 13.940.000 + 27.560.000 = **R$ 41.500.000**;
`fraçãoKrill` 44,1% → **R$ 18.301.500 ≈ R$ 18.300.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 34 · atraso90d 52 · pior 118 · pontualidade 0,44 · renegociações 2 · **`covenantsRompidos` 2 itens**: `COV-PV-1` "Índice de liquidez corrente inferior a 1,2" (apurado 0,71, detecção `2025-11-18`) e `COV-PV-2` "Endividamento líquido acima de 3,0× EBITDA" (apurado 5,4×, detecção `2026-02-09`) |
| `juridico` | execuções12m 2 · valor 4.800.000 · **credores distintos 4** · protestos ativos 3 · protestos12m 4 · credoresProtestantes180d 3 · trabalhistas 3 · **`recuperacaoJudicial`: `dataDistribuicao` `2026-06-23`, `dataDeferimento` `2026-07-08`, `diasProrrogadosStay` 0** |
| `fiscal` | dívida ativa 2.100.000 (90 d atrás 1.700.000) · **CNDT positiva** · débito trabalhista 1.400.000 · **CRF-FGTS irregular** · **parcelamento rompido** · execuções fiscais 2 / R$ 1.900.000 |
| `agro` | ZARC "moderado" · quebra 16 · precipitação −19 · produtividade −9 · área 5.300 · safra "2026/27" |
| `cadastral` | anos 21 · capital 7.000.000 · **alteração societária 180d** (troca do administrador em 2026-05) · comprovada 21 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 18.500.000 · patrimônio 26.000.000 · faturamento 41.000.000 |

**Stay Period conferido.** `dataDeferimento` 2026-07-08 → decorridos **66 dias** em 2026-09-12 →
restantes **114 dias** (180 + 0 − 66) → **ativo**. O painel deve listar como bloqueado: executar
garantias, protestar títulos, cobrar judicialmente; e como permitido: excutir a **alienação
fiduciária** (R$ 5.200.000 declarados / R$ 4.160.000 atualizados — crédito extraconcursal).

**Operações.** OP-1 11.840.000 (P0 4.100.000, 74 dias) · OP-2 **`BARTER` sem lastro** 5.875.000,
milho 94.758 sc × R$ 62,00, **sem `cprVinculadaId`** · **OP-3 585.000,
`dataContratacao` `2024-02-14`.**

**Garantias.** ALIENACAO_FIDUCIARIA R$ 5.200.000 ("Frota de caminhões graneleiros — 6 unidades") ·
PENHOR_SAFRA R$ 6.500.000 · AVAL_FIANCA R$ 4.000.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 1098,0 | 38,6 | −59,4 | **0,0** ⬇satura | 0,22 | 0,000 |
| jurídico | 1554,9 | 0 | −554,9 | **0,0** ⬇satura | 0,20 | 0,000 |
| fiscal | 617,4 | 0 | 382,6 | 382,6 | 0,14 | 53,567 |
| agroclimático | 379,0 | 0 | 621,0 | 621,0 | 0,15 | 93,150 |
| cadastral | 270,0 | 0 | 730,0 | 730,0 | 0,10 | 73,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 707,1 | 0 | 292,9 | 292,9 | 0,10 | 29,290 |
| | | | | | **Σ** | **325,51 → 325,5 · D** |

**Veto `VETO_RJ` → D.** PD 37,71% / 51,72% / 83,80% · **RJ12 = 100% (evento ocorrido**, não
probabilidade — rótulo distinto na UI; `rjIndex` 71,4 permanece visível como diagnóstico) ·
cobertura extra 22,73% · total 52,79% · em risco R$ 8.640.000 ·
**em risco em RJ R$ 14.140.000 (77,3%)** · utilização 98,9%.

---

### 7.11 · `joao-camargo` — João Batista Moreira Camargo

**Persona dupla:** **produtor rural PF não elegível a RJ** (Lei 14.112/2020) **e o lado
"PD alto / RJ baixo" da invariante I5.** As duas coisas são a mesma coisa: sem via de RJ, o risco
migra para execução individual.

**Identidade.** CPF 482.910.573-97 · **PF** · Cristalina/GO · atividade "Produtor rural pessoa
física — grãos" · CNAE 0115-6/00 · culturas `["Soja","Milho safrinha"]` ·
`inicioRelacionamento` 2024-01-15 · **`SUSPENSO`** · `CARTEIRA`.

**Área e razão.** Soja 900 ha + milho safrinha 700 ha → 4.680.000 + 2.380.000 = **R$ 7.060.000**;
`fraçãoKrill` 55,2% → **R$ 3.897.120 ≈ R$ 3.900.000**. ✔ (fração alta porque o produtor concentra
compras num único fornecedor — fato relevante para a análise.)

| Bloco | Campos |
|---|---|
| `interno` | atraso12m **32** · atraso90d **44** · pior **110** · pontualidade **0,42** · renegociações **3** |
| `juridico` | execuções12m 2 · valor 680.000 · **credores distintos 2** (abaixo do limiar de pluralidade — proposital) · protestos ativos 3 · protestos12m 3 · credoresProtestantes180d 2 |
| `fiscal` | dívida ativa 340.000 (90 d atrás 190.000) · **CRF-FGTS irregular** |
| `agro` | ZARC "moderado" · quebra 18 · precipitação −28 · produtividade −20 · área 900 · sem seguro · safra "2026/27" |
| `cadastral` | **`anosAtividade` 2,6** · `capitalSocial` **1.400.000** (patrimônio rural no IRPF — convenção C2) · **`possuiLivroCaixaDigital` false** · **`possuiInscricaoEstadual` false** · **`anosAtividadeComprovada` 1,4** · **`tipoPessoa` "PF"** |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 3.950.000 · patrimônio 9.400.000 · faturamento 6.800.000 |

**Elegibilidade a RJ (conferência).** `PF` **e** `anosAtividadeComprovada` 1,4 < 2,0 **e** sem
livro-caixa digital **e** sem inscrição estadual → **inelegível**. `rjIndexEfetivo` = 18,7 × 0,15
= **2,8** → RJ12 **0,14%**. A UI exibe: *"Não elegível a RJ — produtor rural PF sem 2 anos de
atividade comprovada (Lei 14.112/2020). Risco migra para execução individual."*

**Operações.** OP-1 1.890.000 (P0 450.000, 58 dias) · OP-2 **`CPR`** 1.538.000 ·
**OP-3 472.000, `dataContratacao` `2025-04-16`.**

**Garantias.** PENHOR_SAFRA R$ 2.600.000 · AVAL_FIANCA R$ 1.200.000. **Zero extraconcursal.**

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 924,0 | 21,1 | 97,1 | 97,1 | 0,22 | 21,364 |
| jurídico | 424,7 | 0 | 575,3 | 575,3 | 0,20 | 115,051 |
| fiscal | 253,6 | 0 | 746,4 | 746,4 | 0,14 | 104,497 |
| agroclimático | 362,0 | 0 | 638,0 | 638,0 | 0,15 | 95,700 |
| cadastral | 350,0 | 0 | 650,0 | 650,0 | 0,10 | 65,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 799,2 | 0 | 200,8 | 200,8 | 0,10 | 20,077 |
| | | | | | **Σ** | **498,19 → 498,2 · C** |

**I5, lado B:** PD 12m **31,26%** (alto) · RJ 12m **0,14%** (baixo). Comparar lado a lado com
`ipanema-graos` (§7.13).

---

### 7.12 · `tres-barras` — Fazenda Três Barras Agropecuária Ltda

**Persona:** **inadimplência técnica sem nenhum atraso financeiro.** O caso que prova a tese do
produto: dimensão comportamental em 870,6 com **zero dias de atraso** e ainda assim uma red flag
de severidade ALTA, porque dois covenants estão rompidos e vigentes.

**Identidade.** CNPJ 12.975.603/0001-98 · PJ · Não-Me-Toque/RS · CNAE 0115-6/00 ·
culturas `["Soja","Trigo","Milho"]` · `inicioRelacionamento` 2016-08-09 · **`EM_OBSERVACAO`** ·
`CARTEIRA`.

**Área e razão.** Soja 1.900 ha + trigo 1.100 ha + milho 400 ha → 9.880.000 + 3.410.000 +
1.360.000 = **R$ 14.650.000**; `fraçãoKrill` 48,5% → **R$ 7.105.250 ≈ R$ 7.100.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | **`atrasoMedioDias12m` 0 · `atrasoMedioDias90d` 0 · `piorAtrasoDias12m` 0 · `pctTitulosPagosEmDia12m` 1,0 · `renegociacoes12m` 0 · `semAtrasoRelevante24m` true** · **`covenantsRompidos` 2 itens**: `COV-TB-1` "Endividamento total acima de 2,5× o patrimônio líquido" (limite "2,5×", apurado "**2,53×**", detecção `2026-03-19`) e `COV-TB-2` "Manutenção de seguro agrícola vigente sobre a área financiada" (limite "100% da área", apurado "0% — apólice não renovada", detecção `2026-06-27`) |
| `juridico` | **nenhuma divergência — a dimensão jurídica fecha em 1000 sem nenhum fator materializado** |
| `fiscal` | dívida ativa 3.000.000 (90 d atrás 1.350.000) |
| `agro` | **ZARC "critico"** · quebra 18 · precipitação −28 · produtividade −10 · área 2.300 · **sem seguro** (é o covenant `COV-TB-2`) · safra "2026/27" |
| `cadastral` | anos 13 · capital 1.200.000 · qsa estável true · comprovada 13 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 7.200.000 · **patrimônio 3.400.000** (líquido — é a causa do `COV-TB-1`) · faturamento 16.200.000 |

**Zero atraso, zero parcela vencida.** `P0` não existe; `emAtraso` = R$ 0. Esta ficha é o teste
de que a red flag de inadimplência técnica dispara **antes** de qualquer sinal financeiro.

**Operações.** OP-1 2.580.000 · OP-2 **`CPR`** 3.260.000 · **OP-3 1.260.000,
`dataContratacao` `2024-08-28`.**

**Garantias.** Única: PENHOR_SAFRA R$ 3.900.000. **Zero extraconcursal.**

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 240,0 | 110,6 | 870,6 | 870,6 | 0,22 | 191,531 |
| jurídico | 0 | 0 | 1000,0 | 1000,0 | 0,20 | 200,000 |
| fiscal | 301,3 | 0 | 698,7 | 698,7 | 0,14 | 97,823 |
| agroclimático | 552,0 | 60,0 | 508,0 | 508,0 | 0,15 | 76,200 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 997,6 | 0 | 2,4 | 2,4 | 0,10 | 0,239 |
| | | | | | **Σ** | **735,29 → 735,3 · B** |

Únicos fatores de D1: `inadimplencia_tecnica` **240** (2 × 120), `relacionamento` +30,6,
`historico_limpo` +80. PD 3,68% / 6,30% / 13,35% · rjIndex 27,4 (com o sinal
`covenant_rompido` = 8) → RJ12 2,00% · cobertura extra **0%** · total 32,96% ·
em risco R$ 4.760.000 · **em risco em RJ R$ 7.100.000 (100%)** · utilização 98,6%.

---

### 7.13 · `ipanema-graos` — Agrícola Ipanema Ltda

**Persona:** **lado A da invariante I5 — PD moderado com risco de RJ alto.** Paga a Krill Tech
praticamente em dia (dimensão comportamental 882,9) e ao mesmo tempo tem **quatro credores
distintos executando R$ 7,9 milhões** — o precursor clássico de insolvência coletiva.

**Identidade.** CNPJ 45.621.889/0001-62 · PJ · Barreiras/BA · CNAE 0115-6/00 ·
culturas `["Soja","Milho safrinha"]` · `inicioRelacionamento` 2014-10-17 · **`EM_OBSERVACAO`** ·
`CARTEIRA`.

**Área e razão.** Soja 5.100 ha + milho safrinha 2.000 ha → 26.520.000 + 6.800.000 =
**R$ 33.320.000**; `fraçãoKrill` 47,4% → **R$ 15.793.680 ≈ R$ 15.800.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m **5** · atraso90d **5** · pior 15 · pontualidade **0,94** |
| `juridico` | **execuções12m 4 · execuções90d 2** · **valor 7.900.000** (50% da exposição → `materialidade_execucao` no teto) · **credores distintos 4** · protestos ativos 3 · protestos12m 3 · **credoresProtestantes180d 3** |
| `fiscal` | dívida ativa 2.900.000 (igual 90 d atrás — **não crescente**) · **parcelamento rompido** |
| `agro` | **ZARC "alto"** · quebra 15 · precipitação −30 · produtividade −9 · área 5.100 · seguro true · safra "2026/27" |
| `cadastral` | anos 17 · capital 8.500.000 · qsa estável true · comprovada 17 · IE true · PJ |
| `ambiental` | — (CAR regular) |
| topo | limite 17.000.000 · patrimônio 34.000.000 · faturamento 29.000.000 |

**Operações.** OP-1 3.060.000 (sem parcela vencida) · OP-2 **`BARTER`** 7.925.000, soja
61.673 sc × R$ 128,50 = R$ 7.925.980, `cprVinculadaId` = `GAR-IPANEMA-GRAOS-1` ·
**OP-3 4.815.000, `dataContratacao` `2024-04-22`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 8.600.000 · ALIENACAO_FIDUCIARIA R$ 3.400.000 ·
PENHOR_SAFRA R$ 4.200.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 153,0 | 35,9 | 882,9 | 882,9 | 0,22 | 194,227 |
| jurídico | 915,0 | 0 | 85,0 | 85,0 | 0,20 | 17,000 |
| fiscal | 241,8 | 0 | 758,2 | 758,2 | 0,14 | 106,152 |
| agroclimático | 416,0 | 100,0 | 684,0 | 684,0 | 0,15 | 102,600 |
| cadastral | 80,0 | 80,0 | 1000,0 | 1000,0 | 0,10 | 100,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 299,8 | 0 | 700,2 | 700,2 | 0,10 | 70,019 |
| | | | | | **Σ** | **680,00 · B** |

**Sinais de RJ (soma 75,0):** pluralidade de credores 20 · endividamento judicializado 25 (teto) ·
protestos de credores distintos 12 (teto) · dívida ativa ÷ faturamento 4,0 ·
estresse agroclimático 8 · parcelamento rompido 6.
**I5, lado A:** PD 12m **9,85%** (moderado) · RJ 12m **40,60%** (alto).

---

### 7.14 · `frutivale` — Frutivale Agrícola do Vale Ltda

**Persona:** fruticultura irrigada do Vale do São Francisco, **em recuperação** (tendência
`melhorando`, +55,8 pontos em 90 dias). Único cliente com irrigação integral.

**Identidade.** CNPJ 21.890.345/0001-38 · PJ · Petrolina/PE · CNAE 0133-4/99 (cultivo de frutas
de lavoura permanente) · culturas `["Manga","Uva de mesa"]` · `inicioRelacionamento` 2018-11-23 ·
`ATIVO` · `CARTEIRA`.

**Área e razão.** Manga 210 ha + uva 95 ha = 305 ha × 32.000 = **R$ 9.760.000**;
`fraçãoKrill` 57,4% → **R$ 5.602.240 ≈ R$ 5.600.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 5 · atraso90d 4 · pior 16 · pontualidade 0,92 |
| `juridico` | protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 1 · `semLitigio36m` **true** |
| `fiscal` | `todasCertidoesNegativas` **true** |
| `agro` | ZARC **"baixo"** · quebra 9 · precipitação −18 · produtividade −3 · **área 305 · irrigada 305 (100%)** · seguro true · safra "2026/27" |
| `cadastral` | anos 17 · capital 3.200.000 · qsa estável true · comprovada 17 · IE true · PJ |
| `ambiental` | — (CAR regular) |
| topo | limite 6.000.000 · patrimônio 62.000.000 · faturamento 48.000.000 |

**Operações.** OP-1 1.020.000 · OP-2 **`CPR`** 2.825.000 · **OP-3 1.755.000,
`dataContratacao` `2024-01-30`.**

**Garantias.** ALIENACAO_FIDUCIARIA R$ 3.000.000 ("Sistema de irrigação por gotejamento e
packing house") · CPR_FINANCEIRA registrada R$ 2.200.000 · HIPOTECA R$ 4.000.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 164,0 | 39,3 | 875,3 | 875,3 | 0,22 | 192,557 |
| jurídico | 90,0 | 60,0 | 970,0 | 970,0 | 0,20 | 194,000 |
| fiscal | 0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,14 | 140,000 |
| agroclimático | 120,0 | 100,0 | 980,0 | 980,0 | 0,15 | 147,000 |
| cadastral | 80,0 | 80,0 | 1000,0 | 1000,0 | 0,10 | 100,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 207,1 | 0 | 792,9 | 792,9 | 0,10 | 79,286 |
| | | | | | **Σ** | **942,84 → 942,8 · A** |

PD 0,43% / 1,01% / 1,61% (tendência `melhorando` puxa PD6 e PD24 para baixo) · RJ12 0,10% ·
cobertura extra 78,21% · **total 128,21%** · em risco R$ 0 · em risco em RJ R$ 1.220.000 ·
utilização 93,3%.

---

### 7.15 · `santa-vitoria-arroz` — Arrozeira Santa Vitória Ltda

**Persona:** **teto por execução fiscal.** Score B (723,4), rating final **C**, porque
R$ 3.700.000 de execuções fiscais superam 50% da exposição de R$ 6.800.000. Demonstra teto C sem
força D.

**Identidade.** CNPJ 07.456.231/0001-53 · PJ · Uruguaiana/RS · CNAE 0111-3/01 (cultivo de arroz) ·
culturas `["Arroz irrigado","Soja"]` · `inicioRelacionamento` 2011-07-05 · **`EM_OBSERVACAO`** ·
`CARTEIRA`.

**Área e razão.** Arroz 1.350 ha × 8.500 + soja 600 ha × 5.200 = 11.475.000 + 3.120.000 =
**R$ 14.595.000**; `fraçãoKrill` 46,6% → **R$ 6.801.270 ≈ R$ 6.800.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 10 · atraso90d 12 · pior 32 · pontualidade 0,84 · renegociações 1 |
| `juridico` | execuções12m 1 · valor 290.000 · credores distintos 1 · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 1 |
| `fiscal` | **dívida ativa 3.800.000** (igual 90 d atrás) · **parcelamento rompido** · **`execucoesFiscais` 4 · `valorExecucoesFiscais` 3.700.000** |
| `agro` | ZARC "moderado" · quebra 13 · precipitação −22 · produtividade −8 · **área 1.950 · irrigada 1.350 (69%)** · safra "2026/27" |
| `cadastral` | anos 24 · capital 2.200.000 · qsa estável true · comprovada 24 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 7.000.000 · patrimônio 28.000.000 · faturamento 21.000.000 |

**Conferência do teto.** 3.700.000 > 0,50 × 6.800.000 = 3.400.000 → **`TETO_EXEC_FISCAL` ativo**.

**Operações.** OP-1 1.860.000 (P0 300.000, 14 dias) · OP-2 **`CPR`** 3.185.000 ·
**OP-3 1.755.000, `dataContratacao` `2024-09-19`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 2.600.000 · PENHOR_MAQUINA R$ 2.400.000 ·
PENHOR_SAFRA R$ 2.000.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 408,0 | 29,7 | 621,7 | 621,7 | 0,22 | 136,772 |
| jurídico | 177,1 | 0 | 822,9 | 822,9 | 0,20 | 164,588 |
| fiscal | 429,4 | 0 | 570,6 | 570,6 | 0,14 | 79,882 |
| agroclimático | 266,0 | 100,0 | 834,0 | 834,0 | 0,15 | 125,100 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 524,9 | 0 | 475,1 | 475,1 | 0,10 | 47,515 |
| | | | | | **Σ** | **723,36 → 723,4 · B calculado → C final** |

PD 3,54% / 6,96% / 12,43% · rjIndex 42,2 → RJ12 8,77% · cobertura extra 34,41% · total 75,00% ·
em risco R$ 1.700.000 · em risco em RJ R$ 4.460.000 · utilização 97,1%.

---

### 7.16 · `dois-irmaos` — Agropastoril Dois Irmãos Ltda

**Persona:** **ruptura societária.** Alteração societária e saída de sócio majoritário nos últimos
12 meses, com deterioração comportamental acompanhando. Dimensão cadastral em 630.

**Identidade.** CNPJ 36.510.872/0001-47 · PJ · Rondonópolis/MT · CNAE 0115-6/00 ·
atividade "Produtor rural — grãos e pecuária de corte" · culturas `["Soja","Milho safrinha"]` ·
`inicioRelacionamento` 2017-02-28 · **`EM_OBSERVACAO`** · `CARTEIRA`.

**Área e razão.** Soja 3.100 ha + milho safrinha 2.600 ha → 16.120.000 + 8.840.000 =
**R$ 24.960.000**; `fraçãoKrill` 41,7% → **R$ 10.408.320 ≈ R$ 10.400.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 12 · atraso90d 18 · pior 36 · pontualidade 0,81 · renegociações 1 |
| `juridico` | execuções12m 1 · valor 560.000 · credores distintos 1 · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 2 |
| `fiscal` | dívida ativa 900.000 (90 d atrás 520.000) |
| `agro` | ZARC "moderado" · quebra 15 · precipitação −26 · produtividade −11 · área 3.100 · seguro true · safra "2026/27" |
| `cadastral` | anos 15 · capital 2.800.000 · **`alteracaoSocietaria180d` true** · **`saidaSocioMajoritario12m` true** · `qsaEstavel5anos` **false** · comprovada 15 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 10.600.000 · patrimônio 24.000.000 · faturamento 22.500.000 |

**Operações.** OP-1 4.200.000 (P0 600.000, 21 dias) · OP-2 **`BARTER`** 4.490.000, soja
34.941 sc × R$ 128,50 = R$ 4.489.919, `cprVinculadaId` = `GAR-DOIS-IRMAOS-1` ·
**OP-3 1.710.000, `dataContratacao` `2024-12-03`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 4.000.000 · PENHOR_SAFRA R$ 5.200.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 501,0 | 26,6 | 525,6 | 525,6 | 0,22 | 115,635 |
| jurídico | 181,5 | 0 | 818,5 | 818,5 | 0,20 | 163,692 |
| fiscal | 133,3 | 0 | 866,7 | 866,7 | 0,14 | 121,342 |
| agroclimático | 302,0 | 100,0 | 798,0 | 798,0 | 0,15 | 119,700 |
| cadastral | 370,0 | 0 | 630,0 | 630,0 | 0,10 | 63,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 630,0 | 0 | 370,0 | 370,0 | 0,10 | 37,000 |
| | | | | | **Σ** | **696,87 → 696,9 · B** |

PD 5,05% / 8,62% / 18,00% · rjIndex 17,3 → RJ12 0,67% · cobertura extra 34,62% · total 64,62% ·
em risco R$ 3.680.000 · **em risco em RJ R$ 6.800.000 (65,4%)** · utilização 98,1%.

---

### 7.17 · `maria-nogueira` — Maria Aparecida Ferreira Nogueira

**Persona:** **produtora rural PF elegível a RJ** — o contraste direto com `joao-camargo`.
Mesma natureza jurídica, elegibilidade oposta, porque tem 9 anos de atividade comprovada,
livro-caixa digital e inscrição estadual.

**Identidade.** CPF 317.604.928-50 · **PF** · Luís Eduardo Magalhães/BA · atividade "Produtora
rural pessoa física — grãos e fibras" · CNAE 0115-6/00 · culturas `["Soja","Algodão"]` ·
`inicioRelacionamento` 2017-06-12 · `ATIVO` · `CARTEIRA`.

**Área e razão.** Soja 1.400 ha + algodão 380 ha → 7.280.000 + 5.510.000 = **R$ 12.790.000**;
`fraçãoKrill` 36,8% → **R$ 4.706.720 ≈ R$ 4.700.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 5 · atraso90d 5 · pior 16 · pontualidade 0,93 |
| `juridico` | protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 1 · `semLitigio36m` **true** |
| `fiscal` | `todasCertidoesNegativas` **true** |
| `agro` | ZARC "moderado" · quebra 11 · precipitação −22 · produtividade −4 · área 1.780 · seguro true · safra "2026/27" |
| `cadastral` | anos 9 · `capitalSocial` **12.000.000** (patrimônio rural IRPF — convenção C2) · **`possuiLivroCaixaDigital` true** · **`possuiInscricaoEstadual` true** · **`anosAtividadeComprovada` 9** · `qsaEstavel5anos` false (não se aplica a PF) · **`tipoPessoa` "PF"** |
| `ambiental` | — (CAR regular) |
| topo | limite 5.200.000 · patrimônio 31.000.000 · faturamento 14.600.000 |

**Elegibilidade a RJ (conferência).** PF **e** 9 ≥ 2 anos comprovados **e** (livro-caixa digital
**ou** IE) → **elegível**. Nenhuma atenuação aplicada; `rjIndexEfetivo` = `rjIndex` = 0,0.

**Operações.** OP-1 900.000 · OP-2 **`BARTER`** 2.360.000, soja 18.366 sc × R$ 128,50 =
R$ 2.360.031, `cprVinculadaId` = `GAR-MARIA-NOGUEIRA-1` · **OP-3 1.440.000,
`dataContratacao` `2024-02-26`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 2.800.000 · ALIENACAO_FIDUCIARIA R$ 1.400.000 ·
PENHOR_SAFRA R$ 1.600.000.

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 161,0 | 38,2 | 877,2 | 877,2 | 0,22 | 192,973 |
| jurídico | 90,0 | 60,0 | 970,0 | 970,0 | 0,20 | 194,000 |
| fiscal | 0 | 80,0 | 1080,0 | **1000,0** ⬆satura | 0,14 | 140,000 |
| agroclimático | 238,0 | 100,0 | 862,0 | 862,0 | 0,15 | 129,300 |
| cadastral | 0 | 0 | 1000,0 | 1000,0 | 0,10 | 100,000 |
| ambiental | 0 | 60,0 | 1060,0 | **1000,0** ⬆satura | 0,09 | 90,000 |
| garantias | 215,5 | 0 | 784,5 | 784,5 | 0,10 | 78,447 |
| | | | | | **Σ** | **924,72 → 924,7 · A** |

PD 0,51% / 1,19% / 1,90% · RJ12 0,10% · cobertura extra 77,45% · total 97,87% ·
em risco R$ 100.000 · em risco em RJ R$ 1.060.000 · utilização 90,4% →
`APROVAR_COM_REVISAO_DE_LIMITE`.

---

### 7.18 · `coop-vale-do-ivai` — Cooperativa Agroindustrial Vale do Ivaí

**Persona:** **teto por CNDT positiva.** Score B (718,5), rating final **C**, porque o débito
trabalhista de R$ 2.150.000 supera 15% do patrimônio declarado de R$ 7.400.000 (limiar
R$ 1.110.000). Também o maior faturamento relativo da carteira — é uma cooperativa que repassa
insumos aos cooperados.

**Identidade.** CNPJ 04.827.196/0001-43 · PJ · Cascavel/PR · CNAE 0115-6/00 · atividade
"Cooperativa agroindustrial — recebimento de grãos e revenda de insumos" ·
culturas `["Soja","Milho safrinha","Trigo"]` · `inicioRelacionamento` 2009-04-16 ·
**`EM_OBSERVACAO`** · `CARTEIRA`.

**Área e razão.** Área agregada dos cooperados atendidos pela linha: soja 4.700 ha +
milho safrinha 3.900 ha + trigo 2.800 ha → 24.440.000 + 13.260.000 + 8.680.000 =
**R$ 46.380.000**; `fraçãoKrill` 41,4% → **R$ 19.201.320 ≈ R$ 19.200.000**. ✔

| Bloco | Campos |
|---|---|
| `interno` | atraso12m 11 · atraso90d 14 · pior 33 · pontualidade 0,83 |
| `juridico` | execuções12m 1 · valor 520.000 · credores distintos 1 · protestos ativos 2 · protestos12m 2 · credoresProtestantes180d 2 · **trabalhistas transitadas 3** |
| `fiscal` | dívida ativa 1.900.000 (90 d atrás 1.200.000) · **`cndtPositiva` true** · **`valorDebitoTrabalhista` 2.150.000** |
| `agro` | ZARC "moderado" · quebra 14 · precipitação −23 · produtividade −7 · área 7.500 · seguro true · safra "2026/27" |
| `cadastral` | anos 37 · capital 4.200.000 · qsa estável true · comprovada 37 · IE true · PJ |
| `ambiental` | CAR "PENDENTE" |
| topo | limite 19.800.000 · **patrimônio 7.400.000** · faturamento 96.000.000 |

**Conferência do teto.** 2.150.000 > 0,15 × 7.400.000 = 1.110.000 → **`TETO_CNDT` ativo**.
Note que `semLitigio36m` é **false** aqui (há execução e trabalhistas) — coerência verificada.

**Operações.** OP-1 6.140.000 (P0 1.100.000, 16 dias) · OP-2 **`CPR`** 8.695.000 ·
**OP-3 4.365.000, `dataContratacao` `2024-05-14`.**

**Garantias.** CPR_FINANCEIRA registrada R$ 6.000.000 · PENHOR_SAFRA R$ 8.900.000 ·
AVAL_FIANCA R$ 5.000.000 ("Aval solidário do conselho de administração").

| Dimensão | pen | bon | bruto | score | peso | contrib |
|---|---:|---:|---:|---:|---:|---:|
| comportamental | 378,0 | 34,9 | 656,9 | 656,9 | 0,22 | 144,529 |
| jurídico | 245,8 | 0 | 754,2 | 754,2 | 0,20 | 150,833 |
| fiscal | 339,5 | 0 | 660,5 | 660,5 | 0,14 | 92,473 |
| agroclimático | 271,0 | 160,0 | 889,0 | 889,0 | 0,15 | 133,350 |
| cadastral | 150,0 | 80,0 | 930,0 | 930,0 | 0,10 | 93,000 |
| ambiental | 150,0 | 0 | 850,0 | 850,0 | 0,09 | 76,500 |
| garantias | 721,6 | 0 | 278,4 | 278,4 | 0,10 | 27,839 |
| | | | | | **Σ** | **718,52 → 718,5 · B calculado → C final** |

PD 3,69% / 7,24% / 12,91% · rjIndex 10,1 → RJ12 0,31% · cobertura extra 28,12% · total 66,35% ·
em risco R$ 6.460.000 · **em risco em RJ R$ 13.800.000 (71,9%)** · utilização 97,0%.
O fator `concentracao_patrimonial` dispara (exposição 19,2 MM > 2 × patrimônio 7,4 MM).

---

## 8. Snapshots históricos

### 8.1 · Grade comum

Seis snapshots por cliente, **na mesma grade de datas para todos os 18** — isso permite comparar
a carteira inteira em qualquer instante e alimenta a carteira histórica sem lógica de
interpolação:

| | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---|---|---|---|---|
| Data | `2025-09-15` | `2025-12-10` | `2026-03-12` | `2026-06-10` | `2026-07-14` | `2026-09-12` |
| Momento do ciclo | Pré-plantio 25/26 | Plantio concluído | Colheita 25/26 | Pós-colheita | Entressafra | **Atual — plantio 26/27** |

`T4` é o snapshot usado pelo motor para a **tendência de 90 dias** (2026-09-12 − 90 d =
2026-06-14; T4 é o mais próximo anterior). `T5 → T6` são os **60 dias** da narrativa do briefing.

**Regras de construção dos snapshots:**

1. `dataReferencia` do snapshot = a data da grade.
2. Campos não citados na tabela de trajetória **repetem o valor do snapshot seguinte**
   (ou seja, do estado mais recente), exceto onde a tabela diz o contrário.
3. `operacoes`, `garantias`, `limiteAprovado`, `patrimonioDeclarado` e
   `faturamentoEstimadoAnual` são **iguais aos de T6** em todos os snapshots, salvo exceção
   listada — isso isola a variação de score nos fatos de risco, que é o que a decomposição de
   delta precisa mostrar. Exceções: `tres-barras` (patrimônio decrescente, ver 8.3) e
   `cerrado-norte` em T5 (garantia de CPR menor, ver §9).
4. Nenhum snapshot pode conter um fato que ainda não havia ocorrido na sua data.

### 8.2 · Trajetória de score (verificação de calibração)

| id | T1 | T2 | T3 | T4 | T5 | **T6** | Δ90d | Tendência derivada |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `santa-ines` | 951,6 | 947,7 | 939,0 | 933,5 | 919,7 | **917,9** | −15,6 | estável |
| `vale-do-piquiri` | 881,0 | 867,5 | 804,4 | 751,8 | 767,2 | **745,2** | −6,6 | estável |
| `cerrado-norte` | 888,0 | 868,1 | 799,4 | 724,9 | **712,0** | **604,0** | −120,9 | deterioração acelerada |
| `rio-formoso` | 730,9 | 626,8 | 404,4 | 377,1 | 259,6 | **253,6** | −123,5 | deterioração acelerada |
| `barra-do-ipe` | 843,0 | 800,9 | 734,5 | 643,7 | 619,8 | **571,6** | −72,0 | deteriorando |
| `alto-paranaiba` | 941,0 | 933,2 | 916,3 | 882,0 | 864,8 | **766,2** | −115,8 | deterioração acelerada |
| `serra-do-urucui` | 814,9 | 756,6 | 669,1 | 619,1 | 603,7 | **592,3** | −26,8 | deteriorando |
| `sao-bento-bioenergia` | 925,7 | 916,6 | 882,4 | 875,1 | 869,1 | **865,9** | −9,3 | estável |
| `chapadao-algodoeira` | 844,2 | 822,8 | 769,8 | 762,0 | 730,8 | **724,9** | −37,0 | deteriorando |
| `ponta-verde` | 754,2 | 657,1 | 446,6 | 436,1 | 325,5 | **325,5** | −110,6 | deterioração acelerada |
| `joao-camargo` | 761,5 | 716,8 | 611,8 | 566,1 | 504,4 | **498,2** | −67,9 | deteriorando |
| `tres-barras` | 894,7 | 874,7 | 834,3 | 802,5 | 782,5 | **735,3** | −67,2 | deteriorando |
| `ipanema-graos` | 937,9 | 882,9 | 831,3 | 720,1 | 681,9 | **680,0** | −40,1 | deteriorando |
| `frutivale` | 870,3 | 886,0 | 907,7 | 887,0 | 935,1 | **942,8** | +55,8 | melhorando |
| `santa-vitoria-arroz` | 808,9 | 786,1 | 720,1 | 711,5 | 722,8 | **723,4** | +11,9 | estável |
| `dois-irmaos` | 852,1 | 838,0 | 761,0 | 739,4 | 703,8 | **696,9** | −42,5 | deteriorando |
| `maria-nogueira` | 838,3 | 850,7 | 888,0 | 869,4 | 918,7 | **924,7** | +55,4 | melhorando |
| `coop-vale-do-ivai` | 833,9 | 826,8 | 745,8 | 727,0 | 721,1 | **718,5** | −8,5 | estável |

Cobertura das quatro tendências: **melhorando** 2 · **estável** 4 · **deteriorando** 6 ·
**deterioração acelerada** 4.

### 8.3 · O que muda entre snapshots, cliente a cliente

Só os campos abaixo variam; tudo o mais é constante ao longo da série.

| id | Campos que se movem | Narrativa |
|---|---|---|
| `santa-ines` | `atrasoMedioDias12m` 3→3→4→4→5→5 · `atrasoMedioDias90d` 3→4→5→5→6→6 · `piorAtrasoDias12m` 11→12→14→16→18→18 · pontualidade 0,96→0,95→0,94→0,93→0,92→0,92 · quebra 4→6→8→9→10→11 · precipitação −9→−13→−18→−21→−22→−24 · produtividade +4→+2→0→−2→−4→−5 · `protestosAtivos` 0→0→1→1→2→2 | Desgaste climático lento e dois protestos de fornecedor de combustível contestados. Nenhum evento estrutural. |
| `vale-do-piquiri` | atraso 6→7→9→11→11→12 · pior 21→24→29→36→36→38 · pontualidade 0,90→0,88→0,85→0,81→0,81→0,80 · `execucoesTitulo12m` 0→0→0→1→1→1 · `dividaAtivaPgfn` 0→0→600k→900k→900k→900k (com `…90dAtras` 0→0→0→600k→600k→600k) · `situacaoCar` regular→regular→pendente (T3) | Inscrição em dívida ativa em T3, primeira execução em T4; estabiliza depois. |
| `cerrado-norte` | ver §9 — é o cliente da narrativa | — |
| `rio-formoso` | Toda a espiral: execuções 1→2→3→4→6→6 · credores 1→2→3→3→5→5 · protestos ativos 1→2→3→3→5→5 · dívida ativa 900k→1,5MM→2,2MM→2,4MM→3,4MM→3,4MM · CNDT false→false→**true** (T3) · FGTS regular→regular→**irregular** (T3) · parcelamento rompido em T5 · covenant rompido em T3 · alteração societária em T3 · saída de sócio majoritário em T5 · auto de infração em T3 · **`pedidoFalencia` false até T5, `true` em T6** | O pedido de falência de T6 **não altera o score** (D2 já saturada em 0) mas **altera o rating por veto**. É o caso didático de "veto acima do score". |
| `barra-do-ipe` | atraso 6→8→10→12→13→14 · execuções 0→0→1→2→2→2 · dívida ativa 0→0→440k→440k→700k→700k · ZARC moderado→moderado→moderado→**alto** (T4) · `sobreposicaoAppOuReserva` false→…→**true** (T4) · `autoInfracaoNaoQuitado` **true** (T4) · CAR regular→pendente (T2)→**irregular** (T5) · **`embargoIbamaVigente` e `embargoSobreImovelEmGarantia` false até T5, ambos `true` em T6** | O embargo é o evento de T6. Antes dele o cliente era C; o veto o leva a D **no mesmo instante**. |
| `alto-paranaiba` | atraso 3→4→4→5→6→6 · `execucoesTitulo12m` 0→0→0→1→1→**3** · `execucoesTitulo90d` 0→0→0→1→1→**2** · valor em execução 0→0→0→700k→700k→**2,4MM** · credores 0→0→0→1→1→**3** · protestos 0→0→1→1→2→2 | Risco jurídico **recém-surgido**: duas execuções novas entre T5 e T6 derrubam 98,6 pontos e acionam `pluralidade_credores`. O rating segue A. |
| `serra-do-urucui` | ZARC moderado→**alto** (T2)→alto→**critico** (T4) · quebra 9→14→21→28→31→34 · precipitação −16→−24→−33→−42→−46→−50 · produtividade −6→−11→−17→−23→−26→−28 · atraso 7→9→12→15→17→18 · renegociações 0→1→1→2→2→2 | Seca progressiva no sul do Piauí. A dimensão agroclimática cai de 1000 para 118. |
| `sao-bento-bioenergia` | atraso 6→7→8→8→9→9 · pior 22→24→26→28→29→30 · trabalhistas 2→2→3→3→3→3 · quebra 9→11→12→13→14→14 | Cliente estável. A série existe para provar que "estável" também é um estado calculado. |
| `chapadao-algodoeira` | atraso 7→8→9→9→10→11 · execuções 1→1→2→2→2→2 · protestos ativos 1→2→2→2→3→3 · `protestos12m` 1→2→2→3→3→3 · dívida ativa 1,2MM→1,2MM→1,6MM→1,6MM→2,4MM→2,4MM | Deterioração gradual numa exposição grande — é o cliente cujo delta em reais mais pesa na carteira. |
| `ponta-verde` | atraso 11→16→22→24→32→34 · covenants 0→1→1→1→2→2 · CNDT false→false→**true** (T3) · parcelamento rompido em T3 · alteração de administrador em T3 · **`recuperacaoJudicial` null até T4, preenchida em T5 e T6** | RJ distribuída 2026-06-23 e deferida 2026-07-08 — entre T4 e T5. O salto T4→T5 (−110,6) é o efeito do fator `rj_distribuida` (900 pontos) e do veto. |
| `joao-camargo` | atraso 9→14→20→26→29→32 · pontualidade 0,79→0,70→0,60→0,51→0,46→0,42 · renegociações 1→1→2→2→3→3 · execuções 0→0→1→2→2→2 · protestos 0→1→2→2→3→3 · FGTS regular até T3, **irregular** em T4 | Espiral clássica de produtor PF descapitalizado. Note que os **credores distintos nunca chegam a 3** — é o que mantém o RJ baixo. |
| `tres-barras` | **`covenantsRompidos` 0→0→1→1→1→2** · `patrimonioDeclarado` 6,9MM→6,2MM→5,4MM→4,3MM→3,8MM→**3,4MM** · dívida ativa 800k→1,1MM→1,35MM→2,4MM→2,6MM→3,0MM · ZARC moderado→moderado→**alto** (T3)→**critico** (T4) · `seguroAgricolaVigente` true até T5, **false** em T6 | O patrimônio cai, o endividamento sobe, o `COV-TB-1` rompe em T3; a apólice não é renovada e o `COV-TB-2` rompe em T6. **Zero atraso em toda a série.** |
| `ipanema-graos` | `execucoesTitulo12m` 0→1→2→3→4→4 · valor 0→1,6MM→3,4MM→6,2MM→7,9MM→7,9MM · credores 0→1→2→**3**→**4**→4 · protestos 0→1→1→2→3→3 · dívida ativa 0→900k→1,8MM→2,9MM→2,9MM→2,9MM · parcelamento rompido em T4 · ZARC moderado→moderado→**alto** (T3) · **atraso permanece entre 3 e 5 dias na série inteira** | Crise de liquidez **fora** da relação com a Krill Tech. O `rjIndex` sobe de 0 a 75 sem que o cliente atrase um título. |
| `frutivale` | atraso 9→8→7→8→6→5 · pontualidade 0,86→0,88→0,90→0,87→0,92→0,92 · protestos ativos 3→3→2→3→2→2 · quebra 14→12→11→12→10→9 · precipitação −27→−24→−22→−25→−21→−18 | Recuperação com um recuo em T4 — a série "melhorando" precisa de ruído, senão parece scriptada. |
| `santa-vitoria-arroz` | dívida ativa 2,9MM→3,2MM→3,5MM→3,8MM→3,8MM→3,8MM · **`valorExecucoesFiscais` 1,9MM→2,6MM→3,1MM→3,7MM→3,7MM→3,7MM** · parcelamento rompido em T3 · CAR regular→pendente (T3) | O teto `TETO_EXEC_FISCAL` passa a valer **em T4**, quando 3,7 MM ultrapassa metade da exposição. O score mal se move; o rating cai de B para C. É o exemplo de que rating ≠ score. |
| `dois-irmaos` | atraso 6→7→9→10→11→12 · execuções 0→0→1→1→1→1 · dívida ativa 0→0→520k→520k→900k→900k · **`alteracaoSocietaria180d` false até T3, `true` em T4** · **`saidaSocioMajoritario12m` false até T4, `true` em T5** | A saída do sócio majoritário em T5 é o evento narrativo; o comportamento já vinha piorando. |
| `maria-nogueira` | atraso 9→8→7→8→6→5 · protestos ativos 3→3→2→3→2→2 · quebra 17→15→14→12→11→11 · precipitação −31→−28→−26→−28→−23→−22 · `seguroAgricolaVigente` **false** em T1 e T2, `true` de T3 em diante | A contratação do seguro em T3 é o ponto de inflexão. |
| `coop-vale-do-ivai` | atraso 8→9→10→10→11→11 · execuções 0→0→1→1→1→1 · trabalhistas 2→2→3→3→3→3 · **`cndtPositiva` false até T2, `true` a partir de T3** · `valorDebitoTrabalhista` 0→0→2,15MM→2,15MM→2,15MM→2,15MM · dívida ativa 1,2MM→1,2MM→1,2MM→1,5MM→1,9MM→1,9MM | `TETO_CNDT` passa a valer em T3. |

---

## 9. A narrativa 712 → 604 — `cerrado-norte`, T5 → T6

Sessenta dias exatos (`2026-07-14` → `2026-09-12`). **Nenhum dos dois snapshots satura em nenhuma
dimensão**, de modo que a decomposição fecha sem redistribuição e a conferência de I6 é direta.

### 9.1 · O que mudou nos fatos

| Fato | T5 (2026-07-14) | T6 (2026-09-12) | Causa narrativa |
|---|---|---|---|
| `execucoesTitulo12m` | 1 | **3** | Duas execuções de título ajuizadas em ago/2026 |
| `execucoesTitulo90d` | 0 | **2** | Ambas dentro da janela de 90 dias |
| `credoresDistintosExecutando` | 1 | **3** | Credores distintos — trading, revenda e banco |
| `valorTotalEmExecucao` | 2.500.000 | **2.900.000** | Soma dos novos feitos |
| `dividaAtivaPgfn` | 1.150.000 | **1.950.000** | Nova inscrição em dívida ativa (PGFN) em ago/2026 |
| `dividaAtivaPgfn90dAtras` | 1.150.000 | 1.150.000 | → aciona `divida_ativa_crescente` |
| `atrasoMedioDias12m` | **3** | **11** | Piora do comportamento de pagamento |
| `atrasoMedioDias90d` | 11 | 19 | — |
| `quebraSafraRegionalPct` | 17 | **19** | Revisão da CONAB para o sul do Maranhão |
| `desvioPrecipitacaoPct` | −28 | **−31** | Déficit hídrico acumulado (INMET) |
| `produtividadeVsMediaRegionalPct` | −12 | −11 | Leve reversão |
| Garantia `GAR-CERRADO-NORTE-1` | CPR financeira R$ 6.000.000 | **R$ 7.400.000** | Registro de CPR adicional em ago/2026 — o único movimento **a favor** do cliente |

Todos os demais fatos são idênticos nos dois snapshots.

### 9.2 · Decomposição do delta (invariante I6)

`delta(fator) = impactoGlobal_t1 − impactoGlobal_t0`, ordenado por `|delta|`:

| Fator | Impacto em T5 | Impacto em T6 | **Δ** |
|---|---:|---:|---:|
| `execucoes_titulo` | −14,00 | −42,00 | **−28,00** |
| `pluralidade_credores` | 0,00 | −24,00 | **−24,00** |
| `atraso_medio` | −7,92 | −29,04 | **−21,12** |
| `aceleracao_judicial` | 0,00 | −20,00 | **−20,00** |
| `divida_ativa_crescente` | 0,00 | −12,60 | **−12,60** |
| `divida_ativa` | −3,59 | −6,09 | **−2,50** |
| `descoberto_extraconcursal` | −30,36 | −28,11 | **+2,25** |
| `quebra_safra_regional` | −15,30 | −17,10 | **−1,80** |
| `materialidade_execucao` | −8,93 | −10,36 | **−1,43** |
| `descoberto_total` | −9,93 | −8,53 | **+1,41** |
| `desvio_precipitacao` | −12,60 | −13,95 | **−1,35** |
| `produtividade_abaixo` | −7,20 | −6,60 | **+0,60** |
| `relacionamento` | +7,64 | +8,19 | **+0,54** |
| | | **Σ dos deltas** | **−108,00** |

`score_T6 − score_T5 = 604,0 − 712,0 = −108,0` ✔ — **fecha com diferença 0,00**.

### 9.3 · Como a UI resume (spec 02 §11)

```
712 → 604   (-108 pontos em 60 dias)
  2 novas execuções de título ....................... -49
  pluralidade de credores executando (1 → 3) ........ -24
  atraso médio de pagamento (3d → 11d) .............. -21
  nova inscrição em dívida ativa .................... -15
  deterioração climática regional ................... -3
  reforço de garantia (CPR adicional registrada) .... +4
```

Os agrupamentos acima são de **apresentação** e cada linha é a soma exata dos deltas da §9.2:

| Linha exibida | Fatores somados | Soma |
|---|---|---:|
| 2 novas execuções de título | `execucoes_titulo` + `aceleracao_judicial` + `materialidade_execucao` | −49,43 |
| pluralidade de credores executando | `pluralidade_credores` | −24,00 |
| atraso médio de pagamento | `atraso_medio` | −21,12 |
| nova inscrição em dívida ativa | `divida_ativa_crescente` + `divida_ativa` | −15,10 |
| deterioração climática regional | `quebra_safra_regional` + `desvio_precipitacao` + `produtividade_abaixo` | −2,55 |
| reforço de garantia | `descoberto_extraconcursal` + `descoberto_total` + `relacionamento` | +4,20 |
| | **Σ** | **−108,00** |

**A soma exibida tem de ser a soma dos deltas reais — a UI agrupa e arredonda para exibição, nunca
reescreve.** Os valores arredondados das seis linhas também somam exatamente −108.

---

## 10. Eventos, alertas e evidências

### 10.1 · Eventos de risco

`EventoDeRisco` é **derivado das transições entre snapshots** e escrito em `api/data/eventos.py`
**sem** `scoreApos` e `deltaScore` — esses dois campos são preenchidos em runtime recalculando o
snapshot anterior e o posterior. Regra de derivação: cada mudança material de fato entre dois
snapshots consecutivos vira um evento com a data do snapshot posterior.

| id | Cliente | Data | Tipo | Severidade | Título |
|---|---|---|---|---|---|
| `EV-001` | `cerrado-norte` | 2026-08-06 | `NOVA_EXECUCAO` | CRÍTICA | Duas execuções de título ajuizadas por credores distintos |
| `EV-002` | `cerrado-norte` | 2026-08-21 | `DIVIDA_ATIVA` | ALTA | Nova inscrição em dívida ativa da União — R$ 800.000 |
| `EV-003` | `cerrado-norte` | 2026-09-02 | `MUDANCA_CLIMATICA` | MÉDIA | CONAB revisa quebra de safra do sul do MA para 19% |
| `EV-004` | `cerrado-norte` | 2026-09-08 | `ATRASO_PAGAMENTO` | ALTA | Atraso médio sobe de 3 para 11 dias |
| `EV-005` | `barra-do-ipe` | 2026-08-24 | `EMBARGO_AMBIENTAL` | CRÍTICA | Termo de embargo do IBAMA sobre a matrícula 14.702, dada em hipoteca |
| `EV-006` | `barra-do-ipe` | 2026-06-30 | `MUDANCA_CLIMATICA` | MÉDIA | ZARC da soja em Querência elevado de moderado para alto |
| `EV-007` | `ponta-verde` | 2026-06-23 | `PEDIDO_RJ` | CRÍTICA | Recuperação judicial distribuída |
| `EV-008` | `ponta-verde` | 2026-07-08 | `PEDIDO_RJ` | CRÍTICA | Recuperação judicial deferida — Stay Period iniciado |
| `EV-009` | `ponta-verde` | 2026-02-09 | `COVENANT_ROMPIDO` | ALTA | Endividamento líquido acima de 3,0× EBITDA |
| `EV-010` | `rio-formoso` | 2026-09-03 | `PEDIDO_FALENCIA` | CRÍTICA | Pedido de falência distribuído por credor quirografário |
| `EV-011` | `rio-formoso` | 2026-06-18 | `ALTERACAO_SOCIETARIA` | MÉDIA | Saída do sócio majoritário |
| `EV-012` | `alto-paranaiba` | 2026-08-12 | `NOVA_EXECUCAO` | ALTA | Duas execuções ajuizadas em 30 dias — três credores distintos |
| `EV-013` | `tres-barras` | 2026-06-27 | `COVENANT_ROMPIDO` | ALTA | Apólice de seguro agrícola não renovada — covenant `COV-TB-2` |
| `EV-014` | `tres-barras` | 2026-03-19 | `COVENANT_ROMPIDO` | ALTA | Endividamento total em 2,53× o patrimônio — covenant `COV-TB-1` |
| `EV-015` | `ipanema-graos` | 2026-07-02 | `NOVA_EXECUCAO` | ALTA | Quarto credor distinto ajuíza execução |
| `EV-016` | `ipanema-graos` | 2026-05-14 | `DIVIDA_ATIVA` | MÉDIA | Parcelamento fiscal rompido |
| `EV-017` | `serra-do-urucui` | 2026-06-05 | `MUDANCA_CLIMATICA` | ALTA | ZARC da soja em Uruçuí elevado para crítico |
| `EV-018` | `dois-irmaos` | 2026-07-01 | `ALTERACAO_SOCIETARIA` | MÉDIA | Saída de sócio majoritário registrada na Redesim |
| `EV-019` | `santa-vitoria-arroz` | 2026-05-28 | `DIVIDA_ATIVA` | ALTA | Execuções fiscais alcançam 54% da exposição |
| `EV-020` | `coop-vale-do-ivai` | 2026-02-26 | `CADASTRAL` | ALTA | CNDT positiva — débito trabalhista de R$ 2.150.000 |
| `EV-021` | `joao-camargo` | 2026-05-20 | `ATRASO_PAGAMENTO` | ALTA | Terceira renegociação em 12 meses |
| `EV-022` | `maria-nogueira` | 2026-02-20 | `RECALCULO` | BAIXA | Contratação de seguro agrícola para a safra 2025/26 |
| `EV-023` | `frutivale` | 2026-07-09 | `RECALCULO` | BAIXA | Baixa de protesto em cartório |
| `EV-024` | `santa-ines` | 2026-06-25 | `CADASTRAL` | BAIXA | Atualização de endereço de correspondência na Receita Federal |
| `EV-025` | `chapadao-algodoeira` | 2026-08-05 | `NOVO_PROTESTO` | MÉDIA | Terceiro protesto ativo |
| `EV-026` | `vale-do-piquiri` | 2026-05-11 | `NOVA_EXECUCAO` | MÉDIA | Primeira execução de título em 36 meses |

As quatro severidades estão representadas: CRÍTICA 5 · ALTA 11 · MÉDIA 7 · BAIXA 3.

### 10.2 · Alertas

`ALERTAS` em `api/data/alertas.py` — um alerta por evento de severidade CRÍTICA, ALTA ou MÉDIA
ocorrido **nos últimos 120 dias** (a partir de 2026-05-15), mais os informativos. Cada alerta
carrega `clienteNome` desnormalizado (a central de alertas não pode depender de join), `impacto`
em texto **parametrizado com os números do cliente** e `acaoRecomendada` acionável.

Formato obrigatório de `impacto` e `acaoRecomendada` — exemplo do `EV-005`:

```
impacto:          "R$ 9.200.000 de exposição passam a contar com garantia juridicamente
                   comprometida; a classificação final cai de C para D por regra de negócio."
acaoRecomendada:  "Suspender qualquer nova exposição a prazo e exigir substituição da hipoteca
                   da matrícula 14.702 por alienação fiduciária sobre bem não embargado."
```

`lido` = `false` para todos os alertas posteriores a 2026-08-01; `true` para os anteriores.
`eventoId` sempre preenchido.

### 10.3 · Evidências

Toda `Evidencia` tem `simulada = true`, `dataConsulta` entre `2026-09-08` e `2026-09-12`,
`urlFicticia` no padrão `https://consultas.simuladas.lastro.local/<fonte>/<protocolo>` e
`fatoresRelacionados` apontando para **ids de fator do catálogo da spec 02 §4** — é isso que liga
evidência → número na UI.

**As 14 fontes, com quem as usa e a quais fatores se ligam:**

| `FonteId` | `nomeFonte` | `tipo` | Ligada aos fatores | Clientes que a carregam |
|---|---|---|---|---|
| `RECEITA_FEDERAL` | Receita Federal — CNPJ/CPF | `CADASTRO` | `situacao_cadastral`, `tempo_atividade`, `cnae_incompativel` | **todos os 18** |
| `REDESIM` | Redesim — atos societários | `CADASTRO` | `alteracao_societaria`, `saida_socio_majoritario`, `qsa_estavel` | 14 (todos com QSA ou alteração) |
| `DATAJUD_CNJ` | DataJud — CNJ | `PROCESSO` | `execucoes_titulo`, `materialidade_execucao`, `aceleracao_judicial`, `pluralidade_credores`, `sem_litigio` | **todos os 18** |
| `DJE` | Diário da Justiça Eletrônico | `PUBLICACAO` | `rj_distribuida`, `pedido_falencia` | `ponta-verde`, `rio-formoso` |
| `CARTORIO_PROTESTO` | Central de Protestos — CENPROT | `CERTIDAO` | `protestos`, `protesto_recorrente` | 15 (todos com protesto) |
| `PGFN` | PGFN — Dívida Ativa da União | `CERTIDAO` | `divida_ativa`, `divida_ativa_crescente`, `certidoes_negativas` | **todos os 18** |
| `TST_CNDT` | TST — Certidão Negativa de Débitos Trabalhistas | `CERTIDAO` | `cndt_positiva`, `trabalhistas` | **todos os 18** |
| `CAIXA_CRF_FGTS` | Caixa — CRF/FGTS | `CERTIDAO` | `fgts_irregular` | **todos os 18** |
| `SICAR` | SICAR — Cadastro Ambiental Rural | `CADASTRO` | `car_ausente`, `car_irregular`, `car_regular`, `sobreposicao_app`, `monocultura`, `diversificacao` | **todos os 18** |
| `IBAMA` | IBAMA — embargos e autos de infração | `CADASTRO` | `embargo_ibama`, `auto_infracao` | **todos os 18** (negativa nos 14 sem ocorrência) |
| `CONAB` | CONAB — levantamento de safra | `SERIE_HISTORICA` | `quebra_safra_regional`, `produtividade_abaixo` | **todos os 18** |
| `MAPA_ZARC` | MAPA — Zoneamento Agrícola de Risco Climático | `LAUDO` | `zarc_risco` | **todos os 18** |
| `INMET` | INMET — normais climatológicas | `SERIE_HISTORICA` | `desvio_precipitacao` | **todos os 18** |
| `INTERNO_KRILLTECH` | Krill Tech — histórico interno | `INTERNO` | `atraso_medio`, `pior_atraso`, `pontualidade`, `renegociacoes`, `inadimplencia_tecnica`, `tendencia_atraso`, `relacionamento`, `historico_limpo`, `barter_sem_lastro`, `irrigacao_ou_seguro`, todos os de D7 | **todos os 18** |

**Contagem mínima por cliente: 11 evidências** — as onze fontes marcadas "todos os 18" acima, uma
cada, inclusive quando o resultado é negativo (uma consulta ao IBAMA sem ocorrência é evidência
tão relevante quanto uma com embargo, e a UI precisa poder mostrá-la). Clientes com ocorrência
específica ganham evidências adicionais nominadas:

| Cliente | Evidências nominadas obrigatórias |
|---|---|
| `barra-do-ipe` | `IBAMA` — "Termo de Embargo nº 0092/2026 — Fazenda Barra do Ipê, gleba de 1.860 ha, matrícula 14.702" · `SICAR` — "CAR MT-5107065-A3F2 em situação irregular, com sobreposição de 112 ha de reserva legal" |
| `ponta-verde` | `DJE` — "Decisão de deferimento do processamento da RJ, 3ª Vara Cível de Rio Verde/GO, publicada em 2026-07-08" |
| `rio-formoso` | `DJE` — "Pedido de falência distribuído em 2026-09-03, 1ª Vara Cível de Barreiras/BA" · `TST_CNDT` — "CNDT positiva, débito de R$ 980.000" |
| `tres-barras` | `INTERNO_KRILLTECH` — "Apuração de covenants do contrato 2024/0318: endividamento total em 2,53× o patrimônio líquido e apólice de seguro agrícola não renovada" |
| `ipanema-graos` | `DATAJUD_CNJ` — "Quatro execuções de título extrajudicial de credores distintos, valor agregado R$ 7.900.000" |
| `santa-vitoria-arroz` | `PGFN` — "Quatro execuções fiscais em curso, valor agregado R$ 3.700.000" |
| `coop-vale-do-ivai` | `TST_CNDT` — "CNDT positiva, débito de R$ 2.150.000 com trânsito em julgado" |
| `serra-do-urucui` | `MAPA_ZARC` — "ZARC da soja em Uruçuí/PI classificado como crítico para a janela de plantio 2026/27" · `INMET` — "Déficit de 50% na precipitação acumulada out/2025–mar/2026" |

Ids: `EVID-<ID_CLIENTE>-<FONTE_ABREVIADA>-<n>`, por exemplo `EVID-BARRA-DO-IPE-IBAMA-1`.

---

## 11. Prospects e due diligence

Quatro prospects em `api/data/prospects/`, com `origem = "PROSPECT"` e `estado = "ATIVO"`.
**Cada um carrega uma operação proposta**, não contratada: sem isso a exposição seria zero e os
fatores de D7 penalizariam todo prospect igualmente, o que distorceria a análise. A operação
proposta tem `dataContratacao = "2026-09-12"` (a data da consulta) e representa o **limite
pretendido**; a UI a rotula como *"operação em análise"*.

| id | Razão social | Município/UF | Culturas | Limite pretendido | Score | Rating final | Veredito |
|---|---|---|---|---|---:|---|---|
| `nova-alianca` | Agropecuária Nova Aliança Ltda | Sinop/MT | Soja · Milho safrinha · Feijão | 6.000.000 | **976,9** | **A** | **Aprovável** |
| `ribeirao-claro` | Fazenda Ribeirão Claro Agro Ltda | Jataí/GO | Soja · Milho safrinha | 4.500.000 | **650,5** | **B** | **Limítrofe** |
| `beira-rio` | Agrocomercial Beira Rio Ltda | Paragominas/PA | Soja · Milho | 5.000.000 | 595,1 (C) | **D** | **Recusável — `VETO_CADASTRO_INAPTO`** |
| `santa-helena-norte` | Agrícola Santa Helena do Norte Ltda | Confresa/MT | Soja | 7.000.000 | 748,5 (B) | **D** | **Recusável — `VETO_LISTA_SUJA` + `VETO_FRAUDE`** |

Os prospects não têm histórico interno: `interno` fica **inteiramente no padrão** (atraso 0,
pontualidade 1,0), e a dimensão comportamental resulta em exatamente 1000 — a UI precisa explicitar
*"sem histórico interno; dimensão comportamental não penalizada por ausência de dado"*, para não
sugerir que o prospect é melhor pagador do que os clientes de carteira.

**Fatos distintivos:**

- **`nova-alianca`** — soja 3.400 ha + milho safrinha 2.400 ha + feijão 800 ha → 17.680.000 +
  8.160.000 + 3.280.000 (feijão a R$ 4.100/ha) = **R$ 29.120.000** de custeio; `fraçãoKrill`
  20,6% → **R$ 5.998.720 ≈ R$ 6.000.000**.
  `semLitigio36m` true, `todasCertidoesNegativas` true, CAR regular, ZARC moderado, seguro
  vigente, 3 culturas (diversificação), capital social R$ 7.500.000, patrimônio R$ 41.000.000,
  faturamento R$ 33.000.000. Garantias propostas: CPR financeira R$ 4.500.000 + alienação
  fiduciária R$ 2.600.000 → cobertura extraconcursal **102,2%**. Dois protestos ativos de R$ 31 mil
  contestados — o "ruído" que impede a ficha de parecer perfeita.
- **`ribeirao-claro`** — soja 1.600 ha → **R$ 8.320.000** de custeio; `fraçãoKrill` **54,1%** →
  **R$ 4.501.120 ≈ R$ 4.500.000** (o milho safrinha é custeado com recursos próprios).
  `execucoesTitulo12m` 2 (ambas em 90 dias),
  3 credores distintos, R$ 900.000 em execução, dívida ativa R$ 1.400.000 crescente,
  **ZARC crítico**, quebra 24%, precipitação −40%, produtividade −20%, `anosAtividade` 4,
  capital R$ 1.600.000, CAR pendente, sem garantia extraconcursal (penhor de safra R$ 3.200.000 +
  aval R$ 1.500.000). **rjIndex 55,0 → RJ12 22,50%.** É o caso em que a decisão é humana, e a
  aplicação tem de deixar isso explícito.
- **`beira-rio`** — soja 2.400 ha → **R$ 12.480.000** de custeio; `fraçãoKrill` 40,1% →
  **R$ 5.004.480 ≈ R$ 5.000.000**. **`situacaoRfb` "INAPTA"** e **`cnaeCompativel` false** (CNAE 4930-2/02,
  transporte rodoviário de carga, declarando atividade agrícola). 3 credores distintos
  executando, 3 protestos ativos, dívida ativa R$ 1.250.000 crescente, parcelamento rompido,
  CAR irregular. Score 595,1 (C) → **veto força D**.
- **`santa-helena-norte`** — soja 3.000 ha → **R$ 15.600.000** de custeio; `fraçãoKrill` 44,9% →
  **R$ 7.004.400 ≈ R$ 7.000.000**. **`listaSujaTrabalhoEscravo` true** e **`fraudeConfirmada` true**
  (simulação de área plantada para obtenção de crédito, apurada em auditoria de campo), somados a
  `embargoIbamaVigente` true, auto de infração, CAR irregular e sobreposição de reserva.
  Score 748,5 (B) → **dois vetos de força D compõem**: é a ficha que exercita a **composição de
  vetos** e a lista `vetosAtivos[]` com mais de um item. O embargo **não** recai sobre bem em
  garantia (a garantia é hipoteca de outra matrícula), então `VETO_EMBARGO_GARANTIA` **não**
  dispara — distinção que o teste de vetos deve cobrir.

**Documento desconhecido.** `por_documento()` normaliza a entrada removendo pontuação e compara
com os 22 documentos do dataset. Não havendo correspondência, devolve `None`, e a rota de nova
análise responde **404 com corpo `{"erro": "DOCUMENTO_NAO_ENCONTRADO", "documento": "<normalizado>"}"`**.
A tela mostra o estado "documento não encontrado na base simulada", oferece os quatro prospects
como perfis demonstrativos clicáveis e **jamais inventa um cliente**. Documento com dígito
verificador inválido é rejeitado **antes** da consulta, com `{"erro": "DOCUMENTO_INVALIDO"}`.

---

## 12. Varredura de contradições

Executada sobre os 22 registros (18 clientes + 4 prospects). Cada regra é também um **teste
`pytest` obrigatório** em `api/tests/test_dataset_coerente.py`.

| # | Regra | Resultado | Observação |
|---|---|---|---|
| V1 | `semLitigio36m = true` ⇒ `execucoesTitulo12m = 0` **e** `pedidoFalencia = false` **e** `recuperacaoJudicial = null` | ✅ 0 violações | Os 5 com `semLitigio36m` (`santa-ines`, `sao-bento-bioenergia`, `frutivale`, `maria-nogueira`, `nova-alianca`) têm zero execuções |
| V2 | `todasCertidoesNegativas = true` ⇒ `dividaAtivaPgfn = 0` **e** `cndtPositiva = false` **e** `crfFgtsRegular = true` **e** `execucoesFiscais = 0` | ✅ 0 violações | Os 6 com certidões negativas estão fiscalmente limpos |
| V3 | `atrasoMedioDias12m ≤ piorAtrasoDias12m` | ✅ 0 violações | Máximo observado: 34 ≤ 118 (`ponta-verde`) |
| V4 | `pctTitulosPagosEmDia12m` monotonicamente coerente com `atrasoMedioDias12m` (atraso 0 ⇒ pontualidade 1,0; atraso ≥ 30 ⇒ pontualidade ≤ 0,60) | ✅ 0 violações | `tres-barras` 0 dias / 1,0 · `joao-camargo` 32 dias / 0,42 · `ponta-verde` 34 dias / 0,44 |
| V5 | `semAtrasoRelevante24m = true` ⇒ `piorAtrasoDias12m ≤ 5` **e** `renegociacoes12m = 0` | ✅ 0 violações | Único caso: `tres-barras`, com 0 e 0 |
| V6 | `semLitigio36m = true` **com** `acoesTrabalhistasTransitadas > 0` | ⚠ **1 ocorrência tolerada** | `sao-bento-bioenergia`. Resolvida pela leitura declarada em 7.8: o campo mede **ações ajuizadas em 36 meses**; o trânsito em julgado é anterior. **Deve constar do tooltip da UI.** |
| V7 | `credoresDistintosExecutando ≤ execucoesTitulo12m` | ✅ 0 violações | `ipanema-graos` 4 = 4 é o caso apertado |
| V8 | `execucoesTitulo90d ≤ execucoesTitulo12m` | ✅ 0 violações | — |
| V9 | `credoresProtestantes180d ≤ protestos12m` e `protestosAtivos ≤ protestos12m` | ✅ 0 violações | — |
| V10 | `valorTotalEmExecucao > 0` ⇔ `execucoesTitulo12m > 0` | ✅ 0 violações | — |
| V11 | `cndtPositiva = true` ⇔ `valorDebitoTrabalhista > 0` | ✅ 0 violações | 3 casos: `rio-formoso`, `ponta-verde`, `coop-vale-do-ivai` |
| V12 | `valorExecucoesFiscais > 0` ⇔ `execucoesFiscais > 0` | ✅ 0 violações | — |
| V13 | `dividaAtivaPgfn = 0` ⇒ `dividaAtivaPgfn90dAtras = 0` | ✅ 0 violações | Evita `divida_ativa_crescente` fantasma |
| V14 | `recuperacaoJudicial ≠ null` ⇒ `estado = "RJ_EM_CURSO"`; `pedidoFalencia = true` ⇒ `estado ∈ {SUSPENSO, FALENCIA}` | ✅ 0 violações | `ponta-verde` e `rio-formoso` |
| V15 | `areaIrrigadaHa ≤ areaTotalHa` | ✅ 0 violações | `frutivale` 305 = 305 |
| V16 | `seguroAgricolaVigente = false` **e** `areaIrrigadaHa/areaTotalHa < 0,20` ⇒ sem fator `irrigacao_ou_seguro` | ✅ consistente | 6 clientes sem a proteção |
| V17 | `agro.culturas` idêntico a `Cliente.culturas` | ✅ 0 violações | Fallback do motor nunca é exercido — proposital |
| V18 | `barter.cprVinculadaId`, quando presente, aponta para garantia do próprio cliente, de tipo CPR e `registrada = true` | ✅ 0 violações | 11 operações barter: **8 com lastro** (`santa-ines`, `vale-do-piquiri`, `cerrado-norte`, `alto-paranaiba`, `chapadao-algodoeira`, `ipanema-graos`, `dois-irmaos`, `maria-nogueira`) e **3 sem** (`rio-formoso`, `serra-do-urucui`, `ponta-verde`) |
| V19 | `barter.sacasPrometidas × precoReferenciaSaca` a menos de 2% do `saldoDevedor` da operação | ✅ 0 violações | Máximo desvio: 0,03% |
| V20 | `Σ operacoes.saldoDevedor = exposicaoTotal` declarada | ✅ 0 violações | Por construção (6.2) |
| V21 | `Σ parcelas(A_VENCER) + Σ parcelas(EM_ATRASO) = Σ saldoDevedor` | ✅ 0 violações | Por construção |
| V22 | `EM_ATRASO ⇒ vencimento < dataReferencia` e `diasAtraso` consistente com a data | ✅ 0 violações | 11 clientes com parcela vencida |
| V23 | `EM_ATRASO = 0` para clientes de persona "sem atraso" | ✅ 0 violações | `tres-barras`, `ipanema-graos`, e os 4 prospects |
| V24 | `bemEmbargado = true` ⇒ `ambiental.embargoSobreImovelEmGarantia = true` **e** `embargoIbamaVigente = true` | ✅ 0 violações | Único: `barra-do-ipe` |
| V25 | `embargoSobreImovelEmGarantia = true` ⇒ existe garantia com `bemEmbargado = true` | ✅ 0 violações | Recíproca de V24 |
| V26 | `capitalSocial > 0` para toda PJ; para PF, campo documentado como patrimônio rural IRPF | ✅ 0 violações | Convenção C2 aplicada às 2 PFs |
| V27 | `faturamentoEstimadoAnual ≥ 1,1 × exposicaoTotal` | ✅ 0 violações | Razão mínima da carteira: **1,48×** (`rio-formoso`); máxima 10,11× (`sao-bento-bioenergia`). Os mais apertados são os clientes em crise, como esperado: `rio-formoso` 1,48× · `serra-do-urucui` 1,51× · `barra-do-ipe` 1,72× · `joao-camargo` 1,74× |
| V28 | `anosAtividadeComprovada ≤ anosAtividade` | ✅ 0 violações | `joao-camargo` 1,4 ≤ 2,6 |
| V29 | PF ⇒ `qsaEstavel5anos = false` (não há quadro societário) | ✅ 0 violações | `joao-camargo`, `maria-nogueira` |
| V30 | `situacaoRfb ≠ "ATIVA"` ⇒ `origem = "PROSPECT"` **ou** `estado = "SUSPENSO"` | ✅ 0 violações | Único: prospect `beira-rio` |
| V31 | Município/UF compatível com as culturas declaradas | ✅ 0 violações | Ver matriz abaixo |
| V32 | Exposição dentro de ±5% da razão R$/ha declarada | ✅ 0 violações | Maior desvio: 0,20% (`chapadao-algodoeira`) |
| V33 | CPF/CNPJ com dígito verificador válido e sem sequência repetida | ✅ 0 violações | 22 documentos conferidos |
| V34 | Nenhum documento repetido no dataset | ✅ 0 violações | — |
| V35 | Toda evidência tem `simulada = true` | ✅ 0 violações | — |
| V36 | Todo `fatoresRelacionados` cita um id existente no catálogo da spec 02 §4 | ✅ 0 violações | — |
| V37 | Nenhum snapshot contém fato posterior à sua `dataReferencia` | ✅ 0 violações | Ver 8.3 |
| V38 | `SNAPSHOTS[-1] == FATOS` campo a campo | ✅ 0 violações | — |
| V39 | Nenhum arquivo de `api/data/` importa de `api/scoring/` | ✅ 0 violações | Verificável por AST |
| V40 | Nenhum arquivo de `api/data/` escreve `score`, `rating`, `pd`, `redFlags`, `recomendacao`, `natureza`, `valorAtualizado`, `scoreApos`, `deltaScore` | ✅ 0 violações | Verificável por AST |

**Matriz de compatibilidade agronômica (V31).**

| Município/UF | Culturas do dataset | Justificativa |
|---|---|---|
| Sorriso/MT · Primavera do Leste/MT · Rondonópolis/MT · Querência/MT · Sinop/MT · Confresa/MT | Soja, milho safrinha, algodão | Maior polo de soja/algodão do país; safrinha consolidada |
| Balsas/MA · Uruçuí/PI · Barreiras/BA · Luís Eduardo Magalhães/BA · Formosa do Rio Preto/BA | Soja, milho, algodão | Matopiba; algodão no oeste baiano |
| Campo Mourão/PR · Cascavel/PR | Soja, milho safrinha, trigo | Sistema soja–safrinha–trigo do oeste do Paraná |
| Sertãozinho/SP | Cana-de-açúcar | Coração do cluster sucroenergético paulista |
| Patrocínio/MG | Café arábica | Cerrado Mineiro, denominação de origem |
| Uruguaiana/RS · Não-Me-Toque/RS | Arroz irrigado, soja, trigo | Fronteira Oeste (arroz) e Planalto Médio (soja/trigo) |
| Rio Verde/GO · Jataí/GO · Cristalina/GO | Milho, soja | Sudoeste goiano; Cristalina com pivôs centrais |
| Petrolina/PE | Manga, uva de mesa | Vale do São Francisco, fruticultura irrigada |
| Paragominas/PA | Soja, milho | Fronteira agrícola do nordeste paraense |

### 12.1 · Incoerências residuais assumidas

Duas, ambas conscientes e documentadas para que ninguém as "conserte" sem entender o efeito:

1. **V6 — `sao-bento-bioenergia`**: `semLitigio36m = true` com três reclamações trabalhistas
   transitadas. Depende da leitura "ações **ajuizadas** nos últimos 36 meses". Alternativa
   descartada: zerar `acoesTrabalhistasTransitadas`, o que removeria a única penalidade jurídica
   dessa dimensão e a faria saturar em 1060.
2. **Fração de compras concentrada** — `joao-camargo` (55,2%) e `ribeirao-claro` (54,2%) compram
   mais da metade do custeio de um único fornecedor. É atípico para produtores saudáveis e
   **deliberado**: concentração de fornecedor é, ela própria, sinal de dificuldade de crédito no
   mercado. Não é modelada como fator porque o motor da spec 02 não tem esse fator; fica como
   contexto narrativo do parecer.

---

## 13. Trilha de auditoria inicial

`api/data/auditoria.py` traz **9 registros** pré-existentes, para que a tela de auditoria não nasça
vazia. Analistas fictícios: "Ana Beatriz Carvalho", "Rodrigo Tsuda", "Helena Prado".

**Regra de coerência temporal:** `dataHora` de cada registro cai **entre a data do snapshot que o
analista consultou e a do snapshot seguinte**, e `scoreNoMomento` / `ratingNoMomento` são o
recálculo daquele snapshot. A coluna "snapshot" abaixo não é um campo do modelo — está aqui para
que o teste saiba contra o que comparar.

| id | Cliente | Data/hora | Snapshot | Score no momento | Rating | Recomendação gerada | Decisão | Divergiu? |
|---|---|---|---|---:|---|---|---|---|
| `AUD-001` | `cerrado-norte` | 2026-07-15T09:12:00 | T5 | 712,0 | B | `APROVAR_COM_RESTRICOES` | `APROVAR_COM_RESTRICOES` | não |
| `AUD-002` | `cerrado-norte` | 2026-09-12T16:40:00 | T6 | 604,0 | B | `APROVAR_COM_RESTRICOES` | **`SUSPENDER`** | **sim** |
| `AUD-003` | `barra-do-ipe` | 2026-09-12T11:05:00 | T6 | 571,6 | D (veto) | `SUSPENDER_EXPOSICAO` | `SUSPENDER` | não |
| `AUD-004` | `ponta-verde` | 2026-07-16T08:30:00 | T5 | 325,5 | D (veto) | `SUSPENDER_EXPOSICAO` | `RECUSAR` | não |
| `AUD-005` | `tres-barras` | 2026-07-15T14:22:00 | T5 | 782,5 | A | `APROVAR_COM_REVISAO_DE_LIMITE` | **`REVISAR`** | **sim** |
| `AUD-006` | `ipanema-graos` | 2026-07-15T10:18:00 | T5 | 681,9 | B | `APROVAR_COM_MONITORAMENTO_INTENSIVO` | `APROVAR_COM_RESTRICOES` | **sim** |
| `AUD-007` | `santa-ines` | 2026-06-11T15:55:00 | T4 | 933,5 | A | `APROVAR` | `APROVAR` | não |
| `AUD-008` | `rio-formoso` | 2026-09-12T09:47:00 | T6 | 253,6 | D (veto) | `SUSPENDER_EXPOSICAO` | `RECUSAR` | não |
| `AUD-009` | `santa-vitoria-arroz` | 2026-06-11T13:10:00 | T4 | 711,5 | C (teto) | `APROVAR_COM_RESTRICOES` | `APROVAR_COM_RESTRICOES` | não |

Três divergências entre recomendação e decisão — é o que a tela de auditoria precisa destacar.
`justificativa` de `AUD-002`, como modelo de redação:

> "Apesar do rating B, a queda de 108 pontos em 60 dias, concentrada em execuções de credores
> distintos, indica crise de liquidez. Suspendo nova exposição a prazo até o vencimento de
> 2026-10-28 e condiciono a retomada à baixa de ao menos duas execuções."

`scoreNoMomento` e `ratingNoMomento` **são escritos** aqui, e isso **não viola a regra central**:
são o registro histórico do que o analista viu, não uma avaliação do motor. Devem coincidir com o
recálculo do snapshot correspondente — e o teste `test_auditoria_coerente` verifica exatamente
isso, com tolerância de 0,5 ponto.

---

## 14. Critérios de aceitação do dataset

Testes obrigatórios em `api/tests/test_dataset.py` e `api/tests/test_dataset_coerente.py`:

| Teste | Verifica |
|---|---|
| `test_18_clientes_e_4_prospects` | Contagem, unicidade de `id` e de `documento` |
| `test_documentos_validos` | Dígito verificador de CPF e CNPJ nos 22 registros |
| `test_score_de_cada_cliente` | Score calculado bate com a §5, tolerância 0,1 |
| `test_rating_final_de_cada_cliente` | `ratingFinal` bate com a §5, incluindo os 3 vetos e os 2 tetos |
| `test_todos_os_gatilhos_de_veto` | Os 8 gatilhos da spec 02 §8 são exercidos pelo dataset |
| `test_i5_eixos_independentes` | `ipanema-graos` PD12 < 15% e RJ12 > 30%; `joao-camargo` PD12 > 25% e RJ12 < 5% |
| `test_fechamento_i2_todos_os_snapshots` | 22 × 6 = 132 recálculos, diferença < 0,5 |
| `test_fechamento_i6_snapshots_consecutivos` | 18 × 5 = 90 pares, diferença < 0,5 |
| `test_delta_712_604` | `cerrado-norte` T5 = 712,0 ± 0,5 · T6 = 604,0 ± 0,5 · Σ deltas = −108,0 ± 0,5 |
| `test_tendencia_de_cada_cliente` | A tendência derivada bate com a §8.2 nos 18 |
| `test_stay_period_ponta_verde` | 66 dias decorridos, 114 restantes, ativo em 2026-09-12 |
| `test_exposicao_total_da_carteira` | R$ 244.300.000,00 exatos |
| `test_coerencia_v1_a_v40` | As 40 regras da §12 (V6 e V27 com as exceções declaradas) |
| `test_data_nao_importa_scoring` | AST: nenhum import de `scoring` em `api/data/**` |
| `test_data_nao_escreve_derivado` | AST: nenhuma atribuição a campo derivado em `api/data/**` |
| `test_snapshots_sao_seis_e_terminam_no_atual` | 6 por cliente, último idêntico a `FATOS` |
| `test_todas_as_14_fontes_aparecem` | Cada `FonteId` tem ao menos uma evidência no dataset |
| `test_quatro_severidades_de_evento` | CRÍTICA, ALTA, MÉDIA e BAIXA presentes |
| `test_auditoria_coerente` | `scoreNoMomento` bate com o recálculo do snapshot, tolerância 0,5 |

**Se um destes testes falhar depois de alguém editar um fato, a correção é refazer a calibração
da §7 daquele cliente — nunca alterar `api/scoring/config.py`.**
