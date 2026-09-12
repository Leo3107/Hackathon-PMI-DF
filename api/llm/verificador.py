"""Verificador de fidelidade numérica — a invariante I7 em código.

`specs/04-camada-llm.md` §0 e §4.4. **Este é o mecanismo que impede alucinação
numérica de chegar à tela.** Regra única:

> Número citado no texto que não esteja no contexto invalida a saída do modelo.

O executor roda `verificar_fidelidade_numerica` sobre toda saída do engine
OpenAI. Havendo qualquer violação, o texto é descartado inteiro, o cliente
recebe o evento `substituir` e a narrativa determinística entra no lugar; o
incidente vai para o ledger com `severidade="MAXIMA"`.

O que o verificador **pega**: `17%` no lugar de `17,1%`; `R$ 1,2 milhão`;
`cerca de 30%`; `R$ 2.100.000,00`; qualquer número novo.
O que ele **não pega**: números escritos por extenso ("três execuções"). Por
isso os quatro prompts de sistema proíbem números por palavras e a rubrica do
juiz (§7) cobre o resíduo.

Nota de nomenclatura: a spec chama este módulo `fidelidade.py`. O nome real é
`verificador.py`; a API pública (`extrair_numeros`,
`verificar_fidelidade_numerica`, `contar_palavras`) é a da spec.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover - só para o type checker
    from .contexto import ContextoNarrativo

__all__ = [
    "RE_DATA",
    "RE_NUMERO",
    "RE_ID",
    "RE_LISTA",
    "CONSTANTES",
    "extrair_numeros",
    "verificar_fidelidade_numerica",
    "contar_palavras",
    "TITULOS_DO_PARECER",
]

#: `20/08/2026` — data, comparada inteira, nunca pelos seus três números.
RE_DATA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")

#: Um número com ou sem separador de milhar e com ou sem casa decimal pt-BR.
#: O lookbehind evita casar o sufixo de identificadores como `pd12m` ou `G-01`.
RE_NUMERO = re.compile(
    r"(?<![\w-])[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?|(?<![\w-])[+-]?\d+(?:,\d+)?"
)

#: `E-01`, `G-02` são identificadores de evidência e garantia, não números.
RE_ID = re.compile(r"\b[EG]-\d{2,3}\b")

#: `1. ` no início da linha é marcador de lista numerada, não número citado.
RE_LISTA = re.compile(r"^\s*\d+\.\s", re.MULTILINE)

#: Números que o texto pode usar sem estar no contexto: as janelas temporais do
#: produto, os marcos legais permitidos pelos prompts e os extremos da escala.
#:
#: `90` é acréscimo desta implementação à lista da §4.4: é a janela de
#: monitoramento do produto, presente em `[VARIACAO_90D]` e em `a_vencer_90d`,
#: onde o prefixo `_` impede a extração e geraria falso positivo ao falar de
#: "a vencer em 90 dias". É rótulo de janela, como 6, 12, 24 e 180 — nunca uma
#: grandeza de risco.
CONSTANTES = frozenset(
    {"6", "12", "24", "90", "180", "11.101", "2005", "14.112", "2020", "0", "1000"}
)

#: Os seis títulos de nível 2 exigidos pela §3.a, na ordem.
TITULOS_DO_PARECER: tuple[str, ...] = (
    "## Resumo executivo",
    "## Principais riscos",
    "## Fatores mitigadores",
    "## Análise de garantias",
    "## Recomendação",
    "## Evidências",
)

_SECAO_EVIDENCIAS = "## Evidências"
_RE_MARCADOR = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
_RE_COLCHETES = re.compile(r"\[[^\]\n]{1,40}\]")
_RE_NEGRITO = re.compile(r"\*\*")
_RE_ALFANUMERICO = re.compile(r"[0-9A-Za-zÀ-ÿ]")
_MAIS = "+"
_MENOS = "-"
_ESPACO = " "


def extrair_numeros(texto: str) -> set[str]:
    """Conjunto dos números citados em `texto`, na forma em que aparecem.

    Datas saem inteiras (`11/09/2026`); os demais números saem sem o sinal de
    mais, de modo que `+15,0` e `15,0` sejam a mesma coisa — o contexto escreve
    o impacto de proteção com sinal e a prosa nem sempre o repete.

        >>> sorted(extrair_numeros("Score 604, PD 17,1% em 11/09/2026 [E-01]."))
        ['11/09/2026', '17,1', '604']
    """
    limpo = RE_ID.sub(_ESPACO, RE_LISTA.sub(_ESPACO, texto))
    achados: set[str] = set(RE_DATA.findall(limpo))
    limpo = RE_DATA.sub(_ESPACO, limpo)
    achados |= {encontrado.lstrip(_MAIS) for encontrado in RE_NUMERO.findall(limpo)}
    return achados


def verificar_fidelidade_numerica(
    saida: str,
    contexto: "ContextoNarrativo",
    extras: Iterable[str] = (),
) -> list[str]:
    """Números de `saida` que não existem no contexto. Lista vazia = saída fiel.

    `extras` recebe os números da própria pergunta do analista (§8, caso 9):
    quando ele escreve "o limite de R$ 4.600.000 está alto?", repetir o número
    da pergunta não é invenção.
    """
    permitidos = set(contexto.numeros_permitidos) | CONSTANTES | set(extras)
    return sorted(
        numero
        for numero in extrair_numeros(saida)
        if numero not in permitidos and numero.lstrip(_MENOS) not in permitidos
    )


def contar_palavras(texto: str) -> int:
    """Extensão do parecer pela métrica única da §3.a.

    Descarta a seção `## Evidências`, as linhas de título, os marcadores de
    lista, os ids entre colchetes e os asteriscos de negrito; conta os tokens
    separados por espaço que contenham ao menos uma letra ou dígito.
    """
    corpo = texto.split(_SECAO_EVIDENCIAS)[0]
    linhas = [
        linha for linha in corpo.splitlines() if not linha.lstrip().startswith("#")
    ]
    util = _RE_NEGRITO.sub(
        "", _RE_COLCHETES.sub(_ESPACO, _RE_MARCADOR.sub("", "\n".join(linhas)))
    )
    util = RE_LISTA.sub(_ESPACO, util)
    return sum(1 for token in util.split() if _RE_ALFANUMERICO.search(token))
