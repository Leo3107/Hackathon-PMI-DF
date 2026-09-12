"""Suíte do `repository/` — a camada entre os fatos e o motor.

O pacote `api/data/` é escrito por outro workstream. Para que esta suíte não
dependa do calendário dele, o dataset de teste é montado aqui a partir dos
perfis de `tests/fixtures.py`, que já são `FatosDoCliente` reais e calibrados.
`fonte_de_teste()` é o stub mínimo previsto no briefing; quando `data/` existir,
nada aqui muda — `RepositorioEmMemoria` recebe a fonte por injeção.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from models.cliente import Cliente
from models.enums import (
    CodigoRecomendacao,
    DecisaoAnalista,
    EstadoCliente,
    FonteId,
    OrigemCliente,
    Rating,
    Severidade,
    StatusRedFlag,
    TipoEventoDeRisco,
    TipoPessoa,
)
from models.eventos import Alerta, EventoDeRisco, RegistroAuditoria, SnapshotHistorico
from repository import (
    ClienteNaoEncontrado,
    EstadoDeSessao,
    EventoSimulado,
    FonteDeDados,
    RepositorioEmMemoria,
    aplicar_eventos_simulados,
    divergiu_da_recomendacao,
    so_digitos,
)

from fixtures import DATA_REFERENCIA, serie_em_deterioracao, todos_os_perfis

# ---------------------------------------------------------------------------
# Stub de dataset — some quando `api/data/` existir
# ---------------------------------------------------------------------------

#: Município, UF e cultura por perfil. Reais, como manda D11.5.
_PERFIL_PARA_PRACA = {
    "excelente": ("Sorriso", "MT", ["Soja", "Milho safrinha"]),
    "moderado": ("Rio Verde", "GO", ["Soja"]),
    "em_deterioracao": ("Luís Eduardo Magalhães", "BA", ["Algodão", "Soja"]),
    "critico": ("Balsas", "MA", ["Soja"]),
    "veto_ambiental": ("Querência", "MT", ["Soja"]),
    "rj_com_stay_period": ("Cascavel", "PR", ["Milho"]),
    "pf_nao_elegivel_rj": ("Patrocínio", "MG", ["Café"]),
    "inadimplencia_tecnica": ("Dourados", "MS", ["Soja", "Milho safrinha"]),
    "pd_moderado_rj_alto": ("Uberaba", "MG", ["Cana-de-açúcar"]),
    "pd_alto_rj_baixo": ("Cruz Alta", "RS", ["Soja", "Arroz"]),
}

_PESOS_CNPJ = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_ID_DO_PROSPECT = "cli-prospect"


def _digito_verificador(digitos: list[int], pesos: list[int]) -> int:
    resto = sum(d * p for d, p in zip(digitos, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(base12: str) -> str:
    """Completa um CNPJ **simulado** com dígitos verificadores corretos (D11.5)."""
    digitos = [int(c) for c in base12]
    primeiro = _digito_verificador(digitos, _PESOS_CNPJ)
    segundo = _digito_verificador([*digitos, primeiro], [6, *_PESOS_CNPJ])
    numero = f"{base12}{primeiro}{segundo}"
    return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}"


def _cliente_de_teste(indice: int, nome: str, cliente_id: str) -> Cliente:
    municipio, uf, culturas = _PERFIL_PARA_PRACA.get(nome, ("Sorriso", "MT", ["Soja"]))
    pessoa_fisica = nome == "pf_nao_elegivel_rj"
    return Cliente(
        id=cliente_id,
        razaoSocial=f"Agro {nome.replace('_', ' ').title()} Ltda",
        documento=cnpj_valido(f"{11000000 + indice:08d}0001"),
        tipoPessoa=TipoPessoa.PF if pessoa_fisica else TipoPessoa.PJ,
        municipio=municipio,
        uf=uf,
        atividade="Produtor rural — grãos",
        cnaePrincipal="0111-3/01",
        culturas=culturas,
        inicioRelacionamento="2019-04-10",
        estado=(
            EstadoCliente.RJ_EM_CURSO
            if nome == "rj_com_stay_period"
            else EstadoCliente.ATIVO
        ),
        origem=OrigemCliente.CARTEIRA,
    )


def _snapshots(cliente_id: str, fatos):
    """Série do dataset. Só o perfil em deterioração tem história de verdade."""
    if cliente_id == "cli-deterioracao":
        return [
            SnapshotHistorico(data=instante.data_referencia, fatos=instante)
            for instante in serie_em_deterioracao()
        ]
    anterior_em = (date.fromisoformat(DATA_REFERENCIA) - timedelta(days=120)).isoformat()
    anterior = fatos.model_copy(deep=True)
    anterior.data_referencia = anterior_em
    return [
        SnapshotHistorico(data=anterior_em, fatos=anterior),
        SnapshotHistorico(data=fatos.data_referencia, fatos=fatos),
    ]


def _alertas() -> list[Alerta]:
    return [
        Alerta(
            id="alt-001",
            clienteId="cli-critico",
            clienteNome="Agro Critico Ltda",
            data=DATA_REFERENCIA,
            severidade=Severidade.CRITICA,
            titulo="Nova execução de título distribuída",
            descricao="Execução de título extrajudicial em 12/09/2026.",
            impacto="R$ 1.200.000 de exposição sem cobertura extraconcursal",
            acaoRecomendada="Suspender nova exposição a prazo.",
            lido=False,
        ),
        Alerta(
            id="alt-002",
            clienteId="cli-deterioracao",
            clienteNome="Agro Em Deterioracao Ltda",
            data="2026-09-01",
            severidade=Severidade.ALTA,
            titulo="Inscrição em dívida ativa da União",
            descricao="Novo débito inscrito na PGFN.",
            impacto="Certidões deixam de ser negativas",
            acaoRecomendada="Solicitar comprovação de parcelamento.",
            lido=False,
        ),
        Alerta(
            id="alt-003",
            clienteId="cli-moderado",
            clienteNome="Agro Moderado Ltda",
            data="2026-05-02",
            severidade=Severidade.MEDIA,
            titulo="Atraso de pagamento acima da média",
            descricao="Parcela liquidada com 11 dias de atraso.",
            impacto="Piora do fator comportamental",
            acaoRecomendada="Monitorar o próximo vencimento.",
            lido=True,
        ),
    ]


def fonte_de_teste() -> FonteDeDados:
    """Dataset mínimo: os 10 perfis da suíte do motor + 1 prospect."""
    clientes: list[Cliente] = []
    fatos_por_cliente = {}
    snapshots_por_cliente = {}

    for indice, (nome, fatos) in enumerate(todos_os_perfis()):
        cliente = _cliente_de_teste(indice, nome, fatos.cliente_id)
        clientes.append(cliente)
        fatos_por_cliente[cliente.id] = fatos
        snapshots_por_cliente[cliente.id] = _snapshots(cliente.id, fatos)

    prospect_fatos = todos_os_perfis()[1][1].model_copy(deep=True)
    prospect_fatos.cliente_id = _ID_DO_PROSPECT
    prospect = _cliente_de_teste(90, "moderado", _ID_DO_PROSPECT).model_copy(
        update={"origem": OrigemCliente.PROSPECT, "razao_social": "Nova Aliança Agro"}
    )
    fatos_por_cliente[_ID_DO_PROSPECT] = prospect_fatos
    snapshots_por_cliente[_ID_DO_PROSPECT] = _snapshots(_ID_DO_PROSPECT, prospect_fatos)

    eventos = {
        "cli-deterioracao": [
            EventoDeRisco(
                id="evt-001",
                clienteId="cli-deterioracao",
                data="2026-06-15",
                tipo=TipoEventoDeRisco.NOVA_EXECUCAO,
                severidade=Severidade.ALTA,
                titulo="Duas execuções de título distribuídas",
                descricao="Credores distintos ajuizaram execução no trimestre.",
                fonte=FonteId.DATAJUD_CNJ,
                scoreApos=0.0,
                deltaScore=0.0,
            ),
            EventoDeRisco(
                id="evt-002",
                clienteId="cli-deterioracao",
                data="2026-09-12",
                tipo=TipoEventoDeRisco.DIVIDA_ATIVA,
                severidade=Severidade.ALTA,
                titulo="Nova inscrição em dívida ativa",
                descricao="Saldo inscrito na PGFN cresceu no trimestre.",
                fonte=FonteId.PGFN,
                scoreApos=0.0,
                deltaScore=0.0,
            ),
        ]
    }

    auditoria = [
        RegistroAuditoria(
            id="aud-000",
            clienteId="cli-moderado",
            clienteNome="Agro Moderado Ltda",
            analista="Ana Ribeiro",
            dataHora="2026-08-20T14:02:00-03:00",
            scoreNoMomento=680.0,
            ratingNoMomento=Rating.B,
            recomendacaoGerada=CodigoRecomendacao.APROVAR_COM_RESTRICOES,
            decisaoAnalista=DecisaoAnalista.APROVAR_COM_RESTRICOES,
            justificativa="Limite mantido com reforço de garantia extraconcursal.",
            divergiuDaRecomendacao=False,
        )
    ]

    return FonteDeDados(
        clientes=clientes,
        prospects=[prospect],
        fatos_por_cliente=fatos_por_cliente,
        snapshots_por_cliente=snapshots_por_cliente,
        eventos_por_cliente=eventos,
        alertas=_alertas(),
        registros_auditoria=auditoria,
    )


@pytest.fixture
def repo() -> RepositorioEmMemoria:
    return RepositorioEmMemoria(fonte_de_teste())


# ---------------------------------------------------------------------------
# Fonte
# ---------------------------------------------------------------------------


def test_fonte_vazia_nao_derruba_o_repositorio():
    """`api/data/` ausente degrada para carteira vazia, nunca para exceção."""
    vazio = RepositorioEmMemoria(FonteDeDados())
    assert vazio.listar_clientes() == []
    assert vazio.listar_alertas() == []
    assert vazio.obter_cliente("qualquer") is None


def test_por_documento_ignora_pontuacao(repo: RepositorioEmMemoria):
    documento = repo.listar_clientes()[0].documento
    encontrado = repo.consultar_documento(so_digitos(documento))
    assert encontrado is not None
    assert encontrado.documento == documento


def test_prospect_e_alcancado_por_documento(repo: RepositorioEmMemoria):
    prospect = repo.fonte.prospects[0]
    assert repo.consultar_documento(prospect.documento) is not None
    #: Prospect não polui a carteira.
    assert prospect.id not in {c.id for c in repo.listar_clientes()}


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def test_cliente_inexistente_devolve_none(repo: RepositorioEmMemoria):
    assert repo.obter_cliente("cli-que-nao-existe") is None


def test_fatos_de_cliente_inexistente_levantam(repo: RepositorioEmMemoria):
    with pytest.raises(ClienteNaoEncontrado):
        repo.obter_fatos_atuais("cli-que-nao-existe")


def test_historico_de_cliente_inexistente_levanta(repo: RepositorioEmMemoria):
    with pytest.raises(ClienteNaoEncontrado):
        repo.obter_historico("cli-que-nao-existe")


def test_historico_vem_ordenado_e_completo(repo: RepositorioEmMemoria):
    historico = repo.obter_historico("cli-deterioracao")
    assert len(historico) >= 5
    assert [s.data for s in historico] == sorted(s.data for s in historico)


def test_eventos_recebem_score_recalculado(repo: RepositorioEmMemoria):
    """`scoreApos` e `deltaScore` são runtime, não dataset (spec 06 §3)."""
    eventos = repo.obter_eventos("cli-deterioracao")
    assert eventos, "o stub declara dois eventos para este cliente"
    assert all(evento.score_apos > 0 for evento in eventos)
    assert any(evento.delta_score != 0 for evento in eventos)
    #: Mais recente primeiro — é a ordem da linha do tempo.
    assert [e.data for e in eventos] == sorted((e.data for e in eventos), reverse=True)


# ---------------------------------------------------------------------------
# Avaliação e sessão
# ---------------------------------------------------------------------------


def test_avaliar_fecha_a_invariante_de_soma(repo: RepositorioEmMemoria):
    avaliacao = repo.avaliar("cli-moderado")
    assert abs(avaliacao.auditoria.diferenca) <= 0.5


def test_status_de_red_flag_da_sessao_e_aplicado(repo: RepositorioEmMemoria):
    avaliacao = repo.avaliar("cli-critico")
    assert avaliacao.red_flags, "o perfil crítico precisa de red flags"
    alvo = avaliacao.red_flags[0].id

    sessao = EstadoDeSessao(statusRedFlags={alvo: StatusRedFlag.ANALISADA})
    com_sessao = repo.avaliar("cli-critico", sessao)
    marcada = next(rf for rf in com_sessao.red_flags if rf.id == alvo)
    assert marcada.status is StatusRedFlag.ANALISADA


def test_comparacao_na_janela_fecha_a_invariante_i6(repo: RepositorioEmMemoria):
    avaliacao = repo.avaliar("cli-deterioracao")
    comparacao = repo.comparacao_na_janela("cli-deterioracao", avaliacao)
    assert comparacao is not None
    assert abs(comparacao.diferenca_de_fechamento) <= 0.5
    assert comparacao.delta_score != 0


# ---------------------------------------------------------------------------
# Simulação de evento (D10)
# ---------------------------------------------------------------------------


def test_simular_evento_muda_os_fatos_e_o_score(repo: RepositorioEmMemoria):
    antes = repo.avaliar("cli-excelente")
    fatos_novos = repo.simular_evento("cli-excelente", TipoEventoDeRisco.NOVA_EXECUCAO)
    depois = repo.avaliar_fatos(fatos_novos)
    assert depois.score_calculado < antes.score_calculado


def test_simulacao_nao_contamina_o_dataset(repo: RepositorioEmMemoria):
    original = repo.obter_fatos_atuais("cli-excelente").juridico.execucoes_titulo_12m
    repo.simular_evento("cli-excelente", TipoEventoDeRisco.NOVA_EXECUCAO)
    assert repo.obter_fatos_atuais("cli-excelente").juridico.execucoes_titulo_12m == original


@pytest.mark.parametrize("tipo", list(TipoEventoDeRisco))
def test_todo_tipo_de_evento_tem_mutacao_declarada(
    repo: RepositorioEmMemoria, tipo: TipoEventoDeRisco
):
    """Nenhum tipo pode estourar o motor durante a demonstração ao vivo."""
    fatos = repo.obter_fatos_atuais("cli-moderado")
    mutados = aplicar_eventos_simulados(fatos, [EventoSimulado(tipo=tipo)])
    assert repo.avaliar_fatos(mutados).score_calculado >= 0


def test_recalculo_e_o_unico_evento_neutro(repo: RepositorioEmMemoria):
    fatos = repo.obter_fatos_atuais("cli-moderado")
    antes = repo.avaliar_fatos(fatos).score_calculado
    mutados = aplicar_eventos_simulados(
        fatos, [EventoSimulado(tipo=TipoEventoDeRisco.RECALCULO)]
    )
    assert repo.avaliar_fatos(mutados).score_calculado == antes


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------


def _decisao(decisao: DecisaoAnalista) -> dict:
    return {
        "clienteId": "cli-moderado",
        "analista": "Ana Ribeiro",
        "scoreNoMomento": 604.0,
        "ratingNoMomento": "C",
        "recomendacaoGerada": "SUSPENDER_NOVA_EXPOSICAO_A_PRAZO",
        "decisaoAnalista": decisao.value,
        "justificativa": "Garantia extraconcursal suficiente para o ciclo.",
    }


def test_registro_e_carimbado_pelo_servidor(repo: RepositorioEmMemoria):
    registro = repo.registrar_decisao(_decisao(DecisaoAnalista.SUSPENDER))
    assert registro.id
    assert registro.data_hora
    assert registro.cliente_nome == "Agro Moderado Ltda"
    assert registro.divergiu_da_recomendacao is False


def test_divergencia_e_calculada_pela_tabela_de_equivalencia(
    repo: RepositorioEmMemoria,
):
    registro = repo.registrar_decisao(_decisao(DecisaoAnalista.APROVAR))
    assert registro.divergiu_da_recomendacao is True
    assert repo.listar_auditoria()[0].id == registro.id


@pytest.mark.parametrize(
    ("recomendacao", "decisao", "esperado"),
    [
        (CodigoRecomendacao.APROVAR, DecisaoAnalista.APROVAR, False),
        (CodigoRecomendacao.APROVAR, DecisaoAnalista.REVISAR, True),
        (
            CodigoRecomendacao.APROVAR_COM_MONITORAMENTO_INTENSIVO,
            DecisaoAnalista.APROVAR_COM_RESTRICOES,
            False,
        ),
        (
            CodigoRecomendacao.SUSPENDER_EXPOSICAO,
            DecisaoAnalista.RECUSAR,
            False,
        ),
        (
            CodigoRecomendacao.SUSPENDER_EXPOSICAO,
            DecisaoAnalista.APROVAR,
            True,
        ),
    ],
)
def test_tabela_de_divergencia(recomendacao, decisao, esperado):
    assert divergiu_da_recomendacao(recomendacao, decisao) is esperado
