"""Stay Period — Lei 11.101/2005, `specs/02-motor-de-risco.md` §9.

    diasDecorridos  = dataReferencia − dataDeferimento
    diasRestantes   = max(0, 180 + diasProrrogados − diasDecorridos)
    stayPeriodAtivo = diasRestantes > 0

O painel existe para dizer, em cima do calendário, o que a Krill Tech **não
pode** fazer — e o que segue possível porque a alienação fiduciária é
extraconcursal e sobrevive à RJ.
"""

from __future__ import annotations

from datetime import date

from models.avaliacao import StayPeriod
from models.fatos import FatosDoCliente

from .config import ScoringConfig, resolver_config
from .util import dias_entre, para_data, para_data_opcional

__all__ = ["calcular_stay_period"]

_SEM_DIAS: int = 0


def calcular_stay_period(
    fatos: FatosDoCliente,
    config: ScoringConfig | None = None,
    data_referencia: date | None = None,
) -> StayPeriod | None:
    """`None` quando não há RJ deferida — o painel simplesmente não existe."""
    cfg = resolver_config(config)
    rj = fatos.juridico.recuperacao_judicial
    if rj is None:
        return None

    deferimento = para_data_opcional(rj.data_deferimento)
    if deferimento is None:
        return None

    data_ref = data_referencia or para_data(fatos.data_referencia)
    dias_decorridos = dias_entre(deferimento, data_ref)
    dias_restantes = max(
        _SEM_DIAS, cfg.stay_period_dias + rj.dias_prorrogados_stay - dias_decorridos
    )

    return StayPeriod(
        ativo=dias_restantes > _SEM_DIAS,
        data_deferimento=rj.data_deferimento or "",
        dias_decorridos=dias_decorridos,
        dias_restantes=dias_restantes,
        bloqueios=list(cfg.bloqueios_stay_period),
        permitido=list(cfg.permitido_stay_period),
    )
