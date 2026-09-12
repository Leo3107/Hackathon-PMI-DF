"""Engine determinístico — Anexo A de `specs/04-camada-llm.md`.

**Não é placeholder.** É a rede de segurança do dia do pitch: com
`LASTRO_LLM_ENABLED=false`, sem rede, com o orçamento esgotado ou com o
disjuntor aberto, a aplicação continua inteira e apresentável. O texto daqui
tem a **mesma estrutura** do texto do LLM — os seis títulos do parecer, na
ordem, as mesmas ações, os mesmos números — e é escrito para que um analista de
crédito o leia sem estranhar.

Sem rede, sem custo, sem aleatoriedade: a saída é função pura do
`ContextoNarrativo`. E, por construção, **zero violações de fidelidade
numérica**, porque todo número impresso é uma string que já veio do contexto.

Nota de nomenclatura: a spec chama este módulo `engine_deterministico.py`.
"""

from __future__ import annotations

from typing import Iterator, Literal, Sequence

from .contexto import ContextoNarrativo, FatorFmt
from .engine import MensagemCopiloto, PedacoNarrativa, UsoTokens
from .verificador import TITULOS_DO_PARECER

__all__ = [
    "DeterministicNarrativeEngine",
    "texto_parecer",
    "texto_score",
    "texto_recomendacao",
    "texto_copiloto",
    "SEM_ELEMENTOS",
    "MOTIVO_EXTENSO",
]

#: Frase padrão da regra 6 dos prompts: seção sem sustentação no contexto.
SEM_ELEMENTOS = "Sem elementos no contexto para esta seção."

_MAX_RISCOS_NO_PARECER = 6
_MAX_MITIGADORES = 4
_MAX_FATORES_NO_SCORE = 5
_MAX_RISCOS_CITADOS = 3
_MAX_OBSERVAR = 2

_QUEBRA = "\n"
_PARAGRAFO = "\n\n"
_VIRGULA = ", "
_PONTO_VIRGULA = "; "

MOTIVO_EXTENSO: dict[str, str] = {
    "FORCADO_POR_ENV": "engine determinístico forçado por configuração",
    "LLM_DESLIGADO": "camada de linguagem desligada por configuração",
    "SEM_CHAVE": "credencial da OpenAI ausente neste processo",
    "DISJUNTOR": "disjuntor aberto após falhas consecutivas do provedor",
    "ORCAMENTO": "orçamento do modelo de linguagem atingido",
    "TIMEOUT": "tempo limite da chamada ao modelo excedido",
    "FALHA_REDE": "falha de rede na chamada ao modelo",
    "FIDELIDADE_NUMERICA": "verificação de fidelidade numérica reprovada",
    "SAIDA_VAZIA": "resposta vazia do modelo",
}


# ---------------------------------------------------------------------------
# Auxiliares de prosa
# ---------------------------------------------------------------------------


def _maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:] if texto else texto


def _item_de_fator(fator: FatorFmt) -> str:
    return f"- {_maiuscula(fator.descricao)}, impacto {fator.impacto} {fator.citacao}."


def _descricoes_curtas(fatores: Sequence[FatorFmt], quantos: int) -> str:
    return _VIRGULA.join(f.descricao for f in fatores[:quantos])


def _frase_de_veto(contexto: ContextoNarrativo) -> str:
    if not contexto.vetos:
        return ", sem veto ativo"
    veto = contexto.vetos[0]
    return (
        f", rebaixado de {contexto.rating_calculado} pela regra {veto.rotulo} "
        f"({veto.efeito})"
    )


def _citacao_de_garantia(contexto: ContextoNarrativo) -> str:
    for fator in contexto.fatores_risco:
        if fator.dimensao == "garantias":
            return fator.citacao
    return "[INTERNO_KRILLTECH]"


# ---------------------------------------------------------------------------
# Parecer — os seis títulos da §3.a
# ---------------------------------------------------------------------------


def _resumo_executivo(contexto: ContextoNarrativo) -> str:
    frases = [
        f"{contexto.razao_social}, {contexto.tipo_pessoa_extenso} de "
        f"{contexto.municipio_uf} com atividade de {contexto.atividade}, tem score "
        f"calculado {contexto.score} e rating final {contexto.rating_final}"
        f"{_frase_de_veto(contexto)}, com tendência {contexto.tendencia_extensa}."
    ]
    if contexto.pd is not None and contexto.rj is not None:
        ocorrido = " (evento já ocorrido)" if contexto.rj.evento_ocorrido else ""
        frases.append(
            f"A PD 12m é {contexto.pd.m12} e o risco de RJ em 12m é "
            f"{contexto.rj.risco_12m}{ocorrido}; inadimplência e recuperação judicial "
            "são indicadores distintos, medidos em escalas separadas."
        )
    if contexto.exposicao is not None:
        frases.append(
            f"A exposição total é {contexto.exposicao.total}, com "
            f"{contexto.exposicao.limite_utilizado} do limite aprovado utilizado."
        )
    if contexto.recomendacao is not None:
        frases.append(f"A recomendação do motor é {contexto.recomendacao.rotulo}.")
    return " ".join(frases)


def _principais_riscos(contexto: ContextoNarrativo) -> str:
    fatores = contexto.fatores_risco[:_MAX_RISCOS_NO_PARECER]
    if not fatores:
        return SEM_ELEMENTOS
    return _QUEBRA.join(_item_de_fator(fator) for fator in fatores)


def _mitigadores(contexto: ContextoNarrativo) -> str:
    fatores = contexto.fatores_protecao[:_MAX_MITIGADORES]
    if not fatores:
        return SEM_ELEMENTOS
    return _QUEBRA.join(_item_de_fator(fator) for fator in fatores)


def _analise_de_garantias(contexto: ContextoNarrativo) -> str:
    garantias = contexto.garantias
    if garantias is None:
        return SEM_ELEMENTOS
    extraconcursais = [g for g in garantias.itens if g.natureza == "EXTRACONCURSAL"]
    concursais = [g for g in garantias.itens if g.natureza == "CONCURSAL"]
    citacao = _citacao_de_garantia(contexto)

    def _lista(itens) -> str:
        return _PONTO_VIRGULA.join(f"{g.descricao or g.tipo} ({g.id})" for g in itens)

    partes = [
        f"A cobertura extraconcursal é de {garantias.extraconcursal} "
        f"({garantias.cobertura_extraconcursal} da exposição)"
        + (f", em {_lista(extraconcursais)}" if extraconcursais else "")
        + ", natureza que sobrevive a um cenário de recuperação judicial."
    ]
    partes.append(
        f"A cobertura concursal é de {garantias.concursal}"
        + (f", em {_lista(concursais)}" if concursais else "")
        + ", que entraria no plano de recuperação judicial com deságio."
    )
    partes.append(
        f"A cobertura total é {garantias.cobertura_total}, com exposição protegida de "
        f"{garantias.exposicao_protegida} e exposição em risco de "
        f"{garantias.exposicao_em_risco}. Em cenário de RJ, a exposição em risco é "
        f"{garantias.exposicao_em_risco_em_rj} {citacao}."
    )
    stay = contexto.stay
    if stay is not None and stay.ativo:
        partes.append(
            f"Stay Period ativo desde {stay.deferimento}: {stay.dias_restantes} dias "
            f"restantes. Bloqueado: {_PONTO_VIRGULA.join(stay.bloqueado)}. "
            f"Permitido: {_PONTO_VIRGULA.join(stay.permitido)}."
        )
    else:
        partes.append("Não há Stay Period ativo.")
    return " ".join(partes)


def _secao_recomendacao(contexto: ContextoNarrativo) -> str:
    recomendacao = contexto.recomendacao
    if recomendacao is None:
        return SEM_ELEMENTOS
    cobertura = (
        f" e a cobertura extraconcursal é {contexto.garantias.cobertura_extraconcursal}"
        if contexto.garantias is not None
        else ""
    )
    justificativa = (
        f"A regra do motor foi acionada por: {recomendacao.motivo_da_regra}. "
        f"Os fatores de maior impacto são "
        f"{_descricoes_curtas(contexto.fatores_risco, _MAX_RISCOS_CITADOS)}"
        f"{cobertura}. As ações abaixo decorrem desses números."
    )
    acoes = _QUEBRA.join(
        f"{indice}. {acao.rotulo}" for indice, acao in enumerate(recomendacao.acoes, 1)
    )
    return _QUEBRA.join(
        [f"**{recomendacao.rotulo}**", justificativa, acoes, recomendacao.aviso]
    )


def _secao_evidencias(contexto: ContextoNarrativo) -> str:
    if not contexto.evidencias:
        return SEM_ELEMENTOS
    return _QUEBRA.join(
        f"- [{e.id}] {e.nome_fonte} — {e.titulo} — consulta em {e.data_consulta} "
        "(consulta simulada)"
        for e in contexto.evidencias
    )


def texto_parecer(contexto: ContextoNarrativo) -> str:
    """Parecer completo, com os seis títulos da §3.a na ordem exigida."""
    corpos = [
        _resumo_executivo(contexto),
        _principais_riscos(contexto),
        _mitigadores(contexto),
        _analise_de_garantias(contexto),
        _secao_recomendacao(contexto),
        _secao_evidencias(contexto),
    ]
    return _PARAGRAFO.join(
        f"{titulo}{_QUEBRA}{corpo}"
        for titulo, corpo in zip(TITULOS_DO_PARECER, corpos, strict=True)
    )


# ---------------------------------------------------------------------------
# Score e recomendação
# ---------------------------------------------------------------------------


def texto_score(contexto: ContextoNarrativo) -> str:
    """Prosa corrida de "por que este score" (§3.b)."""
    if contexto.vetos:
        veto = contexto.vetos[0]
        abertura = (
            f"O score calculado é {contexto.score}, rating final "
            f"{contexto.rating_final}; o rating calculado era "
            f"{contexto.rating_calculado} e a regra {veto.rotulo} o rebaixou."
        )
    else:
        abertura = (
            f"O score calculado é {contexto.score}, rating final "
            f"{contexto.rating_final}, com tendência {contexto.tendencia_extensa}."
        )
    fatores = contexto.fatores_risco[:_MAX_FATORES_NO_SCORE]
    if fatores:
        listados = _PONTO_VIRGULA.join(
            f"{f.descricao} (dimensão {f.dimensao_extensa}, {f.impacto}) {f.citacao}"
            for f in fatores
        )
        meio = f" Os fatores de maior impacto negativo são: {listados}."
    else:
        meio = f" {SEM_ELEMENTOS}"
    protecao = ""
    if contexto.fatores_protecao:
        principal = contexto.fatores_protecao[0]
        protecao = (
            f" O principal fator de proteção é {principal.descricao} "
            f"({principal.impacto}) {principal.citacao}."
        )
    variacao = ""
    if contexto.variacao is not None:
        base = (
            f" Nos últimos 90 dias o score passou de "
            f"{contexto.variacao.score_anterior} para "
            f"{contexto.variacao.score_atual} ({contexto.variacao.delta})"
        )
        if contexto.variacao.itens:
            item = contexto.variacao.itens[0]
            base += f", com maior contribuição de {item.rotulo} ({item.delta})"
        variacao = base + "."
    return abertura + meio + protecao + variacao


def texto_recomendacao(contexto: ContextoNarrativo) -> str:
    """Justificativa da recomendação já decidida pelo motor (§3.c)."""
    recomendacao = contexto.recomendacao
    if recomendacao is None:
        return SEM_ELEMENTOS
    frases = [
        f"A recomendação é {recomendacao.rotulo}, acionada por "
        f"{recomendacao.motivo_da_regra}."
    ]
    maior = contexto.fatores_risco[0] if contexto.fatores_risco else None
    garantias = contexto.garantias
    for acao in recomendacao.acoes:
        if acao.id == "reavaliar_em":
            continue
        if acao.id == "reduzir_limite":
            frases.append(
                f"A redução de limite ({acao.rotulo}) responde ao rating "
                f"{contexto.rating_final} com tendência {contexto.tendencia_extensa}."
            )
        elif acao.id == "exigir_garantia_adicional" and garantias is not None:
            frases.append(
                f"A garantia adicional ({acao.rotulo}) cobre a exposição em risco de "
                f"{garantias.exposicao_em_risco} {_citacao_de_garantia(contexto)}."
            )
        elif acao.id == "converter_para_extraconcursal" and garantias is not None:
            frases.append(
                f"A conversão ({acao.rotulo}) reduz a exposição em risco em cenário de "
                f"recuperação judicial, hoje {garantias.exposicao_em_risco_em_rj}."
            )
        elif maior is not None:
            frases.append(
                f"{acao.rotulo}: decorre de {maior.descricao} ({maior.impacto}) "
                f"{maior.citacao}."
            )
        else:
            frases.append(f"{acao.rotulo}.")
    observar = _descricoes_curtas(contexto.fatores_risco, _MAX_OBSERVAR)
    frases.append(
        f"Reavaliação em {recomendacao.reavaliar_em}"
        + (f", observando {observar}." if observar else ".")
    )
    return " ".join(frases)


# ---------------------------------------------------------------------------
# Copiloto — fallback por palavra-chave (Anexo A)
# ---------------------------------------------------------------------------


def _prosa_pd(contexto: ContextoNarrativo) -> str | None:
    if contexto.pd is None:
        return None
    return (
        f"PD 6m {contexto.pd.m6}, 12m {contexto.pd.m12}, 24m {contexto.pd.m24}. "
        "Fonte: motor de risco (cálculo determinístico)."
    )


def _prosa_rj(contexto: ContextoNarrativo) -> str | None:
    if contexto.rj is None:
        return None
    partes = [
        f"Risco de RJ em 12m {contexto.rj.risco_12m}, índice {contexto.rj.rj_index}, "
        f"elegível: {'sim' if contexto.rj.elegivel else 'nao'}."
    ]
    if contexto.rj.motivo_inelegibilidade:
        partes.append(contexto.rj.motivo_inelegibilidade + ".")
    stay = contexto.stay
    if stay is not None and stay.ativo:
        partes.append(
            f"Stay Period ativo desde {stay.deferimento}, {stay.dias_restantes} dias "
            f"restantes. Bloqueado: {_PONTO_VIRGULA.join(stay.bloqueado)}."
        )
    partes.append("Fonte: motor de risco (cálculo determinístico).")
    return " ".join(partes)


def _prosa_garantias(contexto: ContextoNarrativo) -> str | None:
    if contexto.garantias is None:
        return None
    return (
        f"Cobertura extraconcursal {contexto.garantias.extraconcursal} "
        f"({contexto.garantias.cobertura_extraconcursal}), que sobrevive à recuperação "
        f"judicial; cobertura concursal {contexto.garantias.concursal}, que entra no "
        f"plano. Cobertura total {contexto.garantias.cobertura_total}, exposição em "
        f"risco {contexto.garantias.exposicao_em_risco} e, em cenário de RJ, "
        f"{contexto.garantias.exposicao_em_risco_em_rj}. "
        "Fonte: motor de risco (cálculo determinístico)."
    )


def _prosa_exposicao(contexto: ContextoNarrativo) -> str | None:
    if contexto.exposicao is None:
        return None
    return (
        f"Exposição total {contexto.exposicao.total}, limite aprovado "
        f"{contexto.exposicao.limite_aprovado} com "
        f"{contexto.exposicao.limite_utilizado} utilizado, "
        f"{contexto.exposicao.a_vencer_90d} a vencer em 90 dias e "
        f"{contexto.exposicao.em_atraso} em atraso. "
        "Fonte: motor de risco (cálculo determinístico)."
    )


def _prosa_red_flags(contexto: ContextoNarrativo) -> str | None:
    graves = [r for r in contexto.red_flags if r.severidade in ("CRITICA", "ALTA")]
    if not graves:
        return None
    linhas = [
        f"- {r.severidade}: {r.titulo}, {r.data}, impacto {r.impacto} [{r.fonte}]"
        for r in graves
    ]
    return _QUEBRA.join(linhas) + _QUEBRA + "Fonte: motor de risco (cálculo determinístico)."


def _prosa_dimensao(contexto: ContextoNarrativo, dimensao: str) -> str | None:
    fatores = [f for f in contexto.fatores_risco if f.dimensao == dimensao]
    if not fatores:
        return None
    linhas = [f"- {f.descricao} ({f.impacto}) {f.citacao}" for f in fatores]
    fontes = _VIRGULA.join(
        dict.fromkeys(f.citacao for f in fatores)
    )
    return _QUEBRA.join(linhas) + _QUEBRA + f"Fonte: {fontes}"


def _prosa_evidencias(contexto: ContextoNarrativo) -> str | None:
    if not contexto.evidencias:
        return None
    return _QUEBRA.join(
        f"- [{e.id}] {e.nome_fonte} — {e.titulo} — consulta em {e.data_consulta} "
        "(consulta simulada)"
        for e in contexto.evidencias
    )


def _prosa_recomendacao(contexto: ContextoNarrativo) -> str | None:
    if contexto.recomendacao is None:
        return None
    acoes = _QUEBRA.join(
        f"{i}. {a.rotulo}" for i, a in enumerate(contexto.recomendacao.acoes, 1)
    )
    return (
        f"{contexto.recomendacao.rotulo}."
        + _QUEBRA
        + acoes
        + _QUEBRA
        + "A decisão final é do analista responsável."
        + _QUEBRA
        + "Fonte: motor de risco (cálculo determinístico)."
    )


#: Ordem normativa do Anexo A: a primeira casa vence.
_CHAVES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("red flag", "alerta", "sinal"), "red_flags"),
    (("pd", "inadimpl", "default", "probabilidade"), "pd"),
    (("rj", "recupera", "insolv", "stay"), "rj"),
    (("garantia", "cobertura", "penhor", "fiduci", "colateral"), "garantias"),
    (("exposi", "limite", "vencer", "atraso", "saldo"), "exposicao"),
    (("recomenda", "ação", "acao", "aprovar", "decidir"), "recomendacao"),
    (("execu", "protesto", "processo", "judicial"), "juridico"),
    (("dívida ativa", "divida ativa", "pgfn", "fiscal", "cndt", "fgts"), "fiscal"),
    (("safra", "clima", "zarc", "chuva", "produtividade"), "agroclimatico"),
    (("evidência", "evidencia", "fonte", "consulta"), "evidencias"),
    (("score", "rating", "nota", "por que"), "score"),
)


def texto_copiloto(
    contexto: ContextoNarrativo, pergunta: str, motivo: str | None = None
) -> str:
    """Fallback do copiloto: devolve o bloco do contexto que a pergunta pede."""
    alvo = pergunta.lower()
    for termos, secao in _CHAVES:
        if not any(termo in alvo for termo in termos):
            continue
        resposta = {
            "red_flags": lambda: _prosa_red_flags(contexto),
            "pd": lambda: _prosa_pd(contexto),
            "rj": lambda: _prosa_rj(contexto),
            "garantias": lambda: _prosa_garantias(contexto),
            "exposicao": lambda: _prosa_exposicao(contexto),
            "recomendacao": lambda: _prosa_recomendacao(contexto),
            "juridico": lambda: _prosa_dimensao(contexto, "juridico"),
            "fiscal": lambda: _prosa_dimensao(contexto, "fiscal"),
            "agroclimatico": lambda: _prosa_dimensao(contexto, "agroclimatico"),
            "evidencias": lambda: _prosa_evidencias(contexto),
            "score": lambda: texto_score(contexto)
            + _QUEBRA
            + "Fonte: motor de risco (cálculo determinístico).",
        }[secao]()
        if resposta:
            return resposta
    extenso = MOTIVO_EXTENSO.get(motivo or "", "modo determinístico")
    return (
        f"O copiloto por LLM está indisponível ({extenso}). Consulte os painéis de "
        "score, PD, risco de RJ, exposição e garantias, red flags e evidências na "
        "página do cliente."
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_GERADORES = {
    "parecer": texto_parecer,
    "score": texto_score,
    "recomendacao": texto_recomendacao,
}


class DeterministicNarrativeEngine:
    """Implementação de `NarrativeEngine` sem rede, sem custo e sem aleatoriedade."""

    id = "deterministico"
    modelo = None

    def __init__(self, motivo: str | None = None) -> None:
        #: Motivo da degradação, usado na mensagem de indisponibilidade do copiloto.
        self.motivo = motivo

    def gerar(
        self,
        tarefa: Literal["parecer", "score", "recomendacao"],
        contexto: ContextoNarrativo,
        deadline: float = float("inf"),
    ) -> Iterator[PedacoNarrativa]:
        yield from self._emitir(_GERADORES[tarefa](contexto))

    def responder(
        self,
        contexto: ContextoNarrativo,
        pergunta: str,
        historico: list[MensagemCopiloto] | None = None,
        deadline: float = float("inf"),
    ) -> Iterator[PedacoNarrativa]:
        yield from self._emitir(texto_copiloto(contexto, pergunta, self.motivo))

    @staticmethod
    def _emitir(texto: str) -> Iterator[PedacoNarrativa]:
        """Uma linha por pedaço: o cliente vê o texto crescer como no streaming."""
        linhas = texto.split(_QUEBRA)
        for indice, linha in enumerate(linhas):
            sufixo = _QUEBRA if indice < len(linhas) - 1 else ""
            yield PedacoNarrativa(tipo="texto", texto=linha + sufixo)
        yield PedacoNarrativa(tipo="uso", uso=UsoTokens())
