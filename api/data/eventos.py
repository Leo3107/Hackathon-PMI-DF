"""Eventos de risco derivados das transições entre snapshots — §10.1.

`scoreApos` e `deltaScore` nascem em `SEM_RECALCULO` e são preenchidos **em
runtime** pela camada de serviço, recalculando os snapshots que cercam o evento.
Escrevê-los aqui violaria a regra central do dataset.
"""

from __future__ import annotations

from models.enums import FonteId, Severidade, TipoEventoDeRisco
from models.eventos import EventoDeRisco

from ._base import SEM_RECALCULO

__all__ = ["EVENTOS", "EVENTOS_POR_CLIENTE"]


def _evento(
    numero: int,
    cliente_id: str,
    data: str,
    tipo: TipoEventoDeRisco,
    severidade: Severidade,
    titulo: str,
    descricao: str,
    fonte: FonteId,
    evidencia_ids: tuple[str, ...] = (),
) -> EventoDeRisco:
    return EventoDeRisco(
        id=f"EV-{numero:03d}",
        cliente_id=cliente_id,
        data=data,
        tipo=tipo,
        severidade=severidade,
        titulo=titulo,
        descricao=descricao,
        fonte=fonte,
        score_apos=SEM_RECALCULO,
        delta_score=SEM_RECALCULO,
        evidencia_ids=list(evidencia_ids),
    )


EVENTOS: list[EventoDeRisco] = [
    _evento(
        1,
        "cerrado-norte",
        "2026-08-06",
        TipoEventoDeRisco.NOVA_EXECUCAO,
        Severidade.CRITICA,
        "Duas execuções de título ajuizadas por credores distintos",
        "Trading, revenda e banco passam a executar simultaneamente: o número de credores "
        "distintos sobe de 1 para 3 e aciona o sinal de pluralidade.",
        FonteId.DATAJUD_CNJ,
        ("EVID-CERRADO-NORTE-DATAJUD-1",),
    ),
    _evento(
        2,
        "cerrado-norte",
        "2026-08-21",
        TipoEventoDeRisco.DIVIDA_ATIVA,
        Severidade.ALTA,
        "Nova inscrição em dívida ativa da União — R$ 800.000",
        "Dívida ativa na PGFN sobe de R$ 1.150.000 para R$ 1.950.000 e aciona o fator "
        "`divida_ativa_crescente`.",
        FonteId.PGFN,
        ("EVID-CERRADO-NORTE-PGFN-1",),
    ),
    _evento(
        3,
        "cerrado-norte",
        "2026-09-02",
        TipoEventoDeRisco.MUDANCA_CLIMATICA,
        Severidade.MEDIA,
        "CONAB revisa quebra de safra do sul do MA para 19%",
        "Revisão do levantamento de safra combinada a déficit de precipitação de 31%.",
        FonteId.CONAB,
        ("EVID-CERRADO-NORTE-CONAB-1", "EVID-CERRADO-NORTE-INMET-1"),
    ),
    _evento(
        4,
        "cerrado-norte",
        "2026-09-08",
        TipoEventoDeRisco.ATRASO_PAGAMENTO,
        Severidade.ALTA,
        "Atraso médio sobe de 3 para 11 dias",
        "Piora do comportamento de pagamento na janela de 60 dias entre os dois snapshots.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-CERRADO-NORTE-INTERNO-1",),
    ),
    _evento(
        5,
        "barra-do-ipe",
        "2026-08-24",
        TipoEventoDeRisco.EMBARGO_AMBIENTAL,
        Severidade.CRITICA,
        "Termo de embargo do IBAMA sobre a matrícula 14.702, dada em hipoteca",
        "O bem oferecido em garantia passa a ter excussão inviabilizada: gatilho de veto "
        "`VETO_EMBARGO_GARANTIA`.",
        FonteId.IBAMA,
        ("EVID-BARRA-DO-IPE-IBAMA-2",),
    ),
    _evento(
        6,
        "barra-do-ipe",
        "2026-06-30",
        TipoEventoDeRisco.MUDANCA_CLIMATICA,
        Severidade.MEDIA,
        "ZARC da soja em Querência elevado de moderado para alto",
        "Reclassificação do zoneamento agrícola para a janela de plantio 2026/27.",
        FonteId.MAPA_ZARC,
        ("EVID-BARRA-DO-IPE-ZARC-1",),
    ),
    _evento(
        7,
        "ponta-verde",
        "2026-06-23",
        TipoEventoDeRisco.PEDIDO_RJ,
        Severidade.CRITICA,
        "Recuperação judicial distribuída",
        "Pedido de recuperação judicial distribuído na 3ª Vara Cível de Rio Verde/GO.",
        FonteId.DJE,
        ("EVID-PONTA-VERDE-DJE-1",),
    ),
    _evento(
        8,
        "ponta-verde",
        "2026-07-08",
        TipoEventoDeRisco.PEDIDO_RJ,
        Severidade.CRITICA,
        "Recuperação judicial deferida — Stay Period iniciado",
        "Deferimento do processamento. Suspensão de 180 dias das execuções contra o devedor.",
        FonteId.DJE,
        ("EVID-PONTA-VERDE-DJE-1",),
    ),
    _evento(
        9,
        "ponta-verde",
        "2026-02-09",
        TipoEventoDeRisco.COVENANT_ROMPIDO,
        Severidade.ALTA,
        "Endividamento líquido acima de 3,0× EBITDA",
        "Covenant COV-PV-2 apurado em 5,4× o EBITDA — inadimplência técnica.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-PONTA-VERDE-INTERNO-1",),
    ),
    _evento(
        10,
        "rio-formoso",
        "2026-09-03",
        TipoEventoDeRisco.PEDIDO_FALENCIA,
        Severidade.CRITICA,
        "Pedido de falência distribuído por credor quirografário",
        "1ª Vara Cível de Barreiras/BA. O score não se move (D2 já saturada em 0), "
        "mas o rating cai por veto.",
        FonteId.DJE,
        ("EVID-RIO-FORMOSO-DJE-1",),
    ),
    _evento(
        11,
        "rio-formoso",
        "2026-06-18",
        TipoEventoDeRisco.ALTERACAO_SOCIETARIA,
        Severidade.MEDIA,
        "Saída do sócio majoritário",
        "Alteração de controle registrada em junta comercial durante período de crise.",
        FonteId.REDESIM,
        ("EVID-RIO-FORMOSO-REDESIM-1",),
    ),
    _evento(
        12,
        "alto-paranaiba",
        "2026-08-12",
        TipoEventoDeRisco.NOVA_EXECUCAO,
        Severidade.ALTA,
        "Duas execuções ajuizadas em 30 dias — três credores distintos",
        "Risco jurídico recém-surgido num cliente de rating A: a dimensão jurídica cai para 330.",
        FonteId.DATAJUD_CNJ,
        ("EVID-ALTO-PARANAIBA-DATAJUD-1",),
    ),
    _evento(
        13,
        "tres-barras",
        "2026-06-27",
        TipoEventoDeRisco.COVENANT_ROMPIDO,
        Severidade.ALTA,
        "Apólice de seguro agrícola não renovada — covenant COV-TB-2",
        "Inadimplência técnica sem nenhum atraso financeiro: zero dia de atraso na série inteira.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-TRES-BARRAS-INTERNO-2",),
    ),
    _evento(
        14,
        "tres-barras",
        "2026-03-19",
        TipoEventoDeRisco.COVENANT_ROMPIDO,
        Severidade.ALTA,
        "Endividamento total em 2,53× o patrimônio — covenant COV-TB-1",
        "O patrimônio líquido cai e o endividamento ultrapassa o limite contratual de 2,5×.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-TRES-BARRAS-INTERNO-2",),
    ),
    _evento(
        15,
        "ipanema-graos",
        "2026-07-02",
        TipoEventoDeRisco.NOVA_EXECUCAO,
        Severidade.ALTA,
        "Quarto credor distinto ajuíza execução",
        "O rjIndex chega a 75 sem que o cliente atrase um único título com a Krill Tech.",
        FonteId.DATAJUD_CNJ,
        ("EVID-IPANEMA-GRAOS-DATAJUD-2",),
    ),
    _evento(
        16,
        "ipanema-graos",
        "2026-05-14",
        TipoEventoDeRisco.DIVIDA_ATIVA,
        Severidade.MEDIA,
        "Parcelamento fiscal rompido",
        "Rompimento de parcelamento com a PGFN — sinal de RJ e penalidade fiscal.",
        FonteId.PGFN,
        ("EVID-IPANEMA-GRAOS-PGFN-1",),
    ),
    _evento(
        17,
        "serra-do-urucui",
        "2026-06-05",
        TipoEventoDeRisco.MUDANCA_CLIMATICA,
        Severidade.ALTA,
        "ZARC da soja em Uruçuí elevado para crítico",
        "A dimensão agroclimática cai de 1000 para 118 ao longo da série.",
        FonteId.MAPA_ZARC,
        ("EVID-SERRA-DO-URUCUI-ZARC-2",),
    ),
    _evento(
        18,
        "dois-irmaos",
        "2026-07-01",
        TipoEventoDeRisco.ALTERACAO_SOCIETARIA,
        Severidade.MEDIA,
        "Saída de sócio majoritário registrada na Redesim",
        "Ruptura societária com deterioração comportamental já em curso.",
        FonteId.REDESIM,
        ("EVID-DOIS-IRMAOS-REDESIM-1",),
    ),
    _evento(
        19,
        "santa-vitoria-arroz",
        "2026-05-28",
        TipoEventoDeRisco.DIVIDA_ATIVA,
        Severidade.ALTA,
        "Execuções fiscais alcançam 54% da exposição",
        "R$ 3.700.000 em execuções fiscais contra R$ 6.800.000 de exposição: teto "
        "`TETO_EXEC_FISCAL` passa a valer e o rating cai de B para C.",
        FonteId.PGFN,
        ("EVID-SANTA-VITORIA-ARROZ-PGFN-2",),
    ),
    _evento(
        20,
        "coop-vale-do-ivai",
        "2026-02-26",
        TipoEventoDeRisco.CADASTRAL,
        Severidade.ALTA,
        "CNDT positiva — débito trabalhista de R$ 2.150.000",
        "Débito supera 15% do patrimônio declarado: teto `TETO_CNDT`.",
        FonteId.TST_CNDT,
        ("EVID-COOP-VALE-DO-IVAI-CNDT-2",),
    ),
    _evento(
        21,
        "joao-camargo",
        "2026-05-20",
        TipoEventoDeRisco.ATRASO_PAGAMENTO,
        Severidade.ALTA,
        "Terceira renegociação em 12 meses",
        "Espiral de produtor PF descapitalizado; sem via de RJ, o risco migra para execução "
        "individual.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-JOAO-CAMARGO-INTERNO-1",),
    ),
    _evento(
        22,
        "maria-nogueira",
        "2026-02-20",
        TipoEventoDeRisco.RECALCULO,
        Severidade.BAIXA,
        "Contratação de seguro agrícola para a safra 2025/26",
        "Ponto de inflexão da trajetória: a proteção climática passa a valer.",
        FonteId.INTERNO_KRILLTECH,
        ("EVID-MARIA-NOGUEIRA-INTERNO-1",),
    ),
    _evento(
        23,
        "frutivale",
        "2026-07-09",
        TipoEventoDeRisco.RECALCULO,
        Severidade.BAIXA,
        "Baixa de protesto em cartório",
        "Protestos ativos caem de 3 para 2 — a série 'melhorando' com ruído real.",
        FonteId.CARTORIO_PROTESTO,
        ("EVID-FRUTIVALE-CENPROT-1",),
    ),
    _evento(
        24,
        "santa-ines",
        "2026-06-25",
        TipoEventoDeRisco.CADASTRAL,
        Severidade.BAIXA,
        "Atualização de endereço de correspondência na Receita Federal",
        "Evento informativo, sem efeito sobre o score.",
        FonteId.RECEITA_FEDERAL,
        ("EVID-SANTA-INES-RFB-1",),
    ),
    _evento(
        25,
        "chapadao-algodoeira",
        "2026-08-05",
        TipoEventoDeRisco.NOVO_PROTESTO,
        Severidade.MEDIA,
        "Terceiro protesto ativo",
        "Protestos em 12 meses chegam a 3 e acionam `protesto_recorrente`.",
        FonteId.CARTORIO_PROTESTO,
        ("EVID-CHAPADAO-ALGODOEIRA-CENPROT-1",),
    ),
    _evento(
        26,
        "vale-do-piquiri",
        "2026-05-11",
        TipoEventoDeRisco.NOVA_EXECUCAO,
        Severidade.MEDIA,
        "Primeira execução de título em 36 meses",
        "Execução de R$ 520.000 por credor único — disputa bilateral, não pluralidade.",
        FonteId.DATAJUD_CNJ,
        ("EVID-VALE-DO-PIQUIRI-DATAJUD-1",),
    ),
]


def _agrupar() -> dict[str, list[EventoDeRisco]]:
    agrupados: dict[str, list[EventoDeRisco]] = {}
    for evento in EVENTOS:
        agrupados.setdefault(evento.cliente_id, []).append(evento)
    for lista in agrupados.values():
        lista.sort(key=lambda e: e.data, reverse=True)
    return agrupados


EVENTOS_POR_CLIENTE: dict[str, list[EventoDeRisco]] = _agrupar()
