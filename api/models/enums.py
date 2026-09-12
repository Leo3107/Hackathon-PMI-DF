"""Enumerações do contrato — valores literais idênticos aos de `specs/01-modelo-de-dados.md`."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "Rating",
    "DimensaoId",
    "Tendencia",
    "Severidade",
    "StatusRedFlag",
    "TipoPessoa",
    "TipoOperacao",
    "TipoGarantia",
    "NaturezaGarantia",
    "EstadoCliente",
    "RiscoZarc",
    "FonteId",
    "CodigoRecomendacao",
    "DecisaoAnalista",
    "OrigemCliente",
    "SituacaoRfb",
    "SituacaoCar",
    "StatusParcela",
    "TipoEvidencia",
    "DirecaoFator",
    "EfeitoVeto",
    "TipoEventoDeRisco",
]


class Rating(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DimensaoId(StrEnum):
    COMPORTAMENTAL = "comportamental"
    JURIDICO = "juridico"
    FISCAL = "fiscal"
    AGROCLIMATICO = "agroclimatico"
    CADASTRAL = "cadastral"
    AMBIENTAL = "ambiental"
    GARANTIAS = "garantias"


class Tendencia(StrEnum):
    MELHORANDO = "melhorando"
    ESTAVEL = "estavel"
    DETERIORANDO = "deteriorando"
    DETERIORACAO_ACELERADA = "deterioracao_acelerada"


class Severidade(StrEnum):
    CRITICA = "CRITICA"
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class StatusRedFlag(StrEnum):
    NOVA = "nova"
    ANALISADA = "analisada"
    RESOLVIDA = "resolvida"


class TipoPessoa(StrEnum):
    PF = "PF"
    PJ = "PJ"


class TipoOperacao(StrEnum):
    VENDA_A_PRAZO = "VENDA_A_PRAZO"
    BARTER = "BARTER"
    CPR = "CPR"


class TipoGarantia(StrEnum):
    ALIENACAO_FIDUCIARIA = "ALIENACAO_FIDUCIARIA"
    CPR_FINANCEIRA = "CPR_FINANCEIRA"
    CPR_FISICA = "CPR_FISICA"
    PENHOR_SAFRA = "PENHOR_SAFRA"
    PENHOR_MAQUINA = "PENHOR_MAQUINA"
    HIPOTECA = "HIPOTECA"
    AVAL_FIANCA = "AVAL_FIANCA"


class NaturezaGarantia(StrEnum):
    """Distinção jurídica decisiva em cenário de RJ. Ver `02-motor-de-risco.md` §10."""

    EXTRACONCURSAL = "EXTRACONCURSAL"
    CONCURSAL = "CONCURSAL"


class EstadoCliente(StrEnum):
    ATIVO = "ATIVO"
    EM_OBSERVACAO = "EM_OBSERVACAO"
    SUSPENSO = "SUSPENSO"
    RJ_EM_CURSO = "RJ_EM_CURSO"
    FALENCIA = "FALENCIA"


class RiscoZarc(StrEnum):
    BAIXO = "baixo"
    MODERADO = "moderado"
    ALTO = "alto"
    CRITICO = "critico"


class FonteId(StrEnum):
    RECEITA_FEDERAL = "RECEITA_FEDERAL"
    REDESIM = "REDESIM"
    DATAJUD_CNJ = "DATAJUD_CNJ"
    DJE = "DJE"
    CARTORIO_PROTESTO = "CARTORIO_PROTESTO"
    PGFN = "PGFN"
    TST_CNDT = "TST_CNDT"
    CAIXA_CRF_FGTS = "CAIXA_CRF_FGTS"
    SICAR = "SICAR"
    IBAMA = "IBAMA"
    CONAB = "CONAB"
    MAPA_ZARC = "MAPA_ZARC"
    INMET = "INMET"
    INTERNO_KRILLTECH = "INTERNO_KRILLTECH"


class CodigoRecomendacao(StrEnum):
    APROVAR = "APROVAR"
    APROVAR_COM_MONITORAMENTO_INTENSIVO = "APROVAR_COM_MONITORAMENTO_INTENSIVO"
    APROVAR_COM_REVISAO_DE_LIMITE = "APROVAR_COM_REVISAO_DE_LIMITE"
    APROVAR_COM_RESTRICOES = "APROVAR_COM_RESTRICOES"
    SUSPENDER_NOVA_EXPOSICAO_A_PRAZO = "SUSPENDER_NOVA_EXPOSICAO_A_PRAZO"
    SUSPENDER_EXPOSICAO = "SUSPENDER_EXPOSICAO"


class DecisaoAnalista(StrEnum):
    APROVAR = "APROVAR"
    APROVAR_COM_RESTRICOES = "APROVAR_COM_RESTRICOES"
    REVISAR = "REVISAR"
    SUSPENDER = "SUSPENDER"
    RECUSAR = "RECUSAR"


class OrigemCliente(StrEnum):
    CARTEIRA = "CARTEIRA"
    PROSPECT = "PROSPECT"


class SituacaoRfb(StrEnum):
    ATIVA = "ATIVA"
    SUSPENSA = "SUSPENSA"
    INAPTA = "INAPTA"
    BAIXADA = "BAIXADA"


class SituacaoCar(StrEnum):
    ATIVO_REGULAR = "ATIVO_REGULAR"
    PENDENTE = "PENDENTE"
    IRREGULAR = "IRREGULAR"
    AUSENTE = "AUSENTE"


class StatusParcela(StrEnum):
    A_VENCER = "A_VENCER"
    PAGA = "PAGA"
    EM_ATRASO = "EM_ATRASO"


class TipoEvidencia(StrEnum):
    CERTIDAO = "CERTIDAO"
    PROCESSO = "PROCESSO"
    PUBLICACAO = "PUBLICACAO"
    CADASTRO = "CADASTRO"
    LAUDO = "LAUDO"
    SERIE_HISTORICA = "SERIE_HISTORICA"
    INTERNO = "INTERNO"


class DirecaoFator(StrEnum):
    RISCO = "risco"
    PROTECAO = "protecao"


class EfeitoVeto(StrEnum):
    FORCA_D = "FORCA_D"
    TETO_C = "TETO_C"


class TipoEventoDeRisco(StrEnum):
    NOVA_EXECUCAO = "NOVA_EXECUCAO"
    NOVO_PROTESTO = "NOVO_PROTESTO"
    DIVIDA_ATIVA = "DIVIDA_ATIVA"
    PEDIDO_RJ = "PEDIDO_RJ"
    PEDIDO_FALENCIA = "PEDIDO_FALENCIA"
    EMBARGO_AMBIENTAL = "EMBARGO_AMBIENTAL"
    ALTERACAO_SOCIETARIA = "ALTERACAO_SOCIETARIA"
    COVENANT_ROMPIDO = "COVENANT_ROMPIDO"
    MUDANCA_CLIMATICA = "MUDANCA_CLIMATICA"
    ATRASO_PAGAMENTO = "ATRASO_PAGAMENTO"
    CADASTRAL = "CADASTRAL"
    RECALCULO = "RECALCULO"
