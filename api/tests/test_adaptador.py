"""Adaptador `Features` → `FatosDoCliente` + cobertura.

Nenhum teste toca rede ou warehouse: todo `Features` é montado à mão.

O que a suíte protege, em uma frase: **dado ausente nunca vira dado favorável**.
"""

from __future__ import annotations

import pytest
from adaptadores import adaptar, montar_cliente_do_prospect, pesos_renormalizados
from adaptadores.cobertura import Politica, StatusDimensao
from adaptadores.features_para_fatos import PERCENTUAL
from coleta.models import Features
from models.enums import DimensaoId, OrigemCliente, Rating, SituacaoCar, SituacaoRfb
from scoring import calcular_risco
from scoring.audit import fechou
from scoring.config import CONFIG_PADRAO

DATA_REF = "2026-09-12"
CNPJ = "12345678000190"
TOLERANCIA_PESO = 1e-9


def _adaptar(features: Features, **kwargs):
    return adaptar(features, cliente_id="prospect-teste", data_referencia=DATA_REF, **kwargs)


def _avaliar(resultado):
    return calcular_risco(
        resultado.fatos, config=resultado.config, data_referencia=DATA_REF
    )


def features_vazio() -> Features:
    """O pior caso: nenhuma fonte respondeu nada."""
    return Features(documento=CNPJ)


def features_completo() -> Features:
    """Todas as fontes carregadas, empresa saudável."""
    return Features(
        documento=CNPJ,
        cnpj_basico=CNPJ[:8],
        razao_social="Agro Exemplo Ltda",
        uf="MT",
        municipio_ibge="5107602",
        cultura_referencia="soja",
        fontes_disponiveis=[
            "pgfn",
            "receita",
            "grafo_societario",
            "ibama_autos",
            "ibama_embargos",
            "ibge_producao",
            "clima",
        ],
        divida_ativa_total=0.0,
        divida_ativa_ajuizada=0.0,
        n_inscricoes=0,
        delta_divida_2_trimestres=0.0,
        flag_divida_previdenciaria=False,
        flag_divida_fgts=False,
        idade_empresa_meses=240,
        capital_social=5_000_000.0,
        situacao_cadastral="02",
        flag_situacao_irregular=False,
        cnae_principal="0115600",
        flag_cnae_agro=True,
        n_socios=3,
        n_empresas_do_socio=4,
        n_empresas_do_socio_com_divida_ativa=0,
        n_empresas_do_socio_inaptas=0,
        n_autos_infracao=0,
        valor_multas_ambientais=0.0,
        flag_embargo_ativo=False,
        produtividade_municipal_cultura=3500.0,
        desvio_produtividade_vs_media_5a=0.05,
        area_plantada_municipio_cultura=120_000.0,
        precipitacao_acumulada_ciclo=880.0,
        precipitacao_vs_normal_climatologica=-0.02,
        dias_secos_consecutivos_max=9,
        n_protestos_ativos=0,
        valor_total_protestado=0.0,
        n_cartorios_distintos=0,
    )


# ---------------------------------------------------------------------------
# A regra que sustenta o produto
# ---------------------------------------------------------------------------


def test_features_vazio_nunca_produz_rating_a():
    resultado = _adaptar(features_vazio())
    avaliacao = _avaliar(resultado)
    assert avaliacao.rating_final is not Rating.A
    assert avaliacao.rating_calculado is not Rating.A


def test_features_vazio_nao_e_analisavel():
    """Cegueira total não é nota baixa: é ausência de nota."""
    cobertura = _adaptar(features_vazio()).cobertura
    assert cobertura.analisavel is False
    assert cobertura.dimensoes_apuradas == []
    assert len(cobertura.dimensoes_cegas) == len(CONFIG_PADRAO.pesos_dimensoes)
    assert cobertura.cobertura_ponderada == 0.0


def test_features_vazio_nao_concede_nenhum_bonus():
    """Nenhum fator de proteção pode nascer de silêncio."""
    fatos = _adaptar(features_vazio()).fatos
    assert fatos.fiscal.todas_certidoes_negativas is False
    assert fatos.juridico.sem_litigio_36m is False
    assert fatos.cadastral.qsa_estavel_5anos is False
    assert fatos.agro.seguro_agricola_vigente is False
    assert fatos.agro.area_irrigada_ha == 0.0
    assert fatos.interno.sem_atraso_relevante_24m is False


def test_features_vazio_nao_inventa_veto():
    """Silêncio da fonte não vira afirmação jurídica."""
    avaliacao = _avaliar(_adaptar(features_vazio()))
    assert avaliacao.vetos_ativos == []


def test_features_vazio_nao_inventa_exposicao():
    fatos = _adaptar(features_vazio()).fatos
    assert fatos.operacoes == []
    assert fatos.garantias == []
    assert fatos.limite_aprovado == 0.0
    assert fatos.patrimonio_declarado == 0.0
    assert fatos.faturamento_estimado_anual == 0.0


# ---------------------------------------------------------------------------
# Política NEUTRO — renormalização de peso
# ---------------------------------------------------------------------------


def test_dimensoes_sem_fonte_publica_sao_sempre_cegas():
    cobertura = _adaptar(features_completo()).cobertura
    for dimensao in (DimensaoId.COMPORTAMENTAL, DimensaoId.GARANTIAS):
        assert cobertura.de(dimensao).status is StatusDimensao.CEGA
        assert cobertura.de(dimensao).politica is Politica.NEUTRO
        assert cobertura.de(dimensao).peso_aplicado == 0.0


def test_peso_de_dimensao_cega_e_redistribuido_e_a_soma_continua_um():
    cobertura = _adaptar(features_completo()).cobertura
    pesos = pesos_renormalizados(cobertura)
    assert sum(pesos.values()) == pytest.approx(1.0, abs=TOLERANCIA_PESO)
    assert pesos[DimensaoId.COMPORTAMENTAL] == 0.0
    assert pesos[DimensaoId.GARANTIAS] == 0.0
    # Apuradas: jurídico, fiscal, agro, cadastral, ambiental = 0,68 do canônico.
    assert pesos[DimensaoId.FISCAL] == pytest.approx(0.14 / 0.68)
    assert pesos[DimensaoId.JURIDICO] > pesos[DimensaoId.FISCAL]  # hierarquia da §2


def test_renormalizacao_preserva_o_fechamento_i2():
    avaliacao = _avaliar(_adaptar(features_completo()))
    assert fechou(avaliacao.auditoria)


def test_config_padrao_nunca_e_mutada():
    antes = dict(CONFIG_PADRAO.pesos_dimensoes)
    _adaptar(features_completo()).config
    assert CONFIG_PADRAO.pesos_dimensoes == antes


def test_dimensao_cega_nao_entrega_score_de_graca():
    """A dimensão comportamental de um prospect vale 1000 no motor — sem fatores,
    `1000 − Σ penalidades` é 1000. São 22% do score entregues por não ter sido
    olhada. Renormalizado, esse peso vai para quem foi olhado, e a nota cai."""
    features = features_completo()
    features.divida_ativa_total = 4_000_000.0
    features.n_protestos_ativos = 4
    resultado = _adaptar(features, valor_operacao_pretendida=2_000_000.0)
    com_renormalizacao = _avaliar(resultado)
    sem_renormalizacao = calcular_risco(resultado.fatos, data_referencia=DATA_REF)
    assert sem_renormalizacao.score_calculado > com_renormalizacao.score_calculado
    assert resultado.cobertura.de(DimensaoId.COMPORTAMENTAL).peso_aplicado == 0.0


# ---------------------------------------------------------------------------
# Política CONSERVADOR
# ---------------------------------------------------------------------------


def test_receita_carregada_sem_o_cnpj_e_resposta_e_aciona_veto():
    """Base consultada e sem estabelecimento: isso é resposta, não silêncio."""
    features = Features(documento=CNPJ, fontes_disponiveis=["receita"])
    resultado = _adaptar(features)
    assert resultado.fatos.cadastral.situacao_rfb is SituacaoRfb.BAIXADA
    avaliacao = _avaliar(resultado)
    assert [veto.id for veto in avaliacao.vetos_ativos] == ["VETO_CADASTRO_INAPTO"]
    assert avaliacao.rating_final is Rating.D


def test_receita_ausente_nao_afirma_inaptidao():
    fatos = _adaptar(features_vazio()).fatos
    assert fatos.cadastral.situacao_rfb is SituacaoRfb.ATIVA


def test_situacao_cadastral_irregular_e_mapeada_fielmente():
    for codigo, esperado in (
        ("02", SituacaoRfb.ATIVA),
        ("03", SituacaoRfb.SUSPENSA),
        ("04", SituacaoRfb.INAPTA),
        ("08", SituacaoRfb.BAIXADA),
    ):
        features = Features(
            documento=CNPJ, fontes_disponiveis=["receita"], situacao_cadastral=codigo
        )
        assert _adaptar(features).fatos.cadastral.situacao_rfb is esperado


def test_idade_e_capital_ausentes_viram_zero_e_nao_media():
    fatos = _adaptar(Features(documento=CNPJ, fontes_disponiveis=["receita"])).fatos
    assert fatos.cadastral.anos_atividade == 0.0
    assert fatos.cadastral.capital_social == 0.0
    assert fatos.cadastral.cnae_compativel is False


def test_car_nao_consultado_nem_premia_nem_afirma_ausencia():
    fatos = _adaptar(features_completo()).fatos
    assert fatos.ambiental.situacao_car is SituacaoCar.PENDENTE


def test_auto_de_infracao_e_tratado_como_nao_quitado():
    features = features_completo()
    features.n_autos_infracao = 3
    fatos = _adaptar(features).fatos
    assert fatos.ambiental.auto_infracao_nao_quitado is True


# ---------------------------------------------------------------------------
# Política NAO_APURADO
# ---------------------------------------------------------------------------


def test_fatores_sem_fonte_aparecem_na_cobertura_com_impacto_zero():
    resultado = _adaptar(features_completo())
    fiscal = resultado.cobertura.de(DimensaoId.FISCAL)
    assert fiscal.status is StatusDimensao.PARCIAL
    cegos = {campo.fator for campo in fiscal.fatores_cegos}
    assert {"cndt_positiva", "parcelamento_rompido"} <= cegos
    assert all(c.politica is Politica.NAO_APURADO for c in fiscal.fatores_cegos)
    # Impacto zero: os fatos correspondentes são os neutros do motor.
    assert resultado.fatos.fiscal.cndt_positiva is False
    assert resultado.fatos.fiscal.parcelamento_rompido_12m is False


def test_zarc_e_monocultura_ficam_cegos_e_nao_inventam_cultura():
    resultado = _adaptar(features_completo())
    assert resultado.fatos.agro.culturas == []
    cegos = {c.fator for c in resultado.cobertura.de(DimensaoId.AGROCLIMATICO).fatores_cegos}
    assert {"zarc_risco", "monocultura", "produtividade_abaixo"} <= cegos


def test_protestos_ativos_mapeiam_mas_recorrencia_nao():
    features = features_completo()
    features.n_protestos_ativos = 5
    features.dias_desde_protesto_mais_recente = 30
    fatos = _adaptar(features).fatos
    assert fatos.juridico.protestos_ativos == 5
    assert fatos.juridico.protestos_12m == 0  # datas não são inventadas
    avaliacao = _avaliar(_adaptar(features))
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    assert "protestos" in ids
    assert "protesto_recorrente" not in ids


def test_execucoes_e_rj_nunca_sao_inventadas():
    fatos = _adaptar(features_completo()).fatos
    assert fatos.juridico.execucoes_titulo_12m == 0
    assert fatos.juridico.recuperacao_judicial is None
    assert fatos.juridico.pedido_falencia is False
    assert fatos.juridico.lista_suja_trabalho_escravo is False


# ---------------------------------------------------------------------------
# Mapeamento fiel — unidades e sentido
# ---------------------------------------------------------------------------


def test_pgfn_mapeia_divida_e_crescimento():
    features = features_completo()
    features.divida_ativa_total = 1_200_000.0
    features.divida_ativa_ajuizada = 800_000.0
    features.delta_divida_2_trimestres = 300_000.0
    fatos = _adaptar(features).fatos
    assert fatos.fiscal.divida_ativa_pgfn == 1_200_000.0
    assert fatos.fiscal.divida_ativa_pgfn_90d_atras == 900_000.0
    assert fatos.fiscal.valor_execucoes_fiscais == 800_000.0


def test_delta_ausente_nao_afirma_crescimento():
    features = features_completo()
    features.divida_ativa_total = 500_000.0
    features.delta_divida_2_trimestres = None
    fatos = _adaptar(features).fatos
    assert fatos.fiscal.divida_ativa_pgfn_90d_atras == 500_000.0
    avaliacao = _avaliar(_adaptar(features))
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    assert "divida_ativa_crescente" not in ids


def test_fgts_em_divida_ativa_torna_crf_irregular():
    features = features_completo()
    features.flag_divida_fgts = True
    assert _adaptar(features).fatos.fiscal.crf_fgts_regular is False
    features.flag_divida_fgts = None
    assert _adaptar(features).fatos.fiscal.crf_fgts_regular is True


def test_desvios_da_coleta_sao_convertidos_de_fracao_para_percentual():
    features = features_completo()
    features.desvio_produtividade_vs_media_5a = -0.18
    features.precipitacao_vs_normal_climatologica = -0.25
    fatos = _adaptar(features).fatos
    assert fatos.agro.quebra_safra_regional_pct == pytest.approx(18.0)
    assert fatos.agro.desvio_precipitacao_pct == pytest.approx(-25.0)
    assert PERCENTUAL == 100.0


def test_ano_bom_nao_vira_quebra_de_safra():
    features = features_completo()
    features.desvio_produtividade_vs_media_5a = 0.22
    fatos = _adaptar(features).fatos
    assert fatos.agro.quebra_safra_regional_pct == 0.0
    # E não vira bônus: o motor não tem fator de proteção por safra boa.
    assert fatos.agro.produtividade_vs_media_regional_pct == 0.0


def test_quebra_de_safra_real_derruba_o_score():
    boa = _avaliar(_adaptar(features_completo()))
    ruim_features = features_completo()
    ruim_features.desvio_produtividade_vs_media_5a = -0.30
    ruim_features.precipitacao_vs_normal_climatologica = -0.40
    ruim = _avaliar(_adaptar(ruim_features))
    assert ruim.score_calculado < boa.score_calculado


def test_embargo_do_ibama_penaliza_mas_nao_veta_sem_garantia_conhecida():
    features = features_completo()
    features.flag_embargo_ativo = True
    resultado = _adaptar(features)
    assert resultado.fatos.ambiental.embargo_ibama_vigente is True
    assert resultado.fatos.ambiental.embargo_sobre_imovel_em_garantia is False
    avaliacao = _avaliar(resultado)
    assert "VETO_EMBARGO_GARANTIA" not in {v.id for v in avaliacao.vetos_ativos}
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    assert "embargo_ibama" in ids


# ---------------------------------------------------------------------------
# Exposição: só por parâmetro
# ---------------------------------------------------------------------------


def test_valor_pretendido_cria_a_operacao_e_abre_a_dimensao_de_garantias():
    resultado = _adaptar(features_completo(), valor_operacao_pretendida=2_000_000.0)
    assert len(resultado.fatos.operacoes) == 1
    assert resultado.fatos.operacoes[0].saldo_devedor == 2_000_000.0
    garantias = resultado.cobertura.de(DimensaoId.GARANTIAS)
    assert garantias.status is not StatusDimensao.CEGA
    assert garantias.peso_aplicado > 0.0


def test_operacao_sem_garantia_e_cem_por_cento_descoberta():
    avaliacao = _avaliar(
        _adaptar(features_completo(), valor_operacao_pretendida=2_000_000.0)
    )
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    assert {"descoberto_extraconcursal", "descoberto_total"} <= ids


def test_sem_valor_pretendido_nao_ha_exposicao_nem_fator_de_divida():
    features = features_completo()
    features.divida_ativa_total = 5_000_000.0
    resultado = _adaptar(features)
    avaliacao = _avaliar(resultado)
    assert avaliacao.exposicao.exposicao_total == 0.0
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    # `divida_ativa` é razão sobre a exposição: sem exposição não se materializa.
    assert "divida_ativa" not in ids


def test_com_valor_pretendido_a_divida_ativa_pontua():
    features = features_completo()
    features.divida_ativa_total = 5_000_000.0
    avaliacao = _avaliar(_adaptar(features, valor_operacao_pretendida=1_000_000.0))
    ids = {f.id for d in avaliacao.dimensoes for f in d.fatores}
    assert "divida_ativa" in ids


def test_valor_pretendido_nulo_ou_negativo_nao_cria_operacao():
    for valor in (None, 0.0, -1.0):
        assert _adaptar(features_completo(), valor_operacao_pretendida=valor).fatos.operacoes == []


# ---------------------------------------------------------------------------
# Garantias e prazo declarados pelo analista (Tarefa 3)
# ---------------------------------------------------------------------------


def test_garantias_declaradas_viram_fato_e_abrem_a_dimensao():
    from models.enums import TipoGarantia
    from models.exposicao import Garantia

    garantia = Garantia(id="g1", tipo=TipoGarantia.CPR_FINANCEIRA, valor_declarado=100_000.0)
    resultado = _adaptar(features_completo(), garantias=[garantia])
    assert resultado.fatos.garantias == [garantia]
    assert resultado.cobertura.de(DimensaoId.GARANTIAS).status is not StatusDimensao.CEGA


def test_sem_garantia_nem_valor_pretendido_fatos_ficam_vazios():
    resultado = _adaptar(features_completo())
    assert resultado.fatos.garantias == []
    assert resultado.fatos.operacoes == []


def test_prazo_meses_gera_parcela_a_vencer_no_prazo():
    resultado = _adaptar(
        features_completo(), valor_operacao_pretendida=1_000_000.0, prazo_meses=6
    )
    (operacao,) = resultado.fatos.operacoes
    assert len(operacao.parcelas) == 1
    assert operacao.parcelas[0].vencimento > DATA_REF


def test_sem_prazo_meses_operacao_nao_tem_parcela():
    resultado = _adaptar(features_completo(), valor_operacao_pretendida=1_000_000.0)
    (operacao,) = resultado.fatos.operacoes
    assert operacao.parcelas == []


def test_resultado_da_adaptacao_expoe_a_features_de_origem():
    features = features_completo()
    resultado = _adaptar(features)
    assert resultado.features is features
    assert resultado.modelo_pd.pd12 >= 0.0


# ---------------------------------------------------------------------------
# Pureza e determinismo
# ---------------------------------------------------------------------------


def test_adaptador_e_deterministico():
    um = _adaptar(features_completo())
    outro = _adaptar(features_completo())
    assert um.fatos.model_dump() == outro.fatos.model_dump()
    assert um.cobertura.model_dump() == outro.cobertura.model_dump()


def test_adaptador_nao_le_relogio():
    """`gerado_em` muda a cada coleta e não pode mexer no resultado."""
    import datetime as dt

    um = features_completo()
    outro = features_completo()
    outro.gerado_em = dt.datetime(1999, 1, 1)
    assert _adaptar(um).fatos.model_dump() == _adaptar(outro).fatos.model_dump()


def test_data_de_referencia_vem_do_parametro():
    resultado = adaptar(
        features_completo(), cliente_id="x", data_referencia="2020-01-31"
    )
    assert resultado.fatos.data_referencia == "2020-01-31"


# ---------------------------------------------------------------------------
# Cliente do prospect
# ---------------------------------------------------------------------------


def test_cliente_do_prospect_nao_inventa_campo():
    cliente = montar_cliente_do_prospect(
        features_vazio(), cliente_id="p1", data_referencia=DATA_REF
    )
    assert cliente.origem is OrigemCliente.PROSPECT
    assert cliente.razao_social == "Razão social não apurada"
    assert cliente.municipio == "Não apurado"
    assert cliente.culturas == []


def test_cliente_do_prospect_usa_o_que_a_coleta_devolveu():
    cliente = montar_cliente_do_prospect(
        features_completo(), cliente_id="p1", data_referencia=DATA_REF
    )
    assert cliente.razao_social == "Agro Exemplo Ltda"
    assert cliente.uf == "MT"
    assert "5107602" in cliente.municipio


# ---------------------------------------------------------------------------
# O relatório de cobertura bate
# ---------------------------------------------------------------------------


def test_cobertura_nomeia_a_fonte_de_cada_dimensao():
    cobertura = _adaptar(features_completo()).cobertura
    assert "PGFN" in cobertura.de(DimensaoId.FISCAL).fontes_apuradas[0]
    assert "IBAMA" in cobertura.de(DimensaoId.AMBIENTAL).fontes_apuradas[0]
    assert any("IBGE" in f for f in cobertura.de(DimensaoId.AGROCLIMATICO).fontes_apuradas)
    assert "Receita" in cobertura.de(DimensaoId.CADASTRAL).fontes_apuradas[0]


def test_cobertura_ponderada_bate_com_os_pesos_canonicos():
    cobertura = _adaptar(features_completo()).cobertura
    esperado = sum(
        CONFIG_PADRAO.pesos_dimensoes[d] for d in cobertura.dimensoes_apuradas
    )
    assert cobertura.cobertura_ponderada == pytest.approx(esperado)


def test_fonte_sem_fator_e_reportada_em_vez_de_sumir():
    features = features_completo()
    features.volume_credito_rural_municipio = 1.2e9
    cobertura = _adaptar(features).cobertura
    assert any("BCB" in fonte for fonte in cobertura.fontes_sem_fator)


def test_campos_sem_fato_sao_declarados():
    cobertura = _adaptar(features_completo()).cobertura
    assert "acionamentos_proagro_municipio" in cobertura.campos_sem_fato
    assert "area_plantada_municipio_cultura" in cobertura.campos_sem_fato


def test_cobertura_serializa_em_camel_case():
    payload = _adaptar(features_completo()).cobertura.model_dump(by_alias=True, mode="json")
    assert "coberturaPonderada" in payload
    assert "pesoAplicado" in payload["dimensoes"][0]
    assert "fontesApuradas" in payload["dimensoes"][0]
