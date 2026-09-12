"""`/api/due-diligence` — fluxo A, o prospect consultado por documento (`03` §6).

Quatro desfechos:

| Situação | Status | Corpo |
|---|---|---|
| Documento malformado (DV inválido) | 400 | `{erro: CORPO_INVALIDO}` |
| Documento no dataset simulado | 200 | `{encontrado: true, origem: "SIMULADO", …}` |
| Documento achado na coleta pública | 200 | `{encontrado: true, origem: "COLETA_REAL", cobertura, …}` |
| Nenhuma das duas | 200 | `{encontrado: false, origem, cobertura?}` — §6.5 |

"Não encontrado" **não é erro**: é a tela mais didática do protótipo. Por isso
sai com 200 e `encontrado: false`, exatamente como `web/lib/api/cliente.ts` espera.

Os estágios do pipeline não são decorativos (§6.4). No caminho simulado, cada
estágio só é marcado como concluído porque o dado correspondente existe na
resposta do motor. No caminho real, quem decide é o **relatório de cobertura**:
um estágio verde significa que aquela fonte respondeu sobre aquele CNPJ.

────────────────────────────────────────────────────────────────────────────────
`origem` e `cobertura` não são metadados — são o produto
────────────────────────────────────────────────────────────────────────────────

Um score de 780 sobre sete dimensões apuradas e um score de 780 sobre duas são
números diferentes com o mesmo valor. A interface **precisa** distinguir "risco
baixo" de "não olhei", e `origem` + `cobertura` são o que permite isso. Ambos
são acrescentados ao payload já serializado porque `RespostaDueDiligence` vive
em `routes/agregados.py`, que pertence a outro workstream.
"""

from __future__ import annotations

from http import HTTPStatus

from adaptadores import (
    RelatorioDeCobertura,
    ResultadoDaAdaptacao,
    adaptar,
    coleta_padrao,
    montar_cliente_do_prospect,
)
from adaptadores.cobertura import StatusDimensao
from flask import Blueprint, current_app
from models.avaliacao import AvaliacaoDeRisco
from models.enums import DimensaoId, FonteId
from repository import so_digitos
from scoring import calcular_risco
from scoring.formatacao import numero

from .agregados import RespostaDueDiligence, ResultadoEstagio
from .comum import (
    corpo_da_requisicao,
    data_de_referencia,
    repositorio,
    resposta,
    serializar,
    serializar_agregado,
)
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

#: Rótulo de procedência. A interface **tem** de exibi-lo: o dataset simulado e
#: a coleta pública têm confiabilidades diferentes e nenhuma tela pode misturá-las.
ORIGEM_SIMULADO = "SIMULADO"
ORIGEM_COLETA_REAL = "COLETA_REAL"

#: Porta de coleta injetável, para a suíte rodar sem warehouse e sem rede.
CHAVE_COLETA = "lastro.coleta"


def porta_de_coleta():
    return current_app.extensions.get(CHAVE_COLETA) or coleta_padrao()


@due_diligence_bp.post("/api/due-diligence")
def consultar_documento():
    documento = _documento_do_corpo()
    repo = repositorio()

    cliente = repo.consultar_documento(documento)
    if cliente is not None:
        avaliacao = repo.avaliar(cliente.id)
        return resposta(
            _com_procedencia(
                RespostaDueDiligence(
                    encontrado=True,
                    documento=documento,
                    cliente=cliente,
                    avaliacao=avaliacao,
                    estagios=montar_estagios(avaliacao),
                ),
                origem=ORIGEM_SIMULADO,
            )
        )

    return _due_diligence_real(documento)


# ---------------------------------------------------------------------------
# Caminho real — coleta pública → adaptador → motor
# ---------------------------------------------------------------------------


def _due_diligence_real(documento: str):
    """Documento fora do dataset simulado: consulta a coleta de dados públicos.

    Dois desfechos, e a diferença entre eles é o relatório de cobertura:

    - a coleta não respondeu, ou respondeu com **todas** as dimensões cegas →
      `encontrado: false`. Um score montado sobre cegueira total não é uma nota
      baixa nem alta: é um número sem significado, e exibi-lo seria a mentira
      que este workstream existe para impedir.
    - ao menos uma dimensão apurada → avalia com os **pesos renormalizados** da
      cobertura e devolve a nota junto do que ficou de fora.
    """
    features = porta_de_coleta().features_de(documento)
    if features is None:
        return resposta(
            _com_procedencia(
                RespostaDueDiligence(encontrado=False, documento=documento, estagios=[]),
                origem=ORIGEM_COLETA_REAL,
            )
        )

    data_ref = data_de_referencia()
    cliente_id = f"prospect-real-{so_digitos(documento)}"
    resultado: ResultadoDaAdaptacao = adaptar(
        features,
        cliente_id=cliente_id,
        data_referencia=data_ref,
        valor_operacao_pretendida=_valor_pretendido_do_corpo(),
    )

    if not resultado.analisavel:
        return resposta(
            _com_procedencia(
                RespostaDueDiligence(encontrado=False, documento=documento, estagios=[]),
                origem=ORIGEM_COLETA_REAL,
                cobertura=resultado.cobertura,
            )
        )

    avaliacao = calcular_risco(
        resultado.fatos,
        config=resultado.config,
        data_referencia=data_ref,
        modelo_pd=resultado.modelo_pd,
    )
    return resposta(
        _com_procedencia(
            RespostaDueDiligence(
                encontrado=True,
                documento=documento,
                cliente=montar_cliente_do_prospect(
                    features, cliente_id=cliente_id, data_referencia=data_ref
                ),
                avaliacao=avaliacao,
                estagios=montar_estagios_da_cobertura(resultado.cobertura, avaliacao),
            ),
            origem=ORIGEM_COLETA_REAL,
            cobertura=resultado.cobertura,
        )
    )


def _com_procedencia(
    corpo: RespostaDueDiligence,
    *,
    origem: str,
    cobertura: RelatorioDeCobertura | None = None,
) -> dict:
    """Serializa o agregado e acrescenta `origem` e, quando houver, `cobertura`."""
    payload = serializar_agregado(corpo)
    payload["origem"] = origem
    if cobertura is not None:
        payload["cobertura"] = serializar(cobertura)
    return payload


def montar_estagios_da_cobertura(
    cobertura: RelatorioDeCobertura, avaliacao: AvaliacaoDeRisco
) -> list[ResultadoEstagio]:
    """Os mesmos oito estágios da §6.4, decididos pelo relatório de cobertura.

    Verde aqui significa exatamente uma coisa: **a fonte respondeu sobre este
    CNPJ**. Um estágio cinza não é falha do pipeline — é dimensão que não vota.
    """
    estagios: list[ResultadoEstagio] = []
    for indice, (estagio, rotulo, _fontes, exigidas) in enumerate(_PIPELINE_DE_FONTES):
        coberturas = [cobertura.de(dimensao) for dimensao in exigidas]
        apuradas = [c for c in coberturas if c.status is not StatusDimensao.CEGA]
        achados = [
            f"{fonte} · peso aplicado {numero(c.peso_aplicado * 100, 1)}%"
            for c in apuradas
            for fonte in c.fontes_apuradas
        ] or [c.justificativa for c in coberturas]
        estagios.append(
            ResultadoEstagio(
                estagio=estagio,
                rotulo=rotulo,
                status="ok" if len(apuradas) == len(coberturas) else "falha",
                achados=achados,
                duracaoMs=_DURACAO_BASE_MS + indice * _DURACAO_PASSO_MS,
            )
        )

    fechou = abs(avaliacao.auditoria.diferenca) <= TOLERANCIA_FECHAMENTO
    apuradas = len(cobertura.dimensoes_apuradas)
    estagios.append(
        ResultadoEstagio(
            estagio="SCORE",
            rotulo="Motor de Decisão & Scoring",
            status="ok" if fechou else "falha",
            achados=[
                f"Score {numero(avaliacao.score_calculado, 1)} · "
                f"rating final {avaliacao.rating_final.value}",
                f"Calculado sobre {apuradas} de {len(cobertura.dimensoes)} dimensões "
                f"({numero(cobertura.cobertura_ponderada * 100, 1)}% do peso canônico); "
                "o peso das cegas foi redistribuído entre as apuradas",
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


def _valor_pretendido_do_corpo() -> float | None:
    """Valor da operação pretendida. **Nunca** inventado: ou vem, ou não existe."""
    bruto = corpo_da_requisicao().get("valorOperacaoPretendida")
    if bruto is None:
        return None
    if not isinstance(bruto, (int, float)) or isinstance(bruto, bool) or bruto <= 0:
        raise ErroApi(
            CodigoErro.CORPO_INVALIDO,
            HTTPStatus.BAD_REQUEST,
            "`valorOperacaoPretendida` deve ser um número positivo.",
        )
    return float(bruto)


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
