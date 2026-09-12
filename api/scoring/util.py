"""Utilitários puros do motor. Sem I/O, sem relógio, sem aleatoriedade."""

from __future__ import annotations

from datetime import date, datetime

__all__ = [
    "NEUTRO",
    "para_data",
    "para_data_opcional",
    "dias_entre",
    "somar_dias",
    "clamp",
    "limitar",
    "razao_segura",
    "arredondar",
]

#: Elemento neutro das somas e valor de retorno quando um cálculo não se aplica.
NEUTRO: float = 0.0


def para_data(iso: str) -> date:
    """Converte uma string ISO (date ou datetime) em `date`."""
    texto = iso.strip()
    if "T" in texto:
        return datetime.fromisoformat(texto).date()
    return date.fromisoformat(texto)


def para_data_opcional(iso: str | None) -> date | None:
    """Idem, tolerando ausência e string vazia — usado em campos opcionais."""
    if not iso:
        return None
    try:
        return para_data(iso)
    except ValueError:
        return None


def dias_entre(inicio: date, fim: date) -> int:
    """Dias corridos de `inicio` a `fim` (negativo quando `fim` é anterior)."""
    return (fim - inicio).days


def somar_dias(referencia: date, dias: int) -> date:
    from datetime import timedelta

    return referencia + timedelta(days=dias)


def clamp(valor: float, minimo: float, maximo: float) -> float:
    """Restringe `valor` ao intervalo fechado [minimo, maximo]."""
    return max(minimo, min(maximo, valor))


def limitar(valor: float, teto: float) -> float:
    """`min(teto, valor)` — a forma como a spec escreve os tetos dos fatores."""
    return min(teto, valor)


def razao_segura(numerador: float, denominador: float, padrao: float = NEUTRO) -> float:
    """Divisão que devolve `padrao` quando o denominador é nulo ou negativo.

    Denominador zero acontece em cliente sem exposição (prospect em due
    diligence). Nesse caso a razão não é "infinita", é **indefinida**, e o
    fator correspondente simplesmente não se materializa.
    """
    if denominador <= NEUTRO:
        return padrao
    return numerador / denominador


def arredondar(valor: float, casas: int) -> float:
    """Arredondamento de saída, aplicado só na borda dos modelos."""
    return round(valor, casas)
