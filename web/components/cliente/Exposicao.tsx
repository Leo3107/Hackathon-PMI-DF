'use client';

/**
 * Exposição e garantias (`03-ux-e-telas.md` §4.8).
 *
 * O bloco existe para responder uma pergunta que nenhum bureau responde: **quanto a Krill Tech
 * perde de proteção se o cliente pedir recuperação judicial amanhã**. Por isso as coberturas
 * nunca aparecem somadas em um único número — `EXTRACONCURSAL` e `CONCURSAL` são linhas
 * separadas, com a diferença jurídica escrita, e `exposicaoEmRiscoEmRJ` ganha caixa própria.
 */

import { Lock, LockOpen, ShieldAlert, Wallet } from 'lucide-react';
import { useState } from 'react';

import {
  Badge,
  Button,
  CLASSES_RISCO,
  Card,
  DataTable,
  Drawer,
  NATUREZA_GARANTIA,
  ProgressBar,
  SectionHeader,
  StackedBar,
  Termo,
  type Coluna,
} from '@/components/ui';
import {
  formatarData,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarPercentual,
} from '@/lib/format';
import type {
  ExposicaoCalculada,
  FatosDoCliente,
  Garantia,
  Operacao,
  Parcela,
  TipoGarantia,
  TipoOperacao,
} from '@/types';

/** Frase fixa da §10.5 — é a explicação jurídica do número em destaque. */
export const FRASE_RISCO_EM_RJ =
  'O penhor entra no plano de recuperação com deságio; a alienação fiduciária, não.';

const ROTULO_OPERACAO: Record<TipoOperacao, string> = {
  VENDA_A_PRAZO: 'Venda a prazo',
  BARTER: 'Barter',
  CPR: 'CPR',
};

const ROTULO_GARANTIA: Record<TipoGarantia, string> = {
  ALIENACAO_FIDUCIARIA: 'Alienação fiduciária',
  CPR_FINANCEIRA: 'CPR financeira',
  CPR_FISICA: 'CPR física',
  PENHOR_SAFRA: 'Penhor de safra',
  PENHOR_MAQUINA: 'Penhor de máquina',
  HIPOTECA: 'Hipoteca',
  AVAL_FIANCA: 'Aval / fiança',
};

const ROTULO_PARCELA: Record<Parcela['status'], string> = {
  A_VENCER: 'A vencer',
  PAGA: 'Paga',
  EM_ATRASO: 'Em atraso',
};

export interface BlocoExposicaoProps {
  exposicao: ExposicaoCalculada;
  fatos: FatosDoCliente | null;
}

export function BlocoExposicao({ exposicao, fatos }: BlocoExposicaoProps) {
  const [operacoesAbertas, setOperacoesAbertas] = useState(false);
  const garantias = fatos?.garantias ?? [];
  const operacoes = fatos?.operacoes ?? [];
  const temEmbargada = garantias.some((g) => g.bemEmbargado === true);

  const pctEmRiscoEmRj =
    exposicao.exposicaoTotal > 0
      ? exposicao.exposicaoEmRiscoEmRJ / exposicao.exposicaoTotal
      : 0;

  return (
    <Card
      id="exposicao"
      as="section"
      aria-labelledby="titulo-exposicao"
      className="scroll-mt-[88px]"
    >
      <SectionHeader
        nivel={2}
        titulo="Exposição e garantias"
        descricao="Quanto está na rua, quanto está protegido e o que a proteção vale em cenário de recuperação judicial."
        meta={<Wallet size={14} strokeWidth={2} aria-hidden="true" />}
      />
      <h2 id="titulo-exposicao" className="sr-only">
        Exposição e garantias
      </h2>

      {/* Linha de números ------------------------------------------------ */}
      <dl className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Numero rotulo="Exposição total" valor={formatarMoeda(exposicao.exposicaoTotal, { casas: 0 })} forte />
        <Numero rotulo="Limite aprovado" valor={formatarMoeda(exposicao.limiteAprovado, { casas: 0 })} />
        <div className="flex flex-col gap-1">
          <dt className="type-eyebrow text-fg-tertiary">Utilização do limite</dt>
          <dd>
            <ProgressBar
              valor={exposicao.limiteUtilizadoPct}
              rotulo="Utilização do limite aprovado"
              familia={exposicao.limiteUtilizadoPct > 0.85 ? 'd' : 'neutral'}
              valorFormatado={formatarPercentual(exposicao.limiteUtilizadoPct, 0)}
              altura={8}
            />
          </dd>
        </div>
        <Numero rotulo="A vencer em 90 dias" valor={formatarMoeda(exposicao.aVencer90d, { casas: 0 })} />
        <Numero
          rotulo="Em atraso"
          valor={formatarMoeda(exposicao.emAtraso, { casas: 0 })}
          familia={exposicao.emAtraso > 0 ? 'd' : undefined}
        />
        <Numero
          rotulo="Exposição em risco"
          valor={formatarMoeda(exposicao.exposicaoEmRisco, { casas: 0 })}
          familia={exposicao.exposicaoEmRisco > 0 ? 'c' : undefined}
        />
      </dl>

      {/* Barra de proteção ------------------------------------------------ */}
      <div className="mt-4">
        <StackedBar
          total={exposicao.exposicaoTotal}
          altura={16}
          legenda="abaixo"
          destaque="em-risco"
          formatarValor={(valor) => formatarMoedaCompacta(valor)}
          aria-label={`Exposição total de ${formatarMoeda(exposicao.exposicaoTotal, { casas: 0 })}: ${formatarMoeda(exposicao.exposicaoProtegida, { casas: 0 })} protegida por garantia e ${formatarMoeda(exposicao.exposicaoEmRisco, { casas: 0 })} em risco.`}
          segmentos={[
            {
              id: 'protegida',
              rotulo: 'Protegida por garantia',
              valor: exposicao.exposicaoProtegida,
              familia: 'a',
            },
            {
              id: 'em-risco',
              rotulo: 'Em risco',
              valor: exposicao.exposicaoEmRisco,
              familia: 'd',
            },
          ]}
        />
      </div>

      {/* Coberturas separadas --------------------------------------------- */}
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Cobertura
          titulo={<Termo sigla="EXTRACONCURSAL">Extraconcursal</Termo>}
          Icone={Lock}
          familia="a"
          valor={exposicao.valorExtraconcursal}
          cobertura={exposicao.coberturaExtraconcursal}
          explicacao="Fica fora do plano de recuperação: a excussão segue possível mesmo em RJ."
        />
        <Cobertura
          titulo={<Termo sigla="CONCURSAL">Concursal</Termo>}
          Icone={LockOpen}
          familia="c"
          valor={exposicao.valorConcursal}
          cobertura={exposicao.coberturaTotal - exposicao.coberturaExtraconcursal}
          explicacao="Entra no plano de recuperação e é paga com deságio e prazo do quadro-geral."
        />
      </div>
      <p className="type-caption mt-2">
        Cobertura total {formatarPercentual(exposicao.coberturaTotal, 0)} — exibida apenas como
        soma declarada. A decisão de crédito usa as duas linhas acima separadas: em RJ, elas valem
        coisas diferentes.
      </p>

      {/* Exigência 3 — o número que muda a decisão -------------------------- */}
      <div
        data-teste="exposicao-em-risco-em-rj"
        className="mt-4 flex flex-col gap-1 rounded border-2 border-risk-d-line bg-risk-d-tint px-4 py-3"
      >
        <p className="type-eyebrow inline-flex items-center gap-1.5 text-risk-d">
          <ShieldAlert size={14} strokeWidth={2.5} aria-hidden="true" />
          Em risco se pedir RJ amanhã
        </p>
        <p className="type-kpi tnum flex flex-wrap items-baseline gap-x-3 text-fg-primary">
          {formatarMoeda(exposicao.exposicaoEmRiscoEmRJ, { casas: 0 })}
          <span className="type-body-strong text-fg-secondary">
            {formatarPercentual(pctEmRiscoEmRj, 0)} da exposição total
          </span>
        </p>
        <p className="type-body text-fg-secondary">{FRASE_RISCO_EM_RJ}</p>
      </div>

      {/* Tabela de garantias ----------------------------------------------- */}
      <div className="mt-4">
        <h3 className="type-eyebrow mb-2 text-fg-secondary">Garantias ({garantias.length})</h3>
        {/*
          A tabela tem largura mínima por coluna; em tela estreita ela rola de lado. As margens
          negativas compensam o padding do `Card` (p-4) para a rolagem chegar até a borda.
        */}
        {/* A rolagem lateral e a sangria em telas estreitas são da própria DataTable. */}
        <div className="min-w-0">
          <DataTable<Garantia>
            aria-label="Garantias oferecidas pelo cliente"
            densidade="densa"
            linhas={garantias}
            obterId={(linha) => linha.id}
            colunas={colunasDeGarantia(temEmbargada)}
            vazio={
              <p className="type-caption p-3">
                Nenhuma garantia registrada. A exposição está integralmente descoberta.
              </p>
            }
          />
        </div>
      </div>

      {/* Operações --------------------------------------------------------- */}
      <div className="mt-4 border-t border-line-subtle pt-3">
        <h3 className="type-eyebrow mb-2 text-fg-secondary">Operações por tipo</h3>
        <ul className="flex flex-wrap gap-x-6 gap-y-1">
          {(Object.keys(ROTULO_OPERACAO) as TipoOperacao[]).map((tipo) => (
            <li key={tipo} className="type-body flex items-baseline gap-2">
              <span className="text-fg-secondary">
                {tipo === 'BARTER' ? (
                  <Termo sigla="BARTER">Barter</Termo>
                ) : tipo === 'CPR' ? (
                  <Termo sigla="CPR">CPR</Termo>
                ) : (
                  ROTULO_OPERACAO[tipo]
                )}
              </span>
              <span className="tnum text-fg-primary">
                {formatarMoeda(exposicao.porTipoOperacao[tipo] ?? 0, { casas: 0 })}
              </span>
            </li>
          ))}
        </ul>
        {operacoes.length > 0 ? (
          <Button
            variante="fantasma"
            tamanho="sm"
            className="mt-2"
            onClick={() => setOperacoesAbertas(true)}
          >
            {`Ver todas as ${operacoes.length} operações e parcelas →`}
          </Button>
        ) : null}
      </div>

      <DrawerDeOperacoes
        aberto={operacoesAbertas}
        aoFechar={() => setOperacoesAbertas(false)}
        operacoes={operacoes}
      />
    </Card>
  );
}

function Numero({
  rotulo,
  valor,
  forte,
  familia,
}: {
  rotulo: string;
  valor: string;
  forte?: boolean;
  familia?: 'c' | 'd';
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="type-eyebrow text-fg-tertiary">{rotulo}</dt>
      <dd
        className={`tnum ${forte ? 'type-kpi' : 'type-body-strong'} ${
          familia ? CLASSES_RISCO[familia].texto : 'text-fg-primary'
        }`}
      >
        {valor}
      </dd>
    </div>
  );
}

function Cobertura({
  titulo,
  Icone,
  familia,
  valor,
  cobertura,
  explicacao,
}: {
  titulo: React.ReactNode;
  Icone: typeof Lock;
  familia: 'a' | 'c';
  valor: number;
  cobertura: number;
  explicacao: string;
}) {
  const classes = CLASSES_RISCO[familia];
  return (
    <div className="flex flex-col gap-1.5 rounded border border-line-default bg-surface-sunken p-3">
      <p className={`type-eyebrow inline-flex items-center gap-1.5 ${classes.texto}`}>
        <Icone size={13} strokeWidth={2.5} aria-hidden="true" />
        {titulo}
      </p>
      <p className="type-body-strong tnum text-fg-primary">
        {formatarMoeda(valor, { casas: 0 })}
      </p>
      <ProgressBar
        valor={Math.max(0, cobertura)}
        familia={familia}
        rotulo="Cobertura sobre a exposição"
        valorFormatado={formatarPercentual(Math.max(0, cobertura), 0)}
        altura={6}
      />
      <p className="type-caption">{explicacao}</p>
    </div>
  );
}

function colunasDeGarantia(temEmbargada: boolean): Coluna<Garantia>[] {
  const colunas: Coluna<Garantia>[] = [
    {
      id: 'tipo',
      cabecalho: 'Tipo',
      celula: (g) => ROTULO_GARANTIA[g.tipo] ?? g.tipo,
      minLargura: 150,
    },
    {
      id: 'natureza',
      cabecalho: 'Natureza',
      celula: (g) => (
        <Badge variante="natureza" natureza={g.natureza} tamanho="sm">
          {NATUREZA_GARANTIA[g.natureza].rotulo}
        </Badge>
      ),
      minLargura: 140,
    },
    {
      id: 'descricao',
      cabecalho: 'Descrição',
      celula: (g) => g.descricao,
      minLargura: 200,
      ocultarAbaixoDe: 1280,
    },
    {
      id: 'declarado',
      cabecalho: 'Valor declarado',
      numerica: true,
      celula: (g) => formatarMoeda(g.valorDeclarado, { casas: 0 }),
    },
    {
      id: 'atualizado',
      cabecalho: 'Valor atualizado',
      numerica: true,
      termo: 'HAIRCUT',
      celula: (g) => formatarMoeda(g.valorAtualizado, { casas: 0 }),
    },
    {
      id: 'registrada',
      cabecalho: 'Registrada',
      celula: (g) => (g.registrada ? 'Sim' : 'Não'),
      minLargura: 90,
    },
    {
      id: 'avaliacao',
      cabecalho: 'Avaliada em',
      celula: (g) => formatarData(g.dataAvaliacao),
      minLargura: 110,
      ocultarAbaixoDe: 1440,
    },
  ];

  // A coluna só existe quando há bem embargado: coluna inteira de "Não" é ruído.
  if (temEmbargada) {
    colunas.push({
      id: 'embargada',
      cabecalho: 'Embargada',
      celula: (g) =>
        g.bemEmbargado ? (
          <Badge variante="severidade" severidade="CRITICA" tamanho="sm">
            Embargada
          </Badge>
        ) : (
          'Não'
        ),
      minLargura: 110,
    });
  }

  return colunas;
}

function DrawerDeOperacoes({
  aberto,
  aoFechar,
  operacoes,
}: {
  aberto: boolean;
  aoFechar: () => void;
  operacoes: Operacao[];
}) {
  return (
    <Drawer
      aberto={aberto}
      aoFechar={aoFechar}
      largura="larga"
      titulo="Operações e parcelas"
      subtitulo={`${operacoes.length} operações com a Krill Tech`}
    >
      <ul className="flex flex-col gap-4">
        {operacoes.map((operacao) => (
          <li key={operacao.id} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="type-body-strong min-w-0 text-fg-primary">{operacao.descricao}</span>
              <span className="tnum type-body-strong text-fg-primary">
                {formatarMoeda(operacao.saldoDevedor, { casas: 0 })}
              </span>
            </div>
            <p className="type-caption flex flex-wrap items-center gap-2">
              <Badge variante="neutro" tamanho="sm" icone={null}>
                {ROTULO_OPERACAO[operacao.tipo]}
              </Badge>
              <span>Contratada em {formatarData(operacao.dataContratacao)}</span>
            </p>

            {operacao.barter ? (
              <p className="type-caption rounded border border-line-default bg-surface-sunken px-2 py-1.5">
                {operacao.barter.cultura} ·{' '}
                {formatarNumero(operacao.barter.sacasPrometidas, 0)} sacas prometidas ·
                referência {formatarMoeda(operacao.barter.precoReferenciaSaca)}/saca
                {operacao.barter.cprVinculadaId ? null : (
                  <span className="mt-1 block text-risk-c">
                    Barter sem CPR registrada cobrindo a operação.
                  </span>
                )}
              </p>
            ) : null}

            <div className="min-w-0">
              <DataTable<Parcela>
                aria-label={`Parcelas da operação ${operacao.descricao}`}
                densidade="densa"
                linhas={operacao.parcelas}
                obterId={(p) => p.id}
                colunas={[
                  {
                    id: 'venc',
                    cabecalho: 'Vencimento',
                    celula: (p) => formatarData(p.vencimento),
                  },
                  {
                    id: 'valor',
                    cabecalho: 'Valor',
                    numerica: true,
                    celula: (p) => formatarMoeda(p.valor, { casas: 0 }),
                  },
                  {
                    id: 'status',
                    cabecalho: 'Status',
                    celula: (p) => ROTULO_PARCELA[p.status],
                  },
                  {
                    id: 'atraso',
                    cabecalho: 'Atraso',
                    numerica: true,
                    celula: (p) => (p.diasAtraso ? `${formatarNumero(p.diasAtraso, 0)} d` : '—'),
                  },
                ]}
              />
            </div>
          </li>
        ))}
      </ul>
    </Drawer>
  );
}
