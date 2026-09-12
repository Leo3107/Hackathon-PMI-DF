"""Tabelas canônicas compartilhadas entre o contrato de dados e o motor.

Os valores vêm de `specs/02-motor-de-risco.md` §10. Vivem aqui — e não em
`scoring/config.py` — porque `models.exposicao` precisa derivar `natureza` e
`valorAtualizado` de uma `Garantia` sem depender do pacote `scoring`
(dependência circular). `scoring/config.py` importa estas tabelas e as expõe
como os padrões sobrescrevíveis de `ScoringConfig`: o número existe em um
lugar só.
"""

from __future__ import annotations

from .enums import NaturezaGarantia, TipoGarantia

__all__ = [
    "NATUREZA_POR_TIPO_GARANTIA",
    "NATUREZA_CPR_FINANCEIRA_SEM_REGISTRO",
    "HAIRCUT_POR_TIPO_GARANTIA",
    "natureza_da_garantia",
    "valor_atualizado_da_garantia",
]

#: Classificação jurídica por tipo (02 §10). CPR financeira só é
#: extraconcursal quando **registrada** — ver `natureza_da_garantia`.
NATUREZA_POR_TIPO_GARANTIA: dict[TipoGarantia, NaturezaGarantia] = {
    TipoGarantia.ALIENACAO_FIDUCIARIA: NaturezaGarantia.EXTRACONCURSAL,
    TipoGarantia.CPR_FINANCEIRA: NaturezaGarantia.EXTRACONCURSAL,
    TipoGarantia.CPR_FISICA: NaturezaGarantia.CONCURSAL,
    TipoGarantia.PENHOR_SAFRA: NaturezaGarantia.CONCURSAL,
    TipoGarantia.PENHOR_MAQUINA: NaturezaGarantia.CONCURSAL,
    TipoGarantia.HIPOTECA: NaturezaGarantia.CONCURSAL,
    TipoGarantia.AVAL_FIANCA: NaturezaGarantia.CONCURSAL,
}

#: CPR financeira sem registro perde a vinculação específica e volta ao concurso.
NATUREZA_CPR_FINANCEIRA_SEM_REGISTRO: NaturezaGarantia = NaturezaGarantia.CONCURSAL

#: Deságio aplicado ao valor declarado para obter o valor atualizado (02 §10).
#: `PENHOR_MAQUINA` não é tabelado na spec; adotado 35%, entre o penhor de
#: safra (40%) e a alienação fiduciária de máquina (20%).
HAIRCUT_POR_TIPO_GARANTIA: dict[TipoGarantia, float] = {
    TipoGarantia.ALIENACAO_FIDUCIARIA: 0.20,
    TipoGarantia.CPR_FINANCEIRA: 0.10,
    TipoGarantia.CPR_FISICA: 0.25,
    TipoGarantia.PENHOR_SAFRA: 0.40,
    TipoGarantia.PENHOR_MAQUINA: 0.35,
    TipoGarantia.HIPOTECA: 0.30,
    TipoGarantia.AVAL_FIANCA: 0.60,
}


def natureza_da_garantia(
    tipo: TipoGarantia,
    registrada: bool,
    tabela: dict[TipoGarantia, NaturezaGarantia] | None = None,
    natureza_cpr_sem_registro: NaturezaGarantia | None = None,
) -> NaturezaGarantia:
    """Natureza jurídica derivada do tipo — nunca digitada no dataset."""
    tabela = tabela if tabela is not None else NATUREZA_POR_TIPO_GARANTIA
    sem_registro = (
        natureza_cpr_sem_registro
        if natureza_cpr_sem_registro is not None
        else NATUREZA_CPR_FINANCEIRA_SEM_REGISTRO
    )
    if tipo is TipoGarantia.CPR_FINANCEIRA and not registrada:
        return sem_registro
    return tabela[tipo]


def valor_atualizado_da_garantia(
    tipo: TipoGarantia,
    valor_declarado: float,
    haircuts: dict[TipoGarantia, float] | None = None,
) -> float:
    """`valorDeclarado × (1 − haircut do tipo)` (02 §10)."""
    tabela = haircuts if haircuts is not None else HAIRCUT_POR_TIPO_GARANTIA
    return valor_declarado * (1.0 - tabela[tipo])
