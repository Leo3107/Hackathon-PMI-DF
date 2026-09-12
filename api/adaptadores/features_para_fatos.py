"""Tradução `Features` (coleta pública) → `FatosDoCliente` (motor de risco).

`Features` é achatado, tem 39 campos e **todos opcionais por construção**.
`FatosDoCliente` é estruturado e o motor lê todos os campos. Cada `None` é,
portanto, uma decisão de produto — não de código.

    O erro fatal seria tratar dado ausente como dado favorável.

Se a PGFN não respondeu, `divida_ativa_total = None` não significa "não tem
dívida": significa "não sei". Virar `0.0` em silêncio faria o sistema dar nota
alta a quem talvez seja péssimo, e o produto passaria a mentir exatamente onde
promete evidência.

Módulo **puro**: recebe `Features`, devolve `FatosDoCliente` + cobertura. Sem
I/O, sem rede, sem relógio — a data de referência é parâmetro obrigatório.


TABELA DE POLÍTICA POR CAMPO
════════════════════════════

Legenda das políticas (mecânica em `cobertura.py`):
  MAPEADO      — a fonte respondeu; o valor é traduzido fielmente.
  NEUTRO       — nenhuma fonte da dimensão respondeu; a dimensão sai da média
                 ponderada (peso 0, redistribuído entre as apuradas).
  CONSERVADOR  — a fonte respondeu e o campo veio vazio, e o vazio é sinal;
                 assume-se o pior plausível **dentro do score**.
  NAO_APURADO  — o fator não tem fonte nenhuma na coleta; recebe o valor de
                 impacto zero e é listado na cobertura como cego.

┌── FISCAL ← PGFN ──────────────────────────────────────────────────────────┐
│ Features                     │ Fato                            │ Política │
├──────────────────────────────┼─────────────────────────────────┼──────────┤
│ divida_ativa_total           │ fiscal.divida_ativa_pgfn        │ MAPEADO  │
│   ausente                    │   →                             │ NEUTRO   │
│ divida_ativa_ajuizada        │ fiscal.valor_execucoes_fiscais  │ MAPEADO  │
│ delta_divida_2_trimestres    │ fiscal.divida_ativa_pgfn_90d…   │ MAPEADO  │
│   ausente                    │   → igual ao total              │ NEUTRO   │
│ flag_divida_fgts             │ fiscal.crf_fgts_regular         │ MAPEADO  │
│   ausente                    │   → True (não afirma irregular) │ NEUTRO   │
│ —                            │ fiscal.todas_certidoes_negativas│ CONSERV. │
│ —                            │ fiscal.cndt_positiva            │ NAO_APUR.│
│ —                            │ fiscal.parcelamento_rompido_12m │ NAO_APUR.│
└───────────────────────────────────────────────────────────────────────────┘
  · `todas_certidoes_negativas` é **sempre False**. É um bônus de +80 que só
    uma certidão efetivamente emitida justifica; a coleta não emite certidão.
    Conceder bônus por silêncio é a forma mais direta do erro fatal.
  · `divida_ativa_ajuizada` é execução fiscal por definição, e alimenta o teto
    `TETO_EXEC_FISCAL` (§8). A **contagem** de execuções não existe na coleta.
  · `flag_divida_previdenciaria` e `n_inscricoes` não têm fator no catálogo §4.

┌── CADASTRAL ← Receita Federal + grafo societário ─────────────────────────┐
│ situacao_cadastral (código)  │ cadastral.situacao_rfb          │ MAPEADO  │
│   base carregada, CNPJ ausente│  → BAIXADA (aciona veto)       │ CONSERV. │
│   base não carregada         │   → ATIVA + dimensão cega       │ NEUTRO   │
│ idade_empresa_meses          │ cadastral.anos_atividade        │ MAPEADO  │
│   ausente                    │   → 0,0 (tempo não comprovado)  │ CONSERV. │
│ capital_social               │ cadastral.capital_social        │ MAPEADO  │
│   ausente                    │   → 0,0                         │ CONSERV. │
│ flag_cnae_agro               │ cadastral.cnae_compativel       │ MAPEADO  │
│   ausente                    │   → False                       │ CONSERV. │
│ n_empresas_do_socio_inaptas  │ (nega bônus qsa_estavel)        │ MAPEADO  │
│ —                            │ cadastral.qsa_estavel_5anos     │ CONSERV. │
│ —                            │ cadastral.alteracao_societaria… │ NAO_APUR.│
│ —                            │ cadastral.saida_socio_majorit…  │ NAO_APUR.│
└───────────────────────────────────────────────────────────────────────────┘
  · **Por que o veto só existe no caso "base carregada, CNPJ ausente".** Um
    veto é afirmação jurídica nominada. Presumi-lo por silêncio da *fonte*
    inverteria o erro: passaríamos a recusar quem talvez seja ótimo. Mas se a
    base de estabelecimentos da RFB está carregada e não tem este CNPJ, isso
    não é silêncio — é resposta, e a resposta é que não há estabelecimento
    ativo. Aí `SituacaoRfb.BAIXADA` descreve o que se sabe, e o rótulo do veto
    ("inapta, suspensa ou baixada na RFB") é verdadeiro.
  · **O grafo societário não tem fator próprio** na §4. Mapear "sócio com cinco
    empresas inaptas" para `alteracao_societaria_180d` inventaria uma alteração
    societária que não houve. Ele entra só onde é honesto: **negando** o bônus
    `qsa_estavel`, e aparecendo no relatório de cobertura.
  · `porte`, `natureza_juridica`, `n_filiais`, `n_socios`, `cnae_principal`
    não têm fator no catálogo §4.

┌── AMBIENTAL ← IBAMA ──────────────────────────────────────────────────────┐
│ flag_embargo_ativo           │ ambiental.embargo_ibama_vigente │ MAPEADO  │
│ n_autos_infracao > 0         │ ambiental.auto_infracao_nao_qu… │ CONSERV. │
│ —                            │ ambiental.situacao_car          │ CONSERV. │
│ —                            │ ambiental.embargo_sobre_imovel… │ NAO_APUR.│
│ —                            │ ambiental.sobreposicao_app…     │ NAO_APUR.│
└───────────────────────────────────────────────────────────────────────────┘
  · `auto_infracao_nao_quitado`: a base do IBAMA não publica quitação. Um auto
    lavrado é tratado como **não quitado até prova em contrário** — é o pior
    plausível sobre um fato que a fonte confirma existir.
  · `situacao_car` = `PENDENTE`. O SICAR não está na coleta e **não existe
    valor de impacto zero** para este campo: `ATIVO_REGULAR` premia (+60 de
    bônus por uma consulta que nunca aconteceu) e `AUSENTE` afirma (−300) que
    o imóvel não tem CAR. `PENDENTE` (−150) é o único que nem premia nem
    inventa: "regularidade não comprovada".
  · `embargo_sobre_imovel_em_garantia` fica **False**: a coleta não sabe quais
    bens a Krill Tech tomou em garantia. O veto `VETO_EMBARGO_GARANTIA` só
    pode ser acionado com o dado interno, e a cobertura diz isso.
  · `valor_multas_ambientais` e `area_embargada_ha` não têm fator na §4.

┌── JURÍDICO ← protestos ───────────────────────────────────────────────────┐
│ n_protestos_ativos           │ juridico.protestos_ativos       │ MAPEADO  │
│ —                            │ juridico.protestos_12m          │ NAO_APUR.│
│ —                            │ juridico.execucoes_titulo_12m…  │ NAO_APUR.│
│ —                            │ juridico.recuperacao_judicial   │ NAO_APUR.│
│ —                            │ juridico.pedido_falencia        │ NAO_APUR.│
│ —                            │ juridico.sem_litigio_36m        │ CONSERV. │
└───────────────────────────────────────────────────────────────────────────┘
  · `protestos_12m` fica **zero de propósito**. A coleta devolve o total de
    protestos ativos e a idade **do mais recente** — não a distribuição por
    data. Contar todos como "em 12 meses" para acionar `protesto_recorrente`
    inventaria datas. O fator `protestos` (45 pts cada, teto 180) já pune.
  · DataJud/DJE ficam fora da coleta: execuções, falência, RJ e trabalhistas
    são todos `NAO_APURADO`. Nenhum veto jurídico é inventado.
  · `sem_litigio_36m` é bônus de +60: **nunca** concedido por ausência.
  · `valor_total_protestado` e `n_cartorios_distintos` não têm fator na §4
    (`credores_protestantes_180d` não é cartório, e a janela de 180 dias não
    está no dado).

┌── AGROCLIMÁTICO ← IBGE/SIDRA + clima ─────────────────────────────────────┐
│ desvio_produtividade_vs_m…   │ agro.quebra_safra_regional_pct  │ MAPEADO  │
│ precipitacao_vs_normal_cl…   │ agro.desvio_precipitacao_pct    │ MAPEADO  │
│ —                            │ agro.risco_zarc                 │ NAO_APUR.│
│ —                            │ agro.produtividade_vs_media_r…  │ NAO_APUR.│
│ —                            │ agro.seguro_agricola_vigente    │ CONSERV. │
│ —                            │ agro.area_irrigada_ha           │ CONSERV. │
│ cultura_referencia           │ agro.culturas                   │ NAO_APUR.│
└───────────────────────────────────────────────────────────────────────────┘
  · **Unidade.** A coleta devolve desvios como *fração* (`-0,15`); o motor lê
    *porcentagem* (`-15`). A conversão ×100 é obrigatória — sem ela uma quebra
    de safra de 15% viraria 0,15% e a dimensão inteira ficaria muda.
  · **Quebra regional ≠ produtividade do cliente.** O IBGE mede o *município*.
    Isso é `quebra_safra_regional_pct` (só o lado da queda: um ano bom não é
    quebra). `produtividade_vs_media_regional_pct` compara o *cliente* com a
    região — dado que só a Krill Tech tem. Usar o mesmo número nos dois
    contaria a mesma perda duas vezes.
  · `culturas` fica **vazio**. `cultura_referencia` é a cultura usada para
    parametrizar as features agrícolas, não uma declaração de que o cliente só
    planta aquilo. Preenchê-la com um item acionaria `monocultura` (−60) sobre
    uma monocultura que ninguém apurou.
  · Irrigação e seguro são **bônus** (+100): nunca por ausência.
  · `anomalia_na_fase_critica`, `dias_secos_consecutivos_max`,
    `precipitacao_acumulada_ciclo` e `area_plantada_municipio_cultura` não têm
    fator na §4. `area_plantada_municipio_cultura` é do município — usá-la como
    `area_total_ha` do cliente seria inventar a área dele.

┌── COMPORTAMENTAL e GARANTIAS ← Krill Tech (não existem em base pública) ──┐
│ —                            │ interno.*                       │ NEUTRO   │
│ valor_operacao_pretendida    │ operacoes[0].saldo_devedor      │ MAPEADO  │
│ —                            │ garantias, limite_aprovado,     │ NEUTRO   │
│                              │ patrimonio, faturamento         │          │
└───────────────────────────────────────────────────────────────────────────┘
  · Exposição, garantias, operações e histórico de pagamento são **dados da
    Krill Tech**. Nunca são inventados. A dimensão comportamental de um
    prospect é **cega por definição** e sai da média ponderada.
  · `valor_operacao_pretendida` é parâmetro do analista — o valor da operação
    que se pretende fazer. Quando informado, a dimensão de garantias deixa de
    ser cega: uma operação proposta **sem garantia formalizada** é 100%
    descoberta, e isso é fato sobre a proposta, não presunção sobre o cliente.
  · Sem esse parâmetro não há exposição, e os fatores que são razão sobre a
    exposição (`divida_ativa`, `capital_vs_exposicao`) não se materializam —
    `razao_segura` devolve 0 para denominador nulo. É por isso que a rota
    aceita o valor pretendido: sem ele, a dívida ativa da PGFN não pontua.

O QUE NÃO FOI MAPEADO, E POR QUÊ
════════════════════════════════
  BCB/MDCR (5 campos) — estatística municipal de crédito rural. Nenhum fator
    da §4 consome contexto municipal de crédito. Reportado em
    `fontesSemFator` para não parecer esquecimento.
  Evidências — `models.fatos.Evidencia` declara `simulada: Literal[True]`.
    Emitir evidência de consulta **real** com esse selo mentiria, e o modelo
    está fora do território deste workstream. A procedência de dado real vive
    no relatório de cobertura, que é o objeto certo para isso.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from coleta.models import Features
from models.cliente import Cliente
from models.enums import (
    DimensaoId,
    OrigemCliente,
    SituacaoCar,
    SituacaoRfb,
    StatusParcela,
    TipoOperacao,
    TipoPessoa,
)
from models.exposicao import Garantia, Operacao, Parcela
from models.fatos import (
    FatosAgro,
    FatosAmbientais,
    FatosCadastrais,
    FatosDoCliente,
    FatosFiscais,
    FatosInternos,
    FatosJuridicos,
)
from scoring.config import ScoringConfig
from scoring.modelo_pd import ResultadoModeloPd, avaliar_modelo_pd

from .cobertura import (
    CampoNaoApurado,
    FonteDaColeta,
    Politica,
    RelatorioDeCobertura,
    config_da_cobertura,
    montar_cobertura,
)

__all__ = [
    "ResultadoDaAdaptacao",
    "adaptar",
    "montar_cliente_do_prospect",
    "FATORES_SEM_FONTE",
    "CAMPOS_SEM_FATO",
    "PERCENTUAL",
    "SITUACAO_RFB_POR_CODIGO",
]

#: A coleta devolve desvios como fração; o motor lê porcentagem.
PERCENTUAL = 100.0

#: Códigos de situação cadastral da RFB (layout dos Dados Abertos do CNPJ).
SITUACAO_RFB_POR_CODIGO: dict[str, SituacaoRfb] = {
    "01": SituacaoRfb.BAIXADA,  # nula — sem efeito cadastral
    "02": SituacaoRfb.ATIVA,
    "03": SituacaoRfb.SUSPENSA,
    "04": SituacaoRfb.INAPTA,
    "08": SituacaoRfb.BAIXADA,
}

#: Fatores do catálogo §4 que **nenhuma** fonte da coleta alimenta.
FATORES_SEM_FONTE: dict[DimensaoId, tuple[tuple[str, str], ...]] = {
    DimensaoId.FISCAL: (
        ("cndt_positiva", "TST/CNDT não está na camada de coleta."),
        ("parcelamento_rompido", "Parcelamentos da PGFN não são publicados por CNPJ."),
    ),
    DimensaoId.CADASTRAL: (
        (
            "alteracao_societaria",
            "A Receita publica o quadro atual, não o histórico datado de alterações.",
        ),
        (
            "saida_socio_majoritario",
            "Idem: sem série histórica do QSA não há como datar a saída.",
        ),
    ),
    DimensaoId.AMBIENTAL: (
        ("car_ausente", "SICAR não está na camada de coleta."),
        ("sobreposicao_app", "Sobreposição com APP/reserva exige o CAR georreferenciado."),
    ),
    DimensaoId.JURIDICO: (
        ("execucoes_titulo", "DataJud/DJE não estão na camada de coleta."),
        ("materialidade_execucao", "Idem."),
        ("aceleracao_judicial", "Idem."),
        ("pluralidade_credores", "Idem."),
        ("pedido_falencia", "Idem."),
        ("rj_distribuida", "Idem."),
        ("trabalhistas", "Idem."),
        (
            "protesto_recorrente",
            "A coleta devolve o total de protestos ativos e a idade do mais "
            "recente, não a distribuição por data.",
        ),
    ),
    DimensaoId.AGROCLIMATICO: (
        ("zarc_risco", "O zoneamento agrícola do MAPA não está na camada de coleta."),
        (
            "produtividade_abaixo",
            "Compara o cliente com a região; a produtividade do cliente é dado interno.",
        ),
        ("monocultura", "`cultura_referencia` é parâmetro da consulta, não o rol de culturas."),
        ("barter_sem_lastro", "Depende das operações e CPRs da Krill Tech."),
    ),
    DimensaoId.COMPORTAMENTAL: (
        ("atraso_medio", "Histórico de pagamento é dado interno da Krill Tech."),
        ("pior_atraso", "Idem."),
        ("covenants_rompidos", "Covenants são cláusulas dos contratos da Krill Tech."),
        ("relacionamento", "Idem."),
    ),
    DimensaoId.GARANTIAS: (
        ("utilizacao_limite", "Limite aprovado é decisão de crédito da Krill Tech."),
        ("vencimento_concentrado", "Depende do calendário de parcelas da operação."),
        ("concentracao_patrimonial", "Patrimônio declarado é dado cadastral da Krill Tech."),
    ),
}

#: Campos de `Features` que não têm fato correspondente no motor (§4).
CAMPOS_SEM_FATO: tuple[str, ...] = (
    "n_inscricoes",
    "flag_divida_previdenciaria",
    "porte",
    "natureza_juridica",
    "cnae_principal",
    "n_filiais",
    "n_socios",
    "n_empresas_do_socio",
    "n_empresas_do_socio_com_divida_ativa",
    "valor_multas_ambientais",
    "area_embargada_ha",
    "volume_credito_rural_municipio",
    "n_contratos_municipio",
    "ticket_medio_municipio",
    "credito_por_hectare_municipio",
    "acionamentos_proagro_municipio",
    "area_plantada_municipio_cultura",
    "produtividade_municipal_cultura",
    "precipitacao_acumulada_ciclo",
    "dias_secos_consecutivos_max",
    "anomalia_na_fase_critica",
    "valor_total_protestado",
    "dias_desde_protesto_mais_recente",
    "n_cartorios_distintos",
)


@dataclass(frozen=True)
class ResultadoDaAdaptacao:
    """Saída do adaptador: os fatos **e** o que se sabe sobre a própria falta.

    `config` é o que leva a política NEUTRO até o motor — pesos renormalizados
    entre as dimensões efetivamente apuradas. Use sempre
    `calcular_risco(r.fatos, config=r.config)`; usar a configuração padrão
    devolveria 1000 para cada dimensão cega, que é o erro fatal.
    """

    fatos: FatosDoCliente
    cobertura: RelatorioDeCobertura
    #: A `Features` de origem — o que `modelo_pd` precisa (Tarefa 1). Os
    #: coeficientes do modelo usam nomes de campo de `Features`, não de
    #: `FatosDoCliente`, e alguns (`n_empresas_do_socio_inaptas`,
    #: `anomalia_na_fase_critica`) não têm fato correspondente no motor.
    features: Features

    @property
    def config(self) -> ScoringConfig:
        return config_da_cobertura(self.cobertura)

    @property
    def analisavel(self) -> bool:
        return self.cobertura.analisavel

    @property
    def modelo_pd(self) -> ResultadoModeloPd:
        """PD12 e a explicação termo a termo do modelo preditivo (Tarefa 1)."""
        return avaliar_modelo_pd(self.features)


# ---------------------------------------------------------------------------
# Tradução por dimensão
# ---------------------------------------------------------------------------


def _fatos_fiscais(features: Features) -> FatosFiscais:
    total = features.divida_ativa_total
    delta = features.delta_divida_2_trimestres
    # Sem o delta não se afirma crescimento: 90 dias atrás valia o mesmo.
    anterior = (total - delta) if (total is not None and delta is not None) else total
    return FatosFiscais(
        divida_ativa_pgfn=total or 0.0,
        divida_ativa_pgfn_90d_atras=max(0.0, anterior or 0.0),
        valor_execucoes_fiscais=features.divida_ativa_ajuizada or 0.0,
        execucoes_fiscais=0,
        # NEUTRO: `None` não afirma FGTS irregular.
        crf_fgts_regular=not bool(features.flag_divida_fgts),
        # NAO_APURADO — TST/CNDT fora da coleta.
        cndt_positiva=False,
        valor_debito_trabalhista=0.0,
        parcelamento_rompido_12m=False,
        # CONSERVADOR — bônus jamais concedido por silêncio.
        todas_certidoes_negativas=False,
    )


def _situacao_rfb(features: Features, receita_respondeu: bool) -> SituacaoRfb:
    """Situação cadastral, com o único CONSERVADOR que pode acionar veto."""
    codigo = (features.situacao_cadastral or "").strip()
    if codigo:
        return SITUACAO_RFB_POR_CODIGO.get(codigo.zfill(2), SituacaoRfb.INAPTA)
    if features.flag_situacao_irregular:
        return SituacaoRfb.INAPTA
    if receita_respondeu:
        # A base foi consultada e não tem estabelecimento para este CNPJ.
        # Isso é resposta, não silêncio.
        return SituacaoRfb.BAIXADA
    # NEUTRO: a fonte não respondeu. Nada é afirmado; a dimensão fica cega e
    # perde o peso. Afirmar inaptidão aqui inverteria o erro fatal.
    return SituacaoRfb.ATIVA


def _fatos_cadastrais(features: Features, receita_respondeu: bool) -> FatosCadastrais:
    meses = features.idade_empresa_meses
    anos = (meses / 12.0) if meses is not None else 0.0
    return FatosCadastrais(
        situacao_rfb=_situacao_rfb(features, receita_respondeu),
        # CONSERVADOR: tempo de atividade não comprovado é tempo zero.
        anos_atividade=anos,
        anos_atividade_comprovada=anos,
        # CONSERVADOR: capital não comprovado é capital zero.
        capital_social=features.capital_social or 0.0,
        # CONSERVADOR: CNAE não confirmado como agro não é CNAE compatível.
        cnae_compativel=bool(features.flag_cnae_agro),
        # NAO_APURADO — sem série histórica do QSA.
        alteracao_societaria_180d=False,
        saida_socio_majoritario_12m=False,
        # CONSERVADOR: o bônus de estabilidade exige 5 anos de QSA que a coleta
        # não tem. O grafo societário poderia negá-lo, nunca concedê-lo — e o
        # catálogo §4 não tem fator que o grafo alimente (ver docstring).
        qsa_estavel_5anos=False,
        possui_livro_caixa_digital=False,
        possui_inscricao_estadual=False,
        tipo_pessoa=TipoPessoa.PJ if len(features.documento or "") == 14 else None,
    )


def _fatos_ambientais(features: Features) -> FatosAmbientais:
    return FatosAmbientais(
        embargo_ibama_vigente=bool(features.flag_embargo_ativo),
        # A coleta não sabe quais bens são garantia da Krill Tech.
        embargo_sobre_imovel_em_garantia=False,
        # CONSERVADOR: o IBAMA não publica quitação; auto lavrado é auto aberto.
        auto_infracao_nao_quitado=bool(features.n_autos_infracao),
        # CONSERVADOR: não há valor de impacto zero para o CAR. Ver docstring.
        situacao_car=SituacaoCar.PENDENTE,
        sobreposicao_app_ou_reserva=False,
    )


def _fatos_juridicos(features: Features) -> FatosJuridicos:
    return FatosJuridicos(
        protestos_ativos=features.n_protestos_ativos or 0,
        # NAO_APURADO: sem a distribuição por data, contar todos como "12m"
        # inventaria datas.
        protestos_12m=0,
        credores_protestantes_180d=0,
        # NAO_APURADO — DataJud/DJE fora da coleta. Nenhum veto inventado.
        execucoes_titulo_12m=0,
        execucoes_titulo_90d=0,
        valor_total_em_execucao=0.0,
        credores_distintos_executando=0,
        acoes_trabalhistas_transitadas=0,
        pedido_falencia=False,
        recuperacao_judicial=None,
        fraude_confirmada=False,
        lista_suja_trabalho_escravo=False,
        # CONSERVADOR — bônus jamais concedido por silêncio.
        sem_litigio_36m=False,
    )


def _fatos_agro(features: Features) -> FatosAgro:
    desvio_produtividade = features.desvio_produtividade_vs_media_5a
    desvio_chuva = features.precipitacao_vs_normal_climatologica
    return FatosAgro(
        # Só o lado da queda é quebra de safra; um ano bom não é.
        quebra_safra_regional_pct=(
            max(0.0, -desvio_produtividade * PERCENTUAL)
            if desvio_produtividade is not None
            else 0.0
        ),
        desvio_precipitacao_pct=(
            desvio_chuva * PERCENTUAL if desvio_chuva is not None else 0.0
        ),
        # NAO_APURADO — ZARC e produtividade do próprio cliente fora da coleta.
        produtividade_vs_media_regional_pct=0.0,
        area_total_ha=0.0,
        # CONSERVADOR — bônus de irrigação/seguro jamais por ausência.
        area_irrigada_ha=0.0,
        seguro_agricola_vigente=False,
        safra_referencia="",
        # NAO_APURADO — `cultura_referencia` é parâmetro da consulta.
        culturas=[],
    )


def _operacoes_pretendidas(
    valor: float | None,
    data_referencia: str,
    prazo_meses: int | None = None,
) -> list[Operacao]:
    """A operação que o analista pretende fazer. **Nunca** inventada.

    `prazo_meses`, quando informado (declaração do analista — Tarefa 3), vira
    uma única parcela a vencer naquele prazo: é o que faz a operação aparecer
    em "próximo vencimento" e em `aVencer90d`, em vez de existir só como saldo
    devedor sem cronograma algum.
    """
    if valor is None or valor <= 0:
        return []
    parcelas: list[Parcela] = []
    vencimento = data_referencia
    if prazo_meses is not None and prazo_meses > 0:
        vencimento = (
            dt.date.fromisoformat(data_referencia) + dt.timedelta(days=30 * prazo_meses)
        ).isoformat()
        parcelas = [
            Parcela(
                id="parcela-operacao-pretendida",
                vencimento=vencimento,
                valor=float(valor),
                status=StatusParcela.A_VENCER,
            )
        ]
    return [
        Operacao(
            id="operacao-pretendida",
            tipo=TipoOperacao.VENDA_A_PRAZO,
            descricao="Operação pretendida em análise de due diligence",
            saldo_devedor=float(valor),
            data_contratacao=data_referencia,
            parcelas=parcelas,
        )
    ]


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------


def adaptar(
    features: Features,
    *,
    cliente_id: str,
    data_referencia: str,
    valor_operacao_pretendida: float | None = None,
    prazo_meses: int | None = None,
    garantias: list[Garantia] | None = None,
) -> ResultadoDaAdaptacao:
    """`Features` → `FatosDoCliente` + relatório de cobertura. Função pura.

    `data_referencia` é obrigatória: o adaptador não lê relógio, nem o de
    `Features.gerado_em` — dois recálculos do mesmo documento têm de dar o
    mesmo número.

    `valor_operacao_pretendida`, `prazo_meses` e `garantias` são sempre
    **declaração do analista** (Tarefa 3) — nunca inferidos da coleta pública.
    Sem eles a operação e as garantias não existem: `operacoes=[]`,
    `garantias=[]`, e a dimensão de garantias segue cega.
    """
    receita_respondeu = (
        FonteDaColeta.RECEITA.value in features.fontes_disponiveis
        or features.situacao_cadastral is not None
    )
    operacoes = _operacoes_pretendidas(
        valor_operacao_pretendida, data_referencia, prazo_meses
    )
    garantias_declaradas = list(garantias) if garantias else []

    fatos = FatosDoCliente(
        cliente_id=cliente_id,
        data_referencia=data_referencia,
        # Cega por natureza: histórico interno da Krill Tech.
        interno=FatosInternos(),
        juridico=_fatos_juridicos(features),
        fiscal=_fatos_fiscais(features),
        agro=_fatos_agro(features),
        cadastral=_fatos_cadastrais(features, receita_respondeu),
        ambiental=_fatos_ambientais(features),
        operacoes=operacoes,
        # `garantias` é declaração do analista (Tarefa 3); limite aprovado,
        # patrimônio e faturamento continuam dados internos da Krill Tech que
        # a coleta pública e a declaração de operação não substituem.
        garantias=garantias_declaradas,
        limite_aprovado=0.0,
        patrimonio_declarado=0.0,
        faturamento_estimado_anual=0.0,
        evidencias=[],
    )

    tem_proposta = bool(operacoes) or bool(garantias_declaradas)
    cobertura = montar_cobertura(
        features,
        fatores_cegos=_fatores_cegos(features, tem_proposta=tem_proposta),
        tem_proposta=tem_proposta,
        campos_sem_fato=list(CAMPOS_SEM_FATO),
    )
    return ResultadoDaAdaptacao(fatos=fatos, cobertura=cobertura, features=features)


def _fatores_cegos(
    features: Features, *, tem_proposta: bool
) -> dict[DimensaoId, list[CampoNaoApurado]]:
    """Fatores do catálogo §4 sem fonte — os fixos e os que dependem da proposta.

    **Os que dependem da proposta.** `divida_ativa` e `capital_vs_exposicao` são
    *razões sobre a exposição*, e `razao_segura` devolve 0 para denominador
    nulo. Sem o valor da operação pretendida, uma dívida ativa de R$ 2,4 milhões
    **não pontua** — o fator simplesmente não se materializa. Isso não pode
    passar em silêncio: é o caso em que o sistema pareceria estar dizendo "sem
    problema fiscal" quando está dizendo "não tenho contra o que comparar".
    """
    cegos = {
        dimensao: [
            CampoNaoApurado(
                fator=fator,
                dimensao=dimensao,
                politica=Politica.NAO_APURADO,
                motivo=motivo,
            )
            for fator, motivo in entradas
        ]
        for dimensao, entradas in FATORES_SEM_FONTE.items()
    }
    if tem_proposta:
        return cegos

    sem_denominador = (
        (
            DimensaoId.FISCAL,
            "divida_ativa",
            "A materialidade da dívida ativa é razão sobre a exposição. Sem o "
            "valor da operação pretendida não há denominador, e o fator não "
            "pontua — informe `valorOperacaoPretendida` para que ele conte.",
        ),
        (
            DimensaoId.CADASTRAL,
            "capital_vs_exposicao",
            "Compara capital social com exposição. Sem o valor da operação "
            "pretendida não há o que comparar.",
        ),
    )
    for dimensao, fator, motivo in sem_denominador:
        if fator == "divida_ativa" and not features.divida_ativa_total:
            continue
        cegos.setdefault(dimensao, []).append(
            CampoNaoApurado(
                fator=fator,
                dimensao=dimensao,
                politica=Politica.NAO_APURADO,
                motivo=motivo,
            )
        )
    return cegos


def montar_cliente_do_prospect(
    features: Features, *, cliente_id: str, data_referencia: str
) -> Cliente:
    """`Cliente` mínimo para a tela de due diligence de um documento real.

    Nenhum campo é inventado: o que a coleta não devolveu vira "Não apurado",
    que é texto de tela, não fato de risco. `municipio` recebe o **código
    IBGE** porque é o que a coleta devolve — ela não resolve o nome.
    """
    codigo_ibge = features.municipio_ibge
    return Cliente(
        id=cliente_id,
        razao_social=features.razao_social or "Razão social não apurada",
        documento=features.documento,
        tipo_pessoa=TipoPessoa.PJ if len(features.documento or "") == 14 else TipoPessoa.PF,
        municipio=f"Município IBGE {codigo_ibge}" if codigo_ibge else "Não apurado",
        uf=features.uf or "--",
        atividade="Atividade não apurada",
        cnae_principal=features.cnae_principal or "",
        culturas=[],
        inicio_relacionamento=data_referencia,
        origem=OrigemCliente.PROSPECT,
    )
