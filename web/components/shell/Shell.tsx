'use client';

/**
 * Shell da aplicação (`03-ux-e-telas.md` §1.1 e §1.3).
 *
 * Empilhamento fixo, de cima para baixo:
 *
 * ```
 * FaixaMotorIndisponivel 32px  §9.4 — só aparece quando o Flask não responde
 * BarraSuperior          48px
 * BarraLateral 240px │ conteúdo · padding 24px · max-width 1440px
 * ```
 *
 * `/clientes/[id]/parecer` renderiza **sem** sidebar e sem topbar: é documento para impressão,
 * não tela de trabalho. A decisão fica aqui, no shell, e não no layout da rota, porque o layout
 * raiz é único.
 *
 * O copiloto de análise é montado aqui, fora do `<main>`, como widget flutuante: ele acompanha o
 * analista em toda rota de trabalho e some junto com o shell no parecer para impressão.
 */

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { BarraLateral } from './BarraLateral';
import { BarraSuperior } from './BarraSuperior';
import { CopilotoFlutuante } from './CopilotoFlutuante';
import { FaixaMotorIndisponivel } from './FaixaMotorIndisponivel';
import { rotaSemShell } from './rotas';

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (rotaSemShell(pathname)) return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col">
      <FaixaMotorIndisponivel />
      <div className="flex min-h-0 flex-1">
        <BarraLateral />
        <div className="flex min-w-0 flex-1 flex-col">
          <BarraSuperior />
          <main id="conteudo" className="min-w-0 flex-1 overflow-x-hidden">
            <div className="mx-auto w-full max-w-[1440px] p-6">{children}</div>
          </main>
        </div>
      </div>
      <CopilotoFlutuante />
    </div>
  );
}
