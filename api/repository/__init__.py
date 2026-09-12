"""Repositório do Lastro — a ponte entre `data/` (fatos) e `routes/` (HTTP).

    data/ (fatos brutos) → repository/ → scoring.calcular_risco → routes/ → JSON

Nada aqui produz número de risco: o repositório entrega `FatosDoCliente` e
delega o cálculo ao motor. Ver `base.RepositorioLastro` para a interface e
`memoria.RepositorioEmMemoria` para a implementação.

    >>> from repository import RepositorioEmMemoria
    >>> repo = RepositorioEmMemoria()          # carrega `data/` se existir
    >>> isinstance(repo.listar_clientes(), list)
    True
"""

from __future__ import annotations

from .base import ClienteNaoEncontrado, RepositorioLastro
from .declaracoes import (
    DeclaracaoDeOperacao,
    GarantiaDeclarada,
    RepositorioDeDeclaracoes,
)
from .fonte import FonteDeDados, carregar_fonte, fonte_do_modulo, so_digitos
from .memoria import (
    DECISOES_ALINHADAS,
    JANELA_COMPARACAO_DIAS,
    PERIODO_INICIO,
    PERIODOS_DE_COMPARACAO,
    PERIODOS_VALIDOS,
    NovoRegistroAuditoria,
    RepositorioEmMemoria,
    divergiu_da_recomendacao,
)
from .sessao import SESSAO_VAZIA, EstadoDeSessao, EventoSimulado
from .simulacao import (
    ROTULO_DO_EVENTO,
    TIPOS_SIMULAVEIS,
    aplicar_evento,
    aplicar_eventos_simulados,
)

__all__ = [
    "RepositorioLastro",
    "RepositorioEmMemoria",
    "ClienteNaoEncontrado",
    "DeclaracaoDeOperacao",
    "GarantiaDeclarada",
    "RepositorioDeDeclaracoes",
    "FonteDeDados",
    "carregar_fonte",
    "fonte_do_modulo",
    "so_digitos",
    "EstadoDeSessao",
    "EventoSimulado",
    "SESSAO_VAZIA",
    "NovoRegistroAuditoria",
    "DECISOES_ALINHADAS",
    "JANELA_COMPARACAO_DIAS",
    "PERIODOS_DE_COMPARACAO",
    "PERIODOS_VALIDOS",
    "PERIODO_INICIO",
    "divergiu_da_recomendacao",
    "TIPOS_SIMULAVEIS",
    "ROTULO_DO_EVENTO",
    "aplicar_evento",
    "aplicar_eventos_simulados",
]
