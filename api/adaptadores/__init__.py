"""Camada de adaptação entre a coleta de dados públicos e o motor de risco.

    Features (39 campos opcionais)  →  FatosDoCliente + RelatorioDeCobertura

Três módulos, com fronteiras rígidas:

- `features_para_fatos` — a tradução. **Pura**, com a política por campo
  declarada em tabela no topo do módulo.
- `cobertura` — o relatório de cobertura por dimensão e por fonte, e a
  renormalização de pesos que implementa a política NEUTRO.
- `porta_coleta` — a **única** fronteira de I/O: warehouse DuckDB em somente
  leitura, sem rede, tolerante à ausência.

Uso típico:

    >>> resultado = adaptar(features, cliente_id="prospect-x",
    ...                     data_referencia="2026-09-12")
    >>> avaliacao = calcular_risco(resultado.fatos, config=resultado.config)

Passar `config=resultado.config` **não é opcional**: sem ele cada dimensão
cega vale 1000 e o sistema dá nota alta a quem não foi olhado.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# `coleta/` é um pacote irmão de `api/`, na raiz do repositório, e não é
# instalado como dependência (é código de outro workstream, versionado junto).
# Esta é a única linha de infraestrutura necessária para que `from coleta.models
# import Features` funcione tanto com `cd api && flask run` quanto com o pytest
# rodado da raiz.
_RAIZ_DO_REPO = _Path(__file__).resolve().parent.parent.parent
if str(_RAIZ_DO_REPO) not in _sys.path:
    _sys.path.append(str(_RAIZ_DO_REPO))

from .cobertura import (
    CampoNaoApurado,
    CoberturaDeDimensao,
    FonteDaColeta,
    Politica,
    RelatorioDeCobertura,
    StatusDimensao,
    config_da_cobertura,
    montar_cobertura,
    pesos_renormalizados,
)
from .features_para_fatos import (
    ResultadoDaAdaptacao,
    adaptar,
    montar_cliente_do_prospect,
)
from .porta_coleta import ColetaDuckDB, PortaDeColeta, coleta_padrao, warehouse_disponivel

__all__ = [
    "adaptar",
    "montar_cliente_do_prospect",
    "ResultadoDaAdaptacao",
    "Politica",
    "StatusDimensao",
    "FonteDaColeta",
    "CampoNaoApurado",
    "CoberturaDeDimensao",
    "RelatorioDeCobertura",
    "montar_cobertura",
    "pesos_renormalizados",
    "config_da_cobertura",
    "PortaDeColeta",
    "ColetaDuckDB",
    "coleta_padrao",
    "warehouse_disponivel",
]
