"""Declaração de operação do analista — Tarefa 3.

O CSV de features públicas (`data/mock/features_agro_mock.csv`) é só dado
público: exposição, garantias, operações e histórico de pagamento **não
existem nele** e não podem ser inventados. Quem os traz é o analista, por
documento — o valor da operação pretendida, as garantias oferecidas (tipo e
valor) e o prazo.

Sem declaração, a dimensão de garantias (e a exposição inteira) ficam
**cegas**: `adaptadores.cobertura` já sabe redistribuir o peso de uma
dimensão sem fonte, e é essa mesma mecânica que se aplica aqui — a "fonte" é
literalmente a proposta do analista (`FonteDaColeta.PROPOSTA_KRILL`).

Estado em memória do processo único (D3), do mesmo jeito que
`RepositorioEmMemoria` já guarda as decisões de auditoria: nada é persistido
em disco, e um único worker Flask é obrigatório (ver `api/app.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.enums import TipoGarantia
from models.exposicao import Garantia

__all__ = [
    "GarantiaDeclarada",
    "DeclaracaoDeOperacao",
    "RepositorioDeDeclaracoes",
    "normalizar_documento",
]


def normalizar_documento(documento: str) -> str:
    """Mantém só os dígitos — a chave de declaração ignora pontuação."""
    return "".join(caractere for caractere in documento if caractere.isdigit())


@dataclass(frozen=True)
class GarantiaDeclarada:
    """Tipo e valor de uma garantia oferecida. `natureza` e `valorAtualizado`
    continuam derivados do tipo pelo motor (`models.tabelas`) — não são
    digitados aqui."""

    tipo: TipoGarantia
    valor: float
    descricao: str = ""
    registrada: bool = True


@dataclass(frozen=True)
class DeclaracaoDeOperacao:
    """O que o analista declarou para um documento. Nunca inferido do CSV."""

    documento: str
    valor_operacao: float
    prazo_meses: int
    garantias: tuple[GarantiaDeclarada, ...] = ()
    #: Marca declarações criadas por `POST /api/carteira/semear` (Tarefa 3), para
    #: que a rota inversa possa limpar só a demonstração sem tocar em
    #: declarações reais que um analista tenha feito na mesma sessão.
    demonstracao: bool = False

    def garantias_do_motor(self, data_avaliacao: str) -> list[Garantia]:
        """`GarantiaDeclarada` → `Garantia` do motor, uma por item declarado."""
        chave = normalizar_documento(self.documento)
        return [
            Garantia(
                id=f"GAR-DECL-{chave}-{indice}",
                tipo=item.tipo,
                descricao=item.descricao,
                valor_declarado=item.valor,
                registrada=item.registrada,
                data_avaliacao=data_avaliacao,
            )
            for indice, item in enumerate(self.garantias, start=1)
        ]


class RepositorioDeDeclaracoes:
    """`documento normalizado -> DeclaracaoDeOperacao`. Sem banco (D3)."""

    def __init__(self) -> None:
        self._por_documento: dict[str, DeclaracaoDeOperacao] = {}

    def declarar(self, declaracao: DeclaracaoDeOperacao) -> DeclaracaoDeOperacao:
        self._por_documento[normalizar_documento(declaracao.documento)] = declaracao
        return declaracao

    def obter(self, documento: str) -> DeclaracaoDeOperacao | None:
        return self._por_documento.get(normalizar_documento(documento))

    def remover(self, documento: str) -> bool:
        return self._por_documento.pop(normalizar_documento(documento), None) is not None

    def documentos_declarados(self) -> list[str]:
        return list(self._por_documento)

    def limpar(self, *, apenas_demonstracao: bool = False) -> int:
        """Remove declarações. Devolve quantas foram removidas."""
        if not apenas_demonstracao:
            total = len(self._por_documento)
            self._por_documento.clear()
            return total
        alvos = [doc for doc, d in self._por_documento.items() if d.demonstracao]
        for documento in alvos:
            del self._por_documento[documento]
        return len(alvos)

    def __len__(self) -> int:
        return len(self._por_documento)
