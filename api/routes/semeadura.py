"""`/api/carteira/semear` e a rota inversa — Tarefa 3.

O CSV público não tem exposição, garantias nem operações: sem declaração do
analista, `RepositorioEmMemoria.listar_clientes` não devolve nenhum CNPJ (a
carteira é, por definição, o conjunto de documentos com declaração). Para a
demonstração não abrir vazia, esta rota declara operações **fictícias** para
uma amostra fixa de ~20 CNPJs, alguns de cada um dos 6 perfis de risco do
dataset — e diz isso explicitamente na resposta, para nunca passar por dado
real.
"""

from __future__ import annotations

from flask import Blueprint

from .comum import repositorio, resposta

semeadura_bp = Blueprint("semeadura", __name__)

AVISO_DEMONSTRACAO = (
    "Declarações de DEMONSTRAÇÃO: valor da operação, garantias e prazo são "
    "fictícios, criados só para a carteira não abrir vazia. Não representam "
    "operações reais nem foram informados por um analista."
)


@semeadura_bp.post("/api/carteira/semear")
def semear_carteira():
    repo = repositorio()
    documentos = repo.semear_carteira_de_demonstracao()
    return resposta(
        {
            "semeado": True,
            "aviso": AVISO_DEMONSTRACAO,
            "documentos": documentos,
            "totalDeclarado": len(documentos),
        }
    )


@semeadura_bp.post("/api/carteira/semear/limpar")
def limpar_semeadura():
    repo = repositorio()
    total = repo.limpar_declaracoes_de_demonstracao()
    return resposta({"limpo": True, "totalRemovido": total})
