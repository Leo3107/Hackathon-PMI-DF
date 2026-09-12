"""Critérios de aceitação do dataset real de CNPJs — Tarefas 1 e 2.

Substitui a suíte dos 18 clientes inventados (`specs/06-dados-simulados.md`).
Três blocos:

1. **Estrutura e integridade** do CSV carregado — contagens, perfis, unicidade
   de documento, e nenhum campo derivado escrito no meio do caminho (garantia,
   operação, evidência: nada disso existe sem declaração do analista).
2. **Honestidade da etiqueta sintética** — razão social nunca finge ser nome
   real (Tarefa 2).
3. **Calibração do modelo de PD** (Tarefa 1) — a PD média por perfil bate com
   a taxa real de `alvo_sintetico` dentro de poucos pontos percentuais, a
   mesma verificação que o usuário já fez manualmente antes de pedir a
   implementação.
"""

from __future__ import annotations

from collections import Counter

import pytest

import data
from data.carregador_csv import normalizar_documento
from models.cliente import Cliente
from models.enums import OrigemCliente, TipoPessoa
from models.fatos import FatosDoCliente
from scoring.modelo_pd import calcular_pd_12m

TOTAL_DE_REGISTROS = 3000

#: §"Fatos que eu já verifiquei" do pedido — contagem por perfil.
CONTAGEM_POR_PERFIL = {
    "limpo": 2022,
    "divida_ativa": 363,
    "passivo_ambiental_auto": 247,
    "situacao_irregular": 180,
    "grupo_societario": 141,
    "passivo_ambiental_embargo": 47,
}

#: PD média real por perfil (taxa de `alvo_sintetico`) e a tolerância que o
#: usuário já validou manualmente ao pedir esta implementação.
PD_REAL_POR_PERFIL = {
    "limpo": 4.9,
    "divida_ativa": 24.2,
}
PD_REAL_GLOBAL = 8.93
TOLERANCIA_PD_PP = 2.0  # pontos percentuais


# ---------------------------------------------------------------------------
# Estrutura e integridade
# ---------------------------------------------------------------------------


def test_total_de_registros():
    assert len(data.PROSPECTS) == TOTAL_DE_REGISTROS
    assert len(data.FEATURES_POR_CLIENTE) == TOTAL_DE_REGISTROS
    assert len(data.FATOS_POR_CLIENTE) == TOTAL_DE_REGISTROS
    assert len(data.PERFIL_POR_CLIENTE) == TOTAL_DE_REGISTROS


def test_nenhum_cnpj_nasce_em_carteira():
    """A carteira é a declaração do analista (Tarefa 3) — não este dataset."""
    assert data.CLIENTES == []
    assert all(cliente.origem is OrigemCliente.PROSPECT for cliente in data.PROSPECTS)


def test_documentos_sao_unicos_e_sao_cnpj():
    documentos = [cliente.documento for cliente in data.PROSPECTS]
    assert len(documentos) == len(set(documentos))
    assert all(len(normalizar_documento(doc)) == 14 for doc in documentos)
    assert all(cliente.tipo_pessoa is TipoPessoa.PJ for cliente in data.PROSPECTS)


def test_contagem_por_perfil_bate_com_o_pedido():
    assert Counter(data.PERFIL_POR_CLIENTE.values()) == Counter(CONTAGEM_POR_PERFIL)


def test_todos_os_registros_sao_pydantic_validos():
    """Se o carregamento produziu algo inválido, a importação já teria falhado
    — este teste apenas nomeia a garantia explicitamente."""
    for cliente in data.PROSPECTS:
        assert isinstance(cliente, Cliente)
    for fatos in data.FATOS_POR_CLIENTE.values():
        assert isinstance(fatos, FatosDoCliente)


def test_base_nao_inventa_exposicao_nem_garantia():
    """Sem declaração do analista (Tarefa 3), nada disso existe (§ do pedido)."""
    for fatos in data.FATOS_POR_CLIENTE.values():
        assert fatos.operacoes == []
        assert fatos.garantias == []
        assert fatos.limite_aprovado == 0.0
        assert fatos.patrimonio_declarado == 0.0
        assert fatos.faturamento_estimado_anual == 0.0


def test_base_nao_inventa_evidencia_simulada():
    """`Evidencia.simulada` é sempre `True`; a base real não fabrica consultas."""
    for fatos in data.FATOS_POR_CLIENTE.values():
        assert fatos.evidencias == []


def test_todos_os_clientes_tem_cultura_soja_apenas_descritiva():
    """`cultura_referencia` é sempre soja (fato verificado), só para exibição —
    `FatosAgro.culturas` continua vazio (não é prova de monocultura apurada)."""
    assert all(cliente.culturas == ["Soja"] for cliente in data.PROSPECTS)
    assert all(fatos.agro.culturas == [] for fatos in data.FATOS_POR_CLIENTE.values())


# ---------------------------------------------------------------------------
# Etiqueta sintética de razão social (Tarefa 2)
# ---------------------------------------------------------------------------


def test_razao_social_e_descritiva_e_estavel():
    for cliente in data.PROSPECTS:
        assert cliente.razao_social.startswith("Produtor rural ")
        # Estável: os últimos dígitos do documento aparecem na etiqueta.
        assert normalizar_documento(cliente.documento)[-6:] in cliente.razao_social


def test_razao_social_e_estavel_e_deterministica():
    from data.carregador_csv import _razao_social_sintetica

    documento = data.PROSPECTS[0].documento
    perfil = data.PERFIL_POR_CLIENTE[documento]
    assert _razao_social_sintetica(documento, perfil) == _razao_social_sintetica(
        documento, perfil
    )


# ---------------------------------------------------------------------------
# Calibração do modelo de PD (Tarefa 1)
# ---------------------------------------------------------------------------


def _pd_media_do_perfil(perfil: str) -> float:
    pds = [
        calcular_pd_12m(features)
        for documento, features in data.FEATURES_POR_CLIENTE.items()
        if data.PERFIL_POR_CLIENTE[documento] == perfil
    ]
    return 100.0 * sum(pds) / len(pds)


@pytest.mark.parametrize("perfil", sorted(PD_REAL_POR_PERFIL))
def test_pd_media_do_perfil_bate_com_a_taxa_real(perfil):
    pd_media = _pd_media_do_perfil(perfil)
    esperado = PD_REAL_POR_PERFIL[perfil]
    assert pd_media == pytest.approx(esperado, abs=TOLERANCIA_PD_PP)


def test_pd_media_global_bate_com_a_taxa_real():
    pds = [calcular_pd_12m(features) for features in data.FEATURES_POR_CLIENTE.values()]
    pd_media_global = 100.0 * sum(pds) / len(pds)
    assert pd_media_global == pytest.approx(PD_REAL_GLOBAL, abs=TOLERANCIA_PD_PP)


def test_perfil_com_mais_apontamentos_tem_pd_maior_que_o_limpo():
    """Direção do modelo: perfis com apontamentos públicos não podem ter PD
    menor que o perfil limpo — checagem de sanidade, não de calibração fina."""
    pd_limpo = _pd_media_do_perfil("limpo")
    for perfil in CONTAGEM_POR_PERFIL:
        if perfil == "limpo":
            continue
        assert _pd_media_do_perfil(perfil) > pd_limpo
