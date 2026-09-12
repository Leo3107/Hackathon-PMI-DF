"""Gatilhos de veto (§8), coberturas (§10) e Stay Period (§9).

Dois contratos inegociáveis aqui: o veto **nunca** altera `scoreCalculado`, e
garantia extraconcursal **nunca** é somada a garantia concursal sem distinção —
é o que permite dizer quanto a Krill Tech perde se o cliente pedir RJ amanhã.
"""

from __future__ import annotations

from datetime import date

import pytest

from models.enums import NaturezaGarantia, Rating, SituacaoRfb, TipoGarantia
from models.exposicao import Garantia
from scoring import CONFIG_PADRAO, calcular_exposicao, calcular_risco, classificar_rating
from scoring.exposicao import normalizar_garantias
from scoring.stay_period import calcular_stay_period

from fixtures import (
    PERFIS,
    cliente_em_rj_com_stay_period,
    cliente_excelente,
    todos_os_perfis,
)


def _base():
    return cliente_excelente().model_copy(deep=True)


def _ids_dos_vetos(avaliacao) -> list[str]:
    return [veto.id for veto in avaliacao.vetos_ativos]


# ---------------------------------------------------------------------------
# §8 · Cada gatilho força o rating correto e preserva o score calculado
# ---------------------------------------------------------------------------


def test_sem_gatilho_o_rating_final_e_o_calculado():
    avaliacao = calcular_risco(cliente_excelente())
    assert avaliacao.vetos_ativos == []
    assert avaliacao.rating_final is avaliacao.rating_calculado is Rating.A


@pytest.mark.parametrize(
    ("veto_id", "mutacao"),
    [
        (
            "VETO_LISTA_SUJA",
            lambda f: setattr(f.juridico, "lista_suja_trabalho_escravo", True),
        ),
        ("VETO_FRAUDE", lambda f: setattr(f.juridico, "fraude_confirmada", True)),
    ],
)
def test_veto_forca_d_sem_tocar_no_score(veto_id, mutacao):
    """Gatilhos puramente jurídicos: o quantitativo não muda, a regra rebaixa."""
    base = calcular_risco(cliente_excelente())
    fatos = _base()
    mutacao(fatos)
    avaliacao = calcular_risco(fatos)

    assert veto_id in _ids_dos_vetos(avaliacao)
    assert avaliacao.score_calculado == base.score_calculado
    assert avaliacao.rating_calculado is Rating.A
    assert avaliacao.rating_final is Rating.D


def test_veto_embargo_sobre_garantia_depende_do_bem_dado_em_garantia():
    """Embargo sozinho penaliza o score; sobre a garantia, elimina o crédito."""
    sem_garantia_embargada = _base()
    sem_garantia_embargada.ambiental.embargo_ibama_vigente = True

    com_garantia_embargada = sem_garantia_embargada.model_copy(deep=True)
    com_garantia_embargada.ambiental.embargo_sobre_imovel_em_garantia = True

    sem = calcular_risco(sem_garantia_embargada)
    com = calcular_risco(com_garantia_embargada)

    assert "VETO_EMBARGO_GARANTIA" not in _ids_dos_vetos(sem)
    assert "VETO_EMBARGO_GARANTIA" in _ids_dos_vetos(com)
    assert com.score_calculado == sem.score_calculado
    assert com.rating_calculado is sem.rating_calculado
    assert com.rating_final is Rating.D


def test_veto_embargo_reconhece_a_marcacao_na_propria_garantia():
    avaliacao = calcular_risco(PERFIS["veto_ambiental"]())
    assert "VETO_EMBARGO_GARANTIA" in _ids_dos_vetos(avaliacao)
    assert avaliacao.rating_calculado is Rating.A
    assert avaliacao.rating_final is Rating.D
    assert classificar_rating(avaliacao.score_calculado) is avaliacao.rating_calculado


def test_veto_cadastro_inapto():
    fatos = _base()
    fatos.cadastral.situacao_rfb = SituacaoRfb.INAPTA
    avaliacao = calcular_risco(fatos)
    assert "VETO_CADASTRO_INAPTO" in _ids_dos_vetos(avaliacao)
    assert avaliacao.rating_final is Rating.D
    assert classificar_rating(avaliacao.score_calculado) is avaliacao.rating_calculado


def test_veto_pedido_de_falencia():
    fatos = _base()
    fatos.juridico.pedido_falencia = True
    avaliacao = calcular_risco(fatos)
    assert "VETO_FALENCIA" in _ids_dos_vetos(avaliacao)
    assert avaliacao.rating_final is Rating.D


def test_veto_rj_preserva_o_score_quantitativo():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    assert "VETO_RJ" in _ids_dos_vetos(avaliacao)
    assert avaliacao.rating_final is Rating.D
    #: o quantitativo continua visível e coerente com a própria faixa
    assert classificar_rating(avaliacao.score_calculado) is avaliacao.rating_calculado
    assert avaliacao.rating_calculado is not Rating.D


def test_teto_execucoes_fiscais_limita_em_c_sem_alterar_o_score():
    base = calcular_risco(cliente_excelente())
    fatos = _base()
    exposicao = base.exposicao.exposicao_total
    fatos.fiscal.execucoes_fiscais = 3
    fatos.fiscal.valor_execucoes_fiscais = (
        CONFIG_PADRAO.limiar_exec_fiscal_sobre_exposicao * exposicao * 1.2
    )
    avaliacao = calcular_risco(fatos)

    assert "TETO_EXEC_FISCAL" in _ids_dos_vetos(avaliacao)
    assert avaliacao.score_calculado == base.score_calculado
    assert avaliacao.rating_calculado is Rating.A
    assert avaliacao.rating_final is Rating.C


def test_teto_cndt_limita_em_c():
    fatos = _base()
    fatos.fiscal.cndt_positiva = True
    fatos.fiscal.valor_debito_trabalhista = (
        CONFIG_PADRAO.limiar_cndt_sobre_patrimonio * fatos.patrimonio_declarado * 1.5
    )
    avaliacao = calcular_risco(fatos)
    assert "TETO_CNDT" in _ids_dos_vetos(avaliacao)
    assert avaliacao.rating_final is Rating.C


def test_forca_d_prevalece_sobre_teto_c():
    fatos = _base()
    fatos.juridico.fraude_confirmada = True
    fatos.fiscal.execucoes_fiscais = 3
    fatos.fiscal.valor_execucoes_fiscais = fatos.operacoes[0].saldo_devedor
    avaliacao = calcular_risco(fatos)

    ids = _ids_dos_vetos(avaliacao)
    assert {"VETO_FRAUDE", "TETO_EXEC_FISCAL"} <= set(ids)
    assert avaliacao.rating_final is Rating.D


# ---------------------------------------------------------------------------
# §10 · Coberturas — extraconcursal nunca somada a concursal sem distinção
# ---------------------------------------------------------------------------


def test_naturezas_derivam_do_tipo_e_do_registro():
    garantias = normalizar_garantias(
        [
            Garantia(id="g1", tipo=TipoGarantia.ALIENACAO_FIDUCIARIA, valor_declarado=100.0),
            Garantia(
                id="g2",
                tipo=TipoGarantia.CPR_FINANCEIRA,
                valor_declarado=100.0,
                registrada=True,
            ),
            Garantia(
                id="g3",
                tipo=TipoGarantia.CPR_FINANCEIRA,
                valor_declarado=100.0,
                registrada=False,
            ),
            Garantia(id="g4", tipo=TipoGarantia.PENHOR_SAFRA, valor_declarado=100.0),
        ]
    )
    naturezas = {g.id: g.natureza for g in garantias}
    assert naturezas["g1"] is NaturezaGarantia.EXTRACONCURSAL
    assert naturezas["g2"] is NaturezaGarantia.EXTRACONCURSAL
    #: CPR financeira sem registro perde a vinculação e volta ao concurso.
    assert naturezas["g3"] is NaturezaGarantia.CONCURSAL
    assert naturezas["g4"] is NaturezaGarantia.CONCURSAL

    valores = {g.id: g.valor_atualizado for g in garantias}
    assert valores["g1"] == pytest.approx(80.0)
    assert valores["g2"] == pytest.approx(90.0)
    assert valores["g4"] == pytest.approx(60.0)


def test_coberturas_do_perfil_excelente():
    resumo = calcular_exposicao(cliente_excelente())
    exposicao = resumo.calculada
    #: alienação fiduciária 8.000.000 com 20% de deságio
    assert exposicao.valor_extraconcursal == pytest.approx(6_400_000.0)
    #: penhor de safra 3.000.000 com 40% de deságio
    assert exposicao.valor_concursal == pytest.approx(1_800_000.0)
    assert exposicao.cobertura_extraconcursal == pytest.approx(0.8)
    assert exposicao.cobertura_total == pytest.approx(1.025)
    #: protegida satura na exposição total — não há proteção acima de 100%
    assert exposicao.exposicao_em_risco == pytest.approx(0.0)
    #: em cenário de RJ o penhor entra no plano e some da proteção
    assert exposicao.exposicao_em_risco_em_rj == pytest.approx(1_600_000.0)


@pytest.mark.parametrize("nome", sorted(PERFIS))
def test_extraconcursal_nunca_somada_a_concursal(nome):
    fatos = PERFIS[nome]()
    resumo = calcular_exposicao(fatos)
    exposicao = resumo.calculada

    extraconcursais = [
        g for g in resumo.garantias if g.natureza is NaturezaGarantia.EXTRACONCURSAL
    ]
    concursais = [g for g in resumo.garantias if g.natureza is NaturezaGarantia.CONCURSAL]
    assert exposicao.valor_extraconcursal == pytest.approx(
        sum(g.valor_atualizado for g in extraconcursais)
    )
    assert exposicao.valor_concursal == pytest.approx(
        sum(g.valor_atualizado for g in concursais)
    )
    #: nenhuma garantia é contada nas duas naturezas
    assert len(extraconcursais) + len(concursais) == len(resumo.garantias)

    assert exposicao.cobertura_total >= exposicao.cobertura_extraconcursal
    assert exposicao.exposicao_em_risco_em_rj >= exposicao.exposicao_em_risco
    assert exposicao.exposicao_em_risco_em_rj == pytest.approx(
        max(0.0, exposicao.exposicao_total - exposicao.valor_extraconcursal)
    )


def test_exposicao_em_risco_em_rj_ignora_a_garantia_concursal():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    exposicao = avaliacao.exposicao
    assert exposicao.valor_concursal > 0
    assert exposicao.exposicao_em_risco_em_rj > exposicao.exposicao_em_risco
    assert exposicao.exposicao_em_risco_em_rj == pytest.approx(
        exposicao.exposicao_total - exposicao.valor_extraconcursal
    )


# ---------------------------------------------------------------------------
# §9 · Stay Period
# ---------------------------------------------------------------------------


def test_stay_period_ativo_conta_os_dias_a_partir_do_deferimento():
    avaliacao = calcular_risco(cliente_em_rj_com_stay_period())
    stay = avaliacao.stay_period
    assert stay is not None
    assert stay.ativo is True
    #: 2026-06-10 → 2026-09-12
    assert stay.dias_decorridos == 94
    assert stay.dias_restantes == CONFIG_PADRAO.stay_period_dias - 94
    assert stay.bloqueios and stay.permitido
    assert any("alienação fiduciária" in texto for texto in stay.permitido)


def test_stay_period_expira_e_aceita_prorrogacao():
    fatos = cliente_em_rj_com_stay_period()
    expirado = calcular_stay_period(fatos, data_referencia=date(2027, 1, 15))
    assert expirado is not None
    assert expirado.dias_restantes == 0
    assert expirado.ativo is False

    prorrogado = fatos.model_copy(deep=True)
    prorrogado.juridico.recuperacao_judicial.dias_prorrogados_stay = 60
    com_prorrogacao = calcular_stay_period(prorrogado)
    assert com_prorrogacao is not None
    assert com_prorrogacao.dias_restantes == CONFIG_PADRAO.stay_period_dias + 60 - 94


def test_sem_rj_nao_ha_painel_de_stay_period():
    for nome, fatos in todos_os_perfis():
        avaliacao = calcular_risco(fatos)
        if fatos.juridico.recuperacao_judicial is None:
            assert avaliacao.stay_period is None, nome
