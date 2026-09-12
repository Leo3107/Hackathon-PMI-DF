"""Torna `models` e `scoring` importáveis independentemente de onde o pytest roda.

`npm run test:api` executa `cd api && .venv/Scripts/python -m pytest -q`, o que
já coloca `api/` no `sys.path`. Rodar a suíte a partir da raiz do repositório,
porém, não colocaria — e o motor deixaria de ser importável por um detalhe de
invocação. Esta é a única linha de infraestrutura que a suíte precisa.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ_DA_API = Path(__file__).resolve().parent.parent

if str(_RAIZ_DA_API) not in sys.path:
    sys.path.insert(0, str(_RAIZ_DA_API))
