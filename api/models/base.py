"""Base comum a todos os modelos do Lastro.

Convenção obrigatória (ver `specs/02-motor-de-risco.md` §14):
campos internos em `snake_case`, serialização JSON em `camelCase` — exatamente
as chaves do contrato TypeScript de `specs/01-modelo-de-dados.md`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModeloLastro", "para_camel"]


def para_camel(nome: str) -> str:
    """Converte `snake_case` para `camelCase` preservando dígitos colados.

    Diferente de `pydantic.alias_generators.to_camel`, que transforma
    ``pd6m`` em ``pd6M`` e ``atraso_medio_dias_12m`` em ``atrasoMedioDias12M``.
    Aqui o corte acontece **apenas** no underscore, o que reproduz fielmente
    chaves do contrato como ``atrasoMedioDias12m`` e ``qsaEstavel5anos``.
    """
    primeiro, *resto = nome.split("_")
    return primeiro + "".join(parte[:1].upper() + parte[1:] for parte in resto)


class ModeloLastro(BaseModel):
    """Modelo base: aceita entrada em camelCase ou snake_case e emite camelCase.

    ``extra="ignore"`` é deliberado: o dataset simulado e as camadas de rota
    evoluem em paralelo e um campo desconhecido nunca pode derrubar o motor
    durante uma demonstração.
    """

    model_config = ConfigDict(
        alias_generator=para_camel,
        populate_by_name=True,
        extra="ignore",
        ser_json_inf_nan="constants",
    )

    def json_do_contrato(self) -> dict:
        """Dicionário pronto para virar o JSON da API, já em camelCase."""
        return self.model_dump(by_alias=True, mode="json")
