'use client';

/**
 * Estados de falha e de carregamento das telas de carteira e de lista
 * (`03-ux-e-telas.md` §9.1, §9.2 e §9.4).
 *
 * R7: erro nunca é tela branca. Todo estado de falha nomeia a causa, diz a consequência para a
 * análise e oferece uma ação. O shell (`FaixaMotorIndisponivel`) cuida da faixa global; aqui
 * fica o segundo nível, o `ErrorState` no conteúdo, para quando a rota não tem nada a mostrar.
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
        <div className="flex flex-col gap-1">
          <p className="type-eyebrow text-risk-c">Motor de risco indisponível</p>
          <p className="max-w-[72ch] text-[13px]/[20px] text-fg-secondary">
            A interface do Lastro não calcula risco. Todos os scores, probabilidades, coberturas e
            recomendações vêm do serviço de cálculo em Python, que não está respondendo.
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

/**
 * Esqueleto da carteira com a **forma real** do conteúdo (§9.1): a lista de atenção imediata
 * com a primeira linha maior, o número-herói com as duas barras de cobertura ao lado dos seis
 * satélites, as duas colunas de gráfico e oito linhas fantasma de tabela.
 */
export function EsqueletoDaCarteira() {
  return (
    <div className="flex flex-col gap-8" aria-hidden="true">
      <div className="flex flex-col gap-2">
        <div className="esqueleto h-5 w-48" />
        <div className="esqueleto h-[76px] w-full" />
        <div className="esqueleto h-12 w-full" />
        <div className="esqueleto h-12 w-full" />
      </div>

      <div className="grid items-start gap-x-10 gap-y-6 xl:grid-cols-[minmax(300px,0.85fr)_minmax(0,1.6fr)]">
        <div className="flex flex-col gap-4">
          <div className="esqueleto h-14 w-64" />
          <div className="esqueleto h-24 w-full" />
        </div>
        <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="esqueleto h-[68px] w-full" />
          ))}
        </div>
      </div>

      <div className="grid items-start gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="esqueleto h-[300px]" />
        <div className="esqueleto h-[260px]" />
      </div>

      <div className="esqueleto h-[320px] rounded-md" />
    </div>
  );
}
