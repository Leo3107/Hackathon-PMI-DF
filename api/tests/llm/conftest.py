"""Ambiente da suíte da camada de linguagem — `04-camada-llm.md` §6.3.

════════════════════════════════════════════════════════════════════════════════
 SENTINELA DE REDE — nenhum teste desta suíte pode gastar cota
════════════════════════════════════════════════════════════════════════════════

O usuário tem **US$ 10 de saldo** (HANDOFF §3). A fixture `ambiente_sem_rede` é
`autouse`, portanto vale para **todos** os testes deste diretório, e:

- força `LASTRO_LLM_ENGINE=fixture`;
- **remove** `OPENAI_API_KEY` do ambiente do processo de teste;
- zera `LASTRO_LLM_LEDGER_PATH`, para o ledger viver só em memória e nunca
  tocar `api/.lastro/`;
- substitui `openai.OpenAI.__init__` por uma sentinela que **falha o teste** —
  qualquer tentativa de instanciar o cliente real vira `AssertionError`, mesmo
  que alguém mude a seleção de engine por engano.

`test_openai_engine.test_instanciar_o_cliente_real_falha_o_teste` prova que a
sentinela está de pé. Os auxiliares (contexto, `FakeOpenAI`) estão em `apoio.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RAIZ_DA_API = Path(__file__).resolve().parents[2]
if str(_RAIZ_DA_API) not in sys.path:
    sys.path.insert(0, str(_RAIZ_DA_API))

from apoio import (  # noqa: E402
    MENSAGEM_DA_SENTINELA,
    contexto_de,
    ler_apoio,
    nomes_dos_perfis,
)
from llm import ledger as _ledger  # noqa: E402


@pytest.fixture(autouse=True)
def ambiente_sem_rede(monkeypatch):
    """Sem chave, sem disco, sem cliente OpenAI. Vale para toda a suíte."""
    monkeypatch.setenv("LASTRO_LLM_ENGINE", "fixture")
    monkeypatch.setenv("LASTRO_LLM_FIXTURE_FALTANTE", "erro")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LASTRO_LLM_LEDGER_PATH", "")
    monkeypatch.setenv("LASTRO_LLM_BUDGET_USD", "8")
    monkeypatch.setenv("LASTRO_LLM_PRICE_IN_PER_MTOK", "0.25")
    monkeypatch.setenv("LASTRO_LLM_PRICE_OUT_PER_MTOK", "2.00")
    monkeypatch.delenv("LASTRO_LLM_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("LASTRO_LLM_MODEL", raising=False)
    monkeypatch.delenv("LASTRO_LLM_ENABLED", raising=False)

    try:
        import openai
    except ImportError:  # pragma: no cover - sem SDK não há chamada possível
        openai = None
    if openai is not None:

        def _proibido(*_args, **_kwargs):
            raise AssertionError(MENSAGEM_DA_SENTINELA)

        monkeypatch.setattr(openai.OpenAI, "__init__", _proibido)

    _ledger.reiniciar("")
    yield
    _ledger.reiniciar("")


@pytest.fixture
def contexto_moderado():
    return contexto_de("moderado")


@pytest.fixture(params=nomes_dos_perfis())
def nome_do_perfil(request):
    """Parametriza por todas as personas de `tests/fixtures.py`."""
    return request.param


@pytest.fixture(scope="session")
def bloco_da_spec() -> str:
    """O bloco literal da §4.3, base dos dois golden examples."""
    return ler_apoio("contexto/vale-do-araguaia.txt")


@pytest.fixture(scope="session")
def golden_bom() -> str:
    return ler_apoio("golden/parecer-bom.md")


@pytest.fixture(scope="session")
def golden_ruim() -> str:
    return ler_apoio("golden/parecer-ruim.md")
