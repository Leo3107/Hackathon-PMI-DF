"""Critérios de aceitação do dataset simulado — `specs/06-dados-simulados.md` §12 e §14.

Três blocos:

1. **Estrutura e integridade** — contagens, unicidade, validação pydantic de todo
   registro e conferência dos dígitos verificadores dos 22 documentos.
2. **Calibração** — o score que o motor calcula para cada cliente bate com a
   tabela consolidada da §5, com as duas invariantes de fechamento (I2 e I6),
   os oito gatilhos de veto, a invariante I5 e a narrativa 712 → 604.
3. **Varredura de contradições V1 a V40** — uma função por regra, executada
   sobre os 22 registros correntes (18 clientes de carteira + 4 prospects).

Se um destes testes falhar depois de alguém editar um fato, a correção é refazer
a calibração da §7 daquele cliente — **nunca** alterar `api/scoring/config.py`.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

from models.enums import (
    FonteId,
    NaturezaGarantia,
    Severidade,
    SituacaoCar,
    SituacaoRfb,
    StatusParcela,
    TipoGarantia,
    TipoPessoa,
)
from models.fatos import FatosDoCliente
from scoring import calcular_risco, comparar_avaliacoes

import data
from data._base import DATAS_SNAPSHOT, SEM_RECALCULO, normalizar_documento
from data.auditoria import SNAPSHOT_DO_REGISTRO

# ---------------------------------------------------------------------------
# Fixtures de conveniência (o dataset é imutável: basta ler)
# ---------------------------------------------------------------------------

CLIENTES = data.CLIENTES
PROSPECTS = data.PROSPECTS
REGISTROS = data.TODOS_OS_REGISTROS
FATOS = data.FATOS_DE_TODOS_OS_REGISTROS
SNAPSHOTS = data.SNAPSHOTS_POR_CLIENTE

TOLERANCIA_SCORE = 0.1
TOLERANCIA_FECHAMENTO = 0.5

DIRETORIO_DATA = Path(data.__file__).resolve().parent


def _fatos(cliente_id: str) -> FatosDoCliente:
    return FATOS[cliente_id]


def _avaliacao(cliente_id: str):
    return calcular_risco(_fatos(cliente_id))


#: §5 — `id: (score, ratingCalculado, ratingFinal)`.
CALIBRACAO: dict[str, tuple[float, str, str]] = {
    "santa-ines": (917.9, "A", "A"),
    "vale-do-piquiri": (745.2, "B", "B"),
    "cerrado-norte": (604.0, "B", "B"),
    "rio-formoso": (253.6, "D", "D"),
    "barra-do-ipe": (571.6, "C", "D"),
    "alto-paranaiba": (766.2, "A", "A"),
    "serra-do-urucui": (592.3, "C", "C"),
    "sao-bento-bioenergia": (865.9, "A", "A"),
    "chapadao-algodoeira": (724.9, "B", "B"),
    "ponta-verde": (325.5, "D", "D"),
    "joao-camargo": (498.2, "C", "C"),
    "tres-barras": (735.3, "B", "B"),
    "ipanema-graos": (680.0, "B", "B"),
    "frutivale": (942.8, "A", "A"),
    "santa-vitoria-arroz": (723.4, "B", "C"),
    "dois-irmaos": (696.9, "B", "B"),
    "maria-nogueira": (924.7, "A", "A"),
    "coop-vale-do-ivai": (718.5, "B", "C"),
    "nova-alianca": (976.9, "A", "A"),
    "ribeirao-claro": (650.5, "B", "B"),
    "beira-rio": (595.1, "C", "D"),
    "santa-helena-norte": (748.5, "B", "D"),
}

#: §4 C1 — `id: (custeio total em R$, fração Krill)`. Base da regra V32.
RAZAO_POR_HECTARE: dict[str, tuple[float, float]] = {
    "santa-ines": (63_650_000, 0.220),
    "vale-do-piquiri": (17_380_000, 0.495),
    "cerrado-norte": (65_240_000, 0.343),
    "rio-formoso": (46_600_000, 0.253),
    "barra-do-ipe": (27_040_000, 0.340),
    "alto-paranaiba": (21_240_000, 0.301),
    "serra-do-urucui": (30_400_000, 0.414),
    "sao-bento-bioenergia": (126_000_000, 0.210),
    "chapadao-algodoeira": (147_880_000, 0.277),
    "ponta-verde": (41_500_000, 0.441),
    "joao-camargo": (7_060_000, 0.552),
    "tres-barras": (14_650_000, 0.485),
    "ipanema-graos": (33_320_000, 0.474),
    "frutivale": (9_760_000, 0.574),
    "santa-vitoria-arroz": (14_595_000, 0.466),
    "dois-irmaos": (24_960_000, 0.417),
    "maria-nogueira": (12_790_000, 0.368),
    "coop-vale-do-ivai": (46_380_000, 0.414),
    "nova-alianca": (29_120_000, 0.206),
    "ribeirao-claro": (8_320_000, 0.541),
    "beira-rio": (12_480_000, 0.401),
    "santa-helena-norte": (15_600_000, 0.449),
}

#: §12 V31 — culturas admissíveis por município, com a justificativa agronômica.
MATRIZ_AGRONOMICA: dict[str, set[str]] = {
    "Sorriso/MT": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Primavera do Leste/MT": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Rondonópolis/MT": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Querência/MT": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Sinop/MT": {"Soja", "Milho", "Milho safrinha", "Algodão", "Feijão"},
    "Confresa/MT": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Balsas/MA": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Uruçuí/PI": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Barreiras/BA": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Luís Eduardo Magalhães/BA": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Formosa do Rio Preto/BA": {"Soja", "Milho", "Milho safrinha", "Algodão"},
    "Campo Mourão/PR": {"Soja", "Milho", "Milho safrinha", "Trigo"},
    "Cascavel/PR": {"Soja", "Milho", "Milho safrinha", "Trigo"},
    "Sertãozinho/SP": {"Cana-de-açúcar"},
    "Patrocínio/MG": {"Café arábica"},
    "Uruguaiana/RS": {"Arroz irrigado", "Soja"},
    "Não-Me-Toque/RS": {"Soja", "Trigo", "Milho", "Milho safrinha"},
    "Rio Verde/GO": {"Milho", "Milho safrinha", "Soja"},
    "Jataí/GO": {"Milho", "Milho safrinha", "Soja"},
    "Cristalina/GO": {"Milho", "Milho safrinha", "Soja", "Feijão"},
    "Petrolina/PE": {"Manga", "Uva de mesa"},
    "Paragominas/PA": {"Soja", "Milho", "Milho safrinha"},
}

#: Catálogo de ids de fator da spec 02 §4 — base da regra V36.
CATALOGO_DE_FATORES: frozenset[str] = frozenset(
    {
        "atraso_medio",
        "pior_atraso",
        "pontualidade",
        "renegociacoes",
        "inadimplencia_tecnica",
        "tendencia_atraso",
        "relacionamento",
        "historico_limpo",
        "execucoes_titulo",
        "materialidade_execucao",
        "aceleracao_judicial",
        "protestos",
        "protesto_recorrente",
        "pedido_falencia",
        "rj_distribuida",
        "trabalhistas",
        "pluralidade_credores",
        "sem_litigio",
        "divida_ativa",
        "divida_ativa_crescente",
        "cndt_positiva",
        "fgts_irregular",
        "parcelamento_rompido",
        "certidoes_negativas",
        "zarc_risco",
        "quebra_safra_regional",
        "desvio_precipitacao",
        "monocultura",
        "produtividade_abaixo",
        "barter_sem_lastro",
        "irrigacao_ou_seguro",
        "diversificacao",
        "situacao_cadastral",
        "tempo_atividade",
        "alteracao_societaria",
        "saida_socio_majoritario",
        "capital_vs_exposicao",
        "cnae_incompativel",
        "qsa_estavel",
        "embargo_ibama",
        "auto_infracao",
        "car_ausente",
        "car_irregular",
        "sobreposicao_app",
        "car_regular",
        "descoberto_extraconcursal",
        "descoberto_total",
        "utilizacao_limite",
        "concentracao_patrimonial",
        "vencimento_concentrado",
        "sobrecolateral",
    }
)


# ---------------------------------------------------------------------------
# Dígito verificador de CPF e CNPJ
# ---------------------------------------------------------------------------


def _digitos(documento: str) -> str:
    return normalizar_documento(documento)


def cpf_valido(documento: str) -> bool:
    """Módulo 11 clássico, com rejeição de sequência repetida."""
    numeros = _digitos(documento)
    if len(numeros) != 11 or len(set(numeros)) == 1:
        return False
    for corte in (9, 10):
        peso_inicial = corte + 1
        soma = sum(
            int(numeros[i]) * (peso_inicial - i) for i in range(corte)
        )
        resto = (soma * 10) % 11
        digito = 0 if resto == 10 else resto
        if digito != int(numeros[corte]):
            return False
    return True


def cnpj_valido(documento: str) -> bool:
    numeros = _digitos(documento)
    if len(numeros) != 14 or len(set(numeros)) == 1:
        return False
    pesos_primeiro = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    pesos_segundo = (6, *pesos_primeiro)
    for corte, pesos in ((12, pesos_primeiro), (13, pesos_segundo)):
        soma = sum(int(numeros[i]) * pesos[i] for i in range(corte))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(numeros[corte]):
            return False
    return True


def documento_valido(cliente) -> bool:
    if cliente.tipo_pessoa is TipoPessoa.PF:
        return cpf_valido(cliente.documento)
    return cnpj_valido(cliente.documento)


# ---------------------------------------------------------------------------
# 1 · Estrutura e integridade
# ---------------------------------------------------------------------------


def test_18_clientes_e_4_prospects():
    assert len(CLIENTES) == 18
    assert len(PROSPECTS) == 4
    ids = [cliente.id for cliente in REGISTROS]
    assert len(set(ids)) == 22, "id de cliente repetido"
    assert set(FATOS) == set(ids)


def test_todo_registro_valida_no_pydantic():
    """Round-trip completo: modelo → JSON do contrato → modelo."""
    for cliente in REGISTROS:
        assert type(cliente).model_validate(cliente.json_do_contrato()) == cliente
        fatos = FATOS[cliente.id]
        assert FatosDoCliente.model_validate(fatos.json_do_contrato()).cliente_id == cliente.id
    for snapshots in SNAPSHOTS.values():
        for snapshot in snapshots:
            assert type(snapshot).model_validate(snapshot.json_do_contrato()).data == snapshot.data
    for evento in data.EVENTOS:
        assert type(evento).model_validate(evento.json_do_contrato()) == evento
    for alerta in data.ALERTAS:
        assert type(alerta).model_validate(alerta.json_do_contrato()) == alerta
    for registro in data.REGISTROS_AUDITORIA:
        assert type(registro).model_validate(registro.json_do_contrato()) == registro


def test_documentos_validos():
    for cliente in REGISTROS:
        assert documento_valido(cliente), f"dígito verificador inválido em {cliente.id}"


def test_busca_por_documento_normaliza_pontuacao():
    for cliente in REGISTROS:
        assert data.por_documento(cliente.documento) is cliente
        assert data.por_documento(normalizar_documento(cliente.documento)) is cliente
    assert data.por_documento("00.000.000/0000-00") is None


def test_snapshots_sao_seis_e_terminam_no_atual():
    for cliente in CLIENTES:
        snapshots = SNAPSHOTS[cliente.id]
        assert len(snapshots) == 6, cliente.id
        assert [s.data for s in snapshots] == list(DATAS_SNAPSHOT)
        assert snapshots[-1].fatos == FATOS[cliente.id], f"V38 violada em {cliente.id}"


def test_todas_as_14_fontes_aparecem():
    fontes = {
        evidencia.fonte
        for fatos in FATOS.values()
        for evidencia in fatos.evidencias
    }
    assert fontes == set(FonteId)


def test_ao_menos_onze_evidencias_por_registro():
    for cliente in REGISTROS:
        assert len(FATOS[cliente.id].evidencias) >= 11, cliente.id


def test_quatro_severidades_de_evento():
    assert {evento.severidade for evento in data.EVENTOS} == set(Severidade)
    assert {alerta.severidade for alerta in data.ALERTAS} == set(Severidade)
    assert len(data.EVENTOS) == 26


def test_alertas_apontam_para_evento_existente():
    ids = {evento.id for evento in data.EVENTOS}
    for alerta in data.ALERTAS:
        assert alerta.evento_id in ids
        assert alerta.cliente_nome and alerta.impacto and alerta.acao_recomendada


# ---------------------------------------------------------------------------
# 2 · Calibração
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cliente_id", sorted(CALIBRACAO))
def test_score_de_cada_cliente(cliente_id: str):
    esperado, _, _ = CALIBRACAO[cliente_id]
    obtido = _avaliacao(cliente_id).score_calculado
    assert abs(obtido - esperado) <= TOLERANCIA_SCORE, (
        f"{cliente_id}: score {obtido} ≠ {esperado} declarado na §5"
    )


@pytest.mark.parametrize("cliente_id", sorted(CALIBRACAO))
def test_rating_de_cada_cliente(cliente_id: str):
    _, calculado, final = CALIBRACAO[cliente_id]
    avaliacao = _avaliacao(cliente_id)
    assert avaliacao.rating_calculado.value == calculado, cliente_id
    assert avaliacao.rating_final.value == final, cliente_id


def test_todos_os_gatilhos_de_veto():
    exercidos = {
        veto.id for cliente in REGISTROS for veto in _avaliacao(cliente.id).vetos_ativos
    }
    assert exercidos == {
        "VETO_RJ",
        "VETO_FALENCIA",
        "VETO_EMBARGO_GARANTIA",
        "VETO_CADASTRO_INAPTO",
        "VETO_LISTA_SUJA",
        "VETO_FRAUDE",
        "TETO_EXEC_FISCAL",
        "TETO_CNDT",
    }


def test_composicao_de_vetos_em_santa_helena_norte():
    """Dois vetos de força D compõem; o embargo não recai sobre bem em garantia."""
    ativos = {veto.id for veto in _avaliacao("santa-helena-norte").vetos_ativos}
    assert ativos == {"VETO_LISTA_SUJA", "VETO_FRAUDE"}
    assert "VETO_EMBARGO_GARANTIA" not in ativos


def test_i5_eixos_independentes():
    ipanema = _avaliacao("ipanema-graos")
    camargo = _avaliacao("joao-camargo")
    assert ipanema.pd.pd12m < 0.15 and ipanema.risco_rj.probabilidade_12m > 0.30
    assert camargo.pd.pd12m > 0.25 and camargo.risco_rj.probabilidade_12m < 0.05
    assert round(ipanema.pd.pd12m * 100, 2) == 9.85
    assert round(ipanema.risco_rj.probabilidade_12m * 100, 2) == 40.60
    assert round(camargo.pd.pd12m * 100, 2) == 31.26
    assert round(camargo.risco_rj.probabilidade_12m * 100, 2) == 0.14
    assert camargo.risco_rj.elegivel is False
    assert _avaliacao("maria-nogueira").risco_rj.elegivel is True


def test_exposicao_total_da_carteira():
    total = sum(_avaliacao(c.id).exposicao.exposicao_total for c in CLIENTES)
    assert total == pytest.approx(244_300_000.0, abs=0.01)


def test_stay_period_ponta_verde():
    stay = _avaliacao("ponta-verde").stay_period
    assert stay is not None
    assert (stay.dias_decorridos, stay.dias_restantes, stay.ativo) == (66, 114, True)


def test_delta_712_604():
    snapshots = SNAPSHOTS["cerrado-norte"]
    anterior = calcular_risco(snapshots[4].fatos)
    atual = calcular_risco(snapshots[5].fatos)
    assert snapshots[4].data == "2026-07-14" and snapshots[5].data == "2026-09-12"
    assert anterior.score_calculado == pytest.approx(712.0, abs=TOLERANCIA_FECHAMENTO)
    assert atual.score_calculado == pytest.approx(604.0, abs=TOLERANCIA_FECHAMENTO)
    comparacao = comparar_avaliacoes(anterior, atual)
    soma = sum(linha.delta for linha in comparacao.fatores)
    assert soma == pytest.approx(-108.0, abs=TOLERANCIA_FECHAMENTO)
    assert comparacao.diferenca_de_fechamento == pytest.approx(0.0, abs=TOLERANCIA_FECHAMENTO)


def test_fechamento_i2_de_todos_os_registros_e_snapshots():
    alvos = [FATOS[c.id] for c in REGISTROS]
    alvos += [s.fatos for snaps in SNAPSHOTS.values() for s in snaps]
    for fatos in alvos:
        auditoria = calcular_risco(fatos).auditoria
        assert abs(auditoria.diferenca) < TOLERANCIA_FECHAMENTO, fatos.cliente_id


def test_fechamento_i6_snapshots_consecutivos():
    pares = 0
    for cliente_id, snapshots in SNAPSHOTS.items():
        for anterior, atual in zip(snapshots, snapshots[1:]):
            comparacao = comparar_avaliacoes(
                calcular_risco(anterior.fatos), calcular_risco(atual.fatos)
            )
            assert abs(comparacao.diferenca_de_fechamento) < TOLERANCIA_FECHAMENTO, cliente_id
            pares += 1
    assert pares == 18 * 5


def test_auditoria_coerente():
    assert len(data.REGISTROS_AUDITORIA) == 9
    for registro in data.REGISTROS_AUDITORIA:
        indice = SNAPSHOT_DO_REGISTRO[registro.id]
        avaliacao = calcular_risco(SNAPSHOTS[registro.cliente_id][indice].fatos)
        assert registro.score_no_momento == pytest.approx(
            avaliacao.score_calculado, abs=TOLERANCIA_FECHAMENTO
        ), registro.id
        assert registro.rating_no_momento is avaliacao.rating_final, registro.id
    divergentes = [r for r in data.REGISTROS_AUDITORIA if r.divergiu_da_recomendacao]
    assert len(divergentes) == 3


# ---------------------------------------------------------------------------
# 3 · Varredura de contradições — V1 a V40 (§12)
# ---------------------------------------------------------------------------

#: §12.1, item 1 — incoerência residual assumida e documentada.
EXCECAO_V6 = "sao-bento-bioenergia"


def test_v1_sem_litigio_exclui_execucao_falencia_e_rj():
    for cliente_id, fatos in FATOS.items():
        if not fatos.juridico.sem_litigio_36m:
            continue
        assert fatos.juridico.execucoes_titulo_12m == 0, cliente_id
        assert fatos.juridico.pedido_falencia is False, cliente_id
        assert fatos.juridico.recuperacao_judicial is None, cliente_id


def test_v2_certidoes_negativas_exigem_fisco_limpo():
    for cliente_id, fatos in FATOS.items():
        if not fatos.fiscal.todas_certidoes_negativas:
            continue
        assert fatos.fiscal.divida_ativa_pgfn == 0, cliente_id
        assert fatos.fiscal.cndt_positiva is False, cliente_id
        assert fatos.fiscal.crf_fgts_regular is True, cliente_id
        assert fatos.fiscal.execucoes_fiscais == 0, cliente_id


def test_v3_atraso_medio_nao_supera_o_pior_atraso():
    for cliente_id, fatos in FATOS.items():
        assert fatos.interno.atraso_medio_dias_12m <= fatos.interno.pior_atraso_dias_12m, cliente_id


def test_v4_pontualidade_coerente_com_o_atraso():
    for cliente_id, fatos in FATOS.items():
        atraso = fatos.interno.atraso_medio_dias_12m
        pontualidade = fatos.interno.pct_titulos_pagos_em_dia_12m
        if atraso == 0:
            assert pontualidade == 1.0, cliente_id
        if atraso >= 30:
            assert pontualidade <= 0.60, cliente_id


def test_v5_historico_limpo_exige_zero_atraso_relevante():
    for cliente_id, fatos in FATOS.items():
        if not fatos.interno.sem_atraso_relevante_24m:
            continue
        assert fatos.interno.pior_atraso_dias_12m <= 5, cliente_id
        assert fatos.interno.renegociacoes_12m == 0, cliente_id


def test_v6_sem_litigio_com_trabalhistas_transitadas_e_excecao_unica():
    ocorrencias = [
        cliente_id
        for cliente_id, fatos in FATOS.items()
        if fatos.juridico.sem_litigio_36m and fatos.juridico.acoes_trabalhistas_transitadas > 0
    ]
    assert ocorrencias == [EXCECAO_V6], (
        "V6 tolera uma única ocorrência, documentada na §12.1: o campo mede ações "
        "AJUIZADAS em 36 meses e o trânsito em julgado é anterior."
    )


def test_v7_credores_distintos_nao_superam_as_execucoes():
    for cliente_id, fatos in FATOS.items():
        assert (
            fatos.juridico.credores_distintos_executando <= fatos.juridico.execucoes_titulo_12m
        ), cliente_id


def test_v8_execucoes_90d_nao_superam_as_de_12m():
    for cliente_id, fatos in FATOS.items():
        assert fatos.juridico.execucoes_titulo_90d <= fatos.juridico.execucoes_titulo_12m, cliente_id


def test_v9_protestos_coerentes_entre_si():
    for cliente_id, fatos in FATOS.items():
        assert fatos.juridico.credores_protestantes_180d <= fatos.juridico.protestos_12m, cliente_id
        assert fatos.juridico.protestos_ativos <= fatos.juridico.protestos_12m, cliente_id


def test_v10_valor_em_execucao_equivale_a_haver_execucao():
    for cliente_id, fatos in FATOS.items():
        assert (fatos.juridico.valor_total_em_execucao > 0) == (
            fatos.juridico.execucoes_titulo_12m > 0
        ), cliente_id


def test_v11_cndt_positiva_equivale_a_debito_trabalhista():
    casos = [
        cliente_id for cliente_id, fatos in FATOS.items() if fatos.fiscal.cndt_positiva
    ]
    for cliente_id, fatos in FATOS.items():
        assert fatos.fiscal.cndt_positiva == (
            fatos.fiscal.valor_debito_trabalhista > 0
        ), cliente_id
    assert sorted(casos) == ["coop-vale-do-ivai", "ponta-verde", "rio-formoso"]


def test_v12_valor_de_execucao_fiscal_equivale_a_haver_execucao_fiscal():
    for cliente_id, fatos in FATOS.items():
        assert (fatos.fiscal.valor_execucoes_fiscais > 0) == (
            fatos.fiscal.execucoes_fiscais > 0
        ), cliente_id


def test_v13_divida_ativa_zerada_nao_tem_passado():
    for cliente_id, fatos in FATOS.items():
        if fatos.fiscal.divida_ativa_pgfn == 0:
            assert fatos.fiscal.divida_ativa_pgfn_90d_atras == 0, cliente_id


def test_v14_estado_do_cliente_reflete_rj_e_falencia():
    for cliente in REGISTROS:
        fatos = FATOS[cliente.id]
        if fatos.juridico.recuperacao_judicial is not None:
            assert cliente.estado.value == "RJ_EM_CURSO", cliente.id
        if fatos.juridico.pedido_falencia:
            assert cliente.estado.value in {"SUSPENSO", "FALENCIA"}, cliente.id


def test_v15_area_irrigada_nao_supera_a_area_total():
    for cliente_id, fatos in FATOS.items():
        assert fatos.agro.area_irrigada_ha <= fatos.agro.area_total_ha, cliente_id


def test_v16_protecao_climatica_so_existe_com_seguro_ou_irrigacao():
    for cliente_id, fatos in FATOS.items():
        irrigada = (
            fatos.agro.area_irrigada_ha / fatos.agro.area_total_ha
            if fatos.agro.area_total_ha
            else 0.0
        )
        tem_protecao = fatos.agro.seguro_agricola_vigente or irrigada >= 0.20
        fatores = {
            fator.id
            for dimensao in calcular_risco(fatos).dimensoes
            for fator in dimensao.fatores
        }
        assert ("irrigacao_ou_seguro" in fatores) == tem_protecao, cliente_id


def test_v17_culturas_dos_fatos_espelham_as_do_cliente():
    for cliente in REGISTROS:
        assert FATOS[cliente.id].agro.culturas == cliente.culturas, cliente.id
        assert FATOS[cliente.id].agro.safra_referencia, cliente.id
        assert FATOS[cliente.id].cadastral.tipo_pessoa is cliente.tipo_pessoa, cliente.id


def test_v18_cpr_vinculada_ao_barter_existe_e_esta_registrada():
    com_lastro, sem_lastro = [], []
    for cliente_id, fatos in FATOS.items():
        cprs = {
            g.id
            for g in fatos.garantias
            if g.tipo in {TipoGarantia.CPR_FINANCEIRA, TipoGarantia.CPR_FISICA} and g.registrada
        }
        for operacao in fatos.operacoes:
            if operacao.barter is None:
                continue
            vinculo = operacao.barter.cpr_vinculada_id
            if vinculo is None:
                sem_lastro.append(cliente_id)
                continue
            assert vinculo in cprs, f"{cliente_id}: CPR {vinculo} inexistente ou sem registro"
            com_lastro.append(cliente_id)
    assert len(com_lastro) == 8
    assert sorted(sem_lastro) == ["ponta-verde", "rio-formoso", "serra-do-urucui"]


def test_v19_valor_do_barter_bate_com_o_saldo_devedor():
    for cliente_id, fatos in FATOS.items():
        for operacao in fatos.operacoes:
            if operacao.barter is None:
                continue
            valor = operacao.barter.sacas_prometidas * operacao.barter.preco_referencia_saca
            desvio = abs(valor - operacao.saldo_devedor) / operacao.saldo_devedor
            assert desvio < 0.02, f"{cliente_id}: desvio de {desvio:.2%} no barter"


def test_v20_soma_dos_saldos_e_a_exposicao_total():
    for cliente_id, fatos in FATOS.items():
        soma = sum(operacao.saldo_devedor for operacao in fatos.operacoes)
        assert calcular_risco(fatos).exposicao.exposicao_total == pytest.approx(soma), cliente_id


def test_v21_parcelas_em_aberto_reconstroem_o_saldo():
    for cliente_id, fatos in FATOS.items():
        for operacao in fatos.operacoes:
            abertas = sum(
                p.valor
                for p in operacao.parcelas
                if p.status in {StatusParcela.A_VENCER, StatusParcela.EM_ATRASO}
            )
            assert abertas == pytest.approx(operacao.saldo_devedor), (cliente_id, operacao.id)


def test_v22_parcela_em_atraso_venceu_antes_da_data_de_referencia():
    from datetime import date

    com_atraso = set()
    for cliente_id, fatos in FATOS.items():
        referencia = date.fromisoformat(fatos.data_referencia)
        for operacao in fatos.operacoes:
            for parcela in operacao.parcelas:
                if parcela.status is not StatusParcela.EM_ATRASO:
                    continue
                vencimento = date.fromisoformat(parcela.vencimento)
                assert vencimento < referencia, (cliente_id, parcela.id)
                assert parcela.dias_atraso == (referencia - vencimento).days, parcela.id
                com_atraso.add(cliente_id)
    assert len(com_atraso) == 11


def test_v23_personas_sem_atraso_nao_tem_parcela_vencida():
    sem_atraso = {"tres-barras", "ipanema-graos", *[p.id for p in PROSPECTS]}
    for cliente_id in sem_atraso:
        assert calcular_risco(FATOS[cliente_id]).exposicao.em_atraso == 0.0, cliente_id


def test_v24_bem_embargado_exige_embargo_vigente_sobre_garantia():
    for cliente_id, fatos in FATOS.items():
        if not any(g.bem_embargado for g in fatos.garantias):
            continue
        assert fatos.ambiental.embargo_ibama_vigente, cliente_id
        assert fatos.ambiental.embargo_sobre_imovel_em_garantia, cliente_id
        assert cliente_id == "barra-do-ipe"


def test_v25_embargo_sobre_garantia_exige_bem_embargado():
    for cliente_id, fatos in FATOS.items():
        if not fatos.ambiental.embargo_sobre_imovel_em_garantia:
            continue
        assert any(g.bem_embargado for g in fatos.garantias), cliente_id


def test_v26_capital_social_positivo_em_todo_registro():
    for cliente in REGISTROS:
        fatos = FATOS[cliente.id]
        assert fatos.cadastral.capital_social > 0, cliente.id
        if cliente.tipo_pessoa is TipoPessoa.PF:
            # Convenção C2: em PF o campo carrega o patrimônio rural do IRPF.
            assert fatos.cadastral.capital_social <= fatos.patrimonio_declarado, cliente.id


def test_v27_faturamento_cobre_a_exposicao():
    razoes = {}
    for cliente_id, fatos in FATOS.items():
        exposicao = calcular_risco(fatos).exposicao.exposicao_total
        razao = fatos.faturamento_estimado_anual / exposicao
        razoes[cliente_id] = razao
        assert razao >= 1.1, f"{cliente_id}: faturamento é apenas {razao:.2f}× a exposição"
    assert min(razoes, key=razoes.get) == "rio-formoso"


def test_v28_atividade_comprovada_nao_supera_a_atividade():
    for cliente_id, fatos in FATOS.items():
        assert (
            fatos.cadastral.anos_atividade_comprovada <= fatos.cadastral.anos_atividade
        ), cliente_id


def test_v29_pessoa_fisica_nao_tem_quadro_societario():
    for cliente in REGISTROS:
        if cliente.tipo_pessoa is not TipoPessoa.PF:
            continue
        assert FATOS[cliente.id].cadastral.qsa_estavel_5anos is False, cliente.id


def test_v30_cadastro_nao_ativo_so_em_prospect_ou_suspenso():
    inaptos = []
    for cliente in REGISTROS:
        if FATOS[cliente.id].cadastral.situacao_rfb is SituacaoRfb.ATIVA:
            continue
        inaptos.append(cliente.id)
        assert cliente.origem.value == "PROSPECT" or cliente.estado.value == "SUSPENSO", cliente.id
    assert inaptos == ["beira-rio"]


def test_v31_municipio_compativel_com_as_culturas():
    for cliente in REGISTROS:
        chave = f"{cliente.municipio}/{cliente.uf}"
        assert chave in MATRIZ_AGRONOMICA, chave
        assert set(cliente.culturas) <= MATRIZ_AGRONOMICA[chave], cliente.id


def test_v32_exposicao_dentro_da_razao_por_hectare():
    for cliente in REGISTROS:
        custeio, fracao = RAZAO_POR_HECTARE[cliente.id]
        exposicao = calcular_risco(FATOS[cliente.id]).exposicao.exposicao_total
        desvio = abs(custeio * fracao - exposicao) / exposicao
        assert desvio <= 0.05, f"{cliente.id}: desvio de {desvio:.2%} da razão R$/ha"


def test_v33_documentos_com_digito_verificador_valido():
    for cliente in REGISTROS:
        numeros = normalizar_documento(cliente.documento)
        assert len(set(numeros)) > 1, f"{cliente.id}: sequência repetida"
        assert documento_valido(cliente), cliente.id


def test_v34_nenhum_documento_repetido():
    documentos = [normalizar_documento(c.documento) for c in REGISTROS]
    assert len(set(documentos)) == len(documentos) == 22


def test_v35_toda_evidencia_e_simulada():
    total = 0
    for fatos in FATOS.values():
        for evidencia in fatos.evidencias:
            assert evidencia.simulada is True, evidencia.id
            assert evidencia.url_ficticia and evidencia.data_consulta
            total += 1
    assert total >= 22 * 11


def test_v36_fatores_relacionados_existem_no_catalogo():
    for cliente_id, fatos in FATOS.items():
        for evidencia in fatos.evidencias:
            desconhecidos = set(evidencia.fatores_relacionados) - CATALOGO_DE_FATORES
            assert not desconhecidos, f"{cliente_id}/{evidencia.id}: {desconhecidos}"


def test_v37_nenhum_snapshot_contem_fato_posterior_a_sua_data():
    for cliente_id, snapshots in SNAPSHOTS.items():
        for snapshot in snapshots:
            fatos = snapshot.fatos
            assert fatos.data_referencia == snapshot.data, cliente_id
            for covenant in fatos.interno.covenants_rompidos:
                assert covenant.data_deteccao <= snapshot.data, (cliente_id, covenant.id)
            rj = fatos.juridico.recuperacao_judicial
            if rj is not None:
                assert rj.data_distribuicao <= snapshot.data, cliente_id
                assert (rj.data_deferimento or "") <= snapshot.data, cliente_id


def test_v38_ultimo_snapshot_e_identico_aos_fatos_correntes():
    for cliente in CLIENTES:
        assert SNAPSHOTS[cliente.id][-1].fatos == FATOS[cliente.id], cliente.id


def _modulos_de_data() -> list[tuple[str, ast.Module]]:
    arquivos = sorted(DIRETORIO_DATA.rglob("*.py"))
    assert len(arquivos) >= 28, "o pacote data/ perdeu arquivos"
    return [
        (str(caminho.relative_to(DIRETORIO_DATA)), ast.parse(caminho.read_text(encoding="utf-8")))
        for caminho in arquivos
    ]


def test_v39_data_nao_importa_scoring():
    for nome, arvore in _modulos_de_data():
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for alias in no.names:
                    assert not alias.name.startswith("scoring"), nome
            elif isinstance(no, ast.ImportFrom):
                assert not (no.module or "").startswith("scoring"), nome


#: §3 — campos derivados que o pacote `data/` está proibido de escrever.
DERIVADOS_PROIBIDOS = frozenset(
    {
        "score",
        "score_calculado",
        "scoreCalculado",
        "rating",
        "rating_calculado",
        "rating_final",
        "ratingFinal",
        "pd",
        "pd6m",
        "pd12m",
        "pd24m",
        "red_flags",
        "redFlags",
        "recomendacao",
        "natureza",
        "valor_atualizado",
        "valorAtualizado",
        "cobertura_total",
        "cobertura_extraconcursal",
    }
)

#: `scoreApos`/`deltaScore` só podem receber a sentinela — quem os preenche é o runtime.
SENTINELADOS = frozenset({"score_apos", "scoreApos", "delta_score", "deltaScore"})

#: §13 autoriza explicitamente o registro histórico do que o analista viu.
ARQUIVO_DA_AUDITORIA = "auditoria.py"


def test_v40_data_nao_escreve_campo_derivado():
    for nome, arvore in _modulos_de_data():
        for no in ast.walk(arvore):
            if not isinstance(no, ast.keyword) or no.arg is None:
                continue
            if no.arg in SENTINELADOS:
                assert isinstance(no.value, ast.Name) and no.value.id == "SEM_RECALCULO", nome
                continue
            if nome == ARQUIVO_DA_AUDITORIA and no.arg in {"score", "rating"}:
                continue
            assert no.arg not in DERIVADOS_PROIBIDOS, f"{nome}: escreve `{no.arg}`"


def test_sentinela_de_evento_nao_e_valor_calculado():
    for evento in data.EVENTOS:
        assert evento.score_apos == SEM_RECALCULO
        assert evento.delta_score == SEM_RECALCULO


def test_natureza_das_garantias_e_derivada_nao_digitada():
    """A CPR física de `serra-do-urucui` é concursal por natureza (02 §10)."""
    fatos = FATOS["serra-do-urucui"]
    naturezas = {g.tipo: g.natureza for g in fatos.garantias}
    assert naturezas[TipoGarantia.CPR_FISICA] is NaturezaGarantia.CONCURSAL
    assert calcular_risco(fatos).exposicao.valor_extraconcursal == 0.0


def test_pacote_data_importa_sem_efeito_colateral():
    """Nenhum módulo do dataset faz I/O ou depende de rede."""
    for info in pkgutil.walk_packages(data.__path__, prefix="data."):
        importlib.import_module(info.name)


def test_car_pendente_e_irregular_convivem_com_o_enum():
    situacoes = {FATOS[c.id].ambiental.situacao_car for c in REGISTROS}
    assert SituacaoCar.ATIVO_REGULAR in situacoes
    assert SituacaoCar.PENDENTE in situacoes
    assert SituacaoCar.IRREGULAR in situacoes
