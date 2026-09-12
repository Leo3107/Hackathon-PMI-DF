# Camada de coleta — risco de crédito agro

Ingestão, armazenamento e montagem de features para um scorecard de risco de
crédito no agronegócio. A entrada é um CNPJ; a saída é um dicionário de
features em JSON.

Não há modelo de ML aqui — só coleta, warehouse e `build_features()`.

## Stack

Python 3.11+, DuckDB como warehouse, `httpx` para rede, `polars` para as fontes
que chegam como JSON, `pydantic` para o schema de saída, `typer` para a CLI e
`flask` para a API.

Nada passa por pandas em memória: os arquivos da Receita têm ~20 GB
descomprimidos e são lidos direto do disco pelo `read_csv` do DuckDB.

## Instalação

```bash
pip install -r requirements.txt
python -m coleta.cli init
```

`init` cria `data/`, o schema do warehouse e o CSV modelo de protestos.

## Uso

```bash
python -m coleta.cli bulk --source pgfn --quarters 8
```

```bash
python -m coleta.cli bulk --source receita --competencia 2026-08
```

```bash
python -m coleta.cli bulk --all
```

```bash
python -m coleta.cli features --documento 12345678000190
```

```bash
python -m coleta.cli status
```

Opções úteis: `--apenas empresas,socios` (Receita), `--culturas soja,milho`
(IBGE), `--municipios 5300108,3551702` e `--limite-clima 50` (clima),
`--ano-inicial 2020` (BCB), `--offline` (features sem tocar a rede).

## API (Flask)

Feita como Blueprint, para registrar no backend existente:

```python
from coleta.api import features_bp
app.register_blueprint(features_bp, url_prefix="/api/v1")
```

De pé sozinha, para desenvolvimento:

```bash
python -m flask --app "coleta.api:criar_app" run --port 5000
```

| Rota | O que faz |
|---|---|
| `GET /saude` | Liveness + quais fontes estão carregadas de fato |
| `GET /fontes` | Última carga e nº de linhas por tabela — responde "esse dado está velho?" |
| `GET /features/<cnpj>` | As 39 features de um CNPJ. `?cultura=soja`, `?rede=0\|1` |
| `POST /features/lote` | Vários CNPJs numa chamada, para escorar uma carteira |

Aceita CNPJ com ou sem máscara e a base de 8 dígitos. Dígito verificador
inválido devolve **400** — devolver 39 campos nulos para um número digitado
errado esconderia o erro em vez de mostrá-lo.

### Modo de conexão

O warehouse abre em **somente leitura** por padrão. DuckDB aceita vários
leitores simultâneos mas um único escritor, então read-only é o que permite
rodar com vários workers de gunicorn ao lado do agendador que roda as cargas.
Cada requisição usa um `cursor()` próprio sobre a conexão compartilhada.

A consequência é que a consulta ao vivo (clima e protestos) fica desligada —
ela precisa gravar no cache. Na prática isso não custa dado: quem preenche esse
cache é o `bulk --source clima`, rodado pelo agendador. Pedir `?rede=1` nesse
modo devolve **409** com a explicação, em vez de falhar em silêncio.

Para um deploy de um worker só, `COLETA_SOMENTE_LEITURA=0` habilita a consulta
ao vivo.

| Config do Flask | Padrão | Efeito |
|---|---|---|
| `COLETA_WAREHOUSE` | `data/warehouse.duckdb` | Caminho do banco |
| `COLETA_SOMENTE_LEITURA` | `True` | Read-only; desliga a consulta ao vivo |
| `COLETA_PERMITIR_REDE` | segue o modo | Força ligar/desligar a consulta ao vivo |
| `COLETA_LOTE_MAX` | `200` | Teto de documentos por chamada em lote |

Latência medida: **~420 ms** por CNPJ. A exceção é a primeira consulta de um
município ainda sem clima em cache — **17 s**, porque busca a normal
climatológica de 1991–2020 (10.958 dias). Pré-aqueça com
`bulk --source clima` antes de subir.

### Ordem de execução

1. **PGFN** e **Receita Federal** — independentes, dão resultado sozinhas.
2. **IBAMA** — independente.
3. **IBGE/SIDRA** — também carrega a tabela de municípios, de que o mapeamento
   de código da Receita → código IBGE depende.
4. **BCB/MDCR** — precisa do código IBGE para as features municipais.
5. **Clima** — usa o centroide dos municípios com maior área plantada, então
   roda depois do IBGE.
6. **Protestos** — só interface; nada a carregar em lote.

`bulk --all` já executa nessa ordem. Uma fonte que falha é registrada no log e
não impede as demais.

### Espaço em disco e tempo

Windows, SSD, banda doméstica; competência 2026-08 e trimestre 2026T1.
**M** = medido nesta máquina; **E** = extrapolado do tamanho do arquivo a
partir de uma partição medida.

| Fonte | Download | Tempo de carga | |
|---|---|---|---|
| PGFN — FGTS | 18 MB/trim. | 21 s (533 mil linhas) | M |
| PGFN — Previdenciário | 87 MB/trim. | ~2 min/trim. | E |
| PGFN — Dívida Ativa Geral (SIDA) | 1,23 GB/trim. | ~25 min/trim. | E |
| Receita — Empresas (10 partes) | 1,4 GB | 72 s por partição de 4,5 M linhas | M |
| Receita — Estabelecimentos (10 partes) | 5,3 GB | 32 s por partição de 4,8 M linhas | M |
| Receita — Sócios (10 partes) | 0,7 GB | 48 s por partição de 2,0 M linhas | M |
| Receita — Simples + tabelas de domínio | 0,3 GB | ~3 min | E |
| IBAMA — autos (710 mil) + embargos (114 mil) | 130 MB | 60 s (zip em cache) | M |
| IBGE/SIDRA — PAM | — | ~6 min por cultura (24 requisições de ~14 s) | M |
| BCB/MDCR | — | ver limitação abaixo | M |
| Clima — NASA POWER | — | 17 s por município (1991→hoje) | M |

Warehouse: 1,5 GB para ~12 M de linhas. Uma competência completa da Receita
(~60 M estabelecimentos) fica na casa de 25–30 GB.

**Planeje ~45 GB livres** para rodar tudo com 8 trimestres da PGFN: ~10 GB de
ZIPs em `data/raw/` (mantidos como cache) e ~30 GB de warehouse, mais folga
para o maior CSV extraído por vez (~2 GB).

Os ZIPs ficam em `data/raw/` e não são rebaixados se o tamanho confere. Os CSVs
extraídos são apagados assim que carregados — o pico de disco é o de um arquivo
por vez, não o dos 20 GB descomprimidos.

## O que foi verificado nas fontes (e onde a documentação mente)

Os layouts foram conferidos contra os arquivos reais em setembro de 2026, não
assumidos. O que apareceu de diferente do esperado:

- **PGFN — o CNPJ vem COM máscara** (`84.461.748/0001-81`), não sem. O
  coletor normaliza para dígitos. O CPF de pessoa física vem parcialmente
  ocultado (`XXX735.623XX`): é guardado como veio, marcado com
  `pf_mascarado = TRUE`, e nunca usado como chave de join.
- **PGFN — o separador decimal é ponto**, não vírgula, ao contrário do resto
  das bases de governo.
- **PGFN — os três sistemas de origem têm layouts diferentes.** SIDA e
  Previdenciário têm 13 colunas, FGTS tem 15 (com `ENTIDADE_RESPONSAVEL` e
  `UNIDADE_INSCRICAO`), e o Previdenciário troca `RECEITA_PRINCIPAL` por
  `TIPO_CREDITO`. Ler os três com o mesmo schema não funciona.
- **Receita — os CSVs não são latin-1 estrito, são cp1252.** Trazem bytes da
  faixa 0x80–0x9F que o leitor latin-1 do DuckDB recusa com
  `File is not latin-1 encoded`. Os arquivos são transcodificados para UTF-8
  durante a extração.
- **Receita — o diretório público é um Nextcloud (SERPRO+)**, cujas URLs
  "diretas" devolvem 404. O acesso estável é o WebDAV do compartilhamento
  público, com o token do share como usuário e senha vazia.
- **Receita — o código de município é próprio da RFB**, não é o código IBGE, e
  a tabela de domínio não traz UF. O mapeamento é feito por nome normalizado +
  UF do estabelecimento, contra a lista oficial do IBGE.
- **IBAMA — os CSVs são UTF-8 com vírgula decimal**, ao contrário das bases da
  Fazenda. O arquivo de embargos publicado no CKAN aponta para um blob que
  responde 404; a URL que funciona é a de `dadosabertos.ibama.gov.br`.
- **BCB/MDCR — a API OData está quebrada para carga em massa.** O deployment
  Olinda do SICOR aceita só `$top` e `$format`: `$skip` devolve 500 para
  qualquer valor (inclusive `$skip=1`), `$filter` devolve 400/500 em toda
  forma testada, e `$top` acima de ~5.000 estoura o gateway com 504. O dataset
  não publica CSV — os únicos recursos de dados são os endpoints da API. O
  coletor detecta isso em runtime: se `$skip` voltar a funcionar, ele pagina
  normalmente; se não, carrega o que cabe em uma janela de `$top`, registra
  `bcb.carga_parcial` no log e deixa as features do BCB parciais em vez de
  derrubar a carga.
- **BCB/MDCR — não há dado de acionamento de Proagro.** A matriz publica
  `cdTipoSeguro`, que é cobertura contratada, não sinistro.
  `acionamentos_proagro_municipio` é sempre `None` — não há proxy honesto.
- **SIDRA — pedir várias variáveis e anos de uma vez derruba a API.** Fatiado
  em uma requisição por (variável, ano, cultura) cobrindo todos os municípios,
  cada chamada devolve ~5,5 mil linhas em ~10 s.

## Fontes

| # | Fonte | Camada | Tabelas |
|---|---|---|---|
| 1 | PGFN — Dívida Ativa da União | bulk | `pgfn_divida` |
| 2 | Receita Federal — CNPJ | bulk | `rf_empresas`, `rf_estabelecimentos`, `rf_socios`, `rf_simples`, `rf_dominio`, `socio_empresa` |
| 3 | IBAMA — autos e embargos | bulk | `ibama_autos`, `ibama_embargos` |
| 4 | BCB — Matriz de Dados do Crédito Rural | bulk | `bcb_mdcr`, `bcb_mdcr_produto` |
| 5 | IBGE/SIDRA — PAM | bulk | `ibge_producao`, `ibge_municipios` |
| 6 | Clima — NASA POWER / INMET | bulk + sob demanda | `clima_diario`, `municipio_centroide` |
| 7 | Protestos | sob demanda | `protesto_cache` |

## Protestos: por que não há coletor automático

Não existe API pública gratuita de protestos, e o portal da CENPROT é protegido
por CAPTCHA. **Este projeto não quebra CAPTCHA nem contorna proteção
anti-bot** — isso violaria os termos de uso do serviço.

No lugar disso há uma interface de provedor com duas implementações em
[protestos.py](coleta/ondemand/protestos.py):

- `CSVManualProvider` — lê `data/raw/protestos_manual.csv`, preenchido à mão.
  É o caminho do demo. Colunas:
  `documento;data_protesto;valor;cartorio;uf;situacao`
- `ApiProvider` — stub para fornecedor homologado. O token vem de
  `PROTESTO_API_TOKEN` e a base de `PROTESTO_API_BASE_URL`. A chamada HTTP está
  isolada em um único método; o parsing e o cache já são definitivos.

Trocar de provedor é uma variável de ambiente:

```bash
COLETA_PROVEDOR_PROTESTO=api python -m coleta.cli features --documento 12345678000190
```

O resultado é cacheado por 24 h em `protesto_cache`.

## Features produzidas

Todo campo é opcional: `build_features()` devolve `None` quando não há dado e
**nunca** levanta exceção por dado ausente. Um bloco de fonte que falha vira
log e os campos daquela fonte ficam `None`.

Isso é o que faz `features --documento` funcionar com apenas PGFN e Receita
carregadas — todos os demais campos voltam `None`.

**PGFN** — `divida_ativa_total`, `divida_ativa_ajuizada`, `n_inscricoes`,
`delta_divida_2_trimestres`, `flag_divida_previdenciaria`, `flag_divida_fgts`

**Receita** — `idade_empresa_meses`, `capital_social`, `porte`,
`natureza_juridica`, `situacao_cadastral`, `flag_situacao_irregular`,
`cnae_principal`, `flag_cnae_agro`, `n_filiais`, `n_socios`

**Grafo societário** — `n_empresas_do_socio`,
`n_empresas_do_socio_com_divida_ativa`, `n_empresas_do_socio_inaptas`

**IBAMA** — `n_autos_infracao`, `valor_multas_ambientais`,
`flag_embargo_ativo`, `area_embargada_ha`

**BCB/MDCR** — `volume_credito_rural_municipio`, `n_contratos_municipio`,
`ticket_medio_municipio`, `credito_por_hectare_municipio`,
`acionamentos_proagro_municipio`

**IBGE/SIDRA** — `produtividade_municipal_cultura`,
`desvio_produtividade_vs_media_5a`, `area_plantada_municipio_cultura`

**Clima** — `precipitacao_acumulada_ciclo`,
`precipitacao_vs_normal_climatologica`, `dias_secos_consecutivos_max`,
`anomalia_na_fase_critica`

**Protestos** — `n_protestos_ativos`, `valor_total_protestado`,
`dias_desde_protesto_mais_recente`, `n_cartorios_distintos`

### Grafo societário

`socio_empresa` normaliza `rf_socios` em pares (sócio, empresa). A identidade
do sócio é o problema real: o CPF vem mascarado (`***240659**`) e não serve
sozinho como chave. A chave usada é CPF mascarado + nome para pessoa física, o
CNPJ para sócio PJ (que vem completo) e o nome para sócio estrangeiro.

A partir daí dá para sair do CNPJ consultado e andar pelo grafo: um sócio com
cinco empresas inaptas é um sinal que nenhum cadastro do próprio CNPJ mostra.

### Clima

As features de clima são calculadas sobre a **janela da safra**, não sobre o
ano civil, e sempre como **anomalia relativa à normal climatológica**
(1991–2020), não como valor absoluto — chuva crua tem pouco poder preditivo.

`anomalia_na_fase_critica` olha só o florescimento/enchimento de grãos, a
janela em que o déficit hídrico derruba produtividade de fato. O calendário por
cultura está em `CALENDARIO_CULTURAS`, em [config.py](coleta/config.py).

## Estrutura

```
coleta/
  config.py          # URLs, códigos de tabela, calendário agrícola
  http.py            # rate limit 2 req/s por host, backoff, download resumível
  warehouse.py       # conexão DuckDB e schema
  models.py          # schema pydantic da saída
  features.py        # build_features(documento) -> dict
  api.py             # Blueprint Flask
  cli.py
  logging_setup.py   # log estruturado em JSON, com contagem por etapa
  bulk/
    pgfn.py  receita.py  ibama.py  bcb_mdcr.py  ibge_sidra.py  clima.py
    _common.py         # extração streaming de ZIP, read_csv do DuckDB
  ondemand/
    protestos.py
data/
  raw/               # ZIPs baixados (cache) e protestos_manual.csv
  warehouse.duckdb
```

## Garantias de operação

- **Idempotência** — cada carga apaga sua partição (`competencia`, `origem`)
  antes de inserir. Rodar duas vezes não duplica linha; verificado na PGFN.
- **Downloads resumíveis e cacheados** — se o arquivo existe com o tamanho do
  remoto, não rebaixa; se existe parcial, continua via `Range`.
- **Rate limit** — no máximo 2 req/s por host, com backoff exponencial em
  429/5xx e respeito ao `Retry-After`.
- **Isolamento por fonte** — falha de uma fonte é registrada e não derruba as
  outras, tanto em `bulk --all` quanto em `build_features`.
- **Logging estruturado** — JSON lines em stderr, com `linhas` e `duracao_s`
  por etapa. `COLETA_LOG_LEVEL=DEBUG` para mais detalhe.

## Variáveis de ambiente

| Variável | Efeito |
|---|---|
| `COLETA_DATA_DIR` | Raiz de `raw/` e do warehouse |
| `COLETA_WAREHOUSE` | Caminho do arquivo DuckDB |
| `COLETA_PROVEDOR_CLIMA` | `nasa_power` (padrão) ou `inmet` |
| `COLETA_PROVEDOR_PROTESTO` | `csv_manual` (padrão) ou `api` |
| `COLETA_CULTURA_PADRAO` | Cultura de referência (padrão: `soja`) |
| `COLETA_LOG_LEVEL` | Nível de log |
| `PROTESTO_API_BASE_URL`, `PROTESTO_API_TOKEN` | Fornecedor de protestos |
