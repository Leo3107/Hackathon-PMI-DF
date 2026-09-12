"""Blueprints HTTP do Lastro.

Um blueprint por área da interface, todos prefixados com `/api/` no próprio
`@bp.route` — os caminhos são **idênticos** aos do proxy do Next
(`web/app/api/**`), o que faz `web/lib/api/cliente.ts` funcionar sem tradução
de rota nos dois modos de origem.

| Rota | Verbos | Corpo | Resposta |
|---|---|---|---|
| `/api/carteira` | POST · GET | `{sessao}` | `ResumoCarteira` |
| `/api/clientes` | POST · GET | `{sessao}` | `ClienteAvaliado[]` |
| `/api/clientes/<id>` | GET | — | `Cliente` |
| `/api/clientes/<id>/avaliacao` | POST · GET | `{sessao}` | `AvaliacaoDeRisco` |
| `/api/clientes/<id>/comparacao` | POST · GET | `{periodo, sessao}` | `ComparacaoDeAvaliacoes` |
| `/api/clientes/<id>/historico` | GET | — | `SnapshotHistorico[]` |
| `/api/clientes/<id>/eventos` | POST · GET | `{sessao}` | `EventoDeRisco[]` |
| `/api/clientes/<id>/simular-evento` | POST | `{sessao, tipo}` | `RespostaSimulacao` |
| `/api/alertas` | POST · GET | `{sessao}` | `Alerta[]` |
| `/api/auditoria` | GET | — | `RegistroAuditoria[]` |
| `/api/auditoria` | POST | `NovoRegistroAuditoria` | `RegistroAuditoria` (201) |
| `/api/due-diligence` | POST | `{documento}` | `RespostaDueDiligence` |
"""

from __future__ import annotations

from flask import Flask

from .alertas import alertas_bp
from .auditoria import auditoria_bp
from .carteira import carteira_bp
from .clientes import clientes_bp
from .due_diligence import due_diligence_bp

__all__ = ["BLUEPRINTS", "registrar_blueprints"]

BLUEPRINTS = (
    carteira_bp,
    clientes_bp,
    alertas_bp,
    auditoria_bp,
    due_diligence_bp,
)


def registrar_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
