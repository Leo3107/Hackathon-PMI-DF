'use client';

/**
 * Estado do copiloto de análise (`03-ux-e-telas.md` §4.12).
 *
 * Mora no shell, e não na página do cliente, porque o copiloto virou widget global: a mesma
 * conversa é acessível de qualquer rota. O que **não** mudou é a regra de escopo — o motor
 * responde sobre **um** cliente por vez, então o `clienteId` continua sendo entrada obrigatória
 * do hook e carimbo da conversa.
 *
 * Como toda prosa do produto, a resposta chega por NDJSON e degrada sozinha: se o stream falhar,
 * o turno entra em erro local e nenhum número de nenhuma tela é afetado (regra R1).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  TEXTO_INICIAL,
  acumular,
  streamCopiloto,
  type TextoAcumulado,
} from '@/lib/api';
import type { EstadoStreaming } from '@/components/ui';
import type { EstadoDeSessaoApi, MensagemCopiloto } from '@/types';

export interface TurnoCopiloto {
  id: string;
  pergunta: string;
  resposta: string;
  estado: EstadoStreaming;
  origem: 'llm' | 'deterministico';
}

export interface Copiloto {
  turnos: TurnoCopiloto[];
  ocupado: boolean;
  perguntar: (pergunta: string) => void;
  limpar: () => void;
}

/** Histórico enviado ao modelo: máximo de 6 mensagens (`03-ux-e-telas.md` §4.12). */
const MAX_HISTORICO = 6;

export function useCopiloto(clienteId: string, sessao: EstadoDeSessaoApi): Copiloto {
  // A conversa é carimbada com o cliente a que pertence: trocar de rota zera o histórico por
  // derivação, sem um efeito que chame `setState` só para limpar.
  const [conversa, setConversa] = useState<{ clienteId: string; turnos: TurnoCopiloto[] }>({
    clienteId,
    turnos: [],
  });
  const [ocupado, setOcupado] = useState(false);
  const abortar = useRef<AbortController | null>(null);
  const turnos = useMemo(
    () => (conversa.clienteId === clienteId ? conversa.turnos : []),
    [conversa, clienteId],
  );

  useEffect(() => () => abortar.current?.abort(), []);

  const setTurnos = useCallback(
    (proximos: (atuais: TurnoCopiloto[]) => TurnoCopiloto[]) => {
      setConversa((atual) => ({
        clienteId,
        turnos: proximos(atual.clienteId === clienteId ? atual.turnos : []),
      }));
    },
    [clienteId],
  );

  const perguntar = useCallback(
    (pergunta: string) => {
      const texto = pergunta.trim();
      // Sem cliente em contexto não há o que perguntar: o motor exige `cliente_id`.
      if (!texto || !clienteId || ocupado) return;

      const id = `turno-${Date.now()}`;
      const historico: MensagemCopiloto[] = turnos
        .flatMap((t): MensagemCopiloto[] => [
          { papel: 'usuario', texto: t.pergunta },
          { papel: 'assistente', texto: t.resposta },
        ])
        .slice(-MAX_HISTORICO);

      setTurnos((atuais) => [
        ...atuais,
        { id, pergunta: texto, resposta: '', estado: 'aguardando', origem: 'deterministico' },
      ]);
      setOcupado(true);

      const controle = new AbortController();
      abortar.current = controle;

      void (async () => {
        let estado: TextoAcumulado = TEXTO_INICIAL;
        try {
          for await (const evento of streamCopiloto(
            { clienteId, sessao, pergunta: texto, historico },
            controle.signal,
          )) {
            estado = acumular(estado, evento);
            const instantaneo = estado;
            setTurnos((atuais) =>
              atuais.map((t) =>
                t.id === id
                  ? {
                      ...t,
                      resposta: instantaneo.texto,
                      origem: instantaneo.origem === 'openai' ? 'llm' : 'deterministico',
                      estado: instantaneo.erro
                        ? 'erro'
                        : instantaneo.concluido
                          ? instantaneo.degradou
                            ? 'degradado'
                            : 'concluido'
                          : instantaneo.texto
                            ? 'transmitindo'
                            : 'aguardando',
                    }
                  : t,
              ),
            );
          }
        } catch {
          setTurnos((atuais) =>
            atuais.map((t) => (t.id === id ? { ...t, estado: 'erro' } : t)),
          );
        } finally {
          if (abortar.current === controle) abortar.current = null;
          setOcupado(false);
        }
      })();
    },
    [clienteId, sessao, ocupado, turnos, setTurnos],
  );

  const limpar = useCallback(() => {
    abortar.current?.abort();
    setConversa({ clienteId, turnos: [] });
  }, [clienteId]);

  return { turnos, ocupado, perguntar, limpar };
}
