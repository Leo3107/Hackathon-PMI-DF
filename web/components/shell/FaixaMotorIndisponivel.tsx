'use client';

/**
 * Faixa global de motor indisponível (`03-ux-e-telas.md` §9.4, nível 1).
 *
 * O Next é só interface: sem o Flask não há score, PD, RJ, exposição, alerta nem auditoria.
 * Este é o estado de falha mais provável durante a demonstração, e a regra é dura — **nunca
 * tela branca, e nunca número em cache apresentado como atual sem esta faixa por cima**.
 *
 * Comportamento:
 * - Aparece logo abaixo do banner de dados simulados, 32px, em todas as rotas com shell.
 * - Reconecta sozinha em backoff 2s → 4s → 8s → 16s → 30s fixos, exibindo a tentativa.
 * - Botão `Tentar agora` força uma sonda imediata.
 * - Ao voltar, some e confirma com um aviso efêmero, e a rota é revalidada.
 *
 * O shell continua renderizando por baixo: a navegação permanece utilizável e `/canvas` e
 * `/arquitetura` seguem íntegros, porque não dependem do motor.
 */

import { RotateCw, TriangleAlert } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { Button } from '@/components/ui';
import {
  assinarEstadoDoMotor,
  estadoDoMotor,
  registrarSucesso,
  verificarSaude,
  type EstadoDoMotor,
} from '@/lib/api';

const BACKOFF_MS = [2_000, 4_000, 8_000, 16_000, 30_000];

/** Snapshot de servidor estável: no SSR o motor é otimisticamente dado como de pé. */
const NO_SERVIDOR: EstadoDoMotor = { disponivel: true, ultimaRespostaOk: null, tentativas: 0 };

export function FaixaMotorIndisponivel() {
  const router = useRouter();
  // O cliente de API publica cada falha; a faixa só escuta (ver lib/api/disponibilidade.ts).
  const motor = useSyncExternalStore(assinarEstadoDoMotor, estadoDoMotor, () => NO_SERVIDOR);
  const caido = !motor.disponivel;
  const [tentativas, setTentativas] = useState(0);
  const [sondando, setSondando] = useState(false);
  const [reconectou, setReconectou] = useState(false);
  const timer = useRef<number | null>(null);

  const sondar = useCallback(async () => {
    setSondando(true);
    const saude = await verificarSaude();
    setSondando(false);
    if (saude.ok) {
      registrarSucesso();
      setTentativas(0);
      setReconectou(true);
      router.refresh();
      window.setTimeout(() => setReconectou(false), 5_000);
    } else {
      setTentativas((n) => n + 1);
    }
  }, [router]);

  useEffect(() => {
    if (!caido) {
      if (timer.current) window.clearTimeout(timer.current);
      return;
    }
    const espera = BACKOFF_MS[Math.min(tentativas, BACKOFF_MS.length - 1)];
    timer.current = window.setTimeout(() => void sondar(), espera);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [caido, tentativas, sondar]);

  if (reconectou && !caido) {
    return (
      <div
        role="status"
        className="flex h-8 w-full items-center justify-center gap-2 border-b border-line-default bg-surface-card px-4 type-caption text-fg-secondary"
      >
        Motor de risco reconectado.
      </div>
    );
  }

  if (!caido) return null;

  return (
    <div
      role="alert"
      className="flex h-8 w-full items-center gap-2 border-b border-line-strong bg-surface-raised px-4 type-caption text-fg-primary"
    >
      <TriangleAlert aria-hidden className="size-3.5 shrink-0 text-fg-secondary" />
      <span className="min-w-0 truncate">
        Motor de risco indisponível — os valores exibidos podem estar desatualizados.
        {sondando ? ' Reconectando…' : ` Nova tentativa em instantes`} (tentativa {tentativas || 1})
      </span>
      <span className="flex-1" />
      <Button
        tamanho="sm"
        variante="secundario"
        iconeEsquerda={RotateCw}
        carregando={sondando}
        onClick={() => void sondar()}
      >
        Tentar agora
      </Button>
    </div>
  );
}
