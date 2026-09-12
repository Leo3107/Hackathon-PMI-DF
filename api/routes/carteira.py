"""`/api/carteira` — o resumo agregado que abre a aplicação.

**Por que `POST` numa rota de leitura:** o corpo carrega o `EstadoDeSessao`
(D3) — eventos simulados e status de red flag mudam o cálculo de cada cliente
e, portanto, mudam o agregado. `GET` é aceito como cortesia e equivale a uma
sessão limpa.
"""

from __future__ import annotations

from flask import Blueprint

from .comum import (
    data_de_referencia,
    repositorio,
    resposta,
    serializar,
    sessao_da_requisicao,
)
from .servico_carteira import avaliar_carteira, montar_resumo, zarc_por_cliente

carteira_bp = Blueprint("carteira", __name__)


@carteira_bp.post("/api/carteira")
@carteira_bp.get("/api/carteira")
def obter_carteira():
    repo = repositorio()
    linhas = avaliar_carteira(repo, sessao_da_requisicao())
    resumo = montar_resumo(
        linhas,
        repo.listar_alertas(),
        data_de_referencia(),
        zarc_por_cliente(repo),
    )
    return resposta(serializar(resumo))
