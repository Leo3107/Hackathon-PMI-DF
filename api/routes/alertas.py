"""`/api/alertas` — central de alertas (`03-ux-e-telas.md` §7).

`POST` pelo mesmo motivo das demais rotas de leitura (D3): o corpo carrega o
`EstadoDeSessao`. Hoje a sessão não adiciona alertas ao conjunto — o alerta da
simulação ao vivo volta dentro de `RespostaSimulacao.alertaGerado` e é a
interface que o injeta na central — mas o corpo é validado aqui para que o
contrato do verbo seja o mesmo em toda a superfície de leitura.
"""

from __future__ import annotations

from flask import Blueprint

from .comum import lista_serializada, repositorio, resposta, sessao_da_requisicao

alertas_bp = Blueprint("alertas", __name__)


@alertas_bp.post("/api/alertas")
@alertas_bp.get("/api/alertas")
def listar_alertas():
    sessao_da_requisicao()
    return resposta(lista_serializada(repositorio().listar_alertas()))
