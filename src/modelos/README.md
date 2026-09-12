# Camada de modelagem — score de risco de inadimplência agro

Quatro modelos (regressão logística, random forest, XGBoost, LightGBM) treinados
com **entropia cruzada binária** como perda e **AUC** como métrica de seleção,
sobre as features de `coleta.features.build_features`.

```bash
pip install -r requirements-ml.txt
```

## Rodar

```bash
# treinar os quatro na mesma partição e comparar
python -m src.modelos.treino.treinar_todos --promover-melhor

# um modelo só
python -m src.modelos.treino.treinar_xgboost --taxa 0.03 --arvores 1200

# ver as runs
mlflow ui --backend-store-uri sqlite:///mlflow.db

# artefatos de fumaça (segundos, sem CV, sem MLflow) — só para destravar a API
python -m src.modelos.treino.salvar_modelos

# pontuar pela linha de comando
python -m src.modelos.inferencia --csv data/mock/features_agro_mock.csv --limite 3
python -m src.modelos.inferencia --info
```

## Usar na API

```python
from coleta.features import build_features
from src.modelos.inferencia import scorer_padrao

scorer = scorer_padrao()          # carregue no boot, não na 1ª requisição

@app.get("/api/v1/score/<documento>")
def score(documento):
    return jsonify(scorer.pontuar(build_features(documento, con=cursor)))
```

Resposta:

```json
{
  "documento": "12345678000190",
  "probabilidade_inadimplencia": 0.987748,
  "score_risco": 988,
  "faixa_risco": "CRITICO",
  "modelo": "regressao_logistica",
  "sinais_observados": ["divida ativa na PGFN", "embargo ambiental ativo", "..."],
  "fontes_ausentes": []
}
```

> `src` não é pacote instalado: o processo precisa ter a raiz do repo no path.
> Rode a API a partir da raiz (como já é o caso de `flask --app coleta.api`) ou
> exporte `PYTHONPATH=/caminho/do/repo`. O `joblib` guarda o caminho das classes,
> não o código, então `src.modelos.preparo` **tem** de ser importável no processo
> que carrega o modelo — é por isso que `EngenhariaAgro` vive num módulo estável e
> não numa função local do script de treino.

`score_risco` é 0–1000 e **maior = mais risco** (invertido em relação a score de
bureau, de propósito: quem lê é uma política de risco). As faixas saem dos
quantis 0.80/0.95/0.99 da distribuição de treino e viajam dentro do artefato —
mudar de modelo muda a distribuição, então um corte chumbado em `0.3` no código
da API deixaria de significar a mesma coisa.

`pontuar` aceita um dict ou uma lista, em qualquer ordem de chaves, com campo a
mais (ignorado) ou a menos (vira `NaN`, que é o que o modelo viu no treino).
Nunca levanta por dado faltando.

## Arquivos

| arquivo | papel |
|---|---|
| `esquema.py` | papéis das colunas, blocos de ausência, dtypes |
| `dados.py` | carga do CSV e split **agrupado por município** |
| `preparo.py` | engenharia de features + `ColumnTransformer` |
| `avaliacao.py` | AUC, logloss, KS, Brier, captura no decil, gráficos |
| `rastreio.py` | MLflow + diagnóstico da qualidade do dado |
| `artefatos.py` | bundle `.joblib` (pipeline + metadados + faixas) |
| `inferencia.py` | `Scorer` — o que a API importa |
| `treino/` | um script por modelo + `treinar_todos` + `salvar_modelos` |

Produção importa só `esquema`, `preparo`, `dados`, `artefatos` e `inferencia`.
`rastreio` e `avaliacao` (matplotlib, mlflow) ficam do lado do treino.

## As três armadilhas do dado, e o que cada uma exigiu

O `scripts/gerar_mock.py` documenta três propriedades do dado real que quebram um
pipeline de ML se ignoradas. Cada uma virou uma decisão aqui:

**1. As 12 features municipais repetem entre empresas do mesmo município.**
São 45 municípios em 3000 linhas. Um `train_test_split` aleatório põe empresas do
mesmo município nos dois lados e o modelo acerta o teste porque decorou o
município. Todo split é `StratifiedGroupKFold` agrupando por `municipio_ibge` —
estratificado, não só agrupado, porque com 8,1% de positivos um `GroupKFold` puro
pode entregar fold sem positivo e o AUC viraria `NaN`. `municipio_ibge` é o grupo,
nunca uma feature. O harness imprime `municipios_em_comum` e alerta se não for 0.

**2. A ausência é estruturada, não aleatória.** Quando o município não está no
PAM, as três features do IBGE somem juntas. Daí dois mecanismos: um indicador por
**bloco** (`falta_bcb`, `falta_ibge`, `falta_clima`, `falta_protestos`, mais
`n_blocos_ausentes`) em vez de um por coluna; e a distinção entre *zero
semântico* e *ignorância*. Desvio de produtividade ausente é desvio neutro
(zero); protesto ausente é zero protesto — esses são preenchidos com domínio, não
com mediana. Capital social, produtividade absoluta e ticket médio ausentes são
ignorância de verdade: ficam `NaN` e vão para o imputador (logística e random
forest) ou direto para o booster, que escolhe a direção do `NaN` em cada nó.

**3. As categóricas são códigos com zero à esquerda.** `porte` `'02'`,
`cnae_principal` `'0115600'`. Lidos com `dtype=str` via `esquema.mapa_dtypes()`;
`'02'` lido como int vira `2` e não casa com o que a API manda. Há teste para isso.

## O que o mock pode e o que não pode te dizer

`alvo_sintetico` é **fabricado** por uma logística de coeficientes conhecidos
(`data/mock/alvo_coeficientes.json`). O AUC dele não mede nada sobre
inadimplência real. Três coisas nele são informativas:

**O teto de AUC.** Como o alvo é um *sorteio* de Bernoulli sobre `sigmoide(z)`,
existe um máximo teórico: mesmo conhecendo a função geradora exata, o AUC
possível é **0.8216** (logloss 0.2216). Isso muda a leitura de qualquer número
daqui — a logística em 0.79 está a **97% do teto**, não a 79% de um ideal de 1.0.
Não persiga AUC acima disso no mock; se aparecer, é vazamento.

**Recuperação dos sinais.** Os coeficientes estimados pela logística devem
reproduzir os *sinais* dos verdadeiros. O harness reporta como
`recuperacao_sinais_frac`; hoje dá **10/10**. Compare sinal, nunca magnitude: um
termo verdadeiro de 0.14 sai estimado em 0.54 sem que nada esteja errado.

Trate 9/10 e 10/10 como equivalentes, porque o décimo termo é instável por
construção do mock. O gerador faz `tem_auto = perfil.startswith("passivo_ambiental")`,
o que torna o perfil de embargo um subconjunto **estrito** do perfil com auto de
infração — 48 de 48 embargados também têm auto, com média de 8,7 autos contra
0,79 no resto. Sobra pouquíssimo resíduo para identificar o efeito do embargo
separado do efeito dos autos, e o coeficiente oscila com o sorteio: entre duas
regerações do mesmo gerador ele foi de **−0.008** (resíduo de inadimplência
17,0% com embargo vs 16,4% sem) para **+0.15** (20,8% vs 11,7%). Em dado real do
IBAMA os dois eventos não são aninhados assim. Desconfie abaixo de 9/10.

**Qualidade da matéria-prima.** Isso sim vale hoje, e é o que o MLflow registra
em toda run (prefixo `dados_`):

| | preenchimento |
|---|---|
| bloco PGFN / Receita | ~100% |
| bloco BCB (crédito rural) | 75,6% |
| bloco IBGE (produção) | 73,7% |
| bloco clima | 57,3% |
| bloco protestos | **11,5%** |
| `acionamentos_proagro_municipio` | **0%** — excluída do esquema |

Duas colunas são constantes no mock e não carregam sinal nenhum:
`cultura_referencia` (só soja) e `flag_cnae_agro` (sempre verdadeiro). O
`OneHotEncoder` as absorve sem dano, e `dados_colunas_constantes` as conta em
toda run — se continuarem constantes no dado real, vale removê-las do esquema.

E `dados_eventos_por_coluna` = **5,95**. Abaixo de ~10 eventos por parâmetro,
modelo linear começa a decorar. Com 244 positivos e 89 colunas pós-one-hot, a
conclusão acionável do mock é sobre **volume**: mais linhas, e cobertura de
protestos antes de qualquer ajuste fino de hiperparâmetro.

O artefato `preenchimento_por_coluna.csv` de cada run responde "coletar mais o
quê?" — uma coluna com 90% de nulo é, na prática, uma coluna que o modelo não tem.

## Seleção do campeão

Por **AUC médio do CV**, não pelo AUC do holdout. Com 9 municípios e ~52
positivos no holdout, o intervalo de confiança do AUC de teste é largo o bastante
para que escolher por ele seja escolher por sorte de partição. O CV dá 5
estimativas e o desvio-padrão — que é o número que diz se a diferença entre o
primeiro e o segundo colocado significa algo.

`campeao.json` é um ponteiro: trocar o modelo em produção é reescrever duas
linhas de JSON, sem deploy de código.

```bash
python -m src.modelos.treino.treinar_todos --promover xgboost
```

## Calibração

AUC mede **ordenação**. Um modelo com AUC 0.85 pode dizer "40% de chance" para um
grupo que inadimple 8% das vezes: a ordem está certa e o número está errado. Como
este score vira decisão de crédito, o número importa — então `logloss` e `brier`
aparecem em todo relatório ao lado do AUC, e há curva de confiabilidade nos
gráficos de cada run.

`--calibrar sigmoide|isotonica` ajusta um calibrador em holdout agrupado separado
do que treinou o modelo. `--balancear` faz o contrário: melhora recall e **piora**
a calibração, porque o modelo passa a prever a probabilidade de um mundo com 50%
de inadimplência. Deixe desligado se o score vai ser lido como probabilidade.

## Quando o alvo real chegar

```bash
python -m src.modelos.treino.treinar_todos --dados data/features_reais.csv \
    --alvo inadimplencia_90d --promover-melhor
```

Três coisas a revisitar, anotadas no código onde importam:

- **`log1p_area_embargada_ha`** (`preparo.REMOVIDAS_POR_COLINEARIDADE`): saiu
  porque com 47 casos a área não é estimável separada do evento. Com volume real
  de embargo, a área ganha variância própria e o termo volta a valer.
- **Termo de interação safra × clima** (comentado em `preparo.py`): o alvo
  sintético é aditivo em `desvio` e `anomalia`, então no mock não há interação
  para achar. Adicione e **compare o AUC de CV com e sem**, em vez de assumir.
- **Número de árvores dos boosters**: sem early stopping de propósito — dentro de
  um `Pipeline` sob CV agrupado, o conjunto de validação do early stopping sairia
  do mesmo município do treino e pararia cedo pelo motivo errado. Calibre pelo
  desvio do CV.
