'use client';

/**
 * Segundo nível do estado "motor fora do ar" (`03-ux-e-telas.md` §9.4): o conteúdo da rota não
 * tem nada a mostrar. O primeiro nível é a faixa global do shell, que continua no lugar.
 *
 * Vive em `components/alertas/` e é reusado por `/auditoria` — as duas telas são do mesmo
 * workstream e uma cópia só é melhor que três. Quando o erro **não** é indisponibilidade do
 * motor, cai no `ErrorState` do design system, que já traz causa, detalhe e "Tentar novamente".
 */

import { Network, RotateCcw } from 'lucide-react';
import Link from 'next/link';

import { Button, Card, ErrorState, cn } from '@/components/ui';
import { ErroLastro, estadoDoMotor, textoDeErro } from '@/lib/api';
import { formatarDataHora } from '@/lib/format';

const PASSOS = [
  'Verifique se o serviço está de pé: npm run dev',
  'Confirme a porta 5001 e a variável LASTRO_API_URL',
  'Consulte o terminal do serviço api/ para erros de inicialização',
];

export interface FalhaDoMotorProps {
  erro: unknown;
  aoTentarNovamente: () => void;
  /** Rótulo do conteúdo que falhou, usado no título genérico. */
  contexto?: string;
  className?: string;
}

export function FalhaDoMotor({
  erro,
  aoTentarNovamente,
  contexto = 'esta tela',
  className,
}: FalhaDoMotorProps) {
  const indisponivel = erro instanceof ErroLastro && erro.motorIndisponivel;

  if (!indisponivel) {
    return (
      <ErrorState
        className={className}
        titulo={`Não foi possível carregar ${contexto}`}
        detalhe={textoDeErro(erro)}
        aoTentarNovamente={aoTentarNovamente}
      />
    );
  }

  const ultima = estadoDoMotor().ultimaRespostaOk;

  return (
    <Card className={cn('flex flex-col gap-4', className)} destaque="c" role="alert">
      <div className="flex items-start gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-surface-input">
          <Network size={20} strokeWidth={1.75} className="text-risk-c" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1">
          <p className="type-eyebrow text-risk-c">Motor de risco indisponível</p>
          <p className="max-w-[72ch] text-[13px]/[20px] text-fg-secondary">
            A interface do Lastro não calcula risco. Alertas, scores, coberturas e a trilha de
            decisão vêm do serviço de cálculo em Python, que não está respondendo.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="type-label">O que fazer</p>
        <ol className="flex list-decimal flex-col gap-1 pl-5 text-[13px]/[20px] text-fg-secondary">
          {PASSOS.map((passo) => (
            <li key={passo}>{passo}</li>
          ))}
        </ol>
      </div>

      <p className="type-caption tnum">
        Última resposta bem-sucedida: {ultima ? formatarDataHora(ultima) : 'nenhuma nesta sessão'}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <Button variante="primario" iconeEsquerda={RotateCcw} onClick={aoTentarNovamente}>
          Tentar novamente
        </Button>
        <Link
          href="/arquitetura"
          className="transicao-controle inline-flex h-[var(--height-control)] items-center rounded-sm border border-line-default px-3 text-[13px] font-medium text-fg-secondary hover:border-line-strong hover:text-fg-primary"
        >
          Ver arquitetura do sistema
        </Link>
      </div>
    </Card>
  );
}
