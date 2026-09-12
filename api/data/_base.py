"""Construtores compartilhados pelas fichas de `api/data/` — `specs/06-dados-simulados.md` §6.

Regra do pacote: **nada aqui importa de `scoring`** e **nada aqui escreve campo
derivado** (score, rating, PD, red flag, recomendação, `natureza` ou
`valorAtualizado` de garantia, `scoreApos`, `deltaScore`). Só fatos.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from models.enums import (
    FonteId,
    StatusParcela,
    TipoGarantia,
    TipoOperacao,
)
from models.eventos import SnapshotHistorico
from models.exposicao import Barter, Garantia, Operacao, Parcela
from models.fatos import Evidencia, FatosDoCliente

from .fontes import ABREVIACAO_FONTE, FONTES_UNIVERSAIS, ROTULOS_FONTE, TIPO_POR_FONTE

__all__ = [
    "DATA_REFERENCIA",
    "DATAS_SNAPSHOT",
    "DATA_AVALIACAO_GARANTIA",
    "PRECO_SACA",
    "montar_operacoes",
    "operacao_proposta",
    "garantia",
    "barter_de",
    "evidencia",
    "evidencias_padrao",
    "serie_de_snapshots",
    "normalizar_documento",
]

#: Data de referência de todo o dataset. O motor nunca lê o relógio.
DATA_REFERENCIA = "2026-09-12"

#: Grade comum de snapshots (§8.1) — a mesma para os 18 clientes de carteira.
DATAS_SNAPSHOT: tuple[str, ...] = (
    "2025-09-15",
    "2025-12-10",
    "2026-03-12",
    "2026-06-10",
    "2026-07-14",
    "2026-09-12",
)

DATA_AVALIACAO_GARANTIA = "2026-07-31"

#: Preços de referência de agosto/2026 usados nas operações de barter (§6.2).
PRECO_SACA: dict[str, float] = {
    "soja": 128.50,
    "milho": 62.00,
    "algodao": 405.00,
    "cafe": 1980.00,
}

_VENCIMENTO_P1 = "2026-10-28"
_VENCIMENTO_P2 = "2026-11-27"
_VENCIMENTO_P3 = "2027-03-30"
_VENCIMENTO_P4 = "2027-06-30"

_DATA_CONTRATACAO_OP1 = "2025-10-15"
_DATA_CONTRATACAO_OP2 = "2026-08-18"

_DESCRICAO_OP1 = "Fornecimento de insumos — saldo da safra 2025/26"
_DESCRICAO_OP3 = "Investimento em máquinas e estrutura"


def _maiusculo(cliente_id: str) -> str:
    return cliente_id.upper()


def _parcela(
    cliente_id: str,
    numero: int,
    vencimento: str,
    valor: float,
    status: StatusParcela,
    dias_atraso: int | None = None,
) -> Parcela:
    return Parcela(
        id=f"PAR-{_maiusculo(cliente_id)}-{numero}",
        vencimento=vencimento,
        valor=valor,
        status=status,
        dias_atraso=dias_atraso,
    )


def montar_operacoes(
    cliente_id: str,
    *,
    p1: float,
    p2: float,
    p3: float,
    p4: float,
    tipo_op2: TipoOperacao,
    descricao_op2: str,
    data_op3: str,
    p0: float = 0.0,
    dias_atraso: int = 0,
    barter: Barter | None = None,
    data_op1: str = _DATA_CONTRATACAO_OP1,
    data_op2: str = _DATA_CONTRATACAO_OP2,
) -> list[Operacao]:
    """As três operações canônicas da §6.2, com o cronograma P0..P4.

    `saldoDevedor` de cada operação é, por construção, a soma exata das suas
    parcelas em aberto — é o que faz `Σ saldoDevedor = exposicaoTotal`.
    """
    sigla = _maiusculo(cliente_id)
    parcelas_op1: list[Parcela] = []
    if p0 > 0.0:
        vencimento_p0 = (
            date.fromisoformat(DATA_REFERENCIA) - timedelta(days=dias_atraso)
        ).isoformat()
        parcelas_op1.append(
            _parcela(cliente_id, 0, vencimento_p0, p0, StatusParcela.EM_ATRASO, dias_atraso)
        )
    parcelas_op1.append(_parcela(cliente_id, 1, _VENCIMENTO_P1, p1, StatusParcela.A_VENCER))

    return [
        Operacao(
            id=f"OP-{sigla}-1",
            tipo=TipoOperacao.VENDA_A_PRAZO,
            descricao=_DESCRICAO_OP1,
            saldo_devedor=p0 + p1,
            data_contratacao=data_op1,
            parcelas=parcelas_op1,
        ),
        Operacao(
            id=f"OP-{sigla}-2",
            tipo=tipo_op2,
            descricao=descricao_op2,
            saldo_devedor=p2 + p3,
            data_contratacao=data_op2,
            parcelas=[
                _parcela(cliente_id, 2, _VENCIMENTO_P2, p2, StatusParcela.A_VENCER),
                _parcela(cliente_id, 3, _VENCIMENTO_P3, p3, StatusParcela.A_VENCER),
            ],
            barter=barter,
        ),
        Operacao(
            id=f"OP-{sigla}-3",
            tipo=TipoOperacao.VENDA_A_PRAZO,
            descricao=_DESCRICAO_OP3,
            saldo_devedor=p4,
            data_contratacao=data_op3,
            parcelas=[_parcela(cliente_id, 4, _VENCIMENTO_P4, p4, StatusParcela.A_VENCER)],
        ),
    ]


def operacao_proposta(cliente_id: str, valor: float, descricao: str) -> list[Operacao]:
    """Operação **proposta**, não contratada — a exposição pretendida de um prospect (§11).

    Sem ela a exposição seria zero e os fatores de D7 penalizariam todo prospect
    igualmente, o que distorceria a análise. A UI a rotula como "operação em análise".
    """
    sigla = _maiusculo(cliente_id)
    return [
        Operacao(
            id=f"OP-{sigla}-1",
            tipo=TipoOperacao.VENDA_A_PRAZO,
            descricao=descricao,
            saldo_devedor=valor,
            data_contratacao=DATA_REFERENCIA,
            parcelas=[
                _parcela(cliente_id, 1, _VENCIMENTO_P3, valor, StatusParcela.A_VENCER)
            ],
        )
    ]


def barter_de(
    cultura: str,
    sacas: float,
    preco: float,
    cpr_vinculada_id: str | None = None,
) -> Barter:
    """Bloco de barter. Sem `cprVinculadaId` o fator `barter_sem_lastro` dispara."""
    return Barter(
        cultura=cultura,
        sacas_prometidas=sacas,
        preco_referencia_saca=preco,
        cpr_vinculada_id=cpr_vinculada_id,
    )


def garantia(
    cliente_id: str,
    numero: int,
    tipo: TipoGarantia,
    descricao: str,
    valor_declarado: float,
    *,
    registrada: bool = True,
    data_avaliacao: str = DATA_AVALIACAO_GARANTIA,
    bem_embargado: bool | None = None,
) -> Garantia:
    """Garantia com **apenas** os campos de fato — `natureza` e `valorAtualizado`
    são derivados por `models.tabelas` e recalculados pelo motor."""
    campos: dict[str, Any] = {
        "id": f"GAR-{_maiusculo(cliente_id)}-{numero}",
        "tipo": tipo,
        "descricao": descricao,
        "valor_declarado": valor_declarado,
        "registrada": registrada,
        "data_avaliacao": data_avaliacao,
    }
    if bem_embargado is not None:
        campos["bem_embargado"] = bem_embargado
    return Garantia(**campos)


# ---------------------------------------------------------------------------
# Evidências
# ---------------------------------------------------------------------------

_FATORES_EXTRAS: dict[FonteId, tuple[str, ...]] = {
    FonteId.REDESIM: ("alteracao_societaria", "saida_socio_majoritario", "qsa_estavel"),
    FonteId.CARTORIO_PROTESTO: ("protestos", "protesto_recorrente"),
    FonteId.DJE: ("rj_distribuida", "pedido_falencia"),
}

_DATA_CONSULTA_PADRAO = "2026-09-11"


def evidencia(
    cliente_id: str,
    fonte: FonteId,
    titulo: str,
    resumo: str,
    fatores: tuple[str, ...] | list[str],
    *,
    numero: int = 1,
    data_consulta: str = _DATA_CONSULTA_PADRAO,
    data_documento: str | None = None,
) -> Evidencia:
    protocolo = f"{_maiusculo(cliente_id)}-{numero:02d}"
    return Evidencia(
        id=f"EVID-{_maiusculo(cliente_id)}-{ABREVIACAO_FONTE[fonte]}-{numero}",
        fonte=fonte,
        nome_fonte=ROTULOS_FONTE[fonte],
        tipo=TIPO_POR_FONTE[fonte],
        titulo=titulo,
        resumo=resumo,
        data_consulta=data_consulta,
        data_documento=data_documento,
        url_ficticia=(
            f"https://consultas.simuladas.lastro.local/{fonte.value.lower()}/{protocolo}"
        ),
        fatores_relacionados=list(fatores),
    )


def evidencias_padrao(
    cliente_id: str,
    *,
    resumos: dict[FonteId, str],
    redesim: bool = True,
    protesto: bool = True,
    dje: str | None = None,
    extras: tuple[Evidencia, ...] = (),
) -> list[Evidencia]:
    """As onze consultas universais (§10.3), mais Redesim, CENPROT, DJE e nominadas.

    Toda evidência nasce com `simulada = True` — o selo de consulta simulada é
    obrigatório em toda a aplicação (invariante I10).
    """
    itens: list[Evidencia] = []
    for fonte, titulo, fatores in FONTES_UNIVERSAIS:
        itens.append(
            evidencia(
                cliente_id,
                fonte,
                titulo,
                resumos.get(fonte, "Consulta simulada sem ocorrência relevante no período."),
                fatores,
            )
        )
    if redesim:
        itens.append(
            evidencia(
                cliente_id,
                FonteId.REDESIM,
                "Atos societários registrados na junta comercial",
                resumos.get(
                    FonteId.REDESIM, "Quadro societário sem alteração relevante no período."
                ),
                _FATORES_EXTRAS[FonteId.REDESIM],
            )
        )
    if protesto:
        itens.append(
            evidencia(
                cliente_id,
                FonteId.CARTORIO_PROTESTO,
                "Certidão da Central de Protestos",
                resumos.get(FonteId.CARTORIO_PROTESTO, "Protestos ativos apurados na consulta."),
                _FATORES_EXTRAS[FonteId.CARTORIO_PROTESTO],
            )
        )
    if dje is not None:
        itens.append(
            evidencia(
                cliente_id,
                FonteId.DJE,
                "Publicação no Diário da Justiça Eletrônico",
                dje,
                _FATORES_EXTRAS[FonteId.DJE],
            )
        )
    itens.extend(extras)
    return itens


# ---------------------------------------------------------------------------
# Série histórica
# ---------------------------------------------------------------------------


def _mesclar(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    resultado = dict(base)
    for chave, valor in patch.items():
        atual = resultado.get(chave)
        if isinstance(valor, dict) and isinstance(atual, dict):
            resultado[chave] = {**atual, **valor}
        else:
            resultado[chave] = valor
    return resultado


def serie_de_snapshots(
    fatos: FatosDoCliente, ajustes: list[dict[str, Any]]
) -> list[SnapshotHistorico]:
    """Seis snapshots na grade da §8.1; o último é **idêntico** a `fatos` (V38).

    `ajustes` traz cinco dicionários (T1..T5) com os campos que divergem do
    estado atual, aninhados por bloco de `FatosDoCliente`. Tudo o que não é
    citado repete o valor de T6 — é o que isola a variação do score nos fatos
    de risco, como a decomposição de delta precisa (§8.1, regra 2 e 3).
    """
    if len(ajustes) != len(DATAS_SNAPSHOT) - 1:
        raise ValueError("São necessários exatamente 5 ajustes, de T1 a T5.")

    referencia = fatos.model_dump()
    snapshots: list[SnapshotHistorico] = []
    for data, patch in zip(DATAS_SNAPSHOT, ajustes):
        dados = _mesclar(referencia, patch)
        dados["data_referencia"] = data
        snapshots.append(SnapshotHistorico(data=data, fatos=FatosDoCliente(**dados)))
    snapshots.append(SnapshotHistorico(data=DATAS_SNAPSHOT[-1], fatos=fatos))
    return snapshots


def normalizar_documento(documento: str) -> str:
    """Mantém apenas os dígitos — a busca por documento ignora a pontuação."""
    return "".join(caractere for caractere in documento if caractere.isdigit())
