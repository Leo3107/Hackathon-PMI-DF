'use client';

/**
 * `/clientes` — lista de clientes (`03-ux-e-telas.md` §3).
 *
 * 13 colunas, 9 filtros exclusivos, busca por cliente/documento/município, 5 ordenações
 * visíveis mais 2 usadas só por link direto, e **todo o estado na URL** (§3.6):
 * `?filtro=…&busca=…&ordem=…&dir=…`, mais os recortes `?rating=`, `?cultura=` e `?uf=`.
 *
 * Mudança de filtro usa `router.replace` — não empilha histórico. Navegar para um cliente usa
 * `push`, para que o "voltar" do navegador devolva a lista com os mesmos critérios.
 */

import { ShieldAlert, Sprout } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  Badge,
  CLASSES_RISCO,
  DataTable,
  EmptyState,
  FilterChips,
  RatingBadge,
  SEVERIDADE,
  SearchInput,
  SectionHeader,
  Tooltip,
  TrendIndicator,
  type Coluna,
  type OpcaoChip,
} from '@/components/ui';
import { listarClientes } from '@/lib/api';
import {
  TRACO_LONGO,
  formatarData,
  formatarDelta,
  formatarDias,
  formatarDocumento,
  formatarMoeda,
  formatarMoedaCompacta,
  formatarNumero,
  formatarPercentual,
  formatarProbabilidadeRJ,
  formatarScore,
} from '@/lib/format';
import { assinarSessao, sessaoParaApi } from '@/lib/sessao';
import type { ClienteAvaliado } from '@/types';

import { EstadoDeFalha } from './estados';
import {
  DIRECAO_PADRAO,
  FILTROS,
  ORDENS,
  ROTULO_FAIXA_RJ,
  ROTULO_FILTRO,
  type ChaveOrdem,
  type Direcao,
  type LinhaCliente,
  type ValorFiltro,
  aplicarCriterios,
  contarFiltros,
  limiarAltaExposicao,
  paraLinha,
} from './linha-cliente';

const FAMILIA_POR_FILTRO: Partial<Record<ValorFiltro, 'a' | 'b' | 'c' | 'd'>> = {
  'rating-a': 'a',
  'rating-b': 'b',
  'rating-c': 'c',
  'rating-d': 'd',
};

const INICIAL_SEVERIDADE = { CRITICA: 'C', ALTA: 'A', MEDIA: 'M', BAIXA: 'I' } as const;

function ehFiltro(valor: string | null): valor is ValorFiltro {
  return valor !== null && (FILTROS as string[]).includes(valor);
}

function ehOrdem(valor: string | null): valor is ChaveOrdem {
  return valor !== null && (ORDENS as string[]).includes(valor);
}

export function ListaDeClientes() {
  const router = useRouter();
  const caminho = usePathname();
  const parametros = useSearchParams();

  // ---------------------------------------------------------------- dados
  const [avaliados, setAvaliados] = useState<ClienteAvaliado[] | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);
  const [versaoSessao, setVersaoSessao] = useState(0);

  useEffect(() => assinarSessao(() => setVersaoSessao((v) => v + 1)), []);

  useEffect(() => {
    let vivo = true;
    listarClientes(sessaoParaApi())
      .then((lista) => {
        if (!vivo) return;
        setAvaliados(lista);
        setErro(null);
      })
      .catch((causa: unknown) => {
        if (vivo) {
          setAvaliados(null);
          setErro(causa);
        }
      });
    return () => {
      vivo = false;
    };
  }, [tentativa, versaoSessao]);

  // ---------------------------------------------------------------- estado na URL
  const ratingDaUrl = parametros.get('rating');
  const filtroDaUrl = parametros.get('filtro');
  const filtro: ValorFiltro = ehFiltro(filtroDaUrl)
    ? filtroDaUrl
    : ratingDaUrl && 'ABCD'.includes(ratingDaUrl.toUpperCase())
      ? (`rating-${ratingDaUrl.toLowerCase()}` as ValorFiltro)
      : 'todos';

  const cultura = parametros.get('cultura');
  const uf = parametros.get('uf');
  const ordem: ChaveOrdem = ehOrdem(parametros.get('ordem')) ? (parametros.get('ordem') as ChaveOrdem) : 'score';
  const direcaoDaUrl = parametros.get('dir');
  const direcao: Direcao = direcaoDaUrl === 'asc' || direcaoDaUrl === 'desc' ? direcaoDaUrl : DIRECAO_PADRAO[ordem];
  const buscaDaUrl = parametros.get('busca') ?? '';

  const [busca, setBusca] = useState(buscaDaUrl);

  const escrever = useCallback(
    (mudancas: Record<string, string | null>) => {
      const proximos = new URLSearchParams(parametros.toString());
      for (const [chave, valor] of Object.entries(mudancas)) {
        if (valor === null || valor === '') proximos.delete(chave);
        else proximos.set(chave, valor);
      }
      const query = proximos.toString();
      router.replace(query ? `${caminho}?${query}` : caminho, { scroll: false });
    },
    [caminho, parametros, router],
  );

  // Debounce de 200ms (§3.4): a filtragem é imediata na tela; só a URL espera.
  useEffect(() => {
    if (busca === buscaDaUrl) return;
    const id = setTimeout(() => escrever({ busca: busca || null }), 200);
    return () => clearTimeout(id);
  }, [busca, buscaDaUrl, escrever]);

  // ---------------------------------------------------------------- derivações
  const linhas = useMemo(() => (avaliados ?? []).map(paraLinha), [avaliados]);
  const limiar = useMemo(() => limiarAltaExposicao(linhas), [linhas]);
  const contagens = useMemo(() => contarFiltros(linhas, limiar), [linhas, limiar]);

  const visiveis = useMemo(
    () => aplicarCriterios(linhas, { filtro, busca, cultura, uf, ordem, direcao }, limiar),
    [linhas, filtro, busca, cultura, uf, ordem, direcao, limiar],
  );

  const carregando = avaliados === null && erro === null;

  const opcoes: OpcaoChip<ValorFiltro>[] = FILTROS.map((valor) => ({
    valor,
    rotulo: ROTULO_FILTRO[valor],
    contagem: carregando ? undefined : contagens[valor],
    familia: FAMILIA_POR_FILTRO[valor],
  }));

  // ---------------------------------------------------------------- colunas
  const colunas: Coluna<LinhaCliente>[] = useMemo(
    () => [
      {
        id: 'cliente',
        cabecalho: 'Cliente',
        largura: 240,
        fixa: 'esquerda',
        celula: (linha) => (
          <span className="flex min-w-0 flex-col">
            <span className="flex min-w-0 items-center gap-1.5">
              {linha.tipoPessoa === 'PF' ? (
                <Tooltip conteudo="Produtor rural pessoa física">
                  <span tabIndex={0} className="shrink-0 rounded-sm">
                    <Sprout size={13} strokeWidth={2} aria-hidden="true" className="text-fg-tertiary" />
                  </span>
                </Tooltip>
              ) : null}
              <Link
                href={`/clientes/${encodeURIComponent(linha.id)}`}
                title={linha.razaoSocial}
                className="transicao-controle truncate rounded-sm text-fg-primary hover:text-accent-300"
              >
                {linha.razaoSocial}
              </Link>
            </span>
            <Tooltip conteudo={`Documento: ${formatarDocumento(linha.documento)}`}>
              <span tabIndex={0} className="type-mono truncate text-[11px]/[14px] text-fg-tertiary">
                {linha.nomeFantasia ?? formatarDocumento(linha.documento)}
              </span>
            </Tooltip>
          </span>
        ),
      },
      {
        id: 'municipio',
        cabecalho: 'Município/UF',
        largura: 150,
        ocultarAbaixoDe: 1536,
        celula: (linha) => (
          <span className="truncate" title={`${linha.municipio} · ${linha.uf}`}>
            {linha.municipio} <span className="text-fg-secondary">· {linha.uf}</span>
          </span>
        ),
      },
      {
        id: 'cultura',
        cabecalho: 'Cultura',
        largura: 140,
        ocultarAbaixoDe: 1536,
        celula: (linha) =>
          linha.culturas.length === 0 ? (
            <span className="text-fg-tertiary">{TRACO_LONGO}</span>
          ) : (
            <span className="flex min-w-0 items-center gap-1">
              <span className="truncate">{linha.culturas[0]}</span>
              {linha.culturas.length > 1 ? (
                <Tooltip conteudo={linha.culturas.slice(1).join(' · ')}>
                  <span
                    tabIndex={0}
                    className="shrink-0 rounded-sm text-[11px] text-fg-tertiary"
                    aria-label={`Outras culturas: ${linha.culturas.slice(1).join(', ')}`}
                  >
                    +{linha.culturas.length - 1}
                  </span>
                </Tooltip>
              ) : null}
            </span>
          ),
      },
      {
        id: 'exposicao',
        cabecalho: 'Exposição',
        numerica: true,
        alinhamento: 'direita',
        largura: 120,
        ordenavel: true,
        valorOrdenacao: (linha) => linha.exposicaoTotal,
        celula: (linha) => (
          <Tooltip conteudo={formatarMoeda(linha.exposicaoTotal, { casas: 0 })}>
            <span tabIndex={0} className="tnum rounded-sm">
              {formatarMoedaCompacta(linha.exposicaoTotal)}
            </span>
          </Tooltip>
        ),
      },
      {
        id: 'vencimento',
        cabecalho: 'Próx. venc.',
        numerica: true,
        alinhamento: 'direita',
        largura: 120,
        celula: (linha) => <ProximoVencimento linha={linha} />,
      },
      {
        id: 'score',
        cabecalho: 'Score',
        numerica: true,
        alinhamento: 'direita',
        largura: 88,
        ordenavel: true,
        valorOrdenacao: (linha) => linha.score,
        celula: (linha) => (
          <span className="tnum text-[15px] font-medium text-fg-primary">
            {formatarScore(linha.score)}
          </span>
        ),
      },
      {
        id: 'rating',
        cabecalho: 'Rating',
        alinhamento: 'centro',
        largura: 64,
        celula: (linha) => (
          <span className="relative inline-flex items-center">
            <RatingBadge rating={linha.ratingFinal} tamanho="sm" />
            {linha.temVeto ? (
              <Tooltip
                conteudo={`Rating rebaixado por veto: ${linha.rotuloVeto ?? 'gatilho do motor'}. Score calculado: ${linha.score} (rating ${linha.ratingCalculado}).`}
              >
                <span
                  tabIndex={0}
                  role="img"
                  aria-label={`Veto ativo: ${linha.rotuloVeto ?? 'gatilho do motor'}`}
                  className="-ml-1 -mt-3 inline-flex rounded-sm text-risk-d"
                >
                  <ShieldAlert size={10} strokeWidth={2.5} aria-hidden="true" />
                </span>
              </Tooltip>
            ) : null}
          </span>
        ),
      },
      {
        id: 'pd',
        cabecalho: 'PD 12m',
        numerica: true,
        alinhamento: 'direita',
        largura: 80,
        ordenavel: true,
        termo: 'PD',
        valorOrdenacao: (linha) => linha.pd12m,
        celula: (linha) => <span className="tnum">{formatarPercentual(linha.pd12m, 1)}</span>,
      },
      {
        id: 'riscoRj',
        cabecalho: 'Risco de RJ',
        numerica: true,
        alinhamento: 'direita',
        largura: 128,
        termo: 'RJ',
        celula: (linha) => (
          <span className="inline-flex items-center justify-end gap-1.5">
            <span className="tnum">
              {formatarProbabilidadeRJ({
                probabilidade12m: linha.probabilidadeRJ,
                eventoJaOcorrido: linha.eventoRJOcorrido,
              })}
            </span>
            <Badge
              variante="risco"
              familia={
                linha.faixaRJ === 'baixo'
                  ? 'a'
                  : linha.faixaRJ === 'moderado'
                    ? 'b'
                    : linha.faixaRJ === 'alto'
                      ? 'c'
                      : 'd'
              }
              tamanho="sm"
            >
              {ROTULO_FAIXA_RJ[linha.faixaRJ]}
            </Badge>
          </span>
        ),
      },
      {
        id: 'variacao',
        cabecalho: 'Tendência',
        alinhamento: 'centro',
        largura: 116,
        ordenavel: true,
        valorOrdenacao: (linha) => linha.deltaScore,
        celula: (linha) =>
          linha.deltaScore === null ? (
            <Tooltip conteudo="Sem histórico suficiente para calcular variação.">
              <span tabIndex={0} className="rounded-sm text-fg-tertiary">
                {TRACO_LONGO}
              </span>
            </Tooltip>
          ) : (
            <TrendIndicator
              tendencia={linha.tendencia}
              deltaTexto={formatarDelta(linha.deltaScore)}
              tamanho="sm"
              rotuloCurto
            />
          ),
      },
      {
        id: 'alertas',
        cabecalho: 'Alertas',
        alinhamento: 'centro',
        largura: 72,
        ordenavel: true,
        valorOrdenacao: (linha) => linha.alertasNaoLidos,
        celula: (linha) => <PastilhaDeAlertas linha={linha} />,
      },
    ],
    [],
  );

  // ---------------------------------------------------------------- render
  if (erro) {
    return (
      <EstadoDeFalha
        erro={erro}
        contexto="a lista de clientes"
        aoTentarNovamente={() => setTentativa((n) => n + 1)}
      />
    );
  }

  const recortes = [
    cultura ? { chave: 'cultura', rotulo: `Cultura: ${cultura}` } : null,
    uf ? { chave: 'uf', rotulo: `UF: ${uf}` } : null,
  ].filter((r): r is { chave: string; rotulo: string } => r !== null);

  return (
    <div className="flex flex-col gap-4">
      <SectionHeader
        titulo="Clientes"
        meta={
          <span className="type-caption tnum">
            {carregando
              ? '—'
              : `${formatarNumero(visiveis.length)} de ${formatarNumero(linhas.length)} clientes`}
          </span>
        }
      />

      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchInput
            valor={busca}
            aoMudar={setBusca}
            placeholder="Buscar por cliente, documento ou município…"
            aria-label="Buscar cliente por razão social, documento ou município"
            className="w-[320px] max-w-full"
          />
          {recortes.map((recorte) => (
            <button
              key={recorte.chave}
              type="button"
              onClick={() => escrever({ [recorte.chave]: null })}
              className="transicao-controle type-badge inline-flex h-6 items-center gap-1 rounded-sm border border-accent-line bg-accent-tint px-2 font-medium text-accent-300"
            >
              {recorte.rotulo}
              <span aria-hidden="true">×</span>
              <span className="sr-only">Remover este recorte</span>
            </button>
          ))}
        </div>

        <FilterChips
          rotulo="Filtrar clientes"
          modo="unico"
          opcoes={opcoes}
          selecionados={new Set<ValorFiltro>(filtro === 'todos' ? [] : [filtro])}
          aoMudar={(proximos) => {
            const escolhido = [...proximos][0] ?? 'todos';
            escrever({ filtro: escolhido === 'todos' ? null : escolhido, rating: null });
          }}
        />
      </div>

      <DataTable
        aria-label="Clientes da carteira"
        colunas={colunas}
        linhas={visiveis}
        obterId={(linha) => linha.id}
        densidade="densa"
        carregando={carregando}
        linhasEsqueleto={12}
        cabecalhoFixo
        ordenacao={{ colunaId: ordem, direcao }}
        aoOrdenar={(proxima) => {
          if (!proxima || !ehOrdem(proxima.colunaId)) {
            escrever({ ordem: null, dir: null });
            return;
          }
          escrever({ ordem: proxima.colunaId, dir: proxima.direcao });
        }}
        aoClicarLinha={(linha) => router.push(`/clientes/${encodeURIComponent(linha.id)}`)}
        familiaLinha={(linha) => (linha.ratingFinal === 'D' ? 'd' : null)}
        vazio={
          <EstadoVazio
            busca={busca}
            filtro={filtro}
            totalCarteira={linhas.length}
            aoLimparBusca={() => {
              setBusca('');
              escrever({ busca: null });
            }}
            aoLimparFiltro={() => escrever({ filtro: null, rating: null })}
            aoLimparTudo={() => {
              setBusca('');
              router.replace(caminho, { scroll: false });
            }}
            aoRecarregar={() => setTentativa((n) => n + 1)}
          />
        }
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Células compostas
// ---------------------------------------------------------------------------

function ProximoVencimento({ linha }: { linha: LinhaCliente }) {
  const proximo = linha.proximoVencimento;
  if (!proximo) {
    return (
      <Tooltip conteudo="O motor ainda não informa a próxima parcela a vencer deste cliente.">
        <span tabIndex={0} className="rounded-sm text-fg-tertiary">
          {TRACO_LONGO}
        </span>
      </Tooltip>
    );
  }

  const atrasado = (proximo.diasAtraso ?? 0) > 0;
  const apoio = atrasado
    ? `vencido há ${formatarDias(proximo.diasAtraso ?? 0)}`
    : proximo.diasRestantes === null
      ? null
      : `em ${formatarDias(proximo.diasRestantes)}`;

  return (
    <span className="flex flex-col items-end">
      <span className="tnum">{formatarData(proximo.data)}</span>
      {apoio ? (
        <span
          className={
            atrasado
              ? `tnum inline-flex items-center gap-1 text-[11px]/[14px] ${CLASSES_RISCO.d.texto}`
              : 'tnum text-[11px]/[14px] text-fg-tertiary'
          }
        >
          {atrasado ? <span aria-hidden="true">▲</span> : null}
          {apoio}
        </span>
      ) : null}
    </span>
  );
}

function PastilhaDeAlertas({ linha }: { linha: LinhaCliente }) {
  if (linha.alertasNaoLidos === 0) {
    return <span className="text-fg-tertiary">{TRACO_LONGO}</span>;
  }

  const severidade = linha.severidadeMaximaAlerta;
  const apresentacao = severidade ? SEVERIDADE[severidade] : null;
  const inicial = severidade ? INICIAL_SEVERIDADE[severidade] : null;

  return (
    <Tooltip
      conteudo={
        severidade
          ? `${linha.alertasNaoLidos} alerta(s) não lido(s). Maior severidade: ${SEVERIDADE[severidade].rotulo}.`
          : `${linha.alertasNaoLidos} alerta(s) não lido(s).`
      }
    >
      <span tabIndex={0} className="inline-flex items-center gap-1 rounded-sm">
        <Badge variante="risco" familia={apresentacao?.familia ?? 'neutral'} tamanho="sm">
          <span className="tnum">
            {linha.alertasNaoLidos}
            {inicial ? ` ${inicial}` : ''}
          </span>
        </Badge>
      </span>
    </Tooltip>
  );
}

// ---------------------------------------------------------------------------
// Estados vazios (§3.7)
// ---------------------------------------------------------------------------

function EstadoVazio({
  busca,
  filtro,
  totalCarteira,
  aoLimparBusca,
  aoLimparFiltro,
  aoLimparTudo,
  aoRecarregar,
}: {
  busca: string;
  filtro: ValorFiltro;
  totalCarteira: number;
  aoLimparBusca: () => void;
  aoLimparFiltro: () => void;
  aoLimparTudo: () => void;
  aoRecarregar: () => void;
}) {
  if (totalCarteira === 0) {
    return (
      <EmptyState
        titulo="Carteira sem clientes"
        descricao="Nenhum cliente carregado. Verifique se o serviço de dados está ativo."
        acao={{ rotulo: 'Recarregar', aoClicar: aoRecarregar }}
      />
    );
  }

  const comBusca = busca.trim().length > 0;
  const comFiltro = filtro !== 'todos';

  if (comBusca && comFiltro) {
    return (
      <EmptyState
        titulo="Nenhum resultado"
        descricao={`«${busca}» não retorna clientes dentro do filtro «${ROTULO_FILTRO[filtro]}».`}
        acao={{ rotulo: 'Manter busca e ver todos os ratings', aoClicar: aoLimparFiltro }}
      />
    );
  }

  if (comBusca) {
    return (
      <EmptyState
        titulo={`Nenhum resultado para «${busca}»`}
        descricao="Verifique a grafia ou busque por documento ou município."
        acao={{ rotulo: 'Limpar busca', aoClicar: aoLimparBusca }}
      />
    );
  }

  if (comFiltro) {
    return (
      <EmptyState
        titulo="Nenhum cliente neste filtro"
        descricao={`O filtro «${ROTULO_FILTRO[filtro]}» não retornou clientes.`}
        acao={{ rotulo: 'Limpar filtro', aoClicar: aoLimparFiltro }}
      />
    );
  }

  return (
    <EmptyState
      titulo="Nenhum cliente para exibir"
      descricao="Os recortes aplicados não retornaram clientes."
      acao={{ rotulo: 'Limpar tudo', aoClicar: aoLimparTudo }}
    />
  );
}
