'use client';

/**
 * Estado de falha da lista de clientes (`03-ux-e-telas.md` §9.1 e §9.4).
 *
 * R7: erro nunca é tela branca. Todo estado de falha nomeia a causa, diz a consequência para a
 * análise e oferece uma ação. O shell (`FaixaMotorIndisponivel`) cuida da faixa global; aqui
 * fica o segundo nível, o `ErrorState` no conteúdo, para quando a rota não tem nada a mostrar.
 */

import { Network, RotateCcw } from 'lucide-react';

import { Button, Card, ErrorState, cn } from '@/components/ui';
import { ErroLastro, estadoDoMotor, textoDeErro } from '@/lib/api';
import { formatarDataHora } from '@/lib/format';

const PASSOS = [
  'Verifique se o serviço está de pé: npm run dev',
  'Confirme a porta 5001 e a variável LASTRO_API_URL',
  'Consulte o terminal do serviço api/ para erros de inicialização',
];

export interface EstadoDeFalhaProps {
  erro: unknown;
  aoTentarNovamente: () => void;
  /** Rótulo do conteúdo que falhou, usado no título genérico. */
  contexto?: string;
  className?: string;
}

/**
 * Roteia entre o painel dedicado de "motor fora do ar" (§9.4) e o `ErrorState` genérico do
 * design system. O primeiro existe porque, sem o Flask, **nada** na tela tem valor: a interface
 * do Lastro não calcula risco.
 */
export function EstadoDeFalha({
  erro,
  aoTentarNovamente,
  contexto = 'esta tela',
  className,
}: EstadoDeFalhaProps) {
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
        <div className="flex min-w-0 flex-col gap-1">
          <p className="type-eyebrow text-risk-c">Motor de risco indisponível</p>
          <p className="max-w-[72ch] text-[13px]/[20px] break-words text-fg-secondary">
            A interface do Lastro não calcula risco. Todos os scores, probabilidades, coberturas e
            recomendações vêm do serviço de cálculo em Python, que não está respondendo.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="type-label">O que fazer</p>
        <ol className="flex list-decimal flex-col gap-1 pl-5 text-[13px]/[20px] break-words text-fg-secondary">
          {PASSOS.map((passo) => (
            <li key={passo}>{passo}</li>
          ))}
        </ol>
      </div>

      <p className="type-caption tnum">
        Última resposta bem-sucedida: {ultima ? formatarDataHora(ultima) : 'nenhuma nesta sessão'}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variante="primario"
          iconeEsquerda={RotateCcw}
          onClick={aoTentarNovamente}
          className="w-full sm:w-auto"
        >
          Tentar novamente
        </Button>
      </div>
    </Card>
  );
}
