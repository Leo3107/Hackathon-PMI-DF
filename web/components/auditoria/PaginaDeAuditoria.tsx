'use client';

/**
 * `/auditoria` — trilha de decisão humana (`03-ux-e-telas.md` §8).
 *
 * Materializa o *human-in-the-loop*: a máquina recomenda, a pessoa decide, e o registro fica.
 * O dado mais importante da tela é a **divergência** — tratada com cor, ícone, a palavra
 * `DIVERGENTE` e uma linha extra sempre visível, nunca só por cor (I8).
 *
 * O formulário que origina o registro não está aqui: ele vive em `/clientes/[id]#decisao`
 * (§8.3). Esta rota é a leitura da trilha.
 */

import { GitBranch, ListChecks } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { useSessao } from '@/components/shell';
import {
  Badge,
  Card,
  DataTable,
  EmptyState,
  FilterChips,
  RatingBadge,
  SectionHeader,
  Termo,
  cn,
  type Coluna,
  type OpcaoChip,
} from '@/components/ui';
import { listarAuditoria } from '@/lib/api';
import { formatarDataHora, formatarPercentual, formatarScore } from '@/lib/format';
import { decisoesDaSessao } from '@/lib/sessao';
import type { RegistroAuditoria } from '@/types';

import { FalhaDoMotor } from '@/components/alertas';

import {
  ROTULO_DECISAO,
  ROTULO_FILTRO_AUDITORIA,
  ROTULO_RECOMENDACAO,
  clientesDaTrilha,
  estatisticasDaTrilha,
  filtrarTrilha,
  fraseDeDivergencia,
  justificativaCurta,
  resumoDaDivergencia,
  unirTrilha,
  type FiltroAuditoria,
} from './trilha';

const OPCOES_FILTRO: OpcaoChip<FiltroAuditoria>[] = (
  ['divergentes', 'ultimos_30d'] as FiltroAuditoria[]
).map((valor) => ({ valor, rotulo: ROTULO_FILTRO_AUDITORIA[valor] }));

export function PaginaDeAuditoria() {
  const router = useRouter();
  const sessao = useSessao();

  const [doMotor, setDoMotor] = useState<RegistroAuditoria[] | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);
  const [filtros, setFiltros] = useState<ReadonlySet<FiltroAuditoria>>(new Set());
  const [clienteId, setClienteId] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<string | null>(null);
  const [referencia] = useState(() => new Date().toISOString());

  useEffect(() => {
    let vivo = true;
    listarAuditoria()
      .then((dados) => {
        if (!vivo) return;
        setDoMotor(dados);
        setErro(null);
      })
      .catch((causa: unknown) => {
        if (!vivo) return;
        setDoMotor(null);
        setErro(causa);
      });
    return () => {
      vivo = false;
    };
  }, [tentativa]);

  const trilha = useMemo(
    () => unirTrilha(doMotor ?? [], decisoesDaSessao(sessao)),
    [doMotor, sessao],
  );
  const visiveis = useMemo(
    () => filtrarTrilha(trilha, { filtros, clienteId, referencia }),
    [trilha, filtros, clienteId, referencia],
  );
  const estatisticas = useMemo(() => estatisticasDaTrilha(visiveis), [visiveis]);
  const clientes = useMemo(() => clientesDaTrilha(trilha), [trilha]);

  const colunas = useMemo<Coluna<RegistroAuditoria>[]>(
    () => [
      {
        id: 'dataHora',
        cabecalho: 'Data/hora',
        largura: 148,
        ordenavel: true,
        valorOrdenacao: (registro) => registro.dataHora,
        celula: (registro) => (
          <span className="tnum whitespace-nowrap">{formatarDataHora(registro.dataHora)}</span>
        ),
      },
      {
        id: 'analista',
        cabecalho: 'Analista',
        minLargura: 140,
        ocultarAbaixoDe: 1280,
        celula: (registro) => <span className="truncate">{registro.analista}</span>,
      },
      {
        id: 'cliente',
        cabecalho: 'Cliente',
        minLargura: 180,
        ordenavel: true,
        valorOrdenacao: (registro) => registro.clienteNome,
        celula: (registro) => (
          <span className="truncate text-fg-primary">{registro.clienteNome}</span>
        ),
      },
      {
        id: 'score',
        cabecalho: 'Score no momento',
        numerica: true,
        largura: 132,
        ordenavel: true,
        valorOrdenacao: (registro) => registro.scoreNoMomento,
        celula: (registro) => (
          <span className="inline-flex items-center justify-end gap-2">
            <span className="tnum">{formatarScore(registro.scoreNoMomento)}</span>
            <RatingBadge rating={registro.ratingNoMomento} tamanho="sm" />
          </span>
        ),
      },
      {
        id: 'recomendacao',
        cabecalho: 'Recomendação gerada',
        minLargura: 180,
        ocultarAbaixoDe: 1440,
        celula: (registro) => (
          <Badge variante="neutro" tamanho="sm" icone={null}>
            {ROTULO_RECOMENDACAO[registro.recomendacaoGerada]}
          </Badge>
        ),
      },
      {
        id: 'decisao',
        cabecalho: 'Decisão do analista',
        minLargura: 160,
        celula: (registro) => (
          <Badge variante="acento" tamanho="sm" icone={null}>
            {ROTULO_DECISAO[registro.decisaoAnalista]}
          </Badge>
        ),
      },
      {
        id: 'divergencia',
        cabecalho: 'Divergência',
        largura: 136,
        ordenavel: true,
        valorOrdenacao: (registro) => (registro.divergiuDaRecomendacao ? 1 : 0),
        celula: (registro) =>
          registro.divergiuDaRecomendacao ? (
            <span className="type-caption inline-flex items-center gap-1.5 text-risk-c">
              <GitBranch size={14} strokeWidth={2} aria-hidden="true" />
              DIVERGENTE
            </span>
          ) : (
            <span className="type-caption text-fg-tertiary">Alinhada</span>
          ),
      },
      {
        id: 'justificativa',
        cabecalho: 'Justificativa',
        minLargura: 260,
        celula: (registro) => (
          <div className="flex min-w-0 flex-col gap-1">
            <p className={cn('type-caption', expandido === registro.id ? '' : 'truncate')}>
              {expandido === registro.id
                ? registro.justificativa
                : justificativaCurta(registro.justificativa)}
            </p>
            {registro.divergiuDaRecomendacao ? (
              <p className="type-caption text-risk-c">↳ {resumoDaDivergencia(registro)}</p>
            ) : null}
            {expandido === registro.id ? (
              <button
                type="button"
                className="type-caption self-start text-accent-400 underline-offset-2 hover:underline"
                onClick={(evento) => {
                  evento.stopPropagation();
                  router.push(`/clientes/${registro.clienteId}#decisao`);
                }}
              >
                Ver estado do cliente na data →
              </button>
            ) : null}
          </div>
        ),
      },
    ],
    [expandido, router],
  );

  if (erro) {
    return (
      <FalhaDoMotor
        erro={erro}
        contexto="a trilha de auditoria"
        aoTentarNovamente={() => setTentativa((n) => n + 1)}
      />
    );
  }

  const carregando = doMotor === null;
  const percentual = formatarPercentual(estatisticas.fracao, 0);

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-4">
        <SectionHeader
          titulo="Trilha de auditoria"
          descricao="Quem analisou, quando, com qual score, o que o motor recomendou e o que a pessoa decidiu. A recomendação nunca decide sozinha."
          meta={<Badge variante="simulado" tamanho="sm" />}
        />

        <p
          className={cn(
            'type-body flex items-center gap-2',
            estatisticas.divergentes > 0 ? 'text-risk-c' : 'text-fg-secondary',
          )}
          aria-live="polite"
        >
          {estatisticas.divergentes > 0 ? (
            <GitBranch size={16} strokeWidth={2} aria-hidden="true" />
          ) : (
            <ListChecks size={16} strokeWidth={2} aria-hidden="true" />
          )}
          {carregando ? 'Carregando a trilha…' : fraseDeDivergencia(estatisticas, percentual)}
        </p>

        <p className="type-caption max-w-[92ch]">
          O score e o rating gravados são os do instante da decisão. <Termo sigla="PD" /> e o risco
          de <Termo sigla="RJ" /> não são recalculados retroativamente: a trilha registra o que o
          analista via quando decidiu.
        </p>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <FilterChips
            rotulo="Filtros da trilha de auditoria"
            opcoes={OPCOES_FILTRO}
            selecionados={filtros}
            aoMudar={(proximos) => setFiltros(proximos)}
            limparRotulo="Todas"
          />
          <label className="type-caption flex items-center gap-2 text-fg-secondary">
            Cliente
            <select
              aria-label="Filtrar a trilha por cliente"
              value={clienteId ?? ''}
              onChange={(evento) => setClienteId(evento.target.value || null)}
              className="type-body h-8 max-w-[240px] rounded border border-line-default bg-surface-input px-2 text-fg-primary"
            >
              <option value="">Todos os clientes</option>
              {clientes.map((cliente) => (
                <option key={cliente.id} value={cliente.id}>
                  {cliente.nome}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card semPadding>
        <DataTable
          aria-label="Trilha de decisões do analista"
          colunas={colunas}
          linhas={visiveis}
          obterId={(registro) => registro.id}
          densidade="densa"
          carregando={carregando}
          linhasEsqueleto={8}
          ordenacaoInicial={{ colunaId: 'dataHora', direcao: 'desc' }}
          linhaAtiva={expandido}
          familiaLinha={(registro) => (registro.divergiuDaRecomendacao ? 'c' : null)}
          aoClicarLinha={(registro) =>
            setExpandido((atual) => (atual === registro.id ? null : registro.id))
          }
          vazio={
            <EmptyState
              icone={ListChecks}
              titulo="Nenhuma decisão registrada nesta sessão"
              descricao="As decisões que você registrar na página do cliente aparecerão aqui, com o score do momento, a recomendação do motor e a marca de divergência."
              acao={{ rotulo: 'Ir para a carteira', aoClicar: () => router.push('/carteira') }}
            />
          }
        />
      </Card>

      <p className="type-caption text-fg-tertiary">
        Decisão final sujeita à avaliação do analista responsável. A trilha desta demonstração
        vive no navegador e pode ser zerada em &quot;Restaurar dados da demonstração&quot;.
      </p>
    </div>
  );
}
