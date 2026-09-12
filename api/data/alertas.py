"""Central de alertas — §10.2.

Um alerta por evento ocorrido nos **últimos 120 dias** (a partir de 2026-05-15).
`clienteNome` é desnormalizado de propósito: a central de alertas não pode
depender de join. `impacto` vem parametrizado com os números do cliente e
`acaoRecomendada` é sempre acionável.
"""

from __future__ import annotations

from models.enums import Severidade
from models.eventos import Alerta

from .clientes import CLIENTES
from .eventos import EVENTOS

__all__ = ["ALERTAS", "DATA_DE_CORTE"]

#: 120 dias antes de 2026-09-12.
DATA_DE_CORTE = "2026-05-15"

#: Alertas posteriores a esta data nascem não lidos.
_DATA_NAO_LIDO = "2026-08-01"

_NOME_POR_ID = {cliente.id: cliente.razao_social for cliente in CLIENTES}

#: `id do evento -> (impacto, ação recomendada)`.
_TEXTOS: dict[str, tuple[str, str]] = {
    "EV-001": (
        "R$ 22.400.000 de exposição passam a conviver com três credores distintos em "
        "execução; o score cai 73 pontos só por conta do bloco jurídico.",
        "Suspender nova exposição a prazo e exigir baixa de ao menos duas execuções antes "
        "do vencimento de 2026-10-28.",
    ),
    "EV-002": (
        "Dívida ativa sobe para R$ 1.950.000 (8,7% da exposição) e o crescimento em 90 dias "
        "aciona penalidade adicional de 90 pontos na dimensão fiscal.",
        "Solicitar comprovação de parcelamento ativo junto à PGFN em até 15 dias.",
    ),
    "EV-003": (
        "Quebra de safra regional revisada para 19% com déficit de precipitação de 31%: a "
        "dimensão agroclimática fecha em 549.",
        "Condicionar novo custeio à contratação de seguro agrícola para a safra 2026/27.",
    ),
    "EV-004": (
        "Atraso médio de 11 dias sobre R$ 22.400.000 de exposição, com R$ 1.500.000 já "
        "vencidos há 27 dias.",
        "Acionar cobrança da parcela PAR-CERRADO-NORTE-0 e reavaliar o limite de "
        "R$ 23.000.000 em 30 dias.",
    ),
    "EV-005": (
        "R$ 9.200.000 de exposição passam a contar com garantia juridicamente comprometida; "
        "a classificação final cai de C para D por regra de negócio.",
        "Suspender qualquer nova exposição a prazo e exigir substituição da hipoteca da "
        "matrícula 14.702 por alienação fiduciária sobre bem não embargado.",
    ),
    "EV-006": (
        "Reclassificação do ZARC para alto eleva a penalidade agroclimática em 110 pontos "
        "sobre uma monocultura de soja sem seguro.",
        "Exigir contratação de seguro agrícola como condição de liberação do custeio 2026/27.",
    ),
    "EV-007": (
        "R$ 18.300.000 de exposição entram em concurso de credores; apenas R$ 4.160.000 "
        "atualizados de alienação fiduciária permanecem extraconcursais.",
        "Habilitar o crédito no processo e separar imediatamente o crédito extraconcursal "
        "da frota alienada fiduciariamente.",
    ),
    "EV-008": (
        "Stay Period de 180 dias iniciado: execuções, protestos e cobrança judicial ficam "
        "suspensos até 2027-01-04. R$ 14.140.000 sem proteção em cenário de RJ.",
        "Excutir a alienação fiduciária (R$ 5.200.000 declarados) e acompanhar o plano; "
        "nenhuma nova venda a prazo.",
    ),
    "EV-010": (
        "Pedido de falência contra cliente com R$ 11.800.000 de exposição e zero garantia "
        "extraconcursal: 100% em risco em cenário de liquidação.",
        "Recusar qualquer nova operação, habilitar o crédito e acionar o aval dos sócios.",
    ),
    "EV-011": (
        "Saída do sócio majoritário em plena crise: dimensão cadastral cai para 630 e o "
        "sinal de alteração de administrador entra no rjIndex.",
        "Exigir repactuação do aval com os novos controladores em até 30 dias.",
    ),
    "EV-012": (
        "Duas execuções novas somam R$ 2.400.000 (37,5% da exposição de R$ 6.400.000) e "
        "derrubam 98,6 pontos em 60 dias, ainda que o rating siga A.",
        "Reduzir o limite de R$ 7.000.000 e condicionar novas entregas à comprovação de "
        "garantia adicional.",
    ),
    "EV-013": (
        "Apólice não renovada sobre 2.300 ha financiados: covenant rompido e vigente com "
        "R$ 7.100.000 de exposição e nenhum dia de atraso.",
        "Notificar o rompimento do covenant e exigir renovação da apólice em 15 dias, sob "
        "pena de vencimento antecipado.",
    ),
    "EV-015": (
        "Quatro credores distintos executando R$ 7.900.000 — 50% da exposição. Risco de RJ "
        "em 12 meses sobe para 40,60% com PD de apenas 9,85%.",
        "Monitoramento intensivo semanal e antecipação da exigência de CPR adicional "
        "registrada sobre a safra 2026/27.",
    ),
    "EV-017": (
        "ZARC crítico sobre 4.800 ha sem irrigação nem seguro: a dimensão agroclimática cai "
        "para 118 e puxa o score para 592,3.",
        "Exigir seguro agrícola ou CPR física adicional antes de qualquer nova entrega de insumo.",
    ),
    "EV-018": (
        "Alteração de controle com R$ 10.400.000 de exposição e dimensão cadastral em 630.",
        "Repactuar a CPR financeira com os novos sócios e revisar o limite de R$ 10.600.000.",
    ),
    "EV-019": (
        "R$ 3.700.000 em execuções fiscais contra R$ 6.800.000 de exposição: crédito fiscal "
        "com preferência limita o rating final a C.",
        "Aprovar apenas com restrições, exigindo certidão de regularidade fiscal a cada "
        "30 dias.",
    ),
    "EV-021": (
        "Terceira renegociação em 12 meses com 42% de pontualidade; PD 12m de 31,26% sobre "
        "R$ 3.900.000 de exposição.",
        "Suspender novas entregas e exigir reforço de garantia real antes de qualquer "
        "repactuação.",
    ),
    "EV-023": (
        "Baixa de protesto reduz a penalidade jurídica em 45 pontos; o cliente segue em "
        "trajetória de melhora com cobertura total de 128,2%.",
        "Registrar a baixa na ficha e manter o limite atual de R$ 6.000.000.",
    ),
    "EV-024": (
        "Atualização cadastral sem efeito sobre o score de 917,9.",
        "Apenas registrar; nenhuma ação de crédito necessária.",
    ),
    "EV-025": (
        "Terceiro protesto ativo sobre a maior exposição da carteira (R$ 41.000.000), com "
        "R$ 23.700.000 sem cobertura extraconcursal.",
        "Exigir esclarecimento do protesto em 10 dias e reavaliar a concentração da carteira "
        "em Primavera do Leste/MT.",
    ),
}


def _alerta(numero: int, evento_id: str) -> Alerta:
    evento = next(item for item in EVENTOS if item.id == evento_id)
    impacto, acao = _TEXTOS[evento_id]
    return Alerta(
        id=f"ALT-{numero:03d}",
        cliente_id=evento.cliente_id,
        cliente_nome=_NOME_POR_ID[evento.cliente_id],
        data=evento.data,
        severidade=evento.severidade,
        titulo=evento.titulo,
        descricao=evento.descricao,
        impacto=impacto,
        acao_recomendada=acao,
        lido=evento.data <= _DATA_NAO_LIDO,
        evento_id=evento.id,
    )


ALERTAS: list[Alerta] = [
    _alerta(numero, evento_id)
    for numero, evento_id in enumerate(
        sorted(
            (evento.id for evento in EVENTOS if evento.data >= DATA_DE_CORTE),
            key=lambda identificador: (
                next(e for e in EVENTOS if e.id == identificador).data,
                identificador,
            ),
            reverse=True,
        ),
        start=1,
    )
]

#: Cobertura das quatro severidades na central.
SEVERIDADES_PRESENTES: set[Severidade] = {alerta.severidade for alerta in ALERTAS}
