"""Serialização do contexto narrativo — `specs/04-camada-llm.md` §4.

A fronteira entre o motor determinístico e o modelo de linguagem é **um
objeto**: `ContextoNarrativo`. Tudo que o LLM sabe do cliente passou por aqui,
e tudo que ele escreve é conferido contra o mesmo objeto por
`verificador.verificar_fidelidade_numerica`.

O ponto central do desenho (§4.2): **todo número sai daqui já formatado em
pt-BR**, como texto. O modelo nunca recebe `0.1712` para "converter" em
`17,1%` — converter é calcular, e calcular é proibido pela invariante I7.
Recebendo `17,1%` pronto, **copiar é a única operação possível**, e o
verificador pode comparar strings exatas.

Mapa de nomes (a spec 04 foi escrita antes do código existir):

| Spec | Código real |
|---|---|
| `api/motor/` | `api/scoring/` |
| `VariacaoDeScore` | `models.eventos.ComparacaoDeAvaliacoes` |
| `comparar_snapshots()` | `scoring.delta.comparar_avaliacoes()` |
| `Recomendacao.motivo_da_regra` | não existe no motor; derivado aqui de rating, tendência e vetos |
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from models.avaliacao import (
    AvaliacaoDeRisco,
    DimensaoAvaliada,
    FatorCalculado,
    RedFlag,
    VetoAtivo,
)
from models.cliente import Cliente
from models.enums import (
    DirecaoFator,
    EfeitoVeto,
    NaturezaGarantia,
    Severidade,
    TipoPessoa,
)
from models.eventos import ComparacaoDeAvaliacoes
from models.exposicao import Garantia
from models.fatos import Evidencia, FatosDoCliente
from pydantic import BaseModel, ConfigDict, Field
from scoring.formatacao import moeda, numero, percentual, percentual_de_fracao

from .engine import TarefaNarrativa
from .perfis import PERFIS, Perfil
from .verificador import extrair_numeros

__all__ = [
    "ContextoNarrativo",
    "serializar_contexto",
    "estimar_tokens",
    "fmt_moeda",
    "fmt_percentual_de_fracao",
    "fmt_percentual_direto",
    "fmt_inteiro",
    "fmt_impacto",
    "fmt_decimal",
    "fmt_peso",
    "fmt_data",
    "fmt_booleano",
    "TIPO_PESSOA_EXTENSO",
    "TENDENCIA_EXTENSA",
    "NENHUM",
    "NAO_APLICAVEL",
    "CHARS_POR_TOKEN",
]

NENHUM = "nenhum"
NAO_APLICAVEL = "nao_aplicavel"
SEM_DADO = "n/d"
_SIM = "sim"
_NAO = "nao"
_SEPARADOR = " | "
_ITEM = "- "
_PONTO_VIRGULA = "; "
_VIRGULA = ", "
_ESPACO = " "

#: Estimador conservador de tokens para pt-BR com muitos números (§5.2).
CHARS_POR_TOKEN = 3.2

TIPO_PESSOA_EXTENSO: dict[TipoPessoa, str] = {
    TipoPessoa.PJ: "pessoa jurídica",
    TipoPessoa.PF: "pessoa física",
}

TENDENCIA_EXTENSA: dict[str, str] = {
    "melhorando": "melhorando",
    "estavel": "estável",
    "deteriorando": "deteriorando",
    "deterioracao_acelerada": "em deterioração acelerada",
}

DIMENSAO_EXTENSA: dict[str, str] = {
    "comportamental": "comportamental",
    "juridico": "jurídica",
    "fiscal": "fiscal",
    "agroclimatico": "agroclimática",
    "cadastral": "cadastral",
    "ambiental": "ambiental",
    "garantias": "de garantias",
}

_EFEITO_EXTENSO: dict[EfeitoVeto, str] = {
    EfeitoVeto.FORCA_D: "força D",
    EfeitoVeto.TETO_C: "teto C",
}

#: Ordem de exibição das red flags (§4.3): CRITICA primeiro.
_ORDEM_SEVERIDADE: dict[Severidade, int] = {
    Severidade.CRITICA: 0,
    Severidade.ALTA: 1,
    Severidade.MEDIA: 2,
    Severidade.BAIXA: 3,
}

_CABECALHO = "LASTRO · CONTEXTO DE AVALIAÇÃO · dados simulados · referência "


# ---------------------------------------------------------------------------
# Formatadores — a tabela normativa da §4.2, sem exceção
# ---------------------------------------------------------------------------


def fmt_moeda(valor: float) -> str:
    """`1200000.0` → `R$ 1.200.000`. Sem centavos, arredondamento half-even."""
    return moeda(valor)


def fmt_percentual_de_fracao(fracao: float, casas: int = 1) -> str:
    """`0.1712` → `17,1%`. Usado por PD, coberturas, utilização de limite."""
    return percentual_de_fracao(fracao, casas)


def fmt_percentual_direto(valor: float) -> str:
    """Já em pontos percentuais: `25.0` → `25%`, `91.3` → `91,3%`."""
    return percentual(valor, 0 if float(valor).is_integer() else 1)


def fmt_inteiro(valor: float) -> str:
    """`604.0` → `604`."""
    return numero(round(valor))


def fmt_impacto(valor: float) -> str:
    """`-26.4` → `-26,4` · `15.0` → `+15,0`. Sinal sempre explícito."""
    texto = numero(valor, 1)
    return texto if valor < 0 else f"+{texto}"


def fmt_decimal(valor: float, casas: int = 1) -> str:
    """`107.64` → `107,6`. Contribuição de dimensão, rjIndex."""
    return numero(valor, casas)


def fmt_peso(fracao: float) -> str:
    """`0.22` → `22%`."""
    return f"{numero(round(fracao * 100))}%"


def fmt_data(iso: str) -> str:
    """`2026-08-20` → `20/08/2026`. Entrada vazia ou fora do formato passa reta."""
    partes = iso.split("T")[0].split("-")
    if len(partes) != 3:
        return iso or SEM_DADO
    ano, mes, dia = partes
    return f"{dia}/{mes}/{ano}"


def fmt_booleano(valor: bool) -> str:
    return _SIM if valor else _NAO


def estimar_tokens(texto: str) -> int:
    """`len(texto) / 3,2`, arredondado para cima (§5.2)."""
    return math.ceil(len(texto) / CHARS_POR_TOKEN)


# ---------------------------------------------------------------------------
# Campos estruturados — strings, nunca floats
# ---------------------------------------------------------------------------


class VetoFmt(BaseModel):
    id: str
    rotulo: str
    efeito: str
    justificativa: str
    evidencias: list[str] = Field(default_factory=list)


class DimensaoFmt(BaseModel):
    id: str
    rotulo: str
    score: str
    peso: str
    contribuicao: str
    tendencia: str


class FatorFmt(BaseModel):
    id: str
    dimensao: str
    dimensao_extensa: str
    impacto: str
    descricao: str
    fonte: str
    evidencias: list[str] = Field(default_factory=list)

    @property
    def citacao(self) -> str:
        """`[E-01]` quando há evidência; `[INTERNO_KRILLTECH]` quando não há."""
        return f"[{self.evidencias[0] if self.evidencias else self.fonte}]"


class ItemVariacaoFmt(BaseModel):
    rotulo: str
    delta: str
    situacao: str


class VariacaoFmt(BaseModel):
    score_anterior: str
    score_atual: str
    delta: str
    data_anterior: str
    itens: list[ItemVariacaoFmt] = Field(default_factory=list)


class PdFmt(BaseModel):
    m6: str
    m12: str
    m24: str
    metodo: str


class RjFmt(BaseModel):
    risco_12m: str
    evento_ocorrido: bool
    rj_index: str
    rj_index_efetivo: str
    elegivel: bool
    motivo_inelegibilidade: str | None = None
    sinais: list[str] = Field(default_factory=list)


class StayFmt(BaseModel):
    ativo: bool
    deferimento: str
    dias_decorridos: str
    dias_restantes: str
    bloqueado: list[str] = Field(default_factory=list)
    permitido: list[str] = Field(default_factory=list)


class ExposicaoFmt(BaseModel):
    total: str
    limite_aprovado: str
    limite_utilizado: str
    a_vencer_90d: str
    em_atraso: str
    por_tipo: dict[str, str] = Field(default_factory=dict)


class GarantiaFmt(BaseModel):
    id: str
    tipo: str
    natureza: str
    descricao: str
    declarado: str
    atualizado: str
    registrada: str
    data_avaliacao: str


class GarantiasFmt(BaseModel):
    """Coberturas + a lista de bens. A spec previa dois campos; um só é coeso."""

    extraconcursal: str
    cobertura_extraconcursal: str
    concursal: str
    cobertura_total: str
    exposicao_protegida: str
    exposicao_em_risco: str
    exposicao_em_risco_em_rj: str
    itens: list[GarantiaFmt] = Field(default_factory=list)


class RedFlagFmt(BaseModel):
    severidade: str
    titulo: str
    data: str
    fonte: str
    impacto: str
    status: str
    evidencias: list[str] = Field(default_factory=list)


class AcaoFmt(BaseModel):
    id: str
    rotulo: str


class RecomendacaoFmt(BaseModel):
    codigo: str
    rotulo: str
    reavaliar_em: str
    motivo_da_regra: str
    acoes: list[AcaoFmt] = Field(default_factory=list)
    aviso: str


class EvidenciaFmt(BaseModel):
    id: str
    fonte: str
    nome_fonte: str
    tipo: str
    titulo: str
    resumo: str
    data_consulta: str


class ContextoNarrativo(BaseModel):
    """Contexto com **todos** os números já formatados como strings pt-BR.

    Os três engines consomem este objeto: o OpenAI recebe `bloco` dentro do
    prompt; o determinístico usa os campos estruturados; o de fixture usa
    `cliente_id` e `tarefa` para achar o arquivo gravado.
    """

    model_config = ConfigDict(frozen=True)

    cliente_id: str
    razao_social: str
    tarefa: TarefaNarrativa
    perfil: Perfil
    #: O texto literal que entra no prompt (§4.3).
    bloco: str
    #: Extraídos de `bloco`. Base do verificador (§4.4).
    numeros_permitidos: frozenset[str]

    score: str
    rating_calculado: str
    rating_final: str
    tendencia: str
    tendencia_extensa: str
    vetos: list[VetoFmt] = Field(default_factory=list)
    dimensoes: list[DimensaoFmt] = Field(default_factory=list)
    fatores_risco: list[FatorFmt] = Field(default_factory=list)
    fatores_protecao: list[FatorFmt] = Field(default_factory=list)
    variacao: VariacaoFmt | None = None
    pd: PdFmt | None = None
    rj: RjFmt | None = None
    stay: StayFmt | None = None
    exposicao: ExposicaoFmt | None = None
    garantias: GarantiasFmt | None = None
    red_flags: list[RedFlagFmt] = Field(default_factory=list)
    recomendacao: RecomendacaoFmt | None = None
    evidencias: list[EvidenciaFmt] = Field(default_factory=list)

    #: Identidade do cliente em prosa, para os templates determinísticos.
    tipo_pessoa_extenso: str = ""
    municipio_uf: str = ""
    atividade: str = ""

    @property
    def tokens_estimados(self) -> int:
        return estimar_tokens(self.bloco)

    def evidencia_por_id(self, evidencia_id: str) -> EvidenciaFmt | None:
        for evidencia in self.evidencias:
            if evidencia.id == evidencia_id:
                return evidencia
        return None


# ---------------------------------------------------------------------------
# Montagem
# ---------------------------------------------------------------------------


def _descricao_do_fator(fator: FatorCalculado) -> str:
    """`rotulo` e `detalhe` combinados sem repetir a mesma informação.

    `detalhe` é a frase que carrega os números ("Pior atraso de 26 dias"), mas
    nem sempre nomeia o fator ("1 execução(ões) no período"). Quando ela já
    começa pelo mesmo termo do rótulo, o rótulo é dispensável.
    """
    if not fator.detalhe:
        return fator.rotulo
    primeira = fator.detalhe.split(_ESPACO)[0].lower()
    if primeira and primeira in fator.rotulo.lower():
        return fator.detalhe
    return f"{fator.rotulo}: {fator.detalhe}"


def _fator_fmt(fator: FatorCalculado) -> FatorFmt:
    return FatorFmt(
        id=fator.id,
        dimensao=str(fator.dimensao),
        dimensao_extensa=DIMENSAO_EXTENSA.get(str(fator.dimensao), str(fator.dimensao)),
        impacto=fmt_impacto(fator.impacto_global_ajustado),
        descricao=_descricao_do_fator(fator),
        fonte=str(fator.fonte),
        evidencias=list(fator.evidencia_ids),
    )


def _separar_fatores(
    dimensoes: Sequence[DimensaoAvaliada], perfil: Perfil
) -> tuple[list[FatorFmt], list[FatorFmt]]:
    """Risco por |impacto| decrescente; proteção por impacto decrescente (§4.3)."""
    todos = [fator for dimensao in dimensoes for fator in dimensao.fatores]
    risco = sorted(
        (f for f in todos if f.direcao == DirecaoFator.RISCO),
        key=lambda f: abs(f.impacto_global_ajustado),
        reverse=True,
    )
    protecao = sorted(
        (f for f in todos if f.direcao == DirecaoFator.PROTECAO),
        key=lambda f: f.impacto_global_ajustado,
        reverse=True,
    )
    if perfil.max_fatores_risco is not None:
        risco = risco[: perfil.max_fatores_risco]
    if perfil.max_fatores_protecao is not None:
        protecao = protecao[: perfil.max_fatores_protecao]
    return [_fator_fmt(f) for f in risco], [_fator_fmt(f) for f in protecao]


def _red_flags_fmt(red_flags: Sequence[RedFlag], perfil: Perfil) -> list[RedFlagFmt]:
    if perfil.red_flags == "nenhuma":
        return []
    selecionadas = list(red_flags)
    if perfil.red_flags == "criticas_altas":
        selecionadas = [
            r for r in selecionadas if r.severidade in (Severidade.CRITICA, Severidade.ALTA)
        ]
    selecionadas.sort(key=lambda r: (_ORDEM_SEVERIDADE[r.severidade], _inverso(r.data)))
    return [
        RedFlagFmt(
            severidade=str(r.severidade),
            titulo=r.titulo,
            data=fmt_data(r.data),
            fonte=str(r.fonte),
            impacto=fmt_impacto(r.impacto_em_pontos),
            status=str(r.status),
            evidencias=list(r.evidencia_ids),
        )
        for r in selecionadas
    ]


def _inverso(data: str) -> tuple[int, ...]:
    """Chave de ordenação decrescente por data ISO, sem `reverse` global."""
    return tuple(-int(parte) for parte in data.split("T")[0].split("-") if parte.isdigit())


def _vetos_fmt(vetos: Sequence[VetoAtivo]) -> list[VetoFmt]:
    return [
        VetoFmt(
            id=v.id,
            rotulo=v.rotulo,
            efeito=_EFEITO_EXTENSO.get(v.efeito, str(v.efeito)),
            justificativa=v.justificativa,
            evidencias=list(v.evidencia_ids),
        )
        for v in vetos
    ]


def _garantias_fmt(avaliacao: AvaliacaoDeRisco, garantias: Sequence[Garantia]) -> GarantiasFmt:
    exposicao = avaliacao.exposicao
    return GarantiasFmt(
        extraconcursal=fmt_moeda(exposicao.valor_extraconcursal),
        cobertura_extraconcursal=fmt_percentual_de_fracao(exposicao.cobertura_extraconcursal),
        concursal=fmt_moeda(exposicao.valor_concursal),
        cobertura_total=fmt_percentual_de_fracao(exposicao.cobertura_total),
        exposicao_protegida=fmt_moeda(exposicao.exposicao_protegida),
        exposicao_em_risco=fmt_moeda(exposicao.exposicao_em_risco),
        exposicao_em_risco_em_rj=fmt_moeda(exposicao.exposicao_em_risco_em_rj),
        itens=[
            GarantiaFmt(
                id=g.id,
                tipo=str(g.tipo),
                natureza=str(g.natureza),
                descricao=g.descricao,
                declarado=fmt_moeda(g.valor_declarado),
                atualizado=fmt_moeda(g.valor_atualizado),
                registrada=fmt_booleano(g.registrada),
                data_avaliacao=fmt_data(g.data_avaliacao) if g.data_avaliacao else SEM_DADO,
            )
            for g in garantias
        ],
    )


def _motivo_da_regra(avaliacao: AvaliacaoDeRisco) -> str:
    """Derivado — o motor não expõe o campo. Só combina strings já existentes.

    Nenhum número novo entra aqui: rating, tendência e rótulo de veto são
    texto, e é por isso que esta derivação não fere I7.
    """
    base = (
        f"rating final {avaliacao.rating_final.value} com tendência "
        f"{TENDENCIA_EXTENSA.get(str(avaliacao.tendencia), str(avaliacao.tendencia))}"
    )
    if not avaliacao.vetos_ativos:
        return base
    nomes = _VIRGULA.join(v.rotulo for v in avaliacao.vetos_ativos)
    return f"{base}, com gatilho eliminatório: {nomes}"


def _recomendacao_fmt(avaliacao: AvaliacaoDeRisco) -> RecomendacaoFmt:
    recomendacao = avaliacao.recomendacao
    return RecomendacaoFmt(
        codigo=str(recomendacao.codigo),
        rotulo=recomendacao.rotulo,
        reavaliar_em=f"{fmt_inteiro(recomendacao.prazo_reavaliacao_dias)} dias",
        motivo_da_regra=_motivo_da_regra(avaliacao),
        acoes=[AcaoFmt(id=a.id, rotulo=a.rotulo) for a in recomendacao.acoes],
        aviso=recomendacao.aviso,
    )


def _evidencias_fmt(evidencias: Iterable[Evidencia]) -> list[EvidenciaFmt]:
    return sorted(
        (
            EvidenciaFmt(
                id=e.id,
                fonte=str(e.fonte),
                nome_fonte=e.nome_fonte,
                tipo=str(e.tipo),
                titulo=e.titulo,
                resumo=e.resumo,
                data_consulta=fmt_data(e.data_consulta) if e.data_consulta else SEM_DADO,
            )
            for e in evidencias
        ),
        key=lambda e: e.id,
    )


def _variacao_fmt(variacao: ComparacaoDeAvaliacoes | None) -> VariacaoFmt | None:
    if variacao is None:
        return None
    return VariacaoFmt(
        score_anterior=fmt_inteiro(variacao.score_anterior),
        score_atual=fmt_inteiro(variacao.score_atual),
        delta=fmt_impacto(variacao.delta_score),
        data_anterior=fmt_data(variacao.data_anterior),
        itens=[
            ItemVariacaoFmt(
                rotulo=linha.rotulo, delta=fmt_impacto(linha.delta), situacao=linha.situacao
            )
            for linha in variacao.fatores
        ],
    )


# ---------------------------------------------------------------------------
# O bloco literal da §4.3
# ---------------------------------------------------------------------------


def _linha_cliente(cliente: Cliente, perfil: Perfil) -> str:
    documento = "CNPJ" if cliente.tipo_pessoa == TipoPessoa.PJ else "CPF"
    if not perfil.cliente_completo:
        campos = [
            f"id={cliente.id}",
            cliente.razao_social,
            str(cliente.tipo_pessoa),
            f"{cliente.municipio}/{cliente.uf}",
        ]
        return "[CLIENTE] " + _SEPARADOR.join(campos)
    campos = [
        f"id={cliente.id}",
        cliente.razao_social,
        str(cliente.tipo_pessoa),
        f"{documento} {cliente.documento} (simulado)",
        f"{cliente.municipio}/{cliente.uf}",
        cliente.atividade,
        f"culturas: {_VIRGULA.join(cliente.culturas) if cliente.culturas else NENHUM}",
        f"relacionamento desde {fmt_data(cliente.inicio_relacionamento)}",
        f"estado: {cliente.estado}",
        f"origem: {cliente.origem}",
    ]
    return "[CLIENTE] " + _SEPARADOR.join(campos)


def _linha_score(avaliacao: AvaliacaoDeRisco, vetos: Sequence[VetoFmt]) -> str:
    auditoria = avaliacao.auditoria
    campos = [
        f"calculado={fmt_inteiro(avaliacao.score_calculado)}",
        f"rating_calculado={avaliacao.rating_calculado.value}",
        f"rating_final={avaliacao.rating_final.value}",
        f"tendencia={avaliacao.tendencia}",
    ]
    if vetos:
        descritos = _PONTO_VIRGULA.join(
            f"{v.id} ({v.efeito}) — {v.justificativa}"
            + (f" [{v.evidencias[0]}]" if v.evidencias else "")
            for v in vetos
        )
        campos.append(f"vetos: {descritos}")
    else:
        campos.append(f"vetos={NENHUM}")
    campos.append(
        f"auditoria: soma_impactos={fmt_decimal(auditoria.soma_impactos)} "
        f"diferenca={fmt_decimal(auditoria.diferenca)}"
    )
    return "[SCORE] " + _SEPARADOR.join(campos)


def _bloco_variacao(variacao: VariacaoFmt | None, perfil: Perfil) -> list[str]:
    if variacao is None:
        return []
    cabecalho = (
        f"[VARIACAO_90D] {variacao.score_anterior} -> {variacao.score_atual} "
        f"({variacao.delta}) | referencia anterior {variacao.data_anterior}"
    )
    if not perfil.variacao_itens:
        return [cabecalho]
    linhas = [cabecalho]
    for item in variacao.itens:
        sufixo = " (novo)" if item.situacao == "novo" else ""
        linhas.append(f"{_ITEM}{item.rotulo}{sufixo}: {item.delta}")
    return linhas


def _bloco_dimensoes(dimensoes: Sequence[DimensaoFmt]) -> list[str]:
    linhas = ["[DIMENSOES] id | score | peso | contribuicao | tendencia"]
    linhas += [
        f"{_ITEM}{d.id} | {d.score} | {d.peso} | {d.contribuicao} | {d.tendencia}"
        for d in dimensoes
    ]
    return linhas


def _bloco_fatores(risco: Sequence[FatorFmt], protecao: Sequence[FatorFmt]) -> list[str]:
    linhas = [
        "[FATORES] id | dimensao | impacto no score "
        "(negativo = risco, positivo = proteção) | descricao | fonte | evidencias"
    ]
    for fator in [*risco, *protecao]:
        evidencias = _VIRGULA.join(fator.evidencias) if fator.evidencias else NENHUM
        linhas.append(
            f"{_ITEM}{fator.id} | {fator.dimensao} | {fator.impacto} | "
            f"{fator.descricao} | {fator.fonte} | {evidencias}"
        )
    if len(linhas) == 1:
        linhas.append(f"{_ITEM}{NENHUM}")
    return linhas


def _bloco_garantias(garantias: GarantiasFmt) -> list[str]:
    cabecalho = "[GARANTIAS] " + _SEPARADOR.join(
        [
            f"extraconcursal={garantias.extraconcursal}",
            f"cobertura_extraconcursal={garantias.cobertura_extraconcursal}",
            f"concursal={garantias.concursal}",
            f"cobertura_total={garantias.cobertura_total}",
            f"exposicao_protegida={garantias.exposicao_protegida}",
            f"exposicao_em_risco={garantias.exposicao_em_risco}",
            f"exposicao_em_risco_em_RJ={garantias.exposicao_em_risco_em_rj}",
        ]
    )
    linhas = [cabecalho]
    for item in garantias.itens:
        linhas.append(
            f"{_ITEM}{item.id} | {item.tipo} | {item.natureza} | {item.descricao} | "
            f"declarado {item.declarado} | atualizado {item.atualizado} | "
            f"registrada={item.registrada} | avaliada em {item.data_avaliacao}"
        )
    return linhas


def _bloco_red_flags(red_flags: Sequence[RedFlagFmt]) -> list[str]:
    if not red_flags:
        return [f"[RED_FLAGS] {NENHUM}"]
    linhas = ["[RED_FLAGS] severidade | titulo | data | fonte | impacto | status | evidencias"]
    linhas += [
        f"{_ITEM}{r.severidade} | {r.titulo} | {r.data} | {r.fonte} | {r.impacto} | "
        f"{r.status} | {_VIRGULA.join(r.evidencias) if r.evidencias else NENHUM}"
        for r in red_flags
    ]
    return linhas


def _bloco_recomendacao(recomendacao: RecomendacaoFmt) -> list[str]:
    linhas = [
        "[RECOMENDACAO] "
        + _SEPARADOR.join(
            [
                f"codigo={recomendacao.codigo}",
                f"rotulo={recomendacao.rotulo}",
                f"reavaliar_em={recomendacao.reavaliar_em}",
                f"motivo_da_regra: {recomendacao.motivo_da_regra}",
            ]
        )
    ]
    linhas += [f"{indice}. {acao.rotulo}" for indice, acao in enumerate(recomendacao.acoes, 1)]
    linhas.append(f"aviso: {recomendacao.aviso}")
    return linhas


def _bloco_evidencias(evidencias: Sequence[EvidenciaFmt], perfil: Perfil) -> list[str]:
    if not evidencias:
        return [f"[EVIDENCIAS] {NENHUM}"]
    com_resumo = perfil.evidencias == "com_resumo"
    cabecalho = "[EVIDENCIAS] id | fonte | tipo | titulo | consulta" + (
        " | resumo" if com_resumo else ""
    )
    linhas = [cabecalho]
    for evidencia in evidencias:
        partes = [
            evidencia.id,
            evidencia.nome_fonte,
            evidencia.tipo,
            evidencia.titulo,
            evidencia.data_consulta,
        ]
        if com_resumo and evidencia.resumo:
            partes.append(evidencia.resumo)
        linhas.append(_ITEM + _SEPARADOR.join(partes))
    return linhas


def _montar_bloco(
    cliente: Cliente,
    avaliacao: AvaliacaoDeRisco,
    perfil: Perfil,
    *,
    vetos: Sequence[VetoFmt],
    dimensoes: Sequence[DimensaoFmt],
    risco: Sequence[FatorFmt],
    protecao: Sequence[FatorFmt],
    variacao: VariacaoFmt | None,
    pd: PdFmt | None,
    rj: RjFmt | None,
    stay: StayFmt | None,
    exposicao: ExposicaoFmt | None,
    garantias: GarantiasFmt | None,
    red_flags: Sequence[RedFlagFmt],
    recomendacao: RecomendacaoFmt | None,
    evidencias: Sequence[EvidenciaFmt],
) -> str:
    linhas: list[str] = [_CABECALHO + fmt_data(avaliacao.data_referencia)]
    linhas.append(_linha_cliente(cliente, perfil))
    linhas.append(_linha_score(avaliacao, vetos))
    linhas += _bloco_variacao(variacao, perfil)
    if perfil.dimensoes:
        linhas += _bloco_dimensoes(dimensoes)
    linhas += _bloco_fatores(risco, protecao)
    if pd is not None:
        linhas.append(
            f"[PD] 6m={pd.m6} | 12m={pd.m12} | 24m={pd.m24} | metodo: {pd.metodo}"
        )
    if rj is not None:
        campos = [
            f"risco_12m={rj.risco_12m}"
            + (" (evento ocorrido)" if rj.evento_ocorrido else ""),
            f"evento_ocorrido={fmt_booleano(rj.evento_ocorrido)}",
            f"rj_index={rj.rj_index}",
            f"rj_index_efetivo={rj.rj_index_efetivo}",
            f"elegivel={fmt_booleano(rj.elegivel)}"
            + (f" ({rj.motivo_inelegibilidade})" if rj.motivo_inelegibilidade else ""),
        ]
        if rj.sinais:
            campos.append("sinais: " + _PONTO_VIRGULA.join(rj.sinais))
        linhas.append("[RJ] " + _SEPARADOR.join(campos))
    if rj is not None or stay is not None:
        if stay is not None and stay.ativo:
            linhas.append(
                "[STAY_PERIOD] "
                + _SEPARADOR.join(
                    [
                        "ativo=sim",
                        f"deferimento {stay.deferimento}",
                        f"dias_decorridos={stay.dias_decorridos}",
                        f"dias_restantes={stay.dias_restantes}",
                        "bloqueado: " + _PONTO_VIRGULA.join(stay.bloqueado),
                        "permitido: " + _PONTO_VIRGULA.join(stay.permitido),
                    ]
                )
            )
        elif stay is not None or rj is not None:
            linhas.append(f"[STAY_PERIOD] {NAO_APLICAVEL}")
    if exposicao is not None:
        por_tipo = _PONTO_VIRGULA.join(
            f"{tipo}={valor}" for tipo, valor in exposicao.por_tipo.items()
        )
        linhas.append(
            "[EXPOSICAO] "
            + _SEPARADOR.join(
                [
                    f"total={exposicao.total}",
                    f"limite_aprovado={exposicao.limite_aprovado}",
                    f"limite_utilizado={exposicao.limite_utilizado}",
                    f"a_vencer_90d={exposicao.a_vencer_90d}",
                    f"em_atraso={exposicao.em_atraso}",
                    f"por_tipo: {por_tipo or NENHUM}",
                ]
            )
        )
    if garantias is not None:
        linhas += _bloco_garantias(garantias)
    if perfil.red_flags != "nenhuma":
        linhas += _bloco_red_flags(red_flags)
    if recomendacao is not None:
        linhas += _bloco_recomendacao(recomendacao)
    linhas += _bloco_evidencias(evidencias, perfil)
    return "\n".join(linhas)


def serializar_contexto(
    cliente: Cliente,
    fatos: FatosDoCliente,
    avaliacao: AvaliacaoDeRisco,
    variacao: ComparacaoDeAvaliacoes | None,
    tarefa: TarefaNarrativa,
) -> ContextoNarrativo:
    """`AvaliacaoDeRisco` → `ContextoNarrativo`. Único caminho até o modelo.

    Nenhum número é digitado em prompt: tudo que o LLM vê nasceu em
    `scoring.calcular_risco()` no mesmo processo, na mesma requisição.
    """
    perfil = PERFIS[tarefa]
    vetos = _vetos_fmt(avaliacao.vetos_ativos)
    dimensoes = (
        [
            DimensaoFmt(
                id=str(d.id),
                rotulo=d.rotulo,
                score=fmt_inteiro(d.score),
                peso=fmt_peso(d.peso),
                contribuicao=fmt_decimal(d.contribuicao),
                tendencia=str(d.tendencia),
            )
            for d in avaliacao.dimensoes
        ]
        if perfil.dimensoes
        else []
    )
    risco, protecao = _separar_fatores(avaliacao.dimensoes, perfil)
    variacao_fmt = _variacao_fmt(variacao)

    pd = rj = stay = None
    if perfil.pd_rj_stay:
        pd = PdFmt(
            m6=fmt_percentual_de_fracao(avaliacao.pd.pd6m),
            m12=fmt_percentual_de_fracao(avaliacao.pd.pd12m),
            m24=fmt_percentual_de_fracao(avaliacao.pd.pd24m),
            metodo=avaliacao.pd.metodo,
        )
        risco_rj = avaliacao.risco_rj
        rj = RjFmt(
            risco_12m=fmt_percentual_de_fracao(risco_rj.probabilidade_12m),
            evento_ocorrido=risco_rj.evento_ja_ocorrido,
            rj_index=fmt_decimal(risco_rj.rj_index),
            rj_index_efetivo=fmt_decimal(risco_rj.rj_index_efetivo),
            elegivel=risco_rj.elegivel,
            motivo_inelegibilidade=risco_rj.motivo_inelegibilidade,
            sinais=[f"{s.rotulo} {fmt_impacto(s.pontos)}" for s in risco_rj.sinais],
        )
        if avaliacao.stay_period is not None:
            periodo = avaliacao.stay_period
            stay = StayFmt(
                ativo=periodo.ativo,
                deferimento=fmt_data(periodo.data_deferimento),
                dias_decorridos=fmt_inteiro(periodo.dias_decorridos),
                dias_restantes=fmt_inteiro(periodo.dias_restantes),
                bloqueado=list(periodo.bloqueios),
                permitido=list(periodo.permitido),
            )

    exposicao = garantias = None
    if perfil.exposicao_garantias:
        calculada = avaliacao.exposicao
        exposicao = ExposicaoFmt(
            total=fmt_moeda(calculada.exposicao_total),
            limite_aprovado=fmt_moeda(calculada.limite_aprovado),
            limite_utilizado=fmt_percentual_de_fracao(calculada.limite_utilizado_pct),
            a_vencer_90d=fmt_moeda(calculada.a_vencer_90d),
            em_atraso=fmt_moeda(calculada.em_atraso),
            por_tipo={
                str(tipo): fmt_moeda(valor)
                for tipo, valor in calculada.por_tipo_operacao.items()
            },
        )
        garantias = _garantias_fmt(avaliacao, fatos.garantias)

    red_flags = _red_flags_fmt(avaliacao.red_flags, perfil)
    recomendacao = _recomendacao_fmt(avaliacao) if perfil.recomendacao else None
    evidencias = _evidencias_fmt(avaliacao.evidencias)

    bloco = _montar_bloco(
        cliente,
        avaliacao,
        perfil,
        vetos=vetos,
        dimensoes=dimensoes,
        risco=risco,
        protecao=protecao,
        variacao=variacao_fmt,
        pd=pd,
        rj=rj,
        stay=stay,
        exposicao=exposicao,
        garantias=garantias,
        red_flags=red_flags,
        recomendacao=recomendacao,
        evidencias=evidencias,
    )

    return ContextoNarrativo(
        cliente_id=cliente.id,
        razao_social=cliente.razao_social,
        tarefa=tarefa,
        perfil=perfil,
        bloco=bloco,
        numeros_permitidos=frozenset(extrair_numeros(bloco)),
        score=fmt_inteiro(avaliacao.score_calculado),
        rating_calculado=avaliacao.rating_calculado.value,
        rating_final=avaliacao.rating_final.value,
        tendencia=str(avaliacao.tendencia),
        tendencia_extensa=TENDENCIA_EXTENSA.get(
            str(avaliacao.tendencia), str(avaliacao.tendencia)
        ),
        vetos=vetos,
        dimensoes=dimensoes,
        fatores_risco=risco,
        fatores_protecao=protecao,
        variacao=variacao_fmt,
        pd=pd,
        rj=rj,
        stay=stay,
        exposicao=exposicao,
        garantias=garantias,
        red_flags=red_flags,
        recomendacao=recomendacao,
        evidencias=evidencias,
        tipo_pessoa_extenso=TIPO_PESSOA_EXTENSO.get(cliente.tipo_pessoa, ""),
        municipio_uf=f"{cliente.municipio}/{cliente.uf}",
        atividade=cliente.atividade,
    )
