"""Engenharia de features e pre-processamento.

Tudo aqui roda DENTRO do `Pipeline` do sklearn, nunca antes dele. A razao e
operacional: o bundle salvo em `artefatos/` recebe o dicionario cru de
`coleta.features.build_features` e devolve probabilidade, sem que a API precise
repetir uma linha de transformacao. Feature engineering feita fora do pipeline
e a causa numero um de divergencia treino/producao.

Tres decisoes que valem explicacao:

1. **Termos log1p centrados.** `log1p(capital_social)` vale ~12 e, num modelo
   linear, domina o intercepto. Centrar na referencia (180 mil de capital, 240
   meses de idade) devolve ao intercepto o controle da taxa base. As referencias
   sao as mesmas de `alvo_coeficientes.json`, o que permite comparar os
   coeficientes estimados com os que geraram o alvo sintetico.

2. **Zero semantico vs. imputacao.** Parte dos nulos NAO e "nao sei": um desvio
   de produtividade ausente e um desvio neutro (zero), e protesto ausente e zero
   protesto. Esses campos sao preenchidos aqui, com dominio, e nao pelo
   `SimpleImputer`. Os que sao genuinamente desconhecidos -- produtividade
   absoluta, ticket medio, precipitacao acumulada -- ficam NaN e seguem para o
   imputador (ou direto para o booster, que trata NaN nativamente).

3. **Indicador por BLOCO, nao por coluna.** A ausencia vem em bloco: quando o
   municipio nao esta no PAM, as tres features do IBGE somem juntas. Quatro
   indicadores (`falta_bcb`, `falta_ibge`, `falta_clima`, `falta_protestos`)
   carregam essa informacao sem inflar a matriz com 16 colunas redundantes.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import esquema

# Nulo destes campos significa "zero", nao "desconhecido".
#
# Vem da propria coleta: `protestos.features(None)` devolve None quando a
# consulta nao rodou, e a consulta so nao roda quando nao havia protesto a
# achar ou a rede estava desligada. Os dois casos puxam o risco para baixo, e
# `falta_protestos` fica para o modelo distinguir um do outro. Desvio e anomalia
# sao medidas RELATIVAS: ausente = na media = zero, que e tambem o que o gerador
# do alvo sintetico faz (`f[...] or 0.0`).
ZERO_SEMANTICO = (
    "divida_ativa_total",
    "divida_ativa_ajuizada",
    # Passivo CONTINGENTE: inscricoes em que o CNPJ e corresponsavel, nao
    # devedor principal. Nao e componente de `divida_ativa_total` -- no mock,
    # 112 das 130 empresas com corresponsavel nao tem divida propria nenhuma, e
    # a correlacao entre os dois log1p e -0.008. Entra como eixo de risco
    # separado, nao como refinamento do total.
    "divida_ativa_corresponsavel",
    "delta_divida_2_trimestres",
    "n_inscricoes",
    "valor_multas_ambientais",
    "area_embargada_ha",
    "n_autos_infracao",
    "n_filiais",
    "n_empresas_do_socio",
    "n_empresas_do_socio_com_divida_ativa",
    "n_empresas_do_socio_inaptas",
    "desvio_produtividade_vs_media_5a",
    "precipitacao_vs_normal_climatologica",
    "anomalia_na_fase_critica",
    "n_protestos_ativos",
    "valor_total_protestado",
    "n_cartorios_distintos",
)

# Valores absolutos em escala propria: nulo aqui e ignorancia de verdade.
MANTER_NAN = (
    "idade_empresa_meses",
    "capital_social",
    "n_socios",
    "volume_credito_rural_municipio",
    "n_contratos_municipio",
    "ticket_medio_municipio",
    "credito_por_hectare_municipio",
    "produtividade_municipal_cultura",
    "area_plantada_municipio_cultura",
    "precipitacao_acumulada_ciclo",
    "dias_secos_consecutivos_max",
    "dias_desde_protesto_mais_recente",
)

# Cap de 10 autos de infracao: o gerador do alvo satura ali, e em dado real a
# cauda (uma empresa com 200 autos) domina qualquer coeficiente linear.
CAP_AUTOS = 10.0

# Colunas cruas que saem da matriz porque uma derivada as substitui por completo.
#
# Nao e economia de memoria, e corretude de duas naturezas:
#
# - Para ARVORE, `log1p(x)` e monotono em `x`: as duas colunas oferecem
#   exatamente os mesmos pontos de corte. Manter as duas nao adiciona um split
#   possivel, so dilui a importancia da feature entre duas linhas do relatorio.
#
# - Para a LOGISTICA, o par e colinear e a penalidade l2 reparte o coeficiente
#   entre os gemeos de forma arbitraria. Foi o que aconteceu na primeira versao
#   deste arquivo: `n_autos_infracao` ficou com +0.37 e `n_autos_infracao_cap`
#   com -0.06, e `flag_embargo_ativo` saiu NEGATIVO (-0.45) compensado por
#   `log1p_area_embargada_ha` (+0.45) -- dois sinais invertidos em relacao ao
#   alvo conhecido, sem nenhum erro de pipeline por tras. Coeficiente que troca
#   de sinal por colinearidade inviabiliza a auditoria de uma recusa de credito,
#   que e o motivo de a logistica estar neste comparativo.
SUBSTITUIDAS_POR_DERIVADA = (
    # valor -> log1p_valor
    "divida_ativa_total",
    "divida_ativa_ajuizada",
    "divida_ativa_corresponsavel",
    "valor_multas_ambientais",
    "valor_total_protestado",
    "volume_credito_rural_municipio",
    "ticket_medio_municipio",
    "area_plantada_municipio_cultura",
    # valor -> log1p_valor_centrado
    "capital_social",
    "idade_empresa_meses",
    # n_autos_infracao -> n_autos_infracao_cap
    "n_autos_infracao",
    # o evento ja esta em flag_embargo_ativo; ver REMOVIDAS_POR_COLINEARIDADE
    "area_embargada_ha",
)

# Termos log1p gerados. `divida_ativa_ajuizada` e `area_embargada_ha` ficaram
# FORA desta lista de proposito -- ver REMOVIDAS_POR_COLINEARIDADE.
TERMOS_LOG1P = (
    "divida_ativa_total",
    "divida_ativa_corresponsavel",
    "valor_multas_ambientais",
    "valor_total_protestado",
    "volume_credito_rural_municipio",
    "ticket_medio_municipio",
    "area_plantada_municipio_cultura",
)

# Features que uma varredura de colinearidade na matriz derivada eliminou.
#
# Medido no mock (3000 linhas): sete pares com |r| >= 0.90, todos resolvidos
# removendo quatro colunas. Os numeros sao do dado, nao de intuicao:
#
#   0.993  log1p_divida_ativa_total  ~ log1p_divida_ativa_ajuizada
#   0.989  log1p_valor_total_protestado ~ tem_protesto
#   0.987  flag_embargo_ativo        ~ log1p_area_embargada_ha
#   0.983  log1p_divida_ativa_total  ~ tem_divida_ativa
#   0.974  log1p_divida_ativa_ajuizada ~ tem_divida_ativa
#   0.905  falta_protestos           ~ tem_protesto
#   0.903  n_cartorios_distintos     ~ tem_protesto
#
# O que sai e por que a informacao nao se perde:
#
# - `tem_divida_ativa` e `tem_protesto`: indicadores de "passou de zero". A ideia
#   era um modelo hurdle (salto em zero + inclinacao acima dele), mas a r de 0.98
#   com o proprio log1p diz que os dois nao sao separadamente estimaveis nesta
#   amostra. O log1p sozinho ja vale zero exatamente quando o valor e zero.
#
# - `log1p_divida_ativa_ajuizada`: r de 0.993 com o total. A COMPOSICAO da divida
#   (quanto do total ja foi ajuizado) e o que interessa e continua presente, em
#   `razao_divida_ajuizada`, que por ser razao nao e colinear com o nivel.
#
# - `log1p_area_embargada_ha`: `area_embargada_ha > 0` e `flag_embargo_ativo`
#   sao o MESMO evento no dado -- 47 casos cada, zero discordancia, porque a
#   coleta deriva os dois da mesma consulta. Com 47 positivos nao da para
#   estimar um efeito de area separado do efeito de ter embargo. Reavalie quando
#   o dado real trouxer volume de embargo: ai a area passa a ter variancia
#   propria e o termo vale a pena de volta.
REMOVIDAS_POR_COLINEARIDADE = (
    "tem_divida_ativa",
    "tem_protesto",
    "log1p_divida_ativa_ajuizada",
    "log1p_area_embargada_ha",
)

# A excecao ao limiar de 0.90, e o motivo de ele ser triagem e nao regra.
#
# `falta_protestos` ~ `log1p_valor_total_protestado` da r = 0.919 e FICA. A
# correlacao e consequencia mecanica de 88,5% de ausencia no bloco, nao
# redundancia de significado: o indicador separa tres situacoes que o valor
# sozinho funde em duas.
#
#   bloco ausente (nao consultado)   n=2655   inadimplencia 6,9%
#   consultado, sem protesto         n=  43   inadimplencia 4,7%
#   consultado, com protesto         n= 302   inadimplencia 19,5%
#
# Sem `falta_protestos`, as duas primeiras linhas viram o mesmo `valor = 0` e a
# diferenca entre "nao sei" e "sei que nao tem" desaparece. Antes de cortar um
# par por correlacao alta, cheque se os grupos que ele distingue tem taxa
# diferente -- foi o que mudou a decisao aqui.


def _div(numerador: pd.Series, denominador: pd.Series, piso: float = 1.0) -> pd.Series:
    """Razao com piso no denominador. Evita inf sem mascarar o numerador."""
    return numerador / denominador.clip(lower=piso)


def colunas_consumidas() -> set[str]:
    """Colunas de entrada que a engenharia de fato le."""
    return {*ZERO_SEMANTICO, *MANTER_NAN, *esquema.BOOLEANAS, *esquema.CATEGORICAS}


def conferir_cobertura_do_esquema() -> tuple[list[str], list[str]]:
    """Compara o esquema com o que a engenharia consome. Devolve (ignoradas, orfas).

    Existe porque este arquivo tem listas explicitas (`ZERO_SEMANTICO`,
    `MANTER_NAN`) enquanto `esquema.features_de_entrada()` le
    `data/mock/esquema.csv` em tempo de execucao. As duas fontes podem divergir, e
    a divergencia e SILENCIOSA nas duas direcoes:

    - `ignoradas`: coluna no esquema que nenhuma lista le. Foi o que aconteceu
      com `divida_ativa_corresponsavel` -- a coleta passou a publicar a coluna, ela
      entrou em `X` e o `transform` a descartou sem dizer nada. Feature coletada e
      nao usada e o pior dos dois mundos: custa consulta e nao rende AUC.
    - `orfas`: lista aqui que aponta para coluna que o esquema nao tem mais.
      Viraria `KeyError` no primeiro `transform`.

    Chamada em `fit` (aviso) e testada em `tests/test_modelos.py` (falha). O teste
    e o guarda de verdade: ele quebra quando alguem adiciona feature na coleta sem
    ligar aqui.
    """
    entrada = set(esquema.features_de_entrada())
    consumidas = colunas_consumidas()
    return sorted(entrada - consumidas), sorted(consumidas - entrada)


class EngenhariaAgro(BaseEstimator, TransformerMixin):
    """Colunas cruas da coleta -> quadro de features modelaveis.

    Sem estado aprendido: `fit` so memoriza os nomes de saida, para que
    `get_feature_names_out` funcione e o ColumnTransformer a jusante possa
    selecionar por nome. Isso mantem o transformador identico em treino e em
    inferencia, inclusive para uma linha so.
    """

    def __init__(self, referencias: dict[str, float] | None = None) -> None:
        self.referencias = referencias or dict(esquema.REFERENCIAS_LOG)

    # ------------------------------------------------------------- sklearn --
    def fit(self, X: pd.DataFrame, y=None):  # noqa: N803 - convencao do sklearn
        ignoradas, orfas = conferir_cobertura_do_esquema()
        if ignoradas:
            warnings.warn(
                f"colunas do esquema que a engenharia NAO le e que portanto nao "
                f"chegam ao modelo: {ignoradas}. Ligue em ZERO_SEMANTICO ou "
                f"MANTER_NAN (e em TERMOS_LOG1P se for valor de cauda longa).",
                UserWarning,
                stacklevel=2,
            )
        if orfas:
            warnings.warn(
                f"a engenharia referencia colunas que o esquema nao tem: {orfas}",
                UserWarning,
                stacklevel=2,
            )
        quadro = self.transform(X)
        self.feature_names_in_ = np.asarray(list(X.columns), dtype=object)
        self.numericas_ = [c for c in quadro.columns if c not in self.categoricas_]
        self.feature_names_out_ = list(quadro.columns)
        return self

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        return np.asarray(self.feature_names_out_, dtype=object)

    @property
    def categoricas_(self) -> list[str]:
        return [*esquema.CATEGORICAS, "cnae_divisao", "natureza_juridica_grupo"]

    # ----------------------------------------------------------- transform --
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=getattr(self, "feature_names_in_", None))

        bruto = X.copy()
        for col in esquema.features_de_entrada():
            if col not in bruto.columns:
                bruto[col] = np.nan

        saida = pd.DataFrame(index=bruto.index)

        # --- 1. indicadores de bloco, ANTES de qualquer preenchimento -------
        faltas = []
        for bloco, colunas in esquema.BLOCOS_AUSENCIA.items():
            presentes = [c for c in colunas if c in bruto.columns]
            # Sentinela: a primeira coluna do bloco. O bloco sai inteiro junto,
            # entao testar uma coluna ou todas da no mesmo -- `all` e mais
            # seguro contra um nulo solitario dentro de um bloco presente.
            indicador = (
                bruto[presentes].isna().all(axis=1).astype("float64")
                if presentes
                else pd.Series(1.0, index=bruto.index)
            )
            saida[f"falta_{bloco}"] = indicador
            faltas.append(indicador)
        saida["n_blocos_ausentes"] = sum(faltas)

        # --- 2. zero semantico e NaN preservado ----------------------------
        num = pd.DataFrame(index=bruto.index)
        for col in ZERO_SEMANTICO:
            num[col] = pd.to_numeric(bruto[col], errors="coerce").fillna(0.0)
        for col in MANTER_NAN:
            num[col] = pd.to_numeric(bruto[col], errors="coerce")
        for col in esquema.BOOLEANAS:
            # Flag ausente = fonte nao carregada; `falta_*` ja marca o bloco, e
            # tratar como "nao" e a leitura conservadora para uma flag de risco.
            num[col] = pd.to_numeric(bruto[col], errors="coerce").fillna(0.0)

        # --- 3. termos log1p -----------------------------------------------
        for col in TERMOS_LOG1P:
            num[f"log1p_{col}"] = np.log1p(num[col].clip(lower=0))

        for col, referencia in self.referencias.items():
            num[f"log1p_{col}_centrado"] = np.log1p(
                num[col].clip(lower=0)
            ) - np.log1p(referencia)

        # --- 4. razoes de credito ------------------------------------------
        num["razao_divida_ajuizada"] = _div(
            num["divida_ativa_ajuizada"], num["divida_ativa_total"]
        ).clip(0, 1)
        # Alavancagem em ESCALA LOG, nao na razao crua.
        #
        # A razao crua nao sobrevive ao dado real. 44% das agro reais declaram
        # capital social <= R$ 1 (matriz de microempresa e assim mesmo), entao o
        # piso de R$ 1 do `_div` vira o denominador de verdade e a razao explode:
        #
        #   divida_sobre_capital   treino (mock)   p99 16      max      1.187
        #                          real            p99 13 mi   max 55.776.835
        #
        # Num modelo linear isso satura o logit e o score cola em 1,000 para
        # qualquer microempresa com divida -- que e metade da carteira agro. O
        # log1p preserva a ordenacao (e monotono), mantem o sinal "divida grande
        # perto do capital = risco" e traz o max para ~18 em vez de 5,6e7.
        for alvo_, numerador_ in (
            ("divida", "divida_ativa_total"),
            ("protestado", "valor_total_protestado"),
            ("corresponsavel", "divida_ativa_corresponsavel"),
        ):
            num[f"log1p_{alvo_}_sobre_capital"] = np.log1p(
                _div(num[numerador_], num["capital_social"].fillna(0.0)).clip(lower=0)
            )
        num["log1p_divida_por_inscricao"] = np.log1p(
            _div(num["divida_ativa_total"], num["n_inscricoes"]).clip(lower=0)
        )
        num["cresc_divida_rel"] = _div(
            num["delta_divida_2_trimestres"], num["divida_ativa_total"]
        )
        num["prop_ligadas_com_divida"] = _div(
            num["n_empresas_do_socio_com_divida_ativa"], num["n_empresas_do_socio"]
        ).clip(0, 1)
        num["prop_ligadas_inaptas"] = _div(
            num["n_empresas_do_socio_inaptas"], num["n_empresas_do_socio"]
        ).clip(0, 1)

        # --- 5. saturacoes e agregados -------------------------------------
        num["n_autos_infracao_cap"] = num["n_autos_infracao"].clip(upper=CAP_AUTOS)
        num["severidade_fiscal"] = (
            num["flag_divida_previdenciaria"] + num["flag_divida_fgts"]
        )
        # NAO ha termo de "estresse produtivo" aqui, e a ausencia e deliberada.
        #
        # A ideia era capturar a conjuncao quebra-de-safra + seca-na-fase-critica
        # ("cada uma sozinha e ruido, juntas o produtor nao colhe e nao paga").
        # Duas tentativas cairam:
        #
        #   soma    `-min(desvio,0) - min(anomalia,0)`: para um modelo linear,
        #           somar dois termos que ja estao no modelo nao adiciona funcao
        #           representavel nenhuma, so colinearidade (r -0.60 e -0.54 com
        #           as componentes) -- e o coeficiente saiu -0.51, invertido.
        #   produto `min(desvio,0) * min(anomalia,0)`: genuinamente nao-linear,
        #           mas ainda r -0.56 com `anomalia`, e coeficiente -0.13.
        #
        # O motivo de fundo e que `alvo_sintetico` e ADITIVO em desvio e anomalia
        # (coeficientes -0.90 e -0.55, sem termo cruzado): no mock nao existe
        # interacao para achar, e qualquer termo cruzado so rouba coeficiente dos
        # dois que tem sinal de verdade. Como o mock e o unico dado disponivel,
        # um termo que nao da para validar e que comprovadamente embaca a leitura
        # dos coeficientes da logistica sai.
        #
        # As tres arvores, por construcao, encontram essa interacao sozinhas se
        # ela existir. Quando o alvo real chegar, adicione o termo aqui e
        # COMPARE o AUC de CV com e sem -- ai da para decidir com evidencia.

        # As cruas ja cumpriram o papel de insumo das derivadas; daqui para
        # frente seriam so gemeas colineares.
        num = num.drop(
            columns=[*SUBSTITUIDAS_POR_DERIVADA, *REMOVIDAS_POR_COLINEARIDADE],
            errors="ignore",
        )
        saida = pd.concat([saida, num], axis=1)

        # --- 6. categoricas -------------------------------------------------
        for col in esquema.CATEGORICAS:
            saida[col] = bruto[col].astype("string").fillna("DESCONHECIDO")

        cnae = bruto["cnae_principal"].astype("string").str.replace(
            r"\D", "", regex=True
        )
        # Divisao CNAE = 2 primeiros digitos do codigo de 7. Generaliza o que
        # `cnae_principal` com 10+ niveis nao generaliza: soja e milho caem na
        # mesma divisao 01 e compartilham forca estatistica.
        saida["cnae_divisao"] = (
            cnae.str.zfill(7).str[:2].fillna("DESCONHECIDO").replace({"": "DESCONHECIDO"})
        )
        natjur = bruto["natureza_juridica"].astype("string").str.replace(
            r"\D", "", regex=True
        )
        saida["natureza_juridica_grupo"] = (
            natjur.str.zfill(4).str[:2].fillna("DESCONHECIDO").replace({"": "DESCONHECIDO"})
        )

        return saida.replace([np.inf, -np.inf], np.nan)


def construir_preprocessador(
    *, nan_nativo: bool, escalar: bool, min_frequencia: float = 0.01
) -> Pipeline:
    """Pipeline de preparo, configurado para a familia do modelo.

    `nan_nativo=True` (XGBoost, LightGBM): nao imputa nada. Os boosters
    aprendem a direcao do NaN em cada no, o que e melhor que qualquer mediana
    nossa. `nan_nativo=False` (regressao logistica, random forest): mediana nas
    numericas.

    `escalar=True` so para a logistica: sem padronizar, o `l2` pune o
    coeficiente de `capital_social` e deixa as flags livres, e o modelo vira
    outra coisa. Arvore nenhuma precisa de escala.
    """
    engenharia = EngenhariaAgro()
    categoricas = engenharia.categoricas_

    passos_num: list[tuple[str, object]] = []
    if not nan_nativo:
        passos_num.append(("imputar", SimpleImputer(strategy="median")))
    if escalar:
        passos_num.append(("escalar", StandardScaler()))
    ramo_num = Pipeline(passos_num) if passos_num else "passthrough"

    ramo_cat = Pipeline(
        [
            (
                "onehot",
                OneHotEncoder(
                    # `infrequent_if_exist` resolve os dois problemas de uma vez:
                    # CNAE raro no treino vira 'infrequente', e CNAE nunca visto
                    # em producao cai no mesmo balde em vez de explodir.
                    handle_unknown="infrequent_if_exist",
                    min_frequency=min_frequencia,
                    sparse_output=False,
                    dtype=np.float64,
                ),
            )
        ]
    )

    return Pipeline(
        [
            ("engenharia", engenharia),
            (
                "colunas",
                ColumnTransformer(
                    [
                        ("cat", ramo_cat, categoricas),
                        ("num", ramo_num, SelecionarNumericas(categoricas)),
                    ],
                    remainder="drop",
                    verbose_feature_names_out=False,
                ),
            ),
        ]
    )


class SelecionarNumericas:
    """Selector por exclusao: tudo que a engenharia produziu menos as categoricas.

    Callable em vez de lista fixa porque a engenharia cria colunas derivadas, e
    uma lista chumbada aqui desatualiza na primeira feature nova.

    Classe, e nao closure: `joblib.dump` serializa funcao por REFERENCIA ao nome
    qualificado, e uma funcao interna de fabrica nao tem nome importavel --
    `PicklingError` na hora de salvar o bundle. Instancia de classe de modulo
    pickla sem drama.
    """

    def __init__(self, categoricas: list[str]) -> None:
        self.categoricas = list(categoricas)

    def __call__(self, df: pd.DataFrame) -> list[str]:
        return [c for c in df.columns if c not in self.categoricas]

    def __repr__(self) -> str:  # aparece nos params logados no MLflow
        return f"SelecionarNumericas(exclui={len(self.categoricas)} categoricas)"


def nomes_de_features(pipeline: Pipeline) -> list[str]:
    """Nomes das colunas que chegam ao estimador, para importancia e coeficiente."""
    try:
        return list(pipeline.named_steps["colunas"].get_feature_names_out())
    except (KeyError, AttributeError):
        return []


__all__ = [
    "CAP_AUTOS",
    "EngenhariaAgro",
    "MANTER_NAN",
    "REMOVIDAS_POR_COLINEARIDADE",
    "SUBSTITUIDAS_POR_DERIVADA",
    "TERMOS_LOG1P",
    "SelecionarNumericas",
    "colunas_consumidas",
    "conferir_cobertura_do_esquema",
    "ZERO_SEMANTICO",
    "construir_preprocessador",
    "nomes_de_features",
]
