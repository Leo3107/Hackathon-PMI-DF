'use client';

/**
 * Orquestração das três etapas de `/nova-analise` (`03-ux-e-telas.md` §6).
 *
 * `entrada` → `pipeline` → resultado, na **mesma rota**, sem query string. A chamada ao motor é
 * **única**: `POST /api/due-diligence`. Os estágios são revelados em sequência apenas para
 * legibilidade, e nenhum deles é marcado como concluído sem o dado correspondente (§6.4) — a
 * conferência é `dadoDisponivel`, em `pipeline.ts`.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useReducedMotion } from '@/components/ui';
import { consultarDocumento } from '@/lib/api';
import type { Cliente, RespostaDueDiligence } from '@/types';

import { somenteDigitos } from './documento';
import {
  ESTAGIOS,
  INDICE_SCORE,
  PISO_ESTAGIO_MS,
  contadorDoEstagio,
  achadosDoEstagio,
  dadoDisponivel,
  duracaoDeExibicao,
  linhasDoRegistro,
  resultadoDoEstagio,
  statusAposRevelar,
  type DefinicaoEstagio,
  type ItemDeRegistro,
  type StatusEstagio,
} from './pipeline';

export type EtapaAnalise =
  /** Campo de documento e perfis demonstrativos. */
  | 'entrada'
  /** Requisição em voo: o pipeline já está na tela, com o primeiro estágio pulsando. */
  | 'consultando'
  /** Resposta recebida; os estágios são revelados conforme o dado de cada um. */
  | 'pipeline'
  /** Documento com DV válido e sem perfil no dataset (§6.5). */
  | 'nao_encontrado'
  /** Documento pertence a um cliente da carteira (§6.2). */
  | 'ja_na_carteira';

export interface EstadoDeEstagio {
  definicao: DefinicaoEstagio;
  status: StatusEstagio;
  achados: string[];
  contador: string;
}

export interface OpcoesConsulta {
  /** "Reanalisar mesmo assim": ignora o desvio de §6.2 e roda o pipeline. */
  forcarReanalise?: boolean;
}

export interface Analise {
  etapa: EtapaAnalise;
  documento: string;
  cliente: Cliente | null;
  resposta: RespostaDueDiligence | null;
  erro: unknown;
  estagios: EstadoDeEstagio[];
  registro: ItemDeRegistro[];
  consultar: (documento: string, opcoes?: OpcoesConsulta) => void;
  cancelar: () => void;
  tentarNovamente: () => void;
  voltarParaEntrada: () => void;
}

export function useAnalise(aoConcluir: (clienteId: string) => void): Analise {
  const reduzido = useReducedMotion();

  const [etapa, setEtapa] = useState<EtapaAnalise>('entrada');
  const [documento, setDocumento] = useState('');
  const [resposta, setResposta] = useState<RespostaDueDiligence | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [indice, setIndice] = useState(0);
  const [registro, setRegistro] = useState<ItemDeRegistro[]>([]);

  const abortador = useRef<AbortController | null>(null);
  const cancelado = useRef(false);
  const forcado = useRef(false);

  const encerrarRequisicao = useCallback(() => {
    abortador.current?.abort();
    abortador.current = null;
  }, []);

  useEffect(() => () => encerrarRequisicao(), [encerrarRequisicao]);

  const consultar = useCallback(
    (entrada: string, opcoes: OpcoesConsulta = {}) => {
      const digitos = somenteDigitos(entrada);
      if (digitos.length === 0) return;

      encerrarRequisicao();
      cancelado.current = false;
      forcado.current = opcoes.forcarReanalise ?? false;

      setDocumento(digitos);
      setResposta(null);
      setErro(null);
      setIndice(0);
      setRegistro([]);
      setEtapa('consultando');

      const controle = new AbortController();
      abortador.current = controle;

      consultarDocumento(digitos, controle.signal)
        .then((dados) => {
          if (cancelado.current) return;
          setResposta(dados);
          if (!dados.encontrado || !dados.cliente) {
            setEtapa('nao_encontrado');
            return;
          }
          if (dados.cliente.origem === 'CARTEIRA' && !forcado.current) {
            setEtapa('ja_na_carteira');
            return;
          }
          setEtapa('pipeline');
        })
        .catch((causa: unknown) => {
          if (cancelado.current) return;
          setErro(causa);
          setEtapa('pipeline');
        });
    },
    [encerrarRequisicao],
  );

  /** Aborta o `fetch` e volta à etapa 1 sem registrar nada (§6.4). */
  const cancelar = useCallback(() => {
    cancelado.current = true;
    encerrarRequisicao();
    setEtapa('entrada');
    setResposta(null);
    setErro(null);
    setIndice(0);
    setRegistro([]);
  }, [encerrarRequisicao]);

  const tentarNovamente = useCallback(() => {
    if (!documento) return;
    consultar(documento, { forcarReanalise: forcado.current });
  }, [consultar, documento]);

  const voltarParaEntrada = useCallback(() => {
    cancelado.current = true;
    encerrarRequisicao();
    setEtapa('entrada');
    setErro(null);
  }, [encerrarRequisicao]);

  // A falha é **derivada**, não guardada em estado: o estágio corrente falhou quando a resposta
  // chegou sem o dado dele. Guardar isso em `useState` obrigaria a um `setState` dentro do
  // efeito de revelação, que é exatamente o que dispara renderização em cascata.
  const emFalha =
    erro !== null ||
    (etapa === 'pipeline' &&
      resposta !== null &&
      indice <= INDICE_SCORE &&
      !dadoDisponivel(ESTAGIOS[indice], resposta));

  // Revelação sequencial. O estágio corrente pulsa enquanto `resposta` for nula — é exatamente
  // o comportamento exigido por §6.4 quando o motor demora.
  useEffect(() => {
    if (etapa !== 'pipeline' || resposta === null || emFalha) return;
    if (indice > INDICE_SCORE) return;

    const definicao = ESTAGIOS[indice];
    const espera = reduzido
      ? 0
      : duracaoDeExibicao(resultadoDoEstagio(resposta, definicao.id)?.duracaoMs);

    const temporizador = window.setTimeout(() => {
      setRegistro((anterior) => [
        ...anterior,
        ...linhasDoRegistro(definicao, resposta, new Date()),
      ]);
      setIndice((anterior) => anterior + 1);
    }, espera);

    return () => window.clearTimeout(temporizador);
  }, [etapa, resposta, indice, emFalha, reduzido]);

  // Concluído o estágio 7, a rota navega para a página do cliente (§6.6). Não existe quarta
  // tela de relatório: a página do cliente **é** o relatório.
  const clienteId = resposta?.cliente?.id ?? null;
  useEffect(() => {
    if (etapa !== 'pipeline' || emFalha || indice <= INDICE_SCORE || !clienteId) return;
    const temporizador = window.setTimeout(
      () => aoConcluir(clienteId),
      reduzido ? 0 : PISO_ESTAGIO_MS,
    );
    return () => window.clearTimeout(temporizador);
  }, [etapa, indice, emFalha, clienteId, aoConcluir, reduzido]);

  const estagios = useMemo<EstadoDeEstagio[]>(
    () =>
      ESTAGIOS.map((definicao, i) => {
        let status: StatusEstagio;
        if (i < indice) status = statusAposRevelar(definicao, resposta);
        else if (i === indice) status = emFalha ? 'falha' : 'consultando';
        else status = 'pendente';

        return {
          definicao,
          status,
          achados: status === 'pendente' ? [] : achadosDoEstagio(definicao, resposta),
          contador: contadorDoEstagio(definicao, status, resposta),
        };
      }),
    [indice, emFalha, resposta],
  );

  return {
    etapa,
    documento,
    cliente: resposta?.cliente ?? null,
    resposta,
    erro,
    estagios,
    registro,
    consultar,
    cancelar,
    tentarNovamente,
    voltarParaEntrada,
  };
}
