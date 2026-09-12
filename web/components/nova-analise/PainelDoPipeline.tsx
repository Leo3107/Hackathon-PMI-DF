'use client';

/**
 * Etapa 2 de `/nova-analise` — o pipeline visual (§6.3 e §6.4).
 *
 * Cada estágio comunica seu estado por **três canais** (I8): cor, ícone de forma distinta
 * (`○ ◐ ✓ ⚠ ✗`) e texto — o nome do estágio mais o contador. Nada aqui decide quando um
 * estágio conclui: isso é `useAnalise` + `dadoDisponivel`, e o componente só desenha.
 */

import {
  Circle,
  CircleCheck,
  CircleX,
  LoaderCircle,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';

import { Button, Card, ErrorState, cn } from '@/components/ui';
import { textoDeErro } from '@/lib/api';
import { formatarDocumento } from '@/lib/format';
import type { Cliente } from '@/types';

import type { ItemDeRegistro, StatusEstagio } from './pipeline';
import type { EstadoDeEstagio } from './usar-analise';

interface Apresentacao {
  Icone: LucideIcon;
  /** Rótulo textual do estado — nunca comunicar só por cor (R2/I8). */
  rotulo: string;
  cor: string;
  girando?: boolean;
}

const APRESENTACAO: Record<StatusEstagio, Apresentacao> = {
  pendente: { Icone: Circle, rotulo: 'Pendente', cor: 'text-fg-tertiary' },
  consultando: {
    Icone: LoaderCircle,
    rotulo: 'Consultando',
    cor: 'text-accent-400',
    girando: true,
  },
  concluido: { Icone: CircleCheck, rotulo: 'Concluído', cor: 'text-risk-a' },
  sem_dado: { Icone: TriangleAlert, rotulo: 'Sem registro', cor: 'text-risk-b' },
  falha: { Icone: CircleX, rotulo: 'Falhou', cor: 'text-risk-d' },
};

export interface PainelDoPipelineProps {
  documento: string;
  cliente: Cliente | null;
  estagios: EstadoDeEstagio[];
  registro: ItemDeRegistro[];
  erro: unknown;
  aoCancelar: () => void;
  aoTentarNovamente: () => void;
  className?: string;
}

function Estagio({ estado, ordem }: { estado: EstadoDeEstagio; ordem: number }) {
  const { Icone, rotulo, cor, girando } = APRESENTACAO[estado.status];

  return (
    <li
      className={cn(
        'flex min-w-0 flex-col gap-1 rounded-md border border-line-subtle bg-surface-card p-3',
        estado.status === 'consultando' && 'border-accent-line',
      )}
      aria-label={`Estágio ${ordem}, ${estado.definicao.rotulo}: ${rotulo}. ${estado.contador}`}
    >
      <div className="flex items-center gap-1.5">
        <Icone
          size={16}
          strokeWidth={2}
          aria-hidden="true"
          className={cn('shrink-0', cor, girando && 'pipeline-spinner girando')}
        />
        <span className="type-eyebrow truncate text-fg-primary">{estado.definicao.rotulo}</span>
      </div>
      <span className={cn('type-caption', cor)}>{rotulo}</span>
      <ul className="flex flex-col">
        {estado.definicao.fontesExibidas.map((fonte) => (
          <li key={fonte} className="type-caption truncate text-fg-tertiary">
            {fonte}
          </li>
        ))}
      </ul>
      <span className="type-caption tnum text-fg-secondary">{estado.contador}</span>
    </li>
  );
}

export function PainelDoPipeline({
  documento,
  cliente,
  estagios,
  registro,
  erro,
  aoCancelar,
  aoTentarNovamente,
  className,
}: PainelDoPipelineProps) {
  const emFalha = erro !== null || estagios.some((estagio) => estagio.status === 'falha');
  const corrente = estagios.find((estagio) => estagio.status === 'consultando');

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <Card className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
        <div className="flex min-w-0 flex-col gap-1">
          <p className="type-eyebrow break-words text-fg-secondary">
            Analisando{' '}
            <span className="tnum text-fg-primary">
              {formatarDocumento(documento, { mascarar: false })}
            </span>
          </p>
          <p className="type-section-title truncate text-fg-primary">
            {cliente ? cliente.razaoSocial : 'Consultando bases…'}
          </p>
          {cliente ? (
            <p className="type-caption break-words">
              {cliente.municipio}/{cliente.uf} · {cliente.atividade}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button variante="secundario" onClick={aoCancelar} className="w-full sm:w-auto">
            Cancelar
          </Button>
        </div>
      </Card>

      {/*
        Em 390px duas colunas deixavam ~170px por estágio e os nomes das fontes truncavam;
        um estágio por linha lê inteiro. A partir de `sm` a grade volta ao que era.
      */}
      <ol
        aria-label="Estágios da coleta"
        aria-busy={!emFalha && corrente !== undefined}
        className="grid grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-4"
      >
        {estagios.map((estado, indice) => (
          <Estagio key={estado.definicao.id} estado={estado} ordem={indice + 1} />
        ))}
      </ol>

      <Card semPadding className="flex flex-col">
        <p className="type-eyebrow border-b border-line-subtle px-4 py-2 text-fg-secondary">
          Registro da coleta
        </p>
        <div className="scrollbar-thin max-h-[280px] overflow-y-auto">
          {registro.length === 0 && !corrente ? (
            <p className="type-caption px-4 py-3">Nenhuma linha registrada.</p>
          ) : (
            <ul className="flex flex-col">
              {/*
                No celular a hora e o estágio ocupam a primeira linha e o texto desce para a
                segunda (`basis-full`); a partir de `sm` os três voltam a uma linha só.
              */}
              {registro.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-line-subtle px-4 py-1.5 last:border-b-0 sm:flex-nowrap"
                >
                  <span className="type-mono tnum shrink-0 text-fg-tertiary">{item.hora}</span>
                  <span className="type-eyebrow w-[104px] shrink-0 text-fg-secondary">
                    {item.estagio}
                  </span>
                  <span className="type-caption min-w-0 basis-full break-words text-fg-primary sm:flex-1 sm:basis-auto">
                    {item.texto}
                  </span>
                </li>
              ))}
              {corrente ? (
                <li
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-4 py-1.5 sm:flex-nowrap"
                  aria-live="polite"
                  aria-atomic="true"
                >
                  <span className="type-mono tnum shrink-0 text-fg-tertiary">··:··:··</span>
                  <span className="type-eyebrow w-[104px] shrink-0 text-fg-secondary">
                    {corrente.definicao.rotulo}
                  </span>
                  <span className="type-caption min-w-0 basis-full break-words text-fg-secondary sm:flex-1 sm:basis-auto">
                    {corrente.definicao.fontesExibidas.join(' · ')} · consultando…
                  </span>
                </li>
              ) : null}
            </ul>
          )}
        </div>
      </Card>

      {emFalha ? (
        <ErrorState
          compacto
          titulo="A coleta foi interrompida"
          detalhe={
            erro
              ? textoDeErro(erro)
              : 'Um dos estágios não devolveu o dado correspondente, e nenhum estágio é marcado como concluído sem ele.'
          }
          aoTentarNovamente={aoTentarNovamente}
        />
      ) : null}
    </div>
  );
}
