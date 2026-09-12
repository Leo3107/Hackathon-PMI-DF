"""`/api/due-diligence` — fluxo A, o prospect consultado por documento (`03` §6).

Três desfechos, e só três:

| Situação | Status | Corpo |
|---|---|---|
| Documento malformado (DV inválido) | 400 | `{erro: CORPO_INVALIDO}` |
| Documento válido, sem perfil no dataset | 200 | `{encontrado: false, …}` — §6.5 |
| Documento válido, perfil encontrado | 200 | `{encontrado: true, cliente, avaliacao, estagios}` |

"Não encontrado" **não é erro**: é a tela mais didática do protótipo. Por isso
sai com 200 e `encontrado: false`, exatamente como `web/lib/api/cliente.ts` espera.

Os estágios do pipeline não são decorativos (§6.4): cada um só é marcado como
concluído porque o dado correspondente existe na resposta do motor. É a mesma
avaliação, particionada pelas fontes que a alimentaram.
"""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint
from models.avaliacao import AvaliacaoDeRisco
from models.enums import DimensaoId, FonteId
from repository import so_digitos
from scoring.formatacao import numero

from .agregados import RespostaDueDiligence, ResultadoEstagio
from .comum import corpo_da_requisicao, repositorio, resposta, serializar_agregado
from .erros import CodigoErro, ErroApi

due_diligence_bp = Blueprint("due_diligence", __name__)

TAMANHO_CPF = 11
TAMANHO_CNPJ = 14
TOLERANCIA_FECHAMENTO = 0.5
SEM_REGISTRO = "Nenhum registro encontrado"

#: (estágio, rótulo, fontes, dimensões que o estágio conclui) — `03` §6.4.
_PIPELINE_DE_FONTES = (
    (
        "CADASTRAL",
        "Cadastral",
        (FonteId.RECEITA_FEDERAL, FonteId.REDESIM),
        (DimensaoId.CADASTRAL,),
    ),
    (
        "JURIDICO",
        "Jurídico",
        (FonteId.DATAJUD_CNJ, FonteId.DJE, FonteId.CARTORIO_PROTESTO),
        (DimensaoId.JURIDICO,),
    ),
    (
        "FISCAL",
        "Fiscal",
        (FonteId.PGFN, FonteId.TST_CNDT, FonteId.CAIXA_CRF_FGTS),
        (DimensaoId.FISCAL,),
    ),
    (
        "AMBIENTAL",
        "Ambiental",
        (FonteId.SICAR, FonteId.IBAMA),
        (DimensaoId.AMBIENTAL,),
    ),
    (
        "AGROCLIMATICO",
        "Agroclimático",
        (FonteId.MAPA_ZARC, FonteId.CONAB, FonteId.INMET),
        (DimensaoId.AGROCLIMATICO,),
    ),
    (
        "INTERNO",
        "Interno Krill Tech",
        (FonteId.INTERNO_KRILLTECH,),
        (DimensaoId.COMPORTAMENTAL, DimensaoId.GARANTIAS),
    ),
)

_DURACAO_BASE_MS = 280
_DURACAO_PASSO_MS = 60


@due_diligence_bp.post("/api/due-diligence")
def consultar_documento():
    documento = _documento_do_corpo()
    repo = repositorio()
    cliente = repo.consultar_documento(documento)
    if cliente is None:
        return resposta(
            serializar_agregado(
                RespostaDueDiligence(encontrado=False, documento=documento, estagios=[])
            )
        )

    avaliacao = repo.avaliar(cliente.id)
    return resposta(
        serializar_agregado(
            RespostaDueDiligence(
                encontrado=True,
                documento=documento,
                cliente=cliente,
                avaliacao=avaliacao,
                estagios=montar_estagios(avaliacao),
            )
        )
    )


def montar_estagios(avaliacao: AvaliacaoDeRisco) -> list[ResultadoEstagio]:
    """Oito estágios derivados da avaliação já calculada, nunca temporizados."""
    dimensoes = {dimensao.id for dimensao in avaliacao.dimensoes}
    estagios: list[ResultadoEstagio] = []

    for indice, (estagio, rotulo, fontes, exigidas) in enumerate(_PIPELINE_DE_FONTES):
        achados = [
            f"{evidencia.nome_fonte} · {evidencia.titulo}"
            for evidencia in avaliacao.evidencias
            if evidencia.fonte in fontes
        ]
        completo = all(dimensao in dimensoes for dimensao in exigidas)
        estagios.append(
            ResultadoEstagio(
                estagio=estagio,
                rotulo=rotulo,
                status="ok" if completo else "falha",
                achados=achados or [SEM_REGISTRO],
                duracaoMs=_DURACAO_BASE_MS + indice * _DURACAO_PASSO_MS,
            )
        )

    fechou = abs(avaliacao.auditoria.diferenca) <= TOLERANCIA_FECHAMENTO
    estagios.append(
        ResultadoEstagio(
            estagio="SCORE",
            rotulo="Motor de Decisão & Scoring",
            status="ok" if fechou else "falha",
            achados=[
                f"Score {numero(avaliacao.score_calculado, 1)} · "
                f"rating final {avaliacao.rating_final.value}",
                f"Soma das contribuições fecha com diferença de "
                f"{numero(abs(avaliacao.auditoria.diferenca), 2)} ponto(s)",
            ],
            duracaoMs=_DURACAO_BASE_MS,
        )
    )
    estagios.append(
        ResultadoEstagio(
            estagio="RELATORIO",
            rotulo="Agente Sintetizador",
            status="ok",
            achados=["Narrativa gerada sob demanda pela camada de linguagem"],
            duracaoMs=0,
        )
    )
    return estagios


def _documento_do_corpo() -> str:
    bruto = corpo_da_requisicao().get("documento")
    if not isinstance(bruto, str) or not bruto.strip():
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "`documento` é obrigatório.",
        )
    documento = bruto.strip()
    if not documento_valido(documento):
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "CPF ou CNPJ inválido: verifique o número e o dígito verificador.",
        )
    return documento


# ---------------------------------------------------------------------------
# Dígito verificador — a mesma regra que gerou os documentos do dataset (D11.5)
# ---------------------------------------------------------------------------


def _digito(digitos: list[int], pesos: list[int]) -> int:
    resto = sum(d * p for d, p in zip(digitos, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(documento: str) -> bool:
    digitos = [int(caractere) for caractere in documento]
    if len(digitos) != TAMANHO_CPF or len(set(digitos)) == 1:
        return False
    primeiro = _digito(digitos[:9], list(range(10, 1, -1)))
    segundo = _digito(digitos[:10], list(range(11, 1, -1)))
    return digitos[9] == primeiro and digitos[10] == segundo


def cnpj_valido(documento: str) -> bool:
    digitos = [int(caractere) for caractere in documento]
    if len(digitos) != TAMANHO_CNPJ or len(set(digitos)) == 1:
        return False
    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_segundo = [6, *pesos_primeiro]
    primeiro = _digito(digitos[:12], pesos_primeiro)
    segundo = _digito(digitos[:13], pesos_segundo)
    return digitos[12] == primeiro and digitos[13] == segundo


def documento_valido(documento: str) -> bool:
    apenas_digitos = so_digitos(documento)
    if len(apenas_digitos) == TAMANHO_CPF:
        return cpf_valido(apenas_digitos)
    if len(apenas_digitos) == TAMANHO_CNPJ:
        return cnpj_valido(apenas_digitos)
    return False
