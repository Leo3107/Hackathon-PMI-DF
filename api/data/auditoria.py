"""Trilha de auditoria inicial — §13.

Nove registros pré-existentes, para que a tela de auditoria não nasça vazia.
`scoreNoMomento` e `ratingNoMomento` **são escritos** aqui e isso não viola a
regra central: são o registro histórico do que o analista viu, não uma avaliação
do motor. Devem coincidir com o recálculo do snapshot correspondente — é o que
`test_auditoria_coerente` verifica, com tolerância de 0,5 ponto.
"""

from __future__ import annotations

from models.enums import CodigoRecomendacao, DecisaoAnalista, Rating
from models.eventos import RegistroAuditoria

from .clientes import CLIENTES

__all__ = ["REGISTROS", "SNAPSHOT_DO_REGISTRO"]

_NOME_POR_ID = {cliente.id: cliente.razao_social for cliente in CLIENTES}

#: Índice (0-based) do snapshot que o analista consultou. Não é campo do modelo:
#: existe para que o teste saiba contra o que comparar.
SNAPSHOT_DO_REGISTRO: dict[str, int] = {
    "AUD-001": 4,
    "AUD-002": 5,
    "AUD-003": 5,
    "AUD-004": 4,
    "AUD-005": 4,
    "AUD-006": 4,
    "AUD-007": 3,
    "AUD-008": 5,
    "AUD-009": 3,
}


def _registro(
    identificador: str,
    cliente_id: str,
    analista: str,
    data_hora: str,
    score: float,
    rating: Rating,
    recomendacao: CodigoRecomendacao,
    decisao: DecisaoAnalista,
    justificativa: str,
    divergiu: bool,
) -> RegistroAuditoria:
    return RegistroAuditoria(
        id=identificador,
        cliente_id=cliente_id,
        cliente_nome=_NOME_POR_ID[cliente_id],
        analista=analista,
        data_hora=data_hora,
        score_no_momento=score,
        rating_no_momento=rating,
        recomendacao_gerada=recomendacao,
        decisao_analista=decisao,
        justificativa=justificativa,
        divergiu_da_recomendacao=divergiu,
    )


REGISTROS: list[RegistroAuditoria] = [
    _registro(
        "AUD-001",
        "cerrado-norte",
        "Ana Beatriz Carvalho",
        "2026-07-15T09:12:00",
        712.0,
        Rating.B,
        CodigoRecomendacao.APROVAR_COM_RESTRICOES,
        DecisaoAnalista.APROVAR_COM_RESTRICOES,
        "Rating B com exposição em risco em cenário de RJ acima de 40%. Mantenho o "
        "fornecimento condicionado ao reforço da CPR registrada até o fim de agosto.",
        False,
    ),
    _registro(
        "AUD-002",
        "cerrado-norte",
        "Ana Beatriz Carvalho",
        "2026-09-12T16:40:00",
        604.0,
        Rating.B,
        CodigoRecomendacao.APROVAR_COM_RESTRICOES,
        DecisaoAnalista.SUSPENDER,
        "Apesar do rating B, a queda de 108 pontos em 60 dias, concentrada em execuções de "
        "credores distintos, indica crise de liquidez. Suspendo nova exposição a prazo até o "
        "vencimento de 2026-10-28 e condiciono a retomada à baixa de ao menos duas execuções.",
        True,
    ),
    _registro(
        "AUD-003",
        "barra-do-ipe",
        "Rodrigo Tsuda",
        "2026-09-12T11:05:00",
        571.6,
        Rating.D,
        CodigoRecomendacao.SUSPENDER_EXPOSICAO,
        DecisaoAnalista.SUSPENDER,
        "Score calculado 571,6 (C), mas o embargo do IBAMA recai sobre a matrícula 14.702, "
        "dada em hipoteca. Garantia juridicamente comprometida: acompanho o veto.",
        False,
    ),
    _registro(
        "AUD-004",
        "ponta-verde",
        "Helena Prado",
        "2026-07-16T08:30:00",
        333.5,
        Rating.D,
        CodigoRecomendacao.SUSPENDER_EXPOSICAO,
        DecisaoAnalista.RECUSAR,
        "Recuperação judicial deferida em 2026-07-08, Stay Period ativo. Recuso qualquer nova "
        "operação e habilito o crédito, separando a alienação fiduciária extraconcursal.",
        False,
    ),
    _registro(
        "AUD-005",
        "tres-barras",
        "Rodrigo Tsuda",
        "2026-07-15T14:22:00",
        805.5,
        Rating.A,
        CodigoRecomendacao.APROVAR_COM_REVISAO_DE_LIMITE,
        DecisaoAnalista.REVISAR,
        "Nenhum dia de atraso, mas covenant de endividamento rompido e patrimônio líquido em "
        "queda contínua. Prefiro revisar antes de aprovar limite adicional.",
        True,
    ),
    _registro(
        "AUD-006",
        "ipanema-graos",
        "Ana Beatriz Carvalho",
        "2026-07-15T10:18:00",
        681.4,
        Rating.B,
        CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO,
        DecisaoAnalista.APROVAR_COM_RESTRICOES,
        "Paga em dia conosco, mas há quatro credores distintos executando metade da exposição. "
        "Monitoramento não basta: imponho restrição de volume até a baixa de duas execuções.",
        True,
    ),
    _registro(
        "AUD-007",
        "santa-ines",
        "Helena Prado",
        "2026-06-11T15:55:00",
        933.5,
        Rating.A,
        CodigoRecomendacao.APROVAR,
        DecisaoAnalista.APROVAR,
        "Melhor ficha da carteira: certidões negativas, sem litígio em 36 meses e cobertura "
        "extraconcursal de 60%. Aprovo nos termos propostos.",
        False,
    ),
    _registro(
        "AUD-008",
        "rio-formoso",
        "Rodrigo Tsuda",
        "2026-09-12T09:47:00",
        253.6,
        Rating.D,
        CodigoRecomendacao.SUSPENDER_EXPOSICAO,
        DecisaoAnalista.RECUSAR,
        "Pedido de falência distribuído em 2026-09-03, zero garantia extraconcursal e "
        "R$ 11.800.000 integralmente em risco. Recuso e aciono o aval dos sócios.",
        False,
    ),
    _registro(
        "AUD-009",
        "santa-vitoria-arroz",
        "Helena Prado",
        "2026-06-11T13:10:00",
        715.2,
        Rating.C,
        CodigoRecomendacao.APROVAR_COM_RESTRICOES,
        DecisaoAnalista.APROVAR_COM_RESTRICOES,
        "Score B, mas execuções fiscais acima de 50% da exposição impõem teto C. Aprovo com "
        "exigência de certidão de regularidade fiscal a cada 30 dias.",
        False,
    ),
]
