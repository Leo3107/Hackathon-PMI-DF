"""Agregação da carteira — `03-ux-e-telas.md` §2.

Tudo aqui é **derivado** das avaliações individuais que o motor produziu. Não
há número novo: somatórios, contagens, razões e ordenações. O único texto
escrito no servidor é o das frases dos cartões de atenção, e mesmo ele carrega
apenas valores já calculados, formatados pelos formatadores da `scoring`.

Regra de seleção dos cartões, KPIs e concentrações seguem a spec §2.2–§2.6 na
ordem em que ela os define.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from models.enums import (
    EfeitoVeto,
    EstadoCliente,
    Rating,
    RiscoZarc,
    Severidade,
    StatusParcela,
    Tendencia,
)
from models.eventos import Alerta
from models.fatos import FatosDoCliente
from repository import ClienteNaoEncontrado, EstadoDeSessao, RepositorioEmMemoria
from scoring.formatacao import moeda, numero
from scoring.util import para_data

from .agregados import (
    CartaoDeAtencao,
    ClienteAvaliado,
    ContagemPorRating,
    FatiaDeConcentracao,
    LinhaDinheiroEmRisco,
    PontoMatrizDeRisco,
    ProximoVencimento,
    ResumoCarteira,
    ResumoDeAlertas,
    ResumoDeDeterioracao,
)

__all__ = [
    "avaliar_carteira",
    "montar_resumo",
    "proximo_vencimento",
    "zarc_por_cliente",
    "LIMIAR_DETERIORACAO_PONTOS",
]

#: `03` §2.3 K7 e §2.2 slot 2 — a mesma constante governa o KPI e o cartão.
LIMIAR_DETERIORACAO_PONTOS = 25.0
JANELA_ALERTAS_DIAS = 30
TOPO_CULTURAS = 5
TOPO_UFS = 6
LINHAS_DINHEIRO_EM_RISCO = 8
ROTULO_OUTRAS = "Outras"
HORA_DA_VARREDURA = "T06:00:00-03:00"

#: Da mais grave para a mais branda - ordem da pastilha de alertas da lista.
_ORDEM_DE_SEVERIDADE = (
    Severidade.CRITICA,
    Severidade.ALTA,
    Severidade.MEDIA,
    Severidade.BAIXA,
)

#: ZARC que merece o marcador de risco climatico na concentracao por cultura (V3).
_ZARC_ELEVADO = (RiscoZarc.ALTO, RiscoZarc.CRITICO)


def avaliar_carteira(
    repo: RepositorioEmMemoria, sessao: EstadoDeSessao
) -> list[ClienteAvaliado]:
    """Uma linha por cliente da carteira, com a avaliação recalculada agora."""
    alertas = repo.listar_alertas()
    nao_lidos = _alertas_nao_lidos_por_cliente(alertas)
    severidades = _severidade_maxima_por_cliente(alertas)
    linhas: list[ClienteAvaliado] = []
    for cliente in repo.listar_clientes():
        try:
            fatos = repo.obter_fatos_atuais(cliente.id)
        except ClienteNaoEncontrado:
            continue
        avaliacao = repo.avaliar_fatos(fatos, sessao)
        linhas.append(
            ClienteAvaliado(
                cliente=cliente,
                avaliacao=avaliacao,
                variacao90d=repo.comparacao_na_janela(cliente.id, avaliacao),
                alertasNaoLidos=nao_lidos.get(cliente.id, 0),
                proximoVencimento=proximo_vencimento(fatos, avaliacao.data_referencia),
                severidadeMaximaAlerta=severidades.get(cliente.id),
            )
        )
    return linhas


def proximo_vencimento(
    fatos: FatosDoCliente, data_referencia: str
) -> ProximoVencimento | None:
    """Parcela em atraso mais antiga; na falta dela, a proxima a vencer.

    A precedencia e do atraso porque e ele que decide a acao do analista - uma
    parcela vencida ha 40 dias importa mais que a que vence amanha. Exatamente
    um dos dois contadores e emitido.
    """
    referencia = para_data(data_referencia)
    parcelas = [
        parcela
        for operacao in fatos.operacoes
        for parcela in operacao.parcelas
        if parcela.vencimento
    ]
    em_atraso = [p for p in parcelas if p.status is StatusParcela.EM_ATRASO]
    if em_atraso:
        pior = min(em_atraso, key=lambda p: p.vencimento)
        dias = (referencia - para_data(pior.vencimento)).days
        return ProximoVencimento(
            data=pior.vencimento,
            diasAtraso=pior.dias_atraso if pior.dias_atraso is not None else max(dias, 0),
        )
    a_vencer = [
        p
        for p in parcelas
        if p.status is StatusParcela.A_VENCER and para_data(p.vencimento) >= referencia
    ]
    if not a_vencer:
        return None
    proxima = min(a_vencer, key=lambda p: p.vencimento)
    return ProximoVencimento(
        data=proxima.vencimento,
        diasRestantes=(para_data(proxima.vencimento) - referencia).days,
    )


def montar_resumo(
    linhas: list[ClienteAvaliado],
    alertas: list[Alerta],
    data_referencia: str,
    zarc_por_cliente: dict[str, RiscoZarc] | None = None,
) -> ResumoCarteira:
    exposicao_total = sum(l.avaliacao.exposicao.exposicao_total for l in linhas)
    criticos = [l for l in linhas if _e_critico(l)]
    exposicao_critica = sum(l.avaliacao.exposicao.exposicao_total for l in criticos)
    extraconcursal = sum(l.avaliacao.exposicao.valor_extraconcursal for l in linhas)
    concursal = sum(l.avaliacao.exposicao.valor_concursal for l in linhas)
    em_risco = sum(l.avaliacao.exposicao.exposicao_em_risco for l in linhas)
    em_risco_rj = sum(l.avaliacao.exposicao.exposicao_em_risco_em_rj for l in linhas)

    return ResumoCarteira(
        dataReferencia=data_referencia,
        ultimaVarredura=f"{data_referencia}{HORA_DA_VARREDURA}",
        atencaoImediata=_cartoes_de_atencao(linhas, alertas),
        exposicaoTotal=exposicao_total,
        exposicaoAVencer90d=sum(l.avaliacao.exposicao.a_vencer_90d for l in linhas),
        exposicaoEmRisco=em_risco,
        exposicaoEmRiscoEmRJ=em_risco_rj,
        exposicaoCritica=exposicao_critica,
        pctExposicaoEmRisco=_razao(em_risco, exposicao_total),
        pctExposicaoCritica=_razao(exposicao_critica, exposicao_total),
        clientesCriticos=len(criticos),
        coberturaExtraconcursal=_razao(extraconcursal, exposicao_total),
        coberturaTotal=_razao(extraconcursal + concursal, exposicao_total),
        totalClientes=len(linhas),
        clientesPorEstado=_por_estado(linhas),
        clientesPorRating=_por_rating(linhas),
        alertas30d=_alertas_recentes(alertas, data_referencia),
        deterioracao=_deterioracao(linhas),
        concentracaoPorCultura=_concentracao_por_cultura(
            linhas, exposicao_total, zarc_por_cliente or {}
        ),
        concentracaoPorUf=_concentracao_por_uf(linhas, exposicao_total),
        matrizDeRisco=[_ponto_da_matriz(l) for l in linhas],
        dinheiroEmRisco=_dinheiro_em_risco(linhas),
    )


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _razao(parte: float, total: float) -> float:
    return parte / total if total else 0.0


def _tem_veto(linha: ClienteAvaliado) -> bool:
    return bool(linha.avaliacao.vetos_ativos)


def _e_critico(linha: ClienteAvaliado) -> bool:
    """K3 — rating final D **ou** veto ativo. O veto é o que a tabela esconde."""
    return linha.avaliacao.rating_final is Rating.D or _tem_veto(linha)


def _delta_90d(linha: ClienteAvaliado) -> float | None:
    return linha.variacao_90d.delta_score if linha.variacao_90d else None


def _alertas_nao_lidos_por_cliente(alertas: list[Alerta]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for alerta in alertas:
        if not alerta.lido:
            contagem[alerta.cliente_id] = contagem.get(alerta.cliente_id, 0) + 1
    return contagem


def _severidade_maxima_por_cliente(alertas: list[Alerta]) -> dict[str, Severidade]:
    """Severidade do pior alerta **nao lido** de cada cliente."""
    pior: dict[str, Severidade] = {}
    for alerta in alertas:
        if alerta.lido:
            continue
        atual = pior.get(alerta.cliente_id)
        if atual is None or _ORDEM_DE_SEVERIDADE.index(
            alerta.severidade
        ) < _ORDEM_DE_SEVERIDADE.index(atual):
            pior[alerta.cliente_id] = alerta.severidade
    return pior


def _por_estado(linhas: list[ClienteAvaliado]) -> dict[EstadoCliente, int]:
    """Todas as chaves presentes: o contrato TS é `Record<EstadoCliente, number>`."""
    contagem = {estado: 0 for estado in EstadoCliente}
    for linha in linhas:
        contagem[linha.cliente.estado] += 1
    return contagem


def _por_rating(linhas: list[ClienteAvaliado]) -> dict[Rating, ContagemPorRating]:
    contagem = {rating: ContagemPorRating() for rating in Rating}
    for linha in linhas:
        alvo = contagem[linha.avaliacao.rating_final]
        alvo.clientes += 1
        alvo.exposicao += linha.avaliacao.exposicao.exposicao_total
    return contagem


def _alertas_recentes(alertas: list[Alerta], data_referencia: str) -> ResumoDeAlertas:
    corte = para_data(data_referencia) - timedelta(days=JANELA_ALERTAS_DIAS)
    por_severidade = {severidade: 0 for severidade in Severidade}
    total = 0
    for alerta in alertas:
        if para_data(alerta.data) < corte:
            continue
        total += 1
        por_severidade[alerta.severidade] += 1
    return ResumoDeAlertas(total=total, porSeveridade=por_severidade)


def _deterioracao(linhas: list[ClienteAvaliado]) -> ResumoDeDeterioracao:
    em_queda = sum(
        1
        for linha in linhas
        if (_delta_90d(linha) or 0.0) <= -LIMIAR_DETERIORACAO_PONTOS
    )
    aceleradas = sum(
        1
        for linha in linhas
        if linha.avaliacao.tendencia is Tendencia.DETERIORACAO_ACELERADA
    )
    return ResumoDeDeterioracao(
        clientes=em_queda,
        limiarPontos=LIMIAR_DETERIORACAO_PONTOS,
        aceleradas=aceleradas,
    )


@dataclass
class _Acumulador:
    """Uma fatia em construcao: dinheiro, dinheiro descoberto, clientes, clima."""

    exposicao: float = 0.0
    exposicao_em_risco: float = 0.0
    clientes: int = 0
    zarc_alto: bool = False

    def somar(self, outro: "_Acumulador") -> "_Acumulador":
        return _Acumulador(
            exposicao=self.exposicao + outro.exposicao,
            exposicao_em_risco=self.exposicao_em_risco + outro.exposicao_em_risco,
            clientes=self.clientes + outro.clientes,
            zarc_alto=self.zarc_alto or outro.zarc_alto,
        )


def _acumular(
    acumulado: dict[str, _Acumulador],
    rotulo: str,
    linha: ClienteAvaliado,
    zarc_alto: bool = False,
) -> None:
    atual = acumulado.setdefault(rotulo, _Acumulador())
    atual.exposicao += linha.avaliacao.exposicao.exposicao_total
    atual.exposicao_em_risco += linha.avaliacao.exposicao.exposicao_em_risco
    atual.clientes += 1
    atual.zarc_alto = atual.zarc_alto or zarc_alto


def _fatia(
    rotulo: str, dados: _Acumulador, total: float, com_zarc: bool
) -> FatiaDeConcentracao:
    return FatiaDeConcentracao(
        rotulo=rotulo,
        exposicao=dados.exposicao,
        pct=_razao(dados.exposicao, total),
        clientes=dados.clientes,
        exposicaoEmRisco=dados.exposicao_em_risco,
        zarcAlto=dados.zarc_alto if com_zarc else None,
    )


def _fatias(
    acumulado: dict[str, _Acumulador],
    total: float,
    topo: int,
    com_zarc: bool = False,
) -> list[FatiaDeConcentracao]:
    ordenado = sorted(acumulado.items(), key=lambda item: -item[1].exposicao)
    cabeca, cauda = ordenado[:topo], ordenado[topo:]
    fatias = [_fatia(rotulo, dados, total, com_zarc) for rotulo, dados in cabeca]
    if cauda:
        resto = _Acumulador()
        for _, dados in cauda:
            resto = resto.somar(dados)
        fatias.append(_fatia(ROTULO_OUTRAS, resto, total, com_zarc))
    return fatias


def _concentracao_por_cultura(
    linhas: list[ClienteAvaliado],
    total: float,
    zarc_dos_clientes: dict[str, RiscoZarc],
) -> list[FatiaDeConcentracao]:
    """V3 responde "se a soja quebrar, quanto é atingido?".

    A exposição do cliente é atribuída **inteira a cada cultura que ele planta**:
    a quebra de uma cultura ameaça o recebível todo, não uma fração dele. Por
    isso a soma das fatias pode exceder a exposição total — é a leitura correta
    da pergunta, e `pct` continua sendo a fração da carteira exposta àquela cultura.
    """
    acumulado: dict[str, _Acumulador] = {}
    for linha in linhas:
        elevado = zarc_dos_clientes.get(linha.cliente.id) in _ZARC_ELEVADO
        for cultura in linha.cliente.culturas or [ROTULO_OUTRAS]:
            _acumular(acumulado, cultura, linha, elevado)
    return _fatias(acumulado, total, TOPO_CULTURAS, com_zarc=True)


def _concentracao_por_uf(
    linhas: list[ClienteAvaliado], total: float
) -> list[FatiaDeConcentracao]:
    acumulado: dict[str, _Acumulador] = {}
    for linha in linhas:
        _acumular(acumulado, linha.cliente.uf, linha)
    return _fatias(acumulado, total, TOPO_UFS)


def _ponto_da_matriz(linha: ClienteAvaliado) -> PontoMatrizDeRisco:
    return PontoMatrizDeRisco(
        clienteId=linha.cliente.id,
        razaoSocial=linha.cliente.razao_social,
        pd12m=linha.avaliacao.pd.pd12m,
        exposicaoTotal=linha.avaliacao.exposicao.exposicao_total,
        exposicaoEmRiscoEmRJ=linha.avaliacao.exposicao.exposicao_em_risco_em_rj,
        rating=linha.avaliacao.rating_final,
        temVeto=_tem_veto(linha),
    )


def _dinheiro_em_risco(linhas: list[ClienteAvaliado]) -> list[LinhaDinheiroEmRisco]:
    ordenado = sorted(
        linhas,
        key=lambda l: -l.avaliacao.exposicao.exposicao_em_risco_em_rj,
    )[:LINHAS_DINHEIRO_EM_RISCO]
    return [
        LinhaDinheiroEmRisco(
            clienteId=linha.cliente.id,
            razaoSocial=linha.cliente.razao_social,
            uf=linha.cliente.uf,
            exposicaoTotal=linha.avaliacao.exposicao.exposicao_total,
            exposicaoEmRisco=linha.avaliacao.exposicao.exposicao_em_risco,
            exposicaoEmRiscoEmRJ=linha.avaliacao.exposicao.exposicao_em_risco_em_rj,
            rating=linha.avaliacao.rating_final,
            temVeto=_tem_veto(linha),
            tendencia=linha.avaliacao.tendencia,
        )
        for linha in ordenado
    ]


# -- Faixa de atenção imediata (§2.2) ---------------------------------------


def _cartao_de_veto(linha: ClienteAvaliado) -> CartaoDeAtencao:
    veto = linha.avaliacao.vetos_ativos[0] if linha.avaliacao.vetos_ativos else None
    causa = veto.rotulo if veto else f"Rating final {linha.avaliacao.rating_final.value}"
    return CartaoDeAtencao(
        motivo="VETO_ATIVO",
        eyebrow="VETO ATIVO",
        clienteId=linha.cliente.id,
        razaoSocial=linha.cliente.razao_social,
        causa=causa,
        numero=(
            f"{moeda(linha.avaliacao.exposicao.exposicao_em_risco_em_rj)} "
            "em risco em cenário de RJ"
        ),
        acao="Abrir cliente e revisar garantias",
        severidade=Severidade.CRITICA,
    )


def _cartao_de_queda(linha: ClienteAvaliado) -> CartaoDeAtencao:
    delta = _delta_90d(linha)
    causa = (
        f"Score caiu {numero(abs(delta), 0)} pontos em 90 dias"
        if delta is not None and delta <= -LIMIAR_DETERIORACAO_PONTOS
        else "Deterioração acelerada no trimestre"
    )
    return CartaoDeAtencao(
        motivo="MAIOR_QUEDA_90D",
        eyebrow="MAIOR QUEDA EM 90 DIAS",
        clienteId=linha.cliente.id,
        razaoSocial=linha.cliente.razao_social,
        causa=causa,
        numero=f"{moeda(linha.avaliacao.exposicao.exposicao_total)} de exposição total",
        acao="Ver o que mudou no score",
        severidade=Severidade.ALTA,
    )


def _cartao_de_alerta(alerta: Alerta) -> CartaoDeAtencao:
    return CartaoDeAtencao(
        motivo="ALERTA_CRITICO",
        eyebrow=f"ALERTA {alerta.severidade.value}",
        clienteId=alerta.cliente_id,
        razaoSocial=alerta.cliente_nome,
        causa=alerta.titulo,
        numero=alerta.impacto,
        acao=alerta.acao_recomendada,
        severidade=alerta.severidade,
    )


def _candidato_de_veto(linhas: list[ClienteAvaliado]) -> ClienteAvaliado | None:
    def por_risco_rj(candidatos: list[ClienteAvaliado]) -> ClienteAvaliado | None:
        if not candidatos:
            return None
        return max(
            candidatos, key=lambda l: l.avaliacao.exposicao.exposicao_em_risco_em_rj
        )

    forca_d = [
        linha
        for linha in linhas
        if any(v.efeito is EfeitoVeto.FORCA_D for v in linha.avaliacao.vetos_ativos)
    ]
    return por_risco_rj(forca_d) or por_risco_rj(
        [linha for linha in linhas if linha.avaliacao.rating_final is Rating.D]
    )


def _candidato_de_queda(linhas: list[ClienteAvaliado]) -> ClienteAvaliado | None:
    quedas = [
        linha
        for linha in linhas
        if (_delta_90d(linha) or 0.0) <= -LIMIAR_DETERIORACAO_PONTOS
    ]
    if quedas:
        return min(quedas, key=lambda l: _delta_90d(l) or 0.0)
    aceleradas = [
        linha
        for linha in linhas
        if linha.avaliacao.tendencia is Tendencia.DETERIORACAO_ACELERADA
    ]
    return aceleradas[0] if aceleradas else None


def _candidato_de_alerta(alertas: list[Alerta]) -> Alerta | None:
    for severidade in (Severidade.CRITICA, Severidade.ALTA):
        candidatos = [
            alerta
            for alerta in alertas
            if alerta.severidade is severidade and not alerta.lido
        ]
        if candidatos:
            return max(candidatos, key=lambda alerta: alerta.data)
    return None


def _cartoes_de_atencao(
    linhas: list[ClienteAvaliado], alertas: list[Alerta]
) -> list[CartaoDeAtencao]:
    """Três slots, ordem fixa, sem repetir cliente. Slot sem candidato é omitido."""
    cartoes: list[CartaoDeAtencao] = []
    usados: set[str] = set()

    veto = _candidato_de_veto(linhas)
    if veto is not None:
        cartoes.append(_cartao_de_veto(veto))
        usados.add(veto.cliente.id)

    queda = _candidato_de_queda([l for l in linhas if l.cliente.id not in usados])
    if queda is not None:
        cartoes.append(_cartao_de_queda(queda))
        usados.add(queda.cliente.id)

    alerta = _candidato_de_alerta(
        [alerta for alerta in alertas if alerta.cliente_id not in usados]
    )
    if alerta is not None:
        cartoes.append(_cartao_de_alerta(alerta))

    return cartoes


def zarc_por_cliente(repo: RepositorioEmMemoria) -> dict[str, RiscoZarc]:
    """Risco ZARC de cada cliente, lido dos fatos - o motor nao o republica."""
    resultado: dict[str, RiscoZarc] = {}
    for cliente in repo.listar_clientes():
        try:
            fatos = repo.obter_fatos_atuais(cliente.id)
        except ClienteNaoEncontrado:
            continue
        resultado[cliente.id] = fatos.agro.risco_zarc
    return resultado
