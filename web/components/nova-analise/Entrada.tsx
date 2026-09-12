'use client';

/**
 * Etapa 1 de `/nova-analise` — o campo de documento e os perfis de consulta rápida (§6.1, §6.2, §6.7).
 */

import { CircleAlert, CircleCheck, Search } from 'lucide-react';

import { Button, Card, RatingBadge, Termo, cn } from '@/components/ui';
import { formatarDocumento, formatarScore } from '@/lib/format';

import {
  PLACEHOLDER_DOCUMENTO,
  mascararDocumento,
  mensagemDoDocumento,
  type EstadoDocumento,
} from './documento';
import { ROTULO_PERFIL, type PerfilDemonstrativo } from './perfis';

export interface EntradaProps {
  valor: string;
  aoMudar: (valor: string) => void;
  estado: EstadoDocumento;
  aoConsultar: () => void;
  perfis: PerfilDemonstrativo[];
  carregandoPerfis: boolean;
  aoEscolherPerfil: (documento: string) => void;
  className?: string;
}

const CLASSE_FEEDBACK: Record<EstadoDocumento['situacao'], string> = {
  vazio: 'text-fg-tertiary',
  incompleto: 'text-fg-tertiary',
  invalido: 'text-risk-c',
  valido: 'text-risk-a',
};

export function Entrada({
  valor,
  aoMudar,
  estado,
  aoConsultar,
  perfis,
  carregandoPerfis,
  aoEscolherPerfil,
  className,
}: EntradaProps) {
  const podeConsultar = estado.situacao === 'valido';
  const mensagem = mensagemDoDocumento(estado);
  const Icone =
    estado.situacao === 'valido' ? CircleCheck : estado.situacao === 'invalido' ? CircleAlert : null;

  return (
    <div className={cn('flex flex-col gap-6', className)}>
      <header className="flex flex-col items-center gap-2 text-center">
        <h1 className="type-page-title text-fg-primary">Nova análise de crédito</h1>
        <p className="type-body max-w-[64ch] text-fg-secondary">
          Consulte um CPF ou CNPJ antes de conceder crédito a prazo, <Termo sigla="BARTER" /> ou{' '}
          <Termo sigla="CPR" />. A coleta percorre as bases cadastral, jurídica, fiscal, ambiental,
          agroclimática e o histórico interno.
        </p>
      </header>

      <Card className="mx-auto flex w-full max-w-[720px] flex-col gap-3">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(evento) => {
            evento.preventDefault();
            if (podeConsultar) aoConsultar();
          }}
        >
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <label className="type-label text-fg-secondary" htmlFor="documento-da-analise">
              CPF ou CNPJ
            </label>
            <input
              id="documento-da-analise"
              name="documento"
              inputMode="numeric"
              autoComplete="off"
              value={valor}
              aria-invalid={estado.situacao === 'invalido'}
              aria-describedby="feedback-do-documento"
              placeholder={PLACEHOLDER_DOCUMENTO}
              onChange={(evento) => aoMudar(mascararDocumento(evento.target.value))}
              className="transicao-controle type-num tnum h-[var(--height-control)] w-full rounded border border-line-default bg-surface-input px-3 text-fg-primary placeholder:text-fg-tertiary focus-visible:border-accent-line focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-400"
            />
          </div>
          <Button
            type="submit"
            variante="primario"
            iconeEsquerda={Search}
            disabled={!podeConsultar}
          >
            Consultar
          </Button>
        </form>

        <p
          id="feedback-do-documento"
          role="status"
          className={cn('type-caption flex items-center gap-1.5', CLASSE_FEEDBACK[estado.situacao])}
        >
          {Icone ? <Icone size={14} strokeWidth={2} aria-hidden="true" /> : null}
          {mensagem ?? 'Informe o documento do prospect para iniciar a coleta.'}
        </p>
      </Card>

      <section aria-label="Perfis para consulta rápida" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="type-eyebrow text-fg-secondary">
            Perfis para consulta rápida — clique para analisar
          </h2>
        </div>

        {carregandoPerfis ? (
          <div className="grid gap-3 md:grid-cols-3" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="esqueleto h-[120px] rounded-md" />
            ))}
          </div>
        ) : perfis.length === 0 ? (
          <Card densidade="compacta">
            <p className="type-caption">
              Os perfis vêm da base do motor de risco. Sem resposta do serviço de cálculo, digite
              um documento no campo acima.
            </p>
          </Card>
        ) : (
          <ul className="grid gap-3 md:grid-cols-3">
            {perfis.map(({ linha, perfil, naCarteira }) => (
              <li key={linha.cliente.id} className="contents">
                <Card
                  as="article"
                  interativo
                  densidade="compacta"
                  className="cursor-pointer"
                  role="button"
                  tabIndex={0}
                  aria-label={`Analisar ${linha.cliente.razaoSocial}, perfil ${ROTULO_PERFIL[perfil]}`}
                  onClick={() => aoEscolherPerfil(linha.cliente.documento)}
                  onKeyDown={(evento) => {
                    if (evento.key !== 'Enter' && evento.key !== ' ') return;
                    evento.preventDefault();
                    aoEscolherPerfil(linha.cliente.documento);
                  }}
                >
                  <div className="flex min-w-0 flex-col gap-1">
                    <p className="type-body-strong truncate text-fg-primary">
                      {linha.cliente.razaoSocial}
                    </p>
                    <p className="type-caption tnum">
                      {formatarDocumento(linha.cliente.documento, { mascarar: false })}
                    </p>
                    <p className="type-caption truncate">
                      {linha.cliente.municipio}/{linha.cliente.uf} ·{' '}
                      {linha.cliente.culturas[0] ?? linha.cliente.atividade}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <RatingBadge rating={linha.avaliacao.ratingFinal} tamanho="sm" />
                      <span className="type-caption tnum text-fg-secondary">
                        score {formatarScore(linha.avaliacao.scoreCalculado)}
                      </span>
                      <span className="type-caption text-fg-secondary">
                        Perfil: {ROTULO_PERFIL[perfil]}
                      </span>
                    </div>
                    {naCarteira ? (
                      <p className="type-caption text-fg-tertiary">
                        Já é cliente da carteira — a consulta abre a reanálise.
                      </p>
                    ) : null}
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
