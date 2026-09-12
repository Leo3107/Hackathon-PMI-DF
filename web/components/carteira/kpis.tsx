'use client';

/**
 * Indicadores da carteira (`03-ux-e-telas.md` §2.3) e o contrato de drill-down de §2.7.
 *
 * **Uma informação lidera a tela**: a exposição que ficaria desprotegida se a carteira pedisse
 * recuperação judicial hoje. É o número que responde "quanto dinheiro está em jogo" e o que
 * nenhum concorrente mostra; por isso ocupa o corpo tipográfico maior da página. Os demais KPIs
 * são satélites — mesmo conteúdo de antes, um terço do peso visual, sem caixa e sem versalete.
 *
 * Nenhum número é calculado aqui (R6): tudo vem pronto do motor e a tela só formata. K4
 * continua sendo duas barras, dois rótulos e dois números — extraconcursal **nunca** soma com
 * total —, agora encostado no número-herói porque é ele que explica o tamanho da queda em RJ.
 */

import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

import { CLASSES_RISCO, ProgressBar, Termo, cn } from '@/components/ui';
import type { FamiliaRisco } from '@/components/ui';
import { formatarMoedaCompacta, formatarNumero, formatarPercentual } from '@/lib/format';
import type { EstadoCliente, ResumoCarteira, Severidade } from '@/types';

const ROTULO_ESTADO: Record<EstadoCliente, string> = {
  ATIVO: 'ativos',
  EM_OBSERVACAO: 'em observação',
  SUSPENSO: 'suspensos',
  RJ_EM_CURSO: 'RJ em curso',
  FALENCIA: 'em falência',
};

const ORDEM_ESTADO: EstadoCliente[] = [
  'ATIVO',
  'EM_OBSERVACAO',
  'SUSPENSO',
  'RJ_EM_CURSO',
  'FALENCIA',
];

const ROTULO_SEVERIDADE: Record<Severidade, string> = {
  CRITICA: 'críticos',
  ALTA: 'altos',
  MEDIA: 'médios',
  BAIXA: 'informativos',
};

const ORDEM_SEVERIDADE: Severidade[] = ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA'];

export interface KpisDaCarteiraProps {
  resumo: ResumoCarteira | null;
  carregando?: boolean;
}

export function KpisDaCarteira({ resumo, carregando = false }: KpisDaCarteiraProps) {
  const router = useRouter();
  const vazio = carregando || resumo === null;

  const moeda = (valor: number | undefined) =>
    vazio || valor === undefined ? '—' : formatarMoedaCompacta(valor);

  const estados = ORDEM_ESTADO.filter((estado) => (resumo?.clientesPorEstado?.[estado] ?? 0) > 0)
    .map(
      (estado) =>
        `${formatarNumero(resumo?.clientesPorEstado[estado] ?? 0)} ${ROTULO_ESTADO[estado]}`,
    )
    .join(' · ');

  const severidades = ORDEM_SEVERIDADE.filter(
    (severidade) => (resumo?.alertas30d?.porSeveridade?.[severidade] ?? 0) > 0,
  )
    .map(
      (severidade) =>
        `${formatarNumero(resumo?.alertas30d.porSeveridade[severidade] ?? 0)} ${ROTULO_SEVERIDADE[severidade]}`,
    )
    .join(' · ');

  return (
    <section
      aria-label="Indicadores da carteira"
      className="grid items-start gap-x-10 gap-y-6 xl:grid-cols-[minmax(300px,0.85fr)_minmax(0,1.6fr)]"
    >
      <div className="flex flex-col gap-4">
        {/* O número que lidera a tela — a leitura de K2 em cenário de RJ. */}
        <button
          type="button"
          onClick={() => router.push('/clientes?filtro=alta-exposicao&ordem=risco_rj')}
          aria-label="Exposição em risco em cenário de recuperação judicial — ver clientes ordenados por esse valor"
          className="group -mx-2 flex flex-col items-start gap-1 rounded-sm px-2 py-1 text-left"
        >
          {vazio ? (
            <span className="esqueleto h-14 w-64" aria-hidden="true" />
          ) : (
            <span className="type-score-xl transicao-controle text-fg-primary group-hover:text-accent-300">
              {moeda(resumo?.exposicaoEmRiscoEmRJ)}
            </span>
          )}
          <p className="max-w-[36ch] text-[14px]/[20px] text-fg-secondary">
            Exposição desprotegida se a carteira pedisse recuperação judicial hoje.
          </p>
        </button>

        <CoberturaPorGarantia
          extraconcursal={resumo?.coberturaExtraconcursal ?? 0}
          total={resumo?.coberturaTotal ?? 0}
          carregando={vazio}
          aoAbrir={() => router.push('/clientes?ordem=cobertura')}
        />
      </div>

      <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2 xl:border-l xl:border-line-subtle xl:pl-10">
        {/* K1 */}
        <Satelite
          valor={moeda(resumo?.exposicaoTotal)}
          rotulo="Exposição total a prazo"
          detalhe={
            vazio
              ? '—'
              : `${formatarNumero(resumo.totalClientes)} clientes · ${formatarMoedaCompacta(
                  resumo.exposicaoAVencer90d,
                )} a vencer em 90 dias`
          }
          carregando={vazio}
          aoClicar={() => router.push('/clientes?ordem=exposicao')}
        />

        {/* K2 */}
        <Satelite
          valor={moeda(resumo?.exposicaoEmRisco)}
          rotulo="Exposição em risco hoje"
          detalhe={
            vazio ? '—' : `${formatarPercentual(resumo.pctExposicaoEmRisco, 1)} da exposição total`
          }
          carregando={vazio}
          aoClicar={() => router.push('/clientes?filtro=alta-exposicao&ordem=risco_rj')}
        />

        {/* K3 */}
        <Satelite
          valor={moeda(resumo?.exposicaoCritica)}
          rotulo="Exposição crítica"
          familia={vazio ? undefined : 'd'}
          detalhe={
            vazio
              ? '—'
              : `${formatarNumero(resumo.clientesCriticos)} clientes rating D ou com veto · ${formatarPercentual(
                  resumo.pctExposicaoCritica,
                  1,
                )} do total`
          }
          carregando={vazio}
          aoClicar={() => router.push('/clientes?filtro=veto&ordem=exposicao')}
        />

        {/* K5 */}
        <Satelite
          valor={vazio ? '—' : formatarNumero(resumo.totalClientes)}
          rotulo="Clientes"
          detalhe={vazio ? '—' : estados.length > 0 ? estados : 'Sem quebra por estado'}
          carregando={vazio}
          aoClicar={() => router.push('/clientes')}
        />

        {/* K6 */}
        <Satelite
          valor={vazio ? '—' : formatarNumero(resumo.alertas30d.total)}
          rotulo="Alertas em 30 dias"
          detalhe={vazio ? '—' : severidades.length > 0 ? severidades : 'Nenhum alerta no período'}
          carregando={vazio}
          aoClicar={() => router.push('/alertas?periodo=30d')}
        />

        {/* K7 */}
        <Satelite
          valor={vazio ? '—' : formatarNumero(resumo.deterioracao.clientes)}
          rotulo="Deterioração relevante"
          familia={vazio || resumo.deterioracao.clientes === 0 ? undefined : 'c'}
          detalhe={
            vazio
              ? '—'
              : `Queda ≥ ${formatarNumero(resumo.deterioracao.limiarPontos)} pts em 90 dias · ${formatarNumero(
                  resumo.deterioracao.aceleradas,
                )} em deterioração acelerada`
          }
          carregando={vazio}
          aoClicar={() => router.push('/clientes?filtro=deterioracao&ordem=variacao')}
        />
      </div>
    </section>
  );
}

/**
 * Satélite: número, rótulo em caixa normal abaixo dele e a quebra em uma linha de apoio.
 * Sem borda e sem fundo — o que separa um do outro é o espaço, e o que os une é a régua
 * vertical à esquerda do bloco.
 */
function Satelite({
  valor,
  rotulo,
  detalhe,
  familia,
  carregando,
  aoClicar,
}: {
  valor: string;
  rotulo: string;
  detalhe?: ReactNode;
  familia?: FamiliaRisco;
  carregando: boolean;
  aoClicar: () => void;
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      aria-label={rotulo}
      className="transicao-controle -mx-2 flex flex-col items-start gap-0.5 rounded-sm px-2 py-1.5 text-left hover:bg-surface-hover"
    >
      {carregando ? (
        <span className="esqueleto h-6 w-28" aria-hidden="true" />
      ) : (
        <span className={cn('type-kpi', familia ? CLASSES_RISCO[familia].texto : 'text-fg-primary')}>
          {valor}
        </span>
      )}
      <span className="text-[13px]/[18px] text-fg-secondary">{rotulo}</span>
      {detalhe ? <span className="type-caption tnum">{detalhe}</span> : null}
    </button>
  );
}

/**
 * K4 — duas barras que **nunca** se somam. Continua clicável e continua carregando os dois
 * verbetes do glossário; é `role="link"` porque os botões de tooltip vivem dentro dele e botão
 * dentro de botão é HTML inválido.
 */
function CoberturaPorGarantia({
  extraconcursal,
  total,
  carregando,
  aoAbrir,
}: {
  extraconcursal: number;
  total: number;
  carregando: boolean;
  aoAbrir: () => void;
}) {
  return (
    <div
      role="link"
      tabIndex={0}
      aria-label="Cobertura por garantia — ver clientes ordenados por cobertura"
      onClick={aoAbrir}
      onKeyDown={(evento) => {
        if (evento.key === 'Enter' || evento.key === ' ') {
          evento.preventDefault();
          aoAbrir();
        }
      }}
      className="transicao-controle -mx-2 flex cursor-pointer flex-col gap-2.5 rounded-sm border-t border-line-subtle px-2 pt-3.5 pb-1 hover:bg-surface-hover"
    >
      {carregando ? (
        <>
          <span className="esqueleto h-8 w-full" aria-hidden="true" />
          <span className="esqueleto h-8 w-full" aria-hidden="true" />
        </>
      ) : (
        <>
          <ProgressBar
            valor={extraconcursal}
            rotulo="Cobertura extraconcursal"
            termo="EXTRACONCURSAL"
            altura={6}
            valorFormatado={formatarPercentual(extraconcursal, 0)}
          />
          <ProgressBar
            valor={total}
            rotulo="Cobertura total"
            termo="CONCURSAL"
            altura={6}
            valorFormatado={formatarPercentual(total, 0)}
          />
          <p className="type-caption max-w-[40ch]">
            Só a parcela extraconcursal sobrevive a um pedido de{' '}
            <Termo sigla="RJ">recuperação judicial</Termo>. As duas nunca se somam.
          </p>
        </>
      )}
    </div>
  );
}
