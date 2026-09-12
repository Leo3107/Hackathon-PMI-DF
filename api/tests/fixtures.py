"""Perfis sintéticos de `FatosDoCliente` para a suíte do motor (§14 da spec 02).

**Só fatos brutos.** Nenhum score, rating, PD ou red flag é escrito aqui — tudo
é derivado por `scoring.calcular_risco`. É a mesma regra que vale para
`api/data/`: se um valor pode ser calculado, ele não existe no fixture.

Os perfis cobrem as personas que a spec exige provar: excelente, moderado, em
deterioração ao longo de snapshots, crítico, veto de embargo ambiental sobre
bem dado em garantia, RJ em curso com Stay Period ativo, produtor rural PF não
elegível a RJ (Lei 14.112/2020), inadimplência técnica sem nenhum atraso
financeiro, e o par que prova a independência dos eixos (PD moderado com RJ
alto, PD alto com RJ baixo).
"""

from __future__ import annotations

from collections.abc import Callable

from models.enums import (
    FonteId,
    RiscoZarc,
    SituacaoCar,
    SituacaoRfb,
    StatusParcela,
    TipoEvidencia,
    TipoGarantia,
    TipoOperacao,
    TipoPessoa,
)
from models.fatos import (
    CovenantRompido,
    Evidencia,
    FatosAgro,
    FatosAmbientais,
    FatosCadastrais,
    FatosDoCliente,
    FatosFiscais,
    FatosInternos,
    FatosJuridicos,
    RecuperacaoJudicial,
)
from models.exposicao import Barter, Garantia, Operacao, Parcela

#: Data de referência de toda a suíte. O motor nunca lê o relógio.
DATA_REFERENCIA = "2026-09-12"

__all__ = [
    "DATA_REFERENCIA",
    "PERFIS",
    "SERIES",
    "todos_os_perfis",
    "todas_as_series",
    "cliente_excelente",
    "cliente_moderado",
    "cliente_em_deterioracao",
    "serie_em_deterioracao",
    "cliente_critico",
    "cliente_com_veto_ambiental",
    "cliente_em_rj_com_stay_period",
    "cliente_pf_nao_elegivel_rj",
    "cliente_inadimplencia_tecnica",
    "cliente_pd_moderado_rj_alto",
    "cliente_pd_alto_rj_baixo",
]


# ---------------------------------------------------------------------------
# Construtores auxiliares
# ---------------------------------------------------------------------------


def _parcela(
    identificador: str,
    vencimento: str,
    valor: float,
    status: StatusParcela = StatusParcela.A_VENCER,
    dias_atraso: int | None = None,
) -> Parcela:
    return Parcela(
        id=identificador,
        vencimento=vencimento,
        valor=valor,
        status=status,
        dias_atraso=dias_atraso,
    )


def _operacao(
    identificador: str,
    saldo_devedor: float,
    data_contratacao: str,
    parcelas: list[Parcela],
    tipo: TipoOperacao = TipoOperacao.VENDA_A_PRAZO,
    descricao: str = "Fornecimento de insumos — safra 2026/27",
    barter: Barter | None = None,
) -> Operacao:
    return Operacao(
        id=identificador,
        tipo=tipo,
        descricao=descricao,
        saldo_devedor=saldo_devedor,
        data_contratacao=data_contratacao,
        parcelas=parcelas,
        barter=barter,
    )


def _garantia(
    identificador: str,
    tipo: TipoGarantia,
    valor_declarado: float,
    descricao: str = "",
    registrada: bool = True,
    bem_embargado: bool | None = None,
) -> Garantia:
    return Garantia(
        id=identificador,
        tipo=tipo,
        valor_declarado=valor_declarado,
        descricao=descricao,
        registrada=registrada,
        data_avaliacao=DATA_REFERENCIA,
        bem_embargado=bem_embargado,
    )


def _evidencia(
    identificador: str,
    fonte: FonteId,
    nome_fonte: str,
    tipo: TipoEvidencia,
    titulo: str,
    fatores: list[str],
    data_consulta: str = DATA_REFERENCIA,
) -> Evidencia:
    return Evidencia(
        id=identificador,
        fonte=fonte,
        nome_fonte=nome_fonte,
        tipo=tipo,
        titulo=titulo,
        resumo=titulo,
        data_consulta=data_consulta,
        fatores_relacionados=fatores,
    )


def _cronograma(prefixo: str, parcela: float) -> list[Parcela]:
    """Três parcelas a vencer: dentro de 90 dias, depois e na safra seguinte."""
    return [
        _parcela(f"{prefixo}-1", "2026-10-20", parcela),
        _parcela(f"{prefixo}-2", "2027-01-15", parcela),
        _parcela(f"{prefixo}-3", "2027-04-10", parcela),
    ]


# ---------------------------------------------------------------------------
# 1 · Excelente — rating A
# ---------------------------------------------------------------------------


def cliente_excelente() -> FatosDoCliente:
    """Agrícola do Cerrado: paga em dia, diversificada, sobrecolateralizada."""
    return FatosDoCliente(
        cliente_id="cli-excelente",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=0.0,
            atraso_medio_dias_90d=0.0,
            pior_atraso_dias_12m=2.0,
            pct_titulos_pagos_em_dia_12m=0.99,
            renegociacoes_12m=0,
            sem_atraso_relevante_24m=True,
        ),
        juridico=FatosJuridicos(sem_litigio_36m=True),
        fiscal=FatosFiscais(todas_certidoes_negativas=True, crf_fgts_regular=True),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.MODERADO,
            quebra_safra_regional_pct=4.0,
            desvio_precipitacao_pct=-8.0,
            produtividade_vs_media_regional_pct=12.0,
            area_total_ha=6200.0,
            area_irrigada_ha=1800.0,
            seguro_agricola_vigente=True,
            safra_referencia="2025/26",
            culturas=["Soja", "Milho safrinha", "Algodão"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=22.0,
            capital_social=14_000_000.0,
            qsa_estavel_5anos=True,
            cnae_compativel=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.ATIVO_REGULAR),
        operacoes=[
            _operacao(
                "op-exc-1",
                8_000_000.0,
                "2018-03-14",
                _cronograma("pc-exc", 2_700_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-exc-1",
                TipoGarantia.ALIENACAO_FIDUCIARIA,
                8_000_000.0,
                "Alienação fiduciária de frota de colheitadeiras",
            ),
            _garantia(
                "gar-exc-2",
                TipoGarantia.PENHOR_SAFRA,
                3_000_000.0,
                "Penhor de safra de soja 2026/27",
            ),
        ],
        limite_aprovado=12_000_000.0,
        patrimonio_declarado=48_000_000.0,
        faturamento_estimado_anual=39_000_000.0,
    )


# ---------------------------------------------------------------------------
# 2 · Moderado — rating B
# ---------------------------------------------------------------------------


def cliente_moderado() -> FatosDoCliente:
    """Atrasos pontuais, uma execução isolada, cobertura parcial."""
    return FatosDoCliente(
        cliente_id="cli-moderado",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=13.0,
            atraso_medio_dias_90d=11.0,
            pior_atraso_dias_12m=26.0,
            pct_titulos_pagos_em_dia_12m=0.74,
            renegociacoes_12m=2,
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=1,
            execucoes_titulo_90d=1,
            valor_total_em_execucao=420_000.0,
            credores_distintos_executando=1,
            protestos_ativos=2,
            protestos_12m=2,
            credores_protestantes_180d=1,
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=310_000.0,
            divida_ativa_pgfn_90d_atras=260_000.0,
            crf_fgts_regular=True,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.ALTO,
            quebra_safra_regional_pct=14.0,
            desvio_precipitacao_pct=-18.0,
            produtividade_vs_media_regional_pct=-9.0,
            area_total_ha=2400.0,
            area_irrigada_ha=0.0,
            seguro_agricola_vigente=True,
            safra_referencia="2025/26",
            culturas=["Soja", "Milho safrinha"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=9.0,
            capital_social=2_200_000.0,
            cnae_compativel=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
        operacoes=[
            _operacao(
                "op-mod-1",
                5_000_000.0,
                "2020-09-02",
                _cronograma("pc-mod", 1_700_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-mod-1",
                TipoGarantia.CPR_FINANCEIRA,
                2_000_000.0,
                "CPR financeira registrada — soja 2026/27",
            ),
            _garantia(
                "gar-mod-2",
                TipoGarantia.PENHOR_SAFRA,
                2_500_000.0,
                "Penhor de safra",
            ),
        ],
        limite_aprovado=5_500_000.0,
        patrimonio_declarado=9_000_000.0,
        faturamento_estimado_anual=12_000_000.0,
    )


# ---------------------------------------------------------------------------
# 3 · Em deterioração — série de snapshots, B → C
# ---------------------------------------------------------------------------


def _snapshot_em_deterioracao(
    data: str,
    atraso_12m: float,
    atraso_90d: float,
    pior_atraso: float,
    pct_em_dia: float,
    execucoes_12m: int,
    execucoes_90d: int,
    valor_execucao: float,
    protestos: int,
    divida_ativa: float,
    divida_ativa_anterior: float,
    quebra_safra: float,
    desvio_precipitacao: float,
) -> FatosDoCliente:
    """Um instante da série. Só variam os fatos que o briefing narra mudando."""
    return FatosDoCliente(
        cliente_id="cli-deterioracao",
        data_referencia=data,
        interno=FatosInternos(
            atraso_medio_dias_12m=atraso_12m,
            atraso_medio_dias_90d=atraso_90d,
            pior_atraso_dias_12m=pior_atraso,
            pct_titulos_pagos_em_dia_12m=pct_em_dia,
            renegociacoes_12m=1,
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=execucoes_12m,
            execucoes_titulo_90d=execucoes_90d,
            valor_total_em_execucao=valor_execucao,
            credores_distintos_executando=execucoes_12m,
            protestos_ativos=protestos,
            protestos_12m=protestos,
            credores_protestantes_180d=protestos,
            acoes_trabalhistas_transitadas=2,
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=divida_ativa,
            divida_ativa_pgfn_90d_atras=divida_ativa_anterior,
            crf_fgts_regular=False,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.ALTO,
            quebra_safra_regional_pct=quebra_safra,
            desvio_precipitacao_pct=desvio_precipitacao,
            produtividade_vs_media_regional_pct=-20.0,
            area_total_ha=3100.0,
            area_irrigada_ha=0.0,
            seguro_agricola_vigente=False,
            safra_referencia="2025/26",
            culturas=["Soja"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=4.5,
            capital_social=1_500_000.0,
            cnae_compativel=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
        operacoes=[
            _operacao(
                "op-det-1",
                6_400_000.0,
                "2019-07-08",
                _cronograma("pc-det", 2_150_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-det-1",
                TipoGarantia.ALIENACAO_FIDUCIARIA,
                1_500_000.0,
                "Alienação fiduciária de tratores e pulverizadores",
            ),
            _garantia(
                "gar-det-2",
                TipoGarantia.PENHOR_SAFRA,
                2_200_000.0,
                "Penhor de safra de milho",
            ),
        ],
        limite_aprovado=7_000_000.0,
        patrimonio_declarado=3_000_000.0,
        faturamento_estimado_anual=16_000_000.0,
        evidencias=[
            _evidencia(
                "ev-det-1",
                FonteId.DATAJUD_CNJ,
                "DataJud — CNJ",
                TipoEvidencia.PROCESSO,
                "Execuções de título extrajudicial distribuídas contra o cliente",
                ["execucoes_titulo", "aceleracao_judicial", "materialidade_execucao"],
                data_consulta=data,
            ),
            _evidencia(
                "ev-det-2",
                FonteId.PGFN,
                "PGFN — Dívida Ativa da União",
                TipoEvidencia.CERTIDAO,
                "Novas inscrições em dívida ativa",
                ["divida_ativa", "divida_ativa_crescente"],
                data_consulta=data,
            ),
        ],
    )


def serie_em_deterioracao() -> list[FatosDoCliente]:
    """Cinco snapshots em 12 meses: o cliente que cai de B para C.

    Entre um snapshot e outro mudam exatamente os fatos que o briefing cita —
    novas execuções, nova inscrição em dívida ativa, deterioração climática e
    piora do comportamento de pagamento. O delta é calculado da diferença.
    """
    return [
        _snapshot_em_deterioracao(
            "2025-09-15", 6.0, 6.0, 22.0, 0.85, 0, 0, 0.0, 1, 500_000.0, 500_000.0, 13.0, -14.0
        ),
        _snapshot_em_deterioracao(
            "2025-12-15", 6.0, 7.0, 24.0, 0.83, 0, 0, 0.0, 1, 500_000.0, 500_000.0, 14.0, -16.0
        ),
        _snapshot_em_deterioracao(
            "2026-03-16",
            7.0,
            8.0,
            26.0,
            0.80,
            1,
            1,
            180_000.0,
            1,
            500_000.0,
            500_000.0,
            17.0,
            -19.0,
        ),
        _snapshot_em_deterioracao(
            "2026-06-14",
            8.0,
            11.0,
            30.0,
            0.77,
            2,
            1,
            520_000.0,
            2,
            810_000.0,
            500_000.0,
            21.0,
            -23.0,
        ),
        _snapshot_em_deterioracao(
            "2026-09-12",
            9.0,
            19.0,
            41.0,
            0.72,
            4,
            2,
            1_450_000.0,
            3,
            1_260_000.0,
            810_000.0,
            26.0,
            -29.0,
        ),
    ]


def cliente_em_deterioracao() -> FatosDoCliente:
    """O instante mais recente da série — o que a carteira mostra hoje."""
    return serie_em_deterioracao()[-1]


# ---------------------------------------------------------------------------
# 4 · Crítico — rating D sem nenhum veto
# ---------------------------------------------------------------------------


def cliente_critico() -> FatosDoCliente:
    """Inadimplente, executado, com passivo fiscal e quebra de safra severa."""
    return FatosDoCliente(
        cliente_id="cli-critico",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=42.0,
            atraso_medio_dias_90d=68.0,
            pior_atraso_dias_12m=120.0,
            pct_titulos_pagos_em_dia_12m=0.31,
            renegociacoes_12m=3,
            covenants_rompidos=[
                CovenantRompido(
                    id="cov-crit-1",
                    descricao="Endividamento total acima de 2,5× o patrimônio",
                    limite_contratual="2,5×",
                    valor_apurado="3,8×",
                    data_deteccao="2026-07-30",
                )
            ],
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=6,
            execucoes_titulo_90d=3,
            valor_total_em_execucao=3_900_000.0,
            credores_distintos_executando=5,
            protestos_ativos=5,
            protestos_12m=6,
            credores_protestantes_180d=4,
            acoes_trabalhistas_transitadas=3,
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=2_600_000.0,
            divida_ativa_pgfn_90d_atras=1_400_000.0,
            cndt_positiva=True,
            valor_debito_trabalhista=420_000.0,
            crf_fgts_regular=False,
            parcelamento_rompido_12m=True,
            execucoes_fiscais=4,
            valor_execucoes_fiscais=1_800_000.0,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.CRITICO,
            quebra_safra_regional_pct=38.0,
            desvio_precipitacao_pct=-46.0,
            produtividade_vs_media_regional_pct=-27.0,
            area_total_ha=1800.0,
            area_irrigada_ha=0.0,
            seguro_agricola_vigente=False,
            safra_referencia="2025/26",
            culturas=["Soja"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=4.0,
            capital_social=600_000.0,
            alteracao_societaria_180d=True,
            saida_socio_majoritario_12m=True,
            cnae_compativel=False,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(
            auto_infracao_nao_quitado=True,
            situacao_car=SituacaoCar.IRREGULAR,
            sobreposicao_app_ou_reserva=True,
        ),
        operacoes=[
            _operacao(
                "op-crit-1",
                7_200_000.0,
                "2023-11-20",
                [
                    _parcela(
                        "pc-crit-1",
                        "2026-06-10",
                        1_800_000.0,
                        StatusParcela.EM_ATRASO,
                        dias_atraso=94,
                    ),
                    _parcela("pc-crit-2", "2026-10-05", 1_800_000.0),
                    _parcela("pc-crit-3", "2026-11-28", 1_800_000.0),
                ],
                tipo=TipoOperacao.BARTER,
                descricao="Barter de defensivos contra soja — safra 2026/27",
                barter=Barter(
                    cultura="Soja",
                    sacas_prometidas=42_000.0,
                    preco_referencia_saca=128.0,
                ),
            )
        ],
        garantias=[
            _garantia(
                "gar-crit-1",
                TipoGarantia.AVAL_FIANCA,
                1_500_000.0,
                "Aval dos sócios",
            )
        ],
        limite_aprovado=7_000_000.0,
        patrimonio_declarado=2_400_000.0,
        faturamento_estimado_anual=8_500_000.0,
    )


# ---------------------------------------------------------------------------
# 5 · Veto de embargo ambiental sobre bem dado em garantia
# ---------------------------------------------------------------------------


def cliente_com_veto_ambiental() -> FatosDoCliente:
    """Score saudável e, ainda assim, classificação final D.

    O embargo do IBAMA recai sobre a fazenda hipotecada: a garantia tem
    excussão inviabilizada, e a regra de negócio rebaixa o rating sem tocar no
    `scoreCalculado`.
    """
    return FatosDoCliente(
        cliente_id="cli-veto-ambiental",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=2.0,
            atraso_medio_dias_90d=2.0,
            pior_atraso_dias_12m=8.0,
            pct_titulos_pagos_em_dia_12m=0.95,
        ),
        juridico=FatosJuridicos(),
        fiscal=FatosFiscais(todas_certidoes_negativas=True),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.MODERADO,
            quebra_safra_regional_pct=6.0,
            desvio_precipitacao_pct=-10.0,
            produtividade_vs_media_regional_pct=4.0,
            area_total_ha=4100.0,
            area_irrigada_ha=900.0,
            seguro_agricola_vigente=True,
            safra_referencia="2025/26",
            culturas=["Algodão", "Soja"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=16.0,
            capital_social=6_000_000.0,
            qsa_estavel_5anos=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(
            embargo_ibama_vigente=True,
            embargo_sobre_imovel_em_garantia=True,
            auto_infracao_nao_quitado=True,
            situacao_car=SituacaoCar.IRREGULAR,
        ),
        operacoes=[
            _operacao(
                "op-veto-1",
                6_000_000.0,
                "2017-05-19",
                _cronograma("pc-veto", 2_000_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-veto-1",
                TipoGarantia.HIPOTECA,
                9_000_000.0,
                "Hipoteca de imóvel rural embargado pelo IBAMA",
                bem_embargado=True,
            ),
            _garantia(
                "gar-veto-2",
                TipoGarantia.ALIENACAO_FIDUCIARIA,
                2_500_000.0,
                "Alienação fiduciária de máquinas",
            ),
        ],
        limite_aprovado=8_000_000.0,
        patrimonio_declarado=26_000_000.0,
        faturamento_estimado_anual=22_000_000.0,
        evidencias=[
            _evidencia(
                "ev-veto-1",
                FonteId.IBAMA,
                "IBAMA — Sistema de embargos",
                TipoEvidencia.CADASTRO,
                "Termo de embargo vigente sobre a matrícula dada em garantia",
                ["embargo_ibama", "VETO_EMBARGO_GARANTIA"],
            )
        ],
    )


# ---------------------------------------------------------------------------
# 6 · RJ em curso com Stay Period ativo
# ---------------------------------------------------------------------------


def cliente_em_rj_com_stay_period() -> FatosDoCliente:
    """RJ deferida em 2026-06-10: Stay Period ainda corre na data de referência."""
    return FatosDoCliente(
        cliente_id="cli-rj",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=28.0,
            atraso_medio_dias_90d=52.0,
            pior_atraso_dias_12m=96.0,
            pct_titulos_pagos_em_dia_12m=0.44,
            renegociacoes_12m=2,
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=4,
            execucoes_titulo_90d=1,
            valor_total_em_execucao=5_100_000.0,
            credores_distintos_executando=6,
            protestos_ativos=7,
            protestos_12m=9,
            credores_protestantes_180d=5,
            recuperacao_judicial=RecuperacaoJudicial(
                data_distribuicao="2026-05-28",
                data_deferimento="2026-06-10",
                dias_prorrogados_stay=0,
            ),
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=3_100_000.0,
            divida_ativa_pgfn_90d_atras=2_900_000.0,
            crf_fgts_regular=False,
            parcelamento_rompido_12m=True,
            execucoes_fiscais=2,
            valor_execucoes_fiscais=900_000.0,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.ALTO,
            quebra_safra_regional_pct=22.0,
            desvio_precipitacao_pct=-25.0,
            produtividade_vs_media_regional_pct=-14.0,
            area_total_ha=5200.0,
            area_irrigada_ha=0.0,
            safra_referencia="2025/26",
            culturas=["Cana-de-açúcar"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=18.0,
            capital_social=9_000_000.0,
            alteracao_societaria_180d=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.ATIVO_REGULAR),
        operacoes=[
            _operacao(
                "op-rj-1",
                12_000_000.0,
                "2016-08-30",
                [
                    _parcela(
                        "pc-rj-1",
                        "2026-04-15",
                        4_000_000.0,
                        StatusParcela.EM_ATRASO,
                        dias_atraso=150,
                    ),
                    _parcela("pc-rj-2", "2026-11-10", 4_000_000.0),
                    _parcela("pc-rj-3", "2027-02-20", 4_000_000.0),
                ],
            )
        ],
        garantias=[
            _garantia(
                "gar-rj-1",
                TipoGarantia.ALIENACAO_FIDUCIARIA,
                5_000_000.0,
                "Alienação fiduciária de colheitadeiras de cana",
            ),
            _garantia(
                "gar-rj-2",
                TipoGarantia.PENHOR_SAFRA,
                6_000_000.0,
                "Penhor de safra — entra no plano com deságio",
            ),
        ],
        limite_aprovado=12_000_000.0,
        patrimonio_declarado=15_000_000.0,
        faturamento_estimado_anual=28_000_000.0,
    )


# ---------------------------------------------------------------------------
# 7 · Produtor rural PF não elegível a RJ (Lei 14.112/2020)
# ---------------------------------------------------------------------------


def cliente_pf_nao_elegivel_rj() -> FatosDoCliente:
    """Mesmos sinais de insolvência coletiva, sem via de RJ.

    Sem dois anos de atividade comprovada e sem livro-caixa digital ou
    inscrição estadual, o risco migra para execução individual: o índice de RJ
    é atenuado, não zerado.
    """
    return FatosDoCliente(
        cliente_id="cli-pf-inelegivel",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=16.0,
            atraso_medio_dias_90d=23.0,
            pior_atraso_dias_12m=54.0,
            pct_titulos_pagos_em_dia_12m=0.62,
            renegociacoes_12m=1,
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=3,
            execucoes_titulo_90d=2,
            valor_total_em_execucao=1_900_000.0,
            credores_distintos_executando=4,
            protestos_ativos=4,
            protestos_12m=5,
            credores_protestantes_180d=3,
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=900_000.0,
            divida_ativa_pgfn_90d_atras=700_000.0,
            parcelamento_rompido_12m=True,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.ALTO,
            quebra_safra_regional_pct=28.0,
            desvio_precipitacao_pct=-31.0,
            produtividade_vs_media_regional_pct=-12.0,
            area_total_ha=980.0,
            area_irrigada_ha=0.0,
            safra_referencia="2025/26",
            culturas=["Arroz irrigado"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=1.5,
            capital_social=0.0,
            cnae_compativel=True,
            possui_livro_caixa_digital=False,
            possui_inscricao_estadual=False,
            anos_atividade_comprovada=1.0,
            tipo_pessoa=TipoPessoa.PF,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.PENDENTE),
        operacoes=[
            _operacao(
                "op-pf-1",
                3_400_000.0,
                "2025-02-11",
                _cronograma("pc-pf", 1_150_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-pf-1",
                TipoGarantia.PENHOR_SAFRA,
                1_800_000.0,
                "Penhor de safra de arroz",
            )
        ],
        limite_aprovado=3_500_000.0,
        patrimonio_declarado=4_200_000.0,
        faturamento_estimado_anual=5_100_000.0,
    )


# ---------------------------------------------------------------------------
# 8 · Inadimplência técnica sem nenhum atraso financeiro
# ---------------------------------------------------------------------------


def cliente_inadimplencia_tecnica() -> FatosDoCliente:
    """A tese do produto: covenant rompido antes do primeiro dia de atraso.

    Pontualidade perfeita, nenhum título vencido, nenhuma ação judicial — e
    ainda assim uma red flag ALTA, porque dois covenants contratuais estão
    rompidos e vigentes.
    """
    return FatosDoCliente(
        cliente_id="cli-inadimplencia-tecnica",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=0.0,
            atraso_medio_dias_90d=0.0,
            pior_atraso_dias_12m=0.0,
            pct_titulos_pagos_em_dia_12m=1.0,
            renegociacoes_12m=0,
            sem_atraso_relevante_24m=True,
            covenants_rompidos=[
                CovenantRompido(
                    id="cov-tec-1",
                    descricao="Endividamento total acima de 2,5× o patrimônio",
                    limite_contratual="2,5×",
                    valor_apurado="3,1×",
                    data_deteccao="2026-08-14",
                ),
                CovenantRompido(
                    id="cov-tec-2",
                    descricao="Índice de cobertura do serviço da dívida abaixo de 1,2",
                    limite_contratual="1,2",
                    valor_apurado="0,9",
                    data_deteccao="2026-08-14",
                ),
            ],
        ),
        juridico=FatosJuridicos(sem_litigio_36m=True),
        fiscal=FatosFiscais(todas_certidoes_negativas=True),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.MODERADO,
            quebra_safra_regional_pct=9.0,
            desvio_precipitacao_pct=-12.0,
            produtividade_vs_media_regional_pct=2.0,
            area_total_ha=2700.0,
            area_irrigada_ha=400.0,
            seguro_agricola_vigente=True,
            safra_referencia="2025/26",
            culturas=["Café"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=13.0,
            capital_social=1_500_000.0,
            qsa_estavel_5anos=True,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.ATIVO_REGULAR),
        operacoes=[
            _operacao(
                "op-tec-1",
                9_500_000.0,
                "2019-01-22",
                _cronograma("pc-tec", 3_200_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-tec-1",
                TipoGarantia.CPR_FINANCEIRA,
                4_000_000.0,
                "CPR financeira registrada — café arábica",
            ),
            _garantia(
                "gar-tec-2",
                TipoGarantia.HIPOTECA,
                3_000_000.0,
                "Hipoteca de fazenda",
            ),
        ],
        limite_aprovado=10_000_000.0,
        patrimonio_declarado=3_400_000.0,
        faturamento_estimado_anual=11_000_000.0,
        evidencias=[
            _evidencia(
                "ev-tec-1",
                FonteId.INTERNO_KRILLTECH,
                "Krill Tech — monitoramento de covenants",
                TipoEvidencia.INTERNO,
                "Apuração trimestral de covenants contratuais",
                ["inadimplencia_tecnica"],
            )
        ],
    )


# ---------------------------------------------------------------------------
# 9 e 10 · Eixos independentes (invariante I5)
# ---------------------------------------------------------------------------


def cliente_pd_moderado_rj_alto() -> FatosDoCliente:
    """Paga a Krill Tech em dia, mas tem muitos credores distintos executando."""
    return FatosDoCliente(
        cliente_id="cli-pd-moderado-rj-alto",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=1.0,
            atraso_medio_dias_90d=1.0,
            pior_atraso_dias_12m=4.0,
            pct_titulos_pagos_em_dia_12m=0.97,
            sem_atraso_relevante_24m=True,
        ),
        juridico=FatosJuridicos(
            execucoes_titulo_12m=4,
            execucoes_titulo_90d=2,
            valor_total_em_execucao=4_200_000.0,
            credores_distintos_executando=6,
            protestos_ativos=4,
            protestos_12m=5,
            credores_protestantes_180d=4,
        ),
        fiscal=FatosFiscais(
            divida_ativa_pgfn=2_300_000.0,
            divida_ativa_pgfn_90d_atras=2_300_000.0,
            parcelamento_rompido_12m=True,
        ),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.ALTO,
            quebra_safra_regional_pct=27.0,
            desvio_precipitacao_pct=-16.0,
            produtividade_vs_media_regional_pct=1.0,
            area_total_ha=3300.0,
            area_irrigada_ha=1200.0,
            seguro_agricola_vigente=True,
            safra_referencia="2025/26",
            culturas=["Soja", "Milho safrinha", "Feijão"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=15.0,
            capital_social=5_000_000.0,
            alteracao_societaria_180d=True,
            qsa_estavel_5anos=False,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(situacao_car=SituacaoCar.ATIVO_REGULAR),
        operacoes=[
            _operacao(
                "op-rjalto-1",
                6_000_000.0,
                "2015-10-05",
                _cronograma("pc-rjalto", 2_000_000.0),
            )
        ],
        garantias=[
            _garantia(
                "gar-rjalto-1",
                TipoGarantia.ALIENACAO_FIDUCIARIA,
                6_500_000.0,
                "Alienação fiduciária de frota",
            )
        ],
        limite_aprovado=8_000_000.0,
        patrimonio_declarado=12_000_000.0,
        faturamento_estimado_anual=18_000_000.0,
    )


def cliente_pd_alto_rj_baixo() -> FatosDoCliente:
    """Inadimplente com a Krill Tech, sem nenhum sinal de insolvência coletiva."""
    return FatosDoCliente(
        cliente_id="cli-pd-alto-rj-baixo",
        data_referencia=DATA_REFERENCIA,
        interno=FatosInternos(
            atraso_medio_dias_12m=38.0,
            atraso_medio_dias_90d=61.0,
            pior_atraso_dias_12m=110.0,
            pct_titulos_pagos_em_dia_12m=0.28,
            renegociacoes_12m=3,
        ),
        juridico=FatosJuridicos(),
        fiscal=FatosFiscais(),
        agro=FatosAgro(
            risco_zarc=RiscoZarc.CRITICO,
            quebra_safra_regional_pct=41.0,
            desvio_precipitacao_pct=-52.0,
            produtividade_vs_media_regional_pct=-33.0,
            area_total_ha=1200.0,
            area_irrigada_ha=0.0,
            safra_referencia="2025/26",
            culturas=["Soja"],
        ),
        cadastral=FatosCadastrais(
            situacao_rfb=SituacaoRfb.ATIVA,
            anos_atividade=2.0,
            capital_social=400_000.0,
            cnae_compativel=False,
            tipo_pessoa=TipoPessoa.PJ,
        ),
        ambiental=FatosAmbientais(
            situacao_car=SituacaoCar.AUSENTE,
            sobreposicao_app_ou_reserva=True,
        ),
        operacoes=[
            _operacao(
                "op-pdalto-1",
                2_000_000.0,
                "2024-06-18",
                [
                    _parcela(
                        "pc-pdalto-1",
                        "2026-05-20",
                        700_000.0,
                        StatusParcela.EM_ATRASO,
                        dias_atraso=115,
                    ),
                    _parcela("pc-pdalto-2", "2026-10-30", 700_000.0),
                    _parcela("pc-pdalto-3", "2027-03-15", 600_000.0),
                ],
            )
        ],
        garantias=[
            _garantia(
                "gar-pdalto-1",
                TipoGarantia.PENHOR_MAQUINA,
                700_000.0,
                "Penhor de trator",
            )
        ],
        limite_aprovado=2_000_000.0,
        patrimonio_declarado=9_000_000.0,
        faturamento_estimado_anual=3_200_000.0,
    )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

#: Perfis de instante único, por nome — a suíte varre todos.
PERFIS: dict[str, Callable[[], FatosDoCliente]] = {
    "excelente": cliente_excelente,
    "moderado": cliente_moderado,
    "em_deterioracao": cliente_em_deterioracao,
    "critico": cliente_critico,
    "veto_ambiental": cliente_com_veto_ambiental,
    "rj_com_stay_period": cliente_em_rj_com_stay_period,
    "pf_nao_elegivel_rj": cliente_pf_nao_elegivel_rj,
    "inadimplencia_tecnica": cliente_inadimplencia_tecnica,
    "pd_moderado_rj_alto": cliente_pd_moderado_rj_alto,
    "pd_alto_rj_baixo": cliente_pd_alto_rj_baixo,
}

#: Séries históricas, por nome — base dos testes de delta (invariante I6).
SERIES: dict[str, Callable[[], list[FatosDoCliente]]] = {
    "em_deterioracao": serie_em_deterioracao,
}


def todos_os_perfis() -> list[tuple[str, FatosDoCliente]]:
    return [(nome, construtor()) for nome, construtor in PERFIS.items()]


def todas_as_series() -> list[tuple[str, list[FatosDoCliente]]]:
    return [(nome, construtor()) for nome, construtor in SERIES.items()]
