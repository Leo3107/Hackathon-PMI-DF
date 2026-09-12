"""Modelo preditivo de PD 12m — regressão logística validada pelo usuário (Tarefa 1).

Fonte dos coeficientes: `data/mock/alvo_coeficientes.json` (raiz do repo).
`alvo_sintetico` é **FABRICADO** — o próprio JSON diz isso, e o aviso é
reexportado aqui em `AVISO` para viajar até `AvaliacaoDeRisco.modeloPd.aviso`
na API. Nunca apresente esta PD como medindo inadimplência real.

    PD12 = sigmoide(intercepto + Σ coeficiente × termo)

Interpretação validada contra a taxa real por perfil (dívida ativa 23,9% vs
24,2% real; limpo 5,2% vs 4,9%; global 9,33% vs 8,93%):

- os termos `log1p_*` de `idade_empresa_meses` e `capital_social` são
  **centrados** numa referência (`referencias_de_centragem`):
  `log1p(valor) − log1p(referência)`;
- o único outro termo `log1p_*` (`divida_ativa_total`) não tem referência
  declarada, o que equivale a uma referência de 0 —
  `log1p(valor) − log1p(0) == log1p(valor)`;
- **nulo entra como 0** em todo termo, antes de qualquer transformação. Esta é
  uma política própria deste modelo estatístico, distinta das políticas
  MAPEADO/NEUTRO/CONSERVADOR/NAO_APURADO de `adaptadores/cobertura.py`, que
  regem os FATOS do motor de regras (score, rating, red flags, vetos). Este
  módulo alimenta só a PD, e só a PD.

`contribuicoes()` é o que torna o modelo explicável: cada linha liga um termo
do modelo a um número de log-odds, exatamente o que separa um modelo estatístico
de uma caixa-preta.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from math import exp, log1p
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:  # `coleta` só existe no sys.path depois que `adaptadores` é
    # importado (ver `adaptadores/__init__.py`); com `from __future__ import
    # annotations` a anotação abaixo nunca é avaliada em runtime, então este
    # módulo não precisa da bootstrap de sys.path para funcionar sozinho.
    from coleta.models import Features

__all__ = [
    "AVISO",
    "INTERCEPTO",
    "COEFICIENTES",
    "REFERENCIAS_DE_CENTRAGEM",
    "Contribuicao",
    "ResultadoModeloPd",
    "contribuicoes",
    "calcular_pd_12m",
    "avaliar_modelo_pd",
]

_log = logging.getLogger(__name__)

#: `data/mock/` é irmão de `api/` na raiz do repositório (mesma convenção de
#: `adaptadores/__init__.py`).
_CAMINHO_COEFICIENTES = (
    Path(__file__).resolve().parents[2] / "data" / "mock" / "alvo_coeficientes.json"
)

#: Cópia de segurança dos mesmos números, para o serviço subir mesmo que o
#: arquivo de demonstração não esteja presente no disco (mesmo espírito de
#: `repository.fonte.carregar_fonte`: degradar, nunca derrubar o processo).
_FALLBACK: dict[str, Any] = {
    "aviso": (
        "alvo_sintetico e FABRICADO. Serve para validar o pipeline, nao para "
        "medir performance. Nao use como inadimplencia real."
    ),
    "coeficientes": {
        "intercepto": -3.8,
        "log1p_divida_ativa_total": 0.2,
        "flag_situacao_irregular": 1.1,
        "n_empresas_do_socio_inaptas": 0.28,
        "n_autos_infracao": 0.14,
        "flag_embargo_ativo": 0.75,
        "log1p_idade_empresa_meses": -0.45,
        "log1p_capital_social": -0.18,
        "desvio_produtividade_vs_media_5a": -0.9,
        "anomalia_na_fase_critica": -0.55,
        "n_protestos_ativos": 0.4,
    },
    "referencias_de_centragem": {"idade_empresa_meses": 240.0, "capital_social": 180000.0},
}


def _carregar() -> dict[str, Any]:
    try:
        texto = _CAMINHO_COEFICIENTES.read_text(encoding="utf-8")
        return json.loads(texto)
    except (OSError, json.JSONDecodeError):
        _log.warning(
            "alvo_coeficientes.json indisponível em %s; usando cópia embutida.",
            _CAMINHO_COEFICIENTES,
        )
        return _FALLBACK


_DADOS = _carregar()
AVISO: str = _DADOS["aviso"]
_BRUTOS: dict[str, float] = dict(_DADOS["coeficientes"])
INTERCEPTO: float = float(_BRUTOS.pop("intercepto"))
#: Só os termos — sem o intercepto, que não é contribuição de fator algum.
COEFICIENTES: dict[str, float] = {chave: float(valor) for chave, valor in _BRUTOS.items()}
REFERENCIAS_DE_CENTRAGEM: dict[str, float] = {
    chave: float(valor) for chave, valor in _DADOS.get("referencias_de_centragem", {}).items()
}

_PREFIXO_LOG1P = "log1p_"


class Contribuicao(NamedTuple):
    """Uma linha da explicação — o que separa este modelo de uma caixa-preta."""

    termo: str
    coeficiente: float
    valor: float
    contribuicao_log_odds: float


@dataclass(frozen=True)
class ResultadoModeloPd:
    """O que a rota precisa para popular `AvaliacaoDeRisco.pd` e `.modeloPd`."""

    pd12: float
    aviso: str = AVISO
    contribuicoes: tuple[Contribuicao, ...] = field(default_factory=tuple)


def _valor_bruto(features: Features, campo: str) -> float:
    """Valor numérico do campo, com **nulo entrando como 0** (política deste modelo)."""
    bruto = getattr(features, campo, None)
    if bruto is None:
        return 0.0
    if isinstance(bruto, bool):
        return 1.0 if bruto else 0.0
    return float(bruto)


def _valor_e_termo(nome_do_coeficiente: str, features: Features) -> tuple[float, float]:
    """`(valor bruto usado, termo já transformado)` para um coeficiente do modelo."""
    if nome_do_coeficiente.startswith(_PREFIXO_LOG1P):
        campo = nome_do_coeficiente[len(_PREFIXO_LOG1P) :]
        valor = _valor_bruto(features, campo)
        referencia = REFERENCIAS_DE_CENTRAGEM.get(campo, 0.0)
        termo = log1p(valor) - log1p(referencia)
        return valor, termo
    valor = _valor_bruto(features, nome_do_coeficiente)
    return valor, valor


def contribuicoes(features: Features) -> list[Contribuicao]:
    """Uma linha por coeficiente do modelo — o que explica a PD na tela."""
    itens: list[Contribuicao] = []
    for termo, coeficiente in COEFICIENTES.items():
        valor, valor_do_termo = _valor_e_termo(termo, features)
        itens.append(
            Contribuicao(
                termo=termo,
                coeficiente=coeficiente,
                valor=valor,
                contribuicao_log_odds=coeficiente * valor_do_termo,
            )
        )
    return itens


def calcular_pd_12m(features: Features) -> float:
    """`sigmoide(intercepto + Σ coeficiente × termo)` — PD em 12 meses, 0..1."""
    log_odds = INTERCEPTO + sum(c.contribuicao_log_odds for c in contribuicoes(features))
    return 1.0 / (1.0 + exp(-log_odds))


def avaliar_modelo_pd(features: Features) -> ResultadoModeloPd:
    """PD12 e as contribuições, num só objeto — o que `scoring.calcular_risco` consome."""
    itens = contribuicoes(features)
    log_odds = INTERCEPTO + sum(c.contribuicao_log_odds for c in itens)
    pd12 = 1.0 / (1.0 + exp(-log_odds))
    return ResultadoModeloPd(pd12=pd12, aviso=AVISO, contribuicoes=tuple(itens))
