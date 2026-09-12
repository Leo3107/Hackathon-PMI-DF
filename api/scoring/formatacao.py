"""Formatadores pt-BR usados no texto já pronto das ações recomendadas.

Puros e independentes de `locale` — `locale` é estado global de processo e
tornaria o motor não determinístico entre ambientes.
"""

from __future__ import annotations

__all__ = ["numero", "moeda", "percentual", "percentual_de_fracao", "plural_dias"]

_SEPARADOR_MILHAR = "."
_SEPARADOR_DECIMAL = ","
_PREFIXO_MOEDA = "R$ "
_SUFIXO_PERCENTUAL = "%"
_CASAS_PERCENTUAL_PADRAO = 1
_FATOR_PERCENTUAL = 100.0
_SINGULAR_DIA = "dia"
_PLURAL_DIAS = "dias"
_LIMITE_SINGULAR = 1


def numero(valor: float, casas: int = 0) -> str:
    """1480000 → '1.480.000' · 17.13 com 1 casa → '17,1'."""
    texto = f"{valor:,.{casas}f}"
    inteiro, _, decimal = texto.partition(".")
    inteiro = inteiro.replace(",", _SEPARADOR_MILHAR)
    if not decimal:
        return inteiro
    return f"{inteiro}{_SEPARADOR_DECIMAL}{decimal}"


def moeda(valor: float, casas: int = 0) -> str:
    """5000000 → 'R$ 5.000.000'."""
    return f"{_PREFIXO_MOEDA}{numero(valor, casas)}"


def percentual(valor_percentual: float, casas: int = _CASAS_PERCENTUAL_PADRAO) -> str:
    """30.0 → '30,0%' (o argumento já está em pontos percentuais)."""
    return f"{numero(valor_percentual, casas)}{_SUFIXO_PERCENTUAL}"


def percentual_de_fracao(fracao: float, casas: int = _CASAS_PERCENTUAL_PADRAO) -> str:
    """0.3 → '30,0%'."""
    return percentual(fracao * _FATOR_PERCENTUAL, casas)


def plural_dias(dias: int) -> str:
    """1 → '1 dia' · 60 → '60 dias'."""
    rotulo = _SINGULAR_DIA if abs(dias) == _LIMITE_SINGULAR else _PLURAL_DIAS
    return f"{numero(dias)} {rotulo}"
