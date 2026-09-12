"""Harness de treino compartilhado pelos quatro modelos.

Um unico caminho de execucao para todos, porque comparar modelos treinados por
scripts diferentes compara os scripts, nao os modelos. O que cada script de
treino fornece e uma `Especificacao`: nome, como construir o estimador, e se a
familia lida com NaN nativamente e precisa de escala.

Sequencia:

    carregar -> diagnosticar dado -> split AGRUPADO por municipio
             -> CV agrupado (metricas por fold + out-of-fold)
             -> fit no treino inteiro -> calibrar (opcional)
             -> avaliar no holdout -> MLflow -> salvar bundle

Perda e metrica, que foi o pedido: os quatro otimizam ENTROPIA CRUZADA BINARIA
(`binary:logistic` no XGBoost, `binary` no LightGBM, `criterion='log_loss'` na
random forest, a propria verossimilhanca na logistica) e a metrica de selecao e
AUC. `logloss` aparece em todo relatorio ao lado do AUC de proposito: AUC alto
com logloss ruim e ordenacao boa com probabilidade errada, e um score de risco
que vai virar decisao de credito precisa das duas coisas.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.pipeline import Pipeline

from .. import artefatos, avaliacao, dados, preparo, rastreio

DIR_SAIDA = artefatos.DIR_ARTEFATOS
DIR_RELATORIOS = artefatos.DIR_ARTEFATOS.parent / "relatorios"


@dataclass(frozen=True)
class Especificacao:
    """O que distingue um script de treino do outro."""

    nome: str
    descricao: str
    construir: Callable[[argparse.Namespace, float], Any]
    # True para XGBoost e LightGBM: os boosters escolhem a direcao do NaN em
    # cada no, o que bate qualquer mediana que a gente imponha antes.
    nan_nativo: bool = False
    # True so para a logistica: sem padronizar, a penalidade l2 esmaga o
    # coeficiente de `capital_social` e poupa as flags.
    escalar: bool = False
    # Hiperparametros proprios da familia, adicionados ao parser comum.
    argumentos: Callable[[argparse.ArgumentParser], None] | None = None


# ----------------------------------------------------------------- argumentos --

def parser_base(descricao: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=descricao,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--dados", default=str(dados.MOCK_CSV),
        help="CSV de treino (separador ';')",
    )
    p.add_argument("--alvo", default=None, help="coluna-alvo; padrao: do esquema")
    p.add_argument("--folds", type=int, default=5, help="folds do CV agrupado")
    p.add_argument("--fracao-teste", type=float, default=0.2)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument(
        "--balancear", action="store_true",
        help="pesa a classe positiva (class_weight / scale_pos_weight). "
             "Melhora recall e PIORA a calibracao; deixe desligado se o numero "
             "do score vai ser lido como probabilidade",
    )
    p.add_argument(
        "--calibrar", choices=("nenhuma", "sigmoide", "isotonica"), default="nenhuma",
        help="calibracao em holdout agrupado separado do treino",
    )
    p.add_argument(
        "--sem-cv", action="store_true",
        help="pula o cross-validation (usar apenas para depurar o pipeline)",
    )
    p.add_argument(
        "--rapido", action="store_true",
        help="versao enxuta dos hiperparametros: gera artefato em segundos, "
             "nao serve para medir performance",
    )
    p.add_argument("--sufixo", default="", help="sufixo no nome do artefato")
    p.add_argument(
        "--nota", default="",
        help="texto anexado a observacao do bundle; use para marcar a natureza "
             "da run (ex.: artefato de fumaca, experimento de hiperparametro)",
    )
    p.add_argument(
        "--promover", action="store_true",
        help="aponta campeao.json para este modelo ao terminar",
    )
    p.add_argument("--sem-graficos", action="store_true")
    p.add_argument("--sem-mlflow", action="store_true")
    p.add_argument("--experimento", default=rastreio.EXPERIMENTO_PADRAO)
    p.add_argument("--tracking-uri", default=None)
    return p


# -------------------------------------------------------------- construcao ----

def montar_pipeline(spec: Especificacao, args: argparse.Namespace, prevalencia: float) -> Pipeline:
    """Preparo + estimador, num unico objeto que recebe coluna crua da coleta."""
    preprocessador = preparo.construir_preprocessador(
        nan_nativo=spec.nan_nativo, escalar=spec.escalar
    )
    estimador = spec.construir(args, prevalencia)
    return Pipeline([*preprocessador.steps, ("modelo", estimador)])


def peso_positivo(prevalencia: float) -> float:
    """negativos/positivos, para `scale_pos_weight` dos boosters."""
    prevalencia = min(max(prevalencia, 1e-6), 1 - 1e-6)
    return float((1 - prevalencia) / prevalencia)


def _calibrar(pipeline: Pipeline, args: argparse.Namespace, particao_treino):
    """Calibra em holdout AGRUPADO, separado do que treinou o modelo.

    `cv='prefit'` saiu do sklearn 1.8; o caminho atual e congelar o estimador
    com `FrozenEstimator` e ajustar so o calibrador. Calibrar no mesmo dado do
    treino nao calibra nada -- o modelo ja e otimista ali.
    """
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.frozen import FrozenEstimator

    metodo = {"sigmoide": "sigmoid", "isotonica": "isotonic"}[args.calibrar]
    interno = dados.separar_treino_teste(
        particao_treino.X_treino,
        particao_treino.y_treino,
        particao_treino.g_treino,
        fracao_teste=0.25,
        semente=args.semente,
    )
    base = clone(pipeline).fit(interno.X_treino, interno.y_treino)
    calibrado = CalibratedClassifierCV(FrozenEstimator(base), method=metodo)
    calibrado.fit(interno.X_teste, interno.y_teste)
    print(
        f"[calibracao] metodo={metodo} "
        f"ajuste={len(interno.y_treino)} calibracao={len(interno.y_teste)} linhas"
    )
    return calibrado, base


# ---------------------------------------------------------------- execucao ----

def executar(spec: Especificacao, argv: list[str] | None = None) -> dict[str, Any]:
    """Treina, avalia, registra e salva. Devolve o resumo para `treinar_todos`."""
    parser = parser_base(spec.descricao)
    if spec.argumentos is not None:
        spec.argumentos(parser)
    args = parser.parse_args(argv)
    nome = f"{spec.nome}{args.sufixo}"
    semente_np(args.semente)

    X, y, grupos = dados.carregar(args.dados, alvo=args.alvo or dados.esquema.ALVO)
    met_dados, tabela_dados = rastreio.metricas_de_dados(X, y, grupos)
    rastreio.imprimir_bloco(f"dado de entrada ({Path(args.dados).name})", met_dados)

    particao = dados.separar_treino_teste(
        X, y, grupos, fracao_teste=args.fracao_teste, semente=args.semente
    )
    resumo_split = particao.resumo()
    rastreio.imprimir_bloco("particao (agrupada por municipio)", resumo_split)
    if resumo_split["municipios_em_comum"]:
        # Nunca deveria acontecer com StratifiedGroupKFold; se acontecer, o AUC
        # do holdout esta inflado e avisar e melhor que publicar o numero.
        print("[ALERTA] municipio presente no treino E no teste: holdout vazando")

    prevalencia = float(particao.y_treino.mean())
    pipeline = montar_pipeline(spec, args, prevalencia)
    parametros = {
        "modelo": spec.nome,
        "dados": Path(args.dados).name,
        "folds": args.folds,
        "fracao_teste": args.fracao_teste,
        "semente": args.semente,
        "balancear": args.balancear,
        "calibrar": args.calibrar,
        "rapido": args.rapido,
        "nan_nativo": spec.nan_nativo,
        "escalar": spec.escalar,
        "perda": "binary_cross_entropy",
        "metrica_selecao": "auc",
        **{f"hp_{k}": v for k, v in pipeline.named_steps["modelo"].get_params().items()},
    }

    tags = {
        "familia": spec.nome,
        "alvo": args.alvo or dados.esquema.ALVO,
        "alvo_sintetico": str((args.alvo or dados.esquema.ALVO) == "alvo_sintetico"),
        "cv": "StratifiedGroupKFold/municipio_ibge",
    }

    with rastreio.run(
        nome, experimento=args.experimento, tracking_uri=args.tracking_uri,
        ativo=not args.sem_mlflow, tags=tags,
    ) as mlf:
        rastreio.logar_parametros(mlf, parametros)
        rastreio.logar_metricas(mlf, met_dados)
        rastreio.logar_metricas(mlf, {f"split_{k}": v for k, v in resumo_split.items()})
        rastreio.logar_quadro(mlf, tabela_dados, "preenchimento_por_coluna.csv")

        # --- cross-validation agrupado ------------------------------------
        met_cv: dict[str, Any] = {}
        por_fold = pd.DataFrame()
        if not args.sem_cv:
            print(f"\n[{nome}] CV agrupado em {args.folds} folds...")
            met_cv, por_fold = avaliacao.avaliar_cv(
                pipeline,
                particao.X_treino,
                particao.y_treino,
                particao.g_treino,
                dados.cv_agrupado(args.folds, args.semente),
            )
            met_cv.pop("oof_proba", None)
            rastreio.imprimir_bloco("cross-validation", {
                k: v for k, v in met_cv.items()
                if k.startswith(("cv_auc", "cv_logloss", "cv_ks", "oof_auc", "oof_logloss"))
            })
            rastreio.logar_metricas(mlf, met_cv)
            rastreio.logar_quadro(mlf, por_fold, f"metricas_por_fold_{nome}.csv")
            for linha in por_fold.to_dict("records"):
                rastreio.logar_metricas(
                    mlf, {"fold_auc": linha["auc"], "fold_logloss": linha["logloss"]},
                    passo=int(linha["fold"]),
                )

        # --- ajuste final -------------------------------------------------
        print(f"[{nome}] ajustando no treino completo ({len(particao.y_treino)} linhas)...")
        base = clone(pipeline).fit(particao.X_treino, particao.y_treino)
        final = base
        if args.calibrar != "nenhuma":
            final, base = _calibrar(pipeline, args, particao)

        # --- holdout ------------------------------------------------------
        p_teste = final.predict_proba(particao.X_teste)[:, 1]
        p_treino = final.predict_proba(particao.X_treino)[:, 1]
        met_teste = avaliacao.metricas(particao.y_teste, p_teste, prefixo="teste_")
        met_treino = avaliacao.metricas(particao.y_treino, p_treino, prefixo="treino_")
        rastreio.imprimir_bloco("holdout (municipios nunca vistos)", met_teste)
        rastreio.logar_metricas(mlf, met_teste)
        rastreio.logar_metricas(mlf, met_treino)

        # --- diagnostico do pipeline --------------------------------------
        importancia = avaliacao.tabela_de_importancia(base)
        if not importancia.empty:
            print("\ntop 12 features")
            print("---------------")
            print(importancia.head(12).to_string(index=False))
            rastreio.logar_quadro(mlf, importancia, f"importancia_{nome}.csv")

        # O teto de Bayes do alvo sintetico: da escala a todo AUC desta run.
        # Em dado real volta vazio, porque nao ha funcao geradora para reaplicar.
        teto = avaliacao.teto_do_alvo_sintetico(X, y)
        if teto:
            rastreio.imprimir_bloco("teto do alvo sintetico (AUC de Bayes)", teto)
            rastreio.logar_metricas(mlf, teto)
            if teto["teto_auc_bayes"] > 0 and met_teste["teste_auc"] == met_teste["teste_auc"]:
                fracao = met_teste["teste_auc"] / teto["teto_auc_bayes"]
                rastreio.logar_metricas(mlf, {"teste_auc_fracao_do_teto": fracao})
                print(f"  -> holdout esta a {fracao:.1%} do maximo alcancavel")

        # No mock, a unica conclusao honesta: o pre-processamento recuperou os
        # sinais do alvo fabricado?
        recuperacao = avaliacao.conferir_recuperacao_do_alvo(base)
        if recuperacao:
            rastreio.imprimir_bloco("recuperacao dos sinais do alvo sintetico", recuperacao)
            rastreio.logar_metricas(mlf, {
                k: v for k, v in recuperacao.items() if k.startswith("recuperacao")
            })

        if not args.sem_graficos:
            graficos = avaliacao.salvar_graficos(
                particao.y_teste, p_teste,
                DIR_RELATORIOS / nome,
                titulo=f"{nome} -- holdout agrupado",
            )
            rastreio.logar_arquivos(mlf, graficos, "graficos")

        # --- artefato -----------------------------------------------------
        bundle = artefatos.BundleModelo(
            nome=nome,
            pipeline=final,
            metricas={
                **{k: v for k, v in met_cv.items() if isinstance(v, float)},
                **met_teste,
                **{k: v for k, v in recuperacao.items() if k.startswith("recuperacao")},
                **teto,
            },
            parametros=parametros,
            alvo=args.alvo or dados.esquema.ALVO,
            prevalencia_treino=prevalencia,
            mlflow_run_id=(mlf.active_run().info.run_id if mlf else None),
            observacao=" | ".join(filter(None, (spec.descricao, args.nota))),
        )
        bundle.calibrar_faixas(p_treino)
        caminho = bundle.salvar(DIR_SAIDA, campeao=args.promover)
        print(f"\n[{nome}] artefato salvo em {caminho}")
        if args.promover:
            print(f"[{nome}] promovido a campeao (campeao.json)")

        rastreio.logar_arquivos(mlf, [caminho, DIR_SAIDA / f"{nome}.json"], "bundle")
        rastreio.logar_modelo(mlf, final, particao.X_teste)

    return {
        "nome": nome,
        "familia": spec.nome,
        "cv_auc_media": met_cv.get("cv_auc_media", float("nan")),
        "cv_auc_desvio": met_cv.get("cv_auc_desvio", float("nan")),
        "oof_auc": met_cv.get("oof_auc", float("nan")),
        "teste_auc": met_teste["teste_auc"],
        "teste_logloss": met_teste["teste_logloss"],
        "teste_ks": met_teste["teste_ks"],
        "teste_brier": met_teste["teste_brier"],
        "teste_aupr": met_teste["teste_aupr"],
        "teste_captura_top10": met_teste["teste_captura_top10"],
        "artefato": str(caminho),
    }


def semente_np(semente: int) -> None:
    """LightGBM e XGBoost consultam o estado global do numpy em alguns pontos."""
    np.random.seed(semente)


__all__ = ["DIR_RELATORIOS", "DIR_SAIDA", "Especificacao", "executar",
           "montar_pipeline", "parser_base", "peso_positivo"]
