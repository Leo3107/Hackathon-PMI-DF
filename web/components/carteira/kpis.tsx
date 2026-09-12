'use client';

/**
 * Faixa de KPIs da carteira (`03-ux-e-telas.md` §2.3) e o contrato de drill-down de §2.7.
 *
 * Todo número vem pronto do motor (R6): a tela apenas formata com `lib/format.ts`. K4 é o
 * único tile de altura dupla, porque **nunca** soma extraconcursal com total — são duas barras,
 * dois rótulos, dois números e os dois verbetes do glossário.
 */

import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

import { Card, KpiTile, ProgressBar, Termo, cn } from '@/components/ui';
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

function Linhas({ itens }: { itens: ReactNode[] }) {
  return (
    <span className="flex flex-col gap-0.5">
      {itens.map((item, indice) => (
        <span key={indice} className="tnum">
          {item}
        </span>
      ))}
    </span>
  );
}

export interface KpisDaCarteiraProps {
  resumo: ResumoCarteira | null;
  carregando?: boolean;
}

export function KpisDaCarteira({ resumo, carregando = false }: KpisDaCarteiraProps) {
  const router = useRouter();
  const vazio = carregando || resumo === null;

  const moeda = (valor: number | undefined) =>
    vazio || valor === undefined ? '—' : formatarMoedaCompacta(valor);

  const estados = ORDEM_ESTADO.filter(
    (estado) => (resumo?.clientesPorEstado?.[estado] ?? 0) > 0,
  ).map((estado) => `${formatarNumero(resumo?.clientesPorEstado[estado] ?? 0)} ${ROTULO_ESTADO[estado]}`);

  const severidades = ORDEM_SEVERIDADE.filter(
    (severidade) => (resumo?.alertas30d?.porSeveridade?.[severidade] ?? 0) > 0,
  ).map(
    (severidade) =>
      `${formatarNumero(resumo?.alertas30d.porSeveridade[severidade] ?? 0)} ${ROTULO_SEVERIDADE[severidade]}`,
  );

  return (
    <section
      aria-label="Indicadores da carteira"
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      {/* K1 */}
      <KpiTile
        rotulo="Exposição total a prazo"
        valor={moeda(resumo?.exposicaoTotal)}
        carregando={vazio}
        aoClicar={() => router.push('/clientes?ordem=exposicao')}
        rodape={
          <Linhas
            itens={[
              vazio ? '—' : `${formatarNumero(resumo.totalClientes)} clientes`,
              vazio ? '—' : `A vencer em 90 dias: ${formatarMoedaCompacta(resumo.exposicaoAVencer90d)}`,
            ]}
          />
        }
      />

      {/* K2 */}
      <KpiTile
        rotulo="Exposição em risco"
        valor={moeda(resumo?.exposicaoEmRisco)}
        carregando={vazio}
        aoClicar={() => router.push('/clientes?filtro=alta-exposicao&ordem=risco_rj')}
        rodape={
          <Linhas
            itens={[
              vazio ? '—' : `${formatarPercentual(resumo.pctExposicaoEmRisco, 1)} da exposição total`,
              <span key="rj" className="text-fg-secondary">
                Em cenário de <Termo sigla="RJ" />:{' '}
                <span className="tnum font-medium">{moeda(resumo?.exposicaoEmRiscoEmRJ)}</span>
              </span>,
            ]}
          />
        }
      />

      {/* K3 */}
      <KpiTile
        rotulo="Exposição crítica"
        valor={moeda(resumo?.exposicaoCritica)}
        carregando={vazio}
        familia={vazio ? undefined : 'd'}
        aoClicar={() => router.push('/clientes?filtro=veto&ordem=exposicao')}
        rodape={
          <Linhas
            itens={[
              vazio
                ? '—'
                : `${formatarNumero(resumo.clientesCriticos)} clientes rating D ou com veto`,
              vazio ? '—' : `${formatarPercentual(resumo.pctExposicaoCritica, 1)} do total`,
            ]}
          />
        }
      />

      {/* K4 — altura dupla, duas barras, nunca somadas */}
      <CoberturaPorGarantia
        extraconcursal={resumo?.coberturaExtraconcursal ?? 0}
        total={resumo?.coberturaTotal ?? 0}
        carregando={vazio}
        aoAbrir={() => router.push('/clientes?ordem=cobertura')}
      />

      {/* K5 */}
      <KpiTile
        rotulo="Clientes"
        valor={vazio ? '—' : formatarNumero(resumo.totalClientes)}
        carregando={vazio}
        aoClicar={() => router.push('/clientes')}
        rodape={<Linhas itens={vazio ? ['—'] : estados.length > 0 ? estados : ['Sem quebra por estado']} />}
      />

      {/* K6 */}
      <KpiTile
        rotulo="Alertas em 30 dias"
        valor={vazio ? '—' : formatarNumero(resumo.alertas30d.total)}
        carregando={vazio}
        aoClicar={() => router.push('/alertas?periodo=30d')}
        rodape={
          <Linhas
            itens={vazio ? ['—'] : severidades.length > 0 ? severidades : ['Nenhum alerta no período']}
          />
        }
      />

      {/* K7 */}
      <KpiTile
        rotulo="Deterioração relevante"
        valor={vazio ? '—' : formatarNumero(resumo.deterioracao.clientes)}
        carregando={vazio}
        familia={vazio || resumo.deterioracao.clientes === 0 ? undefined : 'c'}
        aoClicar={() => router.push('/clientes?filtro=deterioracao&ordem=variacao')}
        rodape={
          <Linhas
            itens={
              vazio
                ? ['—']
                : [
                    `Queda ≥ ${formatarNumero(resumo.deterioracao.limiarPontos)} pts em 90 dias`,
                    `${formatarNumero(resumo.deterioracao.aceleradas)} em deterioração acelerada`,
                  ]
            }
          />
        }
      />
    </section>
  );
}

/**
 * K4 — não usa `KpiTile` porque o tile tem um único valor e este bloco tem dois, cada um com
 * sua barra, seu rótulo e seu verbete. Também não pode ser `<button>`: os botões de tooltip do
 * glossário vivem dentro dele, e botão dentro de botão é HTML inválido. Daí `role="link"`,
 * que é exatamente o que §2.7 pede para KPI clicável.
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
    <Card
      densidade="compacta"
      className={cn(
        'flex flex-col gap-3 xl:col-start-4 xl:row-span-2 xl:row-start-1',
        'transicao-controle cursor-pointer hover:border-line-strong hover:bg-surface-hover',
      )}
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
    >
      <span className="type-eyebrow">Cobertura por garantia</span>

      {carregando ? (
        <>
          <span className="esqueleto h-10 w-full" aria-hidden="true" />
          <span className="esqueleto h-10 w-full" aria-hidden="true" />
        </>
      ) : (
        <>
          <ProgressBar
            valor={extraconcursal}
            rotulo="Extraconcursal"
            termo="EXTRACONCURSAL"
            valorFormatado={formatarPercentual(extraconcursal, 0)}
          />
          <ProgressBar
            valor={total}
            rotulo="Total"
            termo="CONCURSAL"
            valorFormatado={formatarPercentual(total, 0)}
          />
          <p className="type-caption">
            A parcela extraconcursal é a que sobrevive a um pedido de recuperação judicial. As
            duas nunca se somam.
          </p>
        </>
      )}
    </Card>
  );
}
