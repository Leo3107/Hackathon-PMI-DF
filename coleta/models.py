"""Schema de saida da camada de coleta.

Todo campo e opcional por construcao: `build_features` devolve `None` quando
nao ha dado, nunca levanta excecao por ausencia. O scorecard a jusante decide
o que fazer com o `None` -- imputar, penalizar ou ignorar.
"""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class Features(BaseModel):
    """Dicionario de features de um documento (CNPJ, e CPF quando houver)."""

    # ---- identificacao ----
    documento: str
    cnpj_basico: str | None = None
    razao_social: str | None = None
    uf: str | None = None
    municipio_ibge: str | None = None
    cultura_referencia: str | None = None
    gerado_em: dt.datetime = Field(default_factory=dt.datetime.now)
    fontes_disponiveis: list[str] = Field(default_factory=list)

    # ---- fonte 1: PGFN ----
    divida_ativa_total: float | None = None
    divida_ativa_ajuizada: float | None = None
    n_inscricoes: int | None = None
    delta_divida_2_trimestres: float | None = None
    flag_divida_previdenciaria: bool | None = None
    flag_divida_fgts: bool | None = None

    # ---- fonte 2: Receita Federal ----
    idade_empresa_meses: int | None = None
    capital_social: float | None = None
    porte: str | None = None
    natureza_juridica: str | None = None
    situacao_cadastral: str | None = None
    flag_situacao_irregular: bool | None = None
    cnae_principal: str | None = None
    flag_cnae_agro: bool | None = None
    n_filiais: int | None = None
    n_socios: int | None = None

    # ---- fonte 2b: grafo societario ----
    n_empresas_do_socio: int | None = None
    n_empresas_do_socio_com_divida_ativa: int | None = None
    n_empresas_do_socio_inaptas: int | None = None

    # ---- fonte 3: IBAMA ----
    n_autos_infracao: int | None = None
    valor_multas_ambientais: float | None = None
    flag_embargo_ativo: bool | None = None
    area_embargada_ha: float | None = None

    # ---- fonte 4: BCB / MDCR ----
    volume_credito_rural_municipio: float | None = None
    n_contratos_municipio: int | None = None
    ticket_medio_municipio: float | None = None
    credito_por_hectare_municipio: float | None = None
    acionamentos_proagro_municipio: int | None = None

    # ---- fonte 5: IBGE / SIDRA ----
    produtividade_municipal_cultura: float | None = None
    desvio_produtividade_vs_media_5a: float | None = None
    area_plantada_municipio_cultura: float | None = None

    # ---- fonte 6: clima ----
    precipitacao_acumulada_ciclo: float | None = None
    precipitacao_vs_normal_climatologica: float | None = None
    dias_secos_consecutivos_max: int | None = None
    anomalia_na_fase_critica: float | None = None

    # ---- fonte 7: protestos ----
    n_protestos_ativos: int | None = None
    valor_total_protestado: float | None = None
    dias_desde_protesto_mais_recente: int | None = None
    n_cartorios_distintos: int | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
