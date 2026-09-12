"""Carregador do dataset real — Tarefa 2.

Substitui os 18 clientes inventados à mão por `data/mock/features_agro_mock.csv`
(3.000 CNPJs de soja, 12 UFs, 6 perfis de risco — dado público simulado, mas
estruturalmente real: mesmas colunas de `coleta/models.py:Features`).

Lê o CSV **uma única vez**, na importação deste módulo, e monta para cada
linha:

- uma `Features` (mesma que a coleta pública devolveria);
- um `Cliente` mínimo, via `adaptadores.montar_cliente_do_prospect` — o mesmo
  caminho que a due diligence de CNPJ avulso já usa;
- um `FatosDoCliente` base (sem operação nem garantia), via
  `adaptadores.adaptar` — o mesmo adaptador, reaproveitado.

Razão social não existe no CSV. `_razao_social_sintetica` gera uma etiqueta
estável a partir do documento e do perfil, sempre marcada `[DADO SIMULADO]` —
nunca finge ser nome real.

Exposição, garantias e histórico de pagamento **não estão aqui**: são
declaração do analista (`repository.declaracoes`, Tarefa 3), aplicadas em
runtime por `RepositorioEmMemoria`, não neste carregamento estático.
"""

from __future__ import annotations

import csv
import logging
import sys as _sys
from pathlib import Path as _Path

# `coleta/` é pacote irmão de `api/`, na raiz do repositório — mesma
# infraestrutura de `adaptadores/__init__.py` e `tests/test_coleta_integrada.py`.
_RAIZ_DO_REPO = _Path(__file__).resolve().parent.parent.parent
if str(_RAIZ_DO_REPO) not in _sys.path:
    _sys.path.append(str(_RAIZ_DO_REPO))

from adaptadores import adaptar, montar_cliente_do_prospect  # noqa: E402
from coleta.models import Features  # noqa: E402
from models.cliente import Cliente  # noqa: E402
from models.fatos import FatosDoCliente  # noqa: E402

__all__ = [
    "DATA_REFERENCIA",
    "CAMINHO_CSV",
    "FEATURES_POR_CLIENTE",
    "PERFIL_POR_CLIENTE",
    "PROSPECTS",
    "FATOS_POR_CLIENTE",
    "normalizar_documento",
]

_log = logging.getLogger(__name__)

#: Mesma data de referência usada no resto do protótipo (specs `06`).
DATA_REFERENCIA = "2026-09-12"

CAMINHO_CSV = _RAIZ_DO_REPO / "data" / "mock" / "features_agro_mock.csv"

#: Colunas do CSV que não são campos de `Features` — dado de mock/validação.
_COLUNAS_IGNORADAS = {"perfil", "alvo_sintetico"}

_CAMPOS_BOOLEANOS = {
    "flag_divida_previdenciaria",
    "flag_divida_fgts",
    "flag_situacao_irregular",
    "flag_cnae_agro",
    "flag_embargo_ativo",
}

#: `Int64` no esquema — inteiros que toleram nulo.
_CAMPOS_INTEIROS = {
    "n_inscricoes",
    "idade_empresa_meses",
    "n_filiais",
    "n_socios",
    "n_empresas_do_socio",
    "n_empresas_do_socio_com_divida_ativa",
    "n_empresas_do_socio_inaptas",
    "n_autos_infracao",
    "n_contratos_municipio",
    "acionamentos_proagro_municipio",
    "dias_secos_consecutivos_max",
    "n_protestos_ativos",
    "dias_desde_protesto_mais_recente",
    "n_cartorios_distintos",
}

_CAMPOS_FLUTUANTES = {
    "divida_ativa_total",
    "divida_ativa_ajuizada",
    "delta_divida_2_trimestres",
    "capital_social",
    "valor_multas_ambientais",
    "area_embargada_ha",
    "volume_credito_rural_municipio",
    "ticket_medio_municipio",
    "credito_por_hectare_municipio",
    "produtividade_municipal_cultura",
    "desvio_produtividade_vs_media_5a",
    "area_plantada_municipio_cultura",
    "precipitacao_acumulada_ciclo",
    "precipitacao_vs_normal_climatologica",
    "anomalia_na_fase_critica",
    "valor_total_protestado",
}

#: Rótulo curto do perfil, para compor a etiqueta sintética de razão social.
_ROTULO_DO_PERFIL: dict[str, str] = {
    "limpo": "sem apontamentos públicos",
    "divida_ativa": "dívida ativa na União",
    "passivo_ambiental_auto": "auto de infração ambiental",
    "situacao_irregular": "situação cadastral irregular",
    "grupo_societario": "grupo societário com dívida",
    "passivo_ambiental_embargo": "embargo ambiental",
}


def normalizar_documento(documento: str) -> str:
    return "".join(caractere for caractere in documento if caractere.isdigit())


def _valor_tipado(bruto: str, campo: str) -> object:
    bruto = bruto.strip()
    if bruto == "":
        return None
    if campo in _CAMPOS_BOOLEANOS:
        return bruto == "True"
    if campo in _CAMPOS_INTEIROS:
        return int(float(bruto))
    if campo in _CAMPOS_FLUTUANTES:
        return float(bruto)
    return bruto


def _razao_social_sintetica(documento: str, perfil: str) -> str:
    """Etiqueta estável e claramente sintética — razão social não existe no CSV.

    Determinística (mesmo documento → mesma etiqueta) e nunca finge ser nome
    real: o prefixo `[DADO SIMULADO]` é obrigatório e os últimos dígitos do
    documento substituem qualquer identidade inventada.
    """
    digitos = normalizar_documento(documento)
    rotulo = _ROTULO_DO_PERFIL.get(perfil, perfil.replace("_", " ") or "perfil não identificado")
    return f"[DADO SIMULADO] Produtor rural CNPJ ...{digitos[-6:]} — {rotulo}"


def _features_da_linha(linha: dict[str, str]) -> tuple[Features, str]:
    kwargs: dict[str, object] = {}
    for campo, bruto in linha.items():
        if campo is None or campo in _COLUNAS_IGNORADAS:
            continue
        kwargs[campo] = _valor_tipado(bruto, campo)
    perfil = (linha.get("perfil") or "").strip()
    kwargs["documento"] = normalizar_documento(str(kwargs.get("documento") or ""))
    kwargs["razao_social"] = _razao_social_sintetica(kwargs["documento"], perfil)
    return Features(**kwargs), perfil


def _carregar() -> tuple[
    dict[str, Features], dict[str, str], list[Cliente], dict[str, FatosDoCliente]
]:
    features_por_cliente: dict[str, Features] = {}
    perfil_por_cliente: dict[str, str] = {}
    clientes: list[Cliente] = []
    fatos_por_cliente: dict[str, FatosDoCliente] = {}

    try:
        arquivo = CAMINHO_CSV.open(encoding="utf-8", newline="")
    except OSError:
        _log.warning(
            "features_agro_mock.csv indisponível em %s; dataset real fica vazio.",
            CAMINHO_CSV,
        )
        return features_por_cliente, perfil_por_cliente, clientes, fatos_por_cliente

    with arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for linha in leitor:
            features, perfil = _features_da_linha(linha)
            documento = features.documento

            features_por_cliente[documento] = features
            perfil_por_cliente[documento] = perfil

            cliente = montar_cliente_do_prospect(
                features, cliente_id=documento, data_referencia=DATA_REFERENCIA
            )
            if features.cultura_referencia:
                # Só descritivo (concentração por cultura da carteira). O fato
                # de risco `FatosAgro.culturas` continua vazio de propósito —
                # ver a nota "AGROCLIMÁTICO" em `features_para_fatos.py`: a
                # cultura de referência não é prova de monocultura apurada.
                cliente = cliente.model_copy(
                    update={"culturas": [features.cultura_referencia.capitalize()]}
                )
            clientes.append(cliente)

            resultado = adaptar(
                features, cliente_id=documento, data_referencia=DATA_REFERENCIA
            )
            fatos_por_cliente[documento] = resultado.fatos

    return features_por_cliente, perfil_por_cliente, clientes, fatos_por_cliente


FEATURES_POR_CLIENTE, PERFIL_POR_CLIENTE, PROSPECTS, FATOS_POR_CLIENTE = _carregar()
