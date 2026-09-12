"""O verificador numérico — a invariante I7 em teste. `04-camada-llm.md` §4.4.

Este é o arquivo mais importante da camada: é o que prova que um número
inventado pelo modelo não chega à tela.
"""

from __future__ import annotations

import pytest
from llm.verificador import (
    CONSTANTES,
    contar_palavras,
    extrair_numeros,
    verificar_fidelidade_numerica,
)

from apoio import carregar_fixtures_gravadas

#: As sete violações que a spec (§7.4) atribui ao golden RUIM, literalmente.
VIOLACOES_DO_GOLDEN_RUIM = ["17", "2,1", "3,5", "4,2", "60", "600", "7"]

#: Contagem de palavras do golden BOM pela métrica da §3.a.
PALAVRAS_DO_GOLDEN_BOM = 457


class ContextoFalso:
    """Só o que o verificador consome: o conjunto de números permitidos."""

    def __init__(self, bloco: str):
        self.numeros_permitidos = frozenset(extrair_numeros(bloco))


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Score 604.", {"604"}),
        ("PD 12m de 17,1%.", {"12", "17,1"}),
        ("R$ 1.200.000 de exposição.", {"1.200.000"}),
        ("Impacto -26,4 e proteção +15,0.", {"-26,4", "15,0"}),
        ("Consulta em 11/09/2026.", {"11/09/2026"}),
        ("Evidências [E-01] e garantia G-02.", set()),
        ("1. Reduzir limite\n2. Exigir garantia", set()),
        ("A PD 12m é alta.", {"12"}),
        ("Endividamento de 3,1x o patrimônio.", {"3,1"}),
    ],
)
def test_extrair_numeros_reconhece_as_formas_do_contrato(texto, esperado):
    assert extrair_numeros(texto) == esperado


def test_sinal_de_mais_e_ausencia_dele_sao_o_mesmo_numero():
    """O contexto escreve `+15,0`; a prosa pode escrever `15,0`."""
    assert extrair_numeros("+15,0") == extrair_numeros("15,0") == {"15,0"}


def test_datas_nao_viram_tres_numeros_soltos():
    """`11/09/2026` não pode liberar `11`, `09` e `2026` isoladamente."""
    assert extrair_numeros("em 11/09/2026") == {"11/09/2026"}


# ---------------------------------------------------------------------------
# Golden examples da §7.4 — o coração do teste
# ---------------------------------------------------------------------------


def test_golden_bom_nao_tem_nenhuma_violacao(bloco_da_spec, golden_bom):
    assert verificar_fidelidade_numerica(golden_bom, ContextoFalso(bloco_da_spec)) == []


def test_golden_bom_tem_457_palavras(golden_bom):
    assert contar_palavras(golden_bom) == PALAVRAS_DO_GOLDEN_BOM


def test_golden_ruim_tem_exatamente_as_sete_violacoes_da_spec(bloco_da_spec, golden_ruim):
    """Aproximações, conversões e invenções: `cerca de 17%`, `R$ 4,2 milhões`…"""
    assert (
        verificar_fidelidade_numerica(golden_ruim, ContextoFalso(bloco_da_spec))
        == VIOLACOES_DO_GOLDEN_RUIM
    )


def test_o_verificador_nao_pega_numero_por_extenso(bloco_da_spec):
    """Falso negativo conhecido e documentado: os prompts é que o proíbem."""
    contexto = ContextoFalso(bloco_da_spec)
    assert verificar_fidelidade_numerica("Existem três execuções.", contexto) == []


def test_numero_de_25_por_cento_escapa_porque_existe_no_contexto(bloco_da_spec):
    """O caso que só o juiz pega (§7.4): `25` está lá como quebra de safra."""
    contexto = ContextoFalso(bloco_da_spec)
    assert verificar_fidelidade_numerica("reduzindo o limite em 25%", contexto) == []


# ---------------------------------------------------------------------------
# Regras auxiliares
# ---------------------------------------------------------------------------


def test_constantes_legais_e_janelas_temporais_sao_permitidas():
    contexto = ContextoFalso("nada aqui")
    texto = (
        "Lei 11.101/2005 e Lei 14.112/2020, Stay Period de 180 dias, PD 12 e 24 meses, "
        "variação dos últimos 90 dias."
    )
    assert verificar_fidelidade_numerica(texto, contexto) == []
    assert {"90", "180", "11.101", "2005"} <= CONSTANTES


def test_numeros_da_pergunta_entram_como_extras(bloco_da_spec):
    """§8, caso 9: repetir o número que o analista escreveu não é invenção."""
    contexto = ContextoFalso(bloco_da_spec)
    assert verificar_fidelidade_numerica("São R$ 7.777.777.", contexto) == ["7.777.777"]
    assert verificar_fidelidade_numerica("São R$ 7.777.777.", contexto, {"7.777.777"}) == []


def test_valor_com_centavos_e_violacao(bloco_da_spec):
    """`R$ 2.100.000,00` não é `R$ 2.100.000`: o formato do contexto é sem centavos."""
    contexto = ContextoFalso(bloco_da_spec)
    assert verificar_fidelidade_numerica("R$ 2.100.000,00", contexto) == ["2.100.000,00"]


def test_contar_palavras_descarta_evidencias_titulos_e_marcadores():
    texto = "## Resumo\n- Item com [E-01] e **negrito**\n1. Ação\n## Evidências\n- [E-02] fonte"
    assert contar_palavras(texto) == len("Item com e negrito Ação".split())


# ---------------------------------------------------------------------------
# Fixtures gravadas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "fixture"), carregar_fixtures_gravadas(), ids=lambda v: v if isinstance(v, str) else ""
)
def test_toda_fixture_gravada_e_fiel_ao_proprio_contexto(nome, fixture):
    """Fixtures são, por construção, exemplos fiéis — §6.2 recusa gravar outras."""
    contexto = ContextoFalso(fixture["entrada"]["user"])
    assert verificar_fidelidade_numerica(fixture["saida"], contexto) == []
    assert fixture["fidelidade"]["violacoes"] == []
