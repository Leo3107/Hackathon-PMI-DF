'use client';

/**
 * Tabela "Onde está o dinheiro em risco" (`03-ux-e-telas.md` §2.6).
 *
 * Densa, **8 linhas fixas**, ordenada pelo motor por `exposicaoEmRiscoEmRJ` decrescente, sem
 * filtro, sem paginação e sem ordenação interativa — quem quer filtrar vai para `/clientes`.
 * A coluna "Em risco em RJ" é a destacada tipograficamente: é o número que ninguém mais mostra.
 */

import { Gavel } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import {
  DataTable,
  EmptyState,
  RatingBadge,
  Termo,
  Tooltip,
  TrendIndicator,
  type Coluna,
} from '@/components/ui';
import { formatarMoeda, formatarMoedaCompacta } from '@/lib/format';
import type { LinhaDinheiroEmRisco } from '@/types';

const LINHAS_EXIBIDAS = 8;

function Dinheiro({ valor, destacado = false }: { valor: number; destacado?: boolean }) {
  return (
    <Tooltip conteudo={formatarMoeda(valor, { casas: 0 })}>
      <span
        tabIndex={0}
        className={
          destacado
            ? 'tnum rounded-sm text-[13px]/[20px] font-semibold text-fg-primary'
            : 'tnum rounded-sm text-[13px]/[20px] text-fg-secondary'
        }
      >
        {formatarMoedaCompacta(valor)}
      </span>
    </Tooltip>
  );
}

export interface DinheiroEmRiscoProps {
  linhas: LinhaDinheiroEmRisco[];
  carregando?: boolean;
}

export function DinheiroEmRisco({ linhas, carregando = false }: DinheiroEmRiscoProps) {
  const router = useRouter();

  const colunas: Coluna<LinhaDinheiroEmRisco>[] = [
    {
      id: 'cliente',
      cabecalho: 'Cliente',
      largura: 260,
      fixa: 'esquerda',
      celula: (linha) => (
        <Link
          href={`/clientes/${encodeURIComponent(linha.clienteId)}`}
          className="transicao-controle block truncate rounded-sm text-fg-primary hover:text-accent-300"
          title={linha.razaoSocial}
        >
          {linha.razaoSocial}
        </Link>
      ),
    },
    {
      id: 'uf',
      cabecalho: 'UF',
      alinhamento: 'centro',
      largura: 56,
      celula: (linha) => <span className="text-fg-secondary">{linha.uf}</span>,
    },
    {
      id: 'exposicaoTotal',
      cabecalho: 'Exp. total',
      numerica: true,
      alinhamento: 'direita',
      largura: 120,
      celula: (linha) => <Dinheiro valor={linha.exposicaoTotal} />,
    },
    {
      id: 'exposicaoEmRisco',
      cabecalho: 'Em risco',
      numerica: true,
      alinhamento: 'direita',
      largura: 120,
      celula: (linha) => <Dinheiro valor={linha.exposicaoEmRisco} />,
    },
    {
      id: 'exposicaoEmRiscoEmRJ',
      cabecalho: 'Em risco em RJ',
      numerica: true,
      alinhamento: 'direita',
      largura: 140,
      termo: 'RJ',
      celula: (linha) => <Dinheiro valor={linha.exposicaoEmRiscoEmRJ} destacado />,
    },
    {
      id: 'rating',
      cabecalho: 'Rating',
      alinhamento: 'centro',
      largura: 88,
      celula: (linha) => (
        <span className="inline-flex items-center gap-1">
          <RatingBadge rating={linha.rating} tamanho="sm" />
          {linha.temVeto ? (
            <Tooltip conteudo="Rating rebaixado por veto do motor.">
              <span
                tabIndex={0}
                role="img"
                aria-label="Veto ativo"
                className="inline-flex rounded-sm text-risk-d"
              >
                <Gavel size={12} strokeWidth={2} aria-hidden="true" />
              </span>
            </Tooltip>
          ) : null}
        </span>
      ),
    },
    {
      id: 'tendencia',
      cabecalho: 'Tend.',
      alinhamento: 'centro',
      largura: 72,
      celula: (linha) => <TrendIndicator tendencia={linha.tendencia} somenteIcone />,
    },
  ];

  return (
    <DataTable
      aria-label="Onde está o dinheiro em risco"
      colunas={colunas}
      linhas={linhas.slice(0, LINHAS_EXIBIDAS)}
      obterId={(linha) => linha.clienteId}
      densidade="densa"
      carregando={carregando}
      linhasEsqueleto={LINHAS_EXIBIDAS}
      aoClicarLinha={(linha) => router.push(`/clientes/${encodeURIComponent(linha.clienteId)}`)}
      familiaLinha={(linha) =>
        linha.rating === 'D' ? 'd' : linha.rating === 'C' ? 'c' : null
      }
      vazio={
        <EmptyState
          compacto
          titulo="Nenhuma exposição em risco na carteira"
          descricao="Nenhum cliente apresenta exposição desprotegida em cenário de recuperação judicial nesta varredura."
        />
      }
      rodape={
        <div className="flex items-center justify-between gap-3 px-3 py-2">
          <p className="type-caption">
            Ordenado por exposição em risco em cenário de <Termo sigla="RJ" />. Somente leitura.
          </p>
          <Link
            href="/clientes?ordem=risco_rj"
            className="transicao-controle inline-flex items-center gap-1 rounded-sm text-[12px]/[16px] font-medium text-accent-400 hover:text-accent-300"
          >
            Ver todos os clientes <span aria-hidden="true">→</span>
          </Link>
        </div>
      }
    />
  );
}
