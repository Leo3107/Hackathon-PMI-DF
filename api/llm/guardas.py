"""Pré-filtros determinísticos do copiloto — `specs/04-camada-llm.md` §8.

Duas camadas defendem o copiloto. Esta é a primeira: quando o padrão da
pergunta é **inequívoco**, a resposta sai daqui, com texto fixo, sem chamar o
LLM — custo zero e comportamento garantido no palco. O resto fica com o prompt
de sistema (§3.d), que é a segunda camada.

Os quatro casos com pré-filtro (§8):

| # | Caso | Gatilho |
|---|---|---|
| 1 | Pergunta sobre outro cliente | nome, nome fantasia ou id de qualquer outro cliente do repositório |
| 2 | Pedido de recálculo ou estimativa | `chuta`, `estime`, `recalcule`, `quanto ficaria`, `e se … fosse` |
| 4 | Injeção de instrução | `ignore as instruções`, `prompt do sistema`, `finja que`, `DAN`… sem parte legítima |
| 8 | Pergunta ofensiva ou fora do tema | termo ofensivo **e** nenhum termo do domínio |

Toda recusa é texto fixo com `{{RAZAO_SOCIAL}}` substituído, e as recusas dos
casos 1, 4 e 8 **não levam linha de fonte** — não há conteúdo do contexto nelas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, NamedTuple

from .contexto import ContextoNarrativo

__all__ = [
    "RespostaImediata",
    "pre_filtrar",
    "normalizar",
    "numeros_da_pergunta",
    "RECUSA_OUTRO_CLIENTE",
    "RECUSA_INJECAO",
    "RECUSA_FORA_DE_ESCOPO",
    "RECUSA_RECALCULO",
    "TERMOS_DO_DOMINIO",
]

MARCA_RAZAO_SOCIAL = "{{RAZAO_SOCIAL}}"

RECUSA_OUTRO_CLIENTE = (
    f"Só posso responder sobre {MARCA_RAZAO_SOCIAL} com base nos dados desta "
    "avaliação. Não tenho acesso a dados de outros clientes."
)
RECUSA_INJECAO = (
    "Não posso atender a esse pedido. Posso responder perguntas sobre a avaliação "
    f"de risco de {MARCA_RAZAO_SOCIAL}."
)
RECUSA_FORA_DE_ESCOPO = (
    "Posso ajudar com perguntas sobre a avaliação de risco de "
    f"{MARCA_RAZAO_SOCIAL}."
)
RECUSA_RECALCULO = (
    "Não recalculo nem estimo números. O valor calculado pelo motor é: {valor}. "
    "Para simular cenários, use o controle 'Simular evento de monitoramento' na "
    "página do cliente."
)
RECUSA_RECALCULO_SEM_VALOR = "Não recalculo nem estimo números."
_FONTE_MOTOR = "Fonte: motor de risco (cálculo determinístico)."

#: Termos que caracterizam uma pergunta de análise de crédito (§8, caso 8).
TERMOS_DO_DOMINIO: frozenset[str] = frozenset(
    {
        "score",
        "rating",
        "pd",
        "inadimpl",
        "rj",
        "recupera",
        "garantia",
        "cobertura",
        "execu",
        "protesto",
        "divida",
        "limite",
        "exposi",
        "red flag",
        "alerta",
        "evidencia",
        "safra",
        "covenant",
        "recomenda",
        "risco",
        "fiscal",
        "certidao",
        "stay",
        "penhor",
        "clima",
        "zarc",
        "atraso",
        "parcela",
        "credito",
    }
)

_PADROES_RECALCULO: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bchut[ae]"),
    re.compile(r"\bestim[ae]\b"),
    re.compile(r"\brecalcul[ae]"),
    re.compile(r"\bquanto ficaria\b"),
    re.compile(r"\be se\b.{0,40}\bfosse\b"),
)

_PADROES_INJECAO: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore as instruc"),
    re.compile(r"ignore previous"),
    re.compile(r"system prompt"),
    re.compile(r"prompt do sistema"),
    re.compile(r"voce agora e\b"),
    re.compile(r"finja que"),
    re.compile(r"novo papel"),
    re.compile(r"esquec[ae] suas regras"),
    re.compile(r"\bdan\b"),
)

_TERMOS_OFENSIVOS: frozenset[str] = frozenset(
    {
        "caloteiro",
        "safado",
        "ladrao",
        "idiota",
        "burro",
        "imbecil",
        "otario",
        "piada",
        "vagabundo",
        "lixo",
    }
)

#: Palavras curtas demais para identificar um cliente por si só.
_MIN_TERMO_DE_CLIENTE = 4
_GENERICOS = frozenset(
    {"ltda", "sa", "s/a", "agro", "fazenda", "agropecuaria", "grupo", "comercio", "eireli"}
)

_RE_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")
_RE_NUMERO = re.compile(
    r"(?<![\w-])[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?|(?<![\w-])[+-]?\d+(?:,\d+)?"
)


class RespostaImediata(NamedTuple):
    """Resposta produzida sem LLM. `caso` identifica a linha da tabela do §8."""

    texto: str
    caso: str


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, pontuação virando espaço. Comparação estável."""
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(caractere)
    )
    return _RE_NAO_ALFANUMERICO.sub(" ", sem_acento).strip()


def numeros_da_pergunta(pergunta: str) -> set[str]:
    """Números escritos pelo analista — entram em `extras` do verificador (§8.9)."""
    return {achado.lstrip("+") for achado in _RE_NUMERO.findall(pergunta)}


def _termos_de_cliente(nomes: Iterable[str]) -> list[str]:
    """Tokens longos e não genéricos que identificam um cliente com segurança."""
    termos: list[str] = []
    for nome in nomes:
        normalizado = normalizar(nome)
        if not normalizado:
            continue
        termos.append(normalizado)
        termos += [
            token
            for token in normalizado.split()
            if len(token) >= _MIN_TERMO_DE_CLIENTE and token not in _GENERICOS
        ]
    return termos


def _valor_pertinente(pergunta: str, contexto: ContextoNarrativo) -> str | None:
    """O número do motor que a pergunta pede, para a recusa do caso 2 citar."""
    alvo = normalizar(pergunta)
    if contexto.pd is not None:
        if "24" in alvo:
            return f"PD 24m {contexto.pd.m24}"
        if "6 " in alvo or alvo.endswith(" 6") or "6m" in alvo:
            return f"PD 6m {contexto.pd.m6}"
        if any(termo in alvo for termo in ("pd", "inadimpl", "default")):
            return f"PD 12m {contexto.pd.m12}"
    if contexto.rj is not None and any(termo in alvo for termo in ("rj", "recupera")):
        return f"risco de RJ em 12m {contexto.rj.risco_12m}"
    if any(termo in alvo for termo in ("score", "nota", "rating")):
        return f"score {contexto.score}, rating {contexto.rating_final}"
    if contexto.exposicao is not None and any(
        termo in alvo for termo in ("exposi", "limite")
    ):
        return f"exposição total {contexto.exposicao.total}"
    return None


def pre_filtrar(
    pergunta: str,
    contexto: ContextoNarrativo,
    outros_clientes: Iterable[str] = (),
) -> RespostaImediata | None:
    """Resposta imediata quando o padrão é inequívoco; `None` para seguir ao LLM.

    `outros_clientes` recebe razões sociais, nomes fantasia e ids de **todos os
    demais** clientes do repositório.
    """
    alvo = normalizar(pergunta)
    if not alvo:
        return None

    proprio = set(_termos_de_cliente([contexto.razao_social, contexto.cliente_id]))
    for termo in _termos_de_cliente(outros_clientes):
        if termo in proprio:
            continue
        if re.search(rf"\b{re.escape(termo)}\b", alvo):
            return RespostaImediata(
                RECUSA_OUTRO_CLIENTE.replace(MARCA_RAZAO_SOCIAL, contexto.razao_social),
                "outro_cliente",
            )

    if any(padrao.search(alvo) for padrao in _PADROES_INJECAO):
        if not any(termo in alvo for termo in TERMOS_DO_DOMINIO):
            return RespostaImediata(
                RECUSA_INJECAO.replace(MARCA_RAZAO_SOCIAL, contexto.razao_social),
                "injecao",
            )

    if any(termo in alvo for termo in _TERMOS_OFENSIVOS) and not any(
        termo in alvo for termo in TERMOS_DO_DOMINIO
    ):
        return RespostaImediata(
            RECUSA_FORA_DE_ESCOPO.replace(MARCA_RAZAO_SOCIAL, contexto.razao_social),
            "fora_de_escopo",
        )

    if any(padrao.search(alvo) for padrao in _PADROES_RECALCULO):
        valor = _valor_pertinente(pergunta, contexto)
        texto = (
            RECUSA_RECALCULO.format(valor=valor)
            if valor
            else RECUSA_RECALCULO_SEM_VALOR
        )
        return RespostaImediata(f"{texto}\n{_FONTE_MOTOR}", "recalculo")

    return None
