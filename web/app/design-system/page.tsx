'use client';

import { Download, Filter, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';

import {
  AlertRow,
  Badge,
  Button,
  Card,
  CostCounter,
  DataTable,
  Drawer,
  EmptyState,
  ErrorState,
  EvidenceCard,
  FactorBar,
  FilterChips,
  IconButton,
  KpiTile,
  Modal,
  ProgressBar,
  RatingBadge,
  ScoreGauge,
  SearchInput,
  SectionHeader,
  SimulatedDataBanner,
  StackedBar,
  StreamingText,
  Termo,
  Timeline,
  Tooltip,
  TrendIndicator,
  type Alerta,
  type Coluna,
  type EstadoStreaming,
  type Evidencia,
  type Rating,
  type Severidade,
  type Tendencia,
} from '@/components/ui';
import {
  formatarDocumento,
  formatarMoedaCompacta,
  formatarPercentual,
  formatarScore,
} from '@/lib/format';

/** Data de referência do protótipo — os formatadores nunca leem o relógio. */
const HOJE = '2026-09-12';

interface LinhaDemo {
  id: string;
  nome: string;
  documento: string;
  municipio: string;
  exposicao: number;
  score: number;
  rating: Rating;
  pd12m: number;
  tendencia: Tendencia;
  alertas: number;
}

const LINHAS: LinhaDemo[] = [
  {
    id: 'c1',
    nome: 'Vale do Araguaia Agropecuária Ltda.',
    documento: '12345678000190',
    municipio: 'Luís Eduardo Magalhães/BA',
    exposicao: 14_800_000,
    score: 604,
    rating: 'B',
    pd12m: 0.0713,
    tendencia: 'deterioracao_acelerada',
    alertas: 3,
  },
  {
    id: 'c2',
    nome: 'Fazenda Santa Helena S/A',
    documento: '98765432000155',
    municipio: 'Sorriso/MT',
    exposicao: 32_400_000,
    score: 812,
    rating: 'A',
    pd12m: 0.0142,
    tendencia: 'estavel',
    alertas: 0,
  },
  {
    id: 'c3',
    nome: 'Agro Ribeirão Comércio de Insumos',
    documento: '11222333000181',
    municipio: 'Rio Verde/GO',
    exposicao: 8_150_000,
    score: 468,
    rating: 'C',
    pd12m: 0.1713,
    tendencia: 'deteriorando',
    alertas: 2,
  },
  {
    id: 'c4',
    nome: 'Cerrado Grãos Participações Ltda.',
    documento: '44555666000122',
    municipio: 'Balsas/MA',
    exposicao: 21_000_000,
    score: 318,
    rating: 'D',
    pd12m: 0.3241,
    tendencia: 'melhorando',
    alertas: 5,
  },
];

const COLUNAS: Coluna<LinhaDemo>[] = [
  {
    id: 'nome',
    cabecalho: 'Cliente',
    fixa: 'esquerda',
    minLargura: 220,
    ordenavel: true,
    valorOrdenacao: (linha) => linha.nome,
    celula: (linha) => (
      <div className="min-w-0">
        <p className="type-body-strong truncate">{linha.nome}</p>
        <p className="type-mono truncate">{formatarDocumento(linha.documento)}</p>
      </div>
    ),
  },
  {
    id: 'municipio',
    cabecalho: 'Município/UF',
    ocultarAbaixoDe: 1280,
    celula: (linha) => linha.municipio,
  },
  {
    id: 'exposicao',
    cabecalho: 'Exposição',
    numerica: true,
    ordenavel: true,
    valorOrdenacao: (linha) => linha.exposicao,
    celula: (linha) => formatarMoedaCompacta(linha.exposicao),
  },
  {
    id: 'score',
    cabecalho: 'Score',
    numerica: true,
    ordenavel: true,
    valorOrdenacao: (linha) => linha.score,
    celula: (linha) => formatarScore(linha.score),
  },
  {
    id: 'rating',
    cabecalho: 'Rating',
    largura: 120,
    celula: (linha) => <RatingBadge rating={linha.rating} tamanho="sm" />,
  },
  {
    id: 'pd12m',
    cabecalho: 'PD 12m',
    numerica: true,
    termo: 'PD',
    ordenavel: true,
    valorOrdenacao: (linha) => linha.pd12m,
    celula: (linha) => formatarPercentual(linha.pd12m, 1),
  },
  {
    id: 'tendencia',
    cabecalho: 'Tendência',
    largura: 140,
    celula: (linha) => <TrendIndicator tendencia={linha.tendencia} tamanho="sm" />,
  },
  {
    id: 'alertas',
    cabecalho: 'Alertas',
    numerica: true,
    ordenavel: true,
    valorOrdenacao: (linha) => linha.alertas,
    celula: (linha) => linha.alertas,
  },
];

const EVIDENCIA: Evidencia = {
  id: 'e1',
  fonte: 'TST_CNDT',
  nomeFonte: 'TST — CNDT',
  tipo: 'CERTIDAO',
  titulo: 'Certidão positiva de débitos trabalhistas',
  resumo:
    'Débito trabalhista com trânsito em julgado e não quitado, no valor de R$ 412.300,00, com preferência sobre credores quirografários.',
  dataConsulta: HOJE,
  dataDocumento: '2026-08-03',
  simulada: true,
  urlFicticia: 'https://consulta-simulada.lastro.local/cndt/12345678000190',
  fatoresRelacionados: ['f_cndt'],
};

const ALERTAS: Alerta[] = (['CRITICA', 'ALTA', 'MEDIA', 'BAIXA'] as Severidade[]).map(
  (severidade, indice) => ({
    id: `a${indice}`,
    clienteId: 'c1',
    clienteNome: 'Vale do Araguaia Agropecuária Ltda.',
    data: '2026-09-10',
    severidade,
    titulo:
      severidade === 'CRITICA'
        ? 'Recuperação judicial deferida'
        : severidade === 'ALTA'
          ? 'Nova execução fiscal distribuída'
          : severidade === 'MEDIA'
            ? 'CNDT passou a positiva'
            : 'Atualização cadastral na Receita Federal',
    descricao: 'Evento detectado pelo monitoramento contínuo.',
    impacto: 'Exposição de R$ 14,8 mi passa a concorrer no plano, com deságio estimado.',
    acaoRecomendada: 'Suspender novos embarques e acionar a garantia extraconcursal.',
    lido: indice > 1,
  }),
);

function Secao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeader titulo={titulo} descricao={descricao} nivel={2} />
      {children}
    </section>
  );
}

function Amostra({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="type-eyebrow">{rotulo}</p>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}

const CORES: { grupo: string; nomes: string[] }[] = [
  {
    grupo: 'Superfícies',
    nomes: ['surface-page', 'surface-card', 'surface-raised', 'surface-input', 'surface-hover', 'surface-sunken'],
  },
  { grupo: 'Bordas', nomes: ['line-subtle', 'line-default', 'line-strong'] },
  { grupo: 'Acento', nomes: ['accent-300', 'accent-400', 'accent-500', 'accent-600', 'accent-tint', 'accent-line'] },
  {
    grupo: 'Risco',
    nomes: ['risk-a', 'risk-b', 'risk-c', 'risk-d', 'risk-neutral'],
  },
  { grupo: 'Categóricas', nomes: ['cat-1', 'cat-2', 'cat-3', 'cat-4', 'cat-5', 'cat-6'] },
];

export default function PaginaDesignSystem() {
  const [busca, setBusca] = useState('');
  const [filtros, setFiltros] = useState<ReadonlySet<string>>(new Set(['B']));
  const [selecionados, setSelecionados] = useState<ReadonlySet<string>>(new Set());
  const [drawerAberto, setDrawerAberto] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [evidenciaAberta, setEvidenciaAberta] = useState(true);
  const [estadoStream, setEstadoStream] = useState<EstadoStreaming>('transmitindo');
  const botaoDrawer = useRef<HTMLButtonElement>(null);

  return (
    <div className="min-h-screen bg-surface-page">
      <SimulatedDataBanner />

      <main className="mx-auto flex max-w-[var(--width-content-max)] flex-col gap-8 p-6">
        <header className="flex flex-col gap-1">
          <p className="type-eyebrow">Lastro · specs/05-design-system.md</p>
          <h1 className="type-page-title">Design system</h1>
          <p className="type-caption max-w-[68ch]">
            Catálogo vivo dos primitivos em todos os estados. Dark-only, sem biblioteca de
            componentes. Nenhum estado de risco é comunicado só por cor: cor, rótulo e ícone,
            sempre os três.
          </p>
        </header>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Tokens de cor" descricao="Nada além destes tokens pode ser inventado.">
          <div className="flex flex-col gap-4">
            {CORES.map((grupo) => (
              <Amostra key={grupo.grupo} rotulo={grupo.grupo}>
                {grupo.nomes.map((nome) => (
                  <span key={nome} className="flex flex-col items-start gap-1">
                    <span
                      className="block size-12 rounded-md border border-line-default"
                      style={{ backgroundColor: `var(--color-${nome})` }}
                      aria-hidden="true"
                    />
                    <span className="type-caption">{nome}</span>
                  </span>
                ))}
              </Amostra>
            ))}
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Tipografia" descricao="Base densa de 13px/20px. Todo número em tabular-nums.">
          <Card className="flex flex-col gap-3">
            <p className="type-score-xl">604</p>
            <p className="type-score-md">604</p>
            <p className="type-score-sm">604</p>
            <p className="type-kpi">R$ 14,8 mi</p>
            <p className="type-kpi-sm">R$ 14,8 mi</p>
            <p className="type-page-title">Título de página</p>
            <p className="type-section-title">Título de seção</p>
            <p className="type-eyebrow">Sobretítulo</p>
            <p className="type-label">Rótulo de campo</p>
            <p className="type-body">Texto padrão da interface e das células.</p>
            <p className="type-body-strong">Ênfase em linha: nome do cliente.</p>
            <p className="type-prose">
              Prosa do parecer e do copiloto, limitada a 68 caracteres por linha para leitura
              confortável em bloco.
            </p>
            <p className="type-caption">Texto auxiliar, fontes e datas de consulta.</p>
            <p className="type-mono">12.345.678/0001-90</p>
            <p className="type-badge">TEXTO DE BADGE</p>
          </Card>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Button e IconButton">
          <Card className="flex flex-col gap-4">
            <Amostra rotulo="Variantes (md)">
              <Button variante="primario" iconeEsquerda={Plus}>
                Nova análise
              </Button>
              <Button variante="secundario" iconeEsquerda={Download}>
                Exportar PDF
              </Button>
              <Button variante="fantasma">Cancelar</Button>
              <Button variante="perigo-neutro" iconeEsquerda={Trash2}>
                Restaurar demonstração
              </Button>
            </Amostra>
            <Amostra rotulo="Tamanho sm, carregando e desabilitado">
              <Button tamanho="sm" variante="primario">
                Consultar
              </Button>
              <Button tamanho="sm" variante="secundario" iconeEsquerda={Filter}>
                Filtros
              </Button>
              <Button variante="primario" carregando>
                Consultando
              </Button>
              <Button variante="secundario" disabled>
                Indisponível
              </Button>
            </Amostra>
            <Amostra rotulo="IconButton">
              <IconButton icone={RotateCcw} rotulo="Recalcular" variante="secundario" />
              <IconButton icone={Download} rotulo="Baixar" variante="fantasma" />
              <IconButton icone={Filter} rotulo="Filtrar" tamanho="sm" variante="secundario" />
            </Amostra>
          </Card>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Badge, RatingBadge e TrendIndicator">
          <Card className="flex flex-col gap-4">
            <Amostra rotulo="Badge — variantes">
              <Badge variante="neutro">Neutro</Badge>
              <Badge variante="acento">Acento</Badge>
              <Badge variante="severidade" severidade="CRITICA" aparencia="solido" />
              <Badge variante="severidade" severidade="ALTA" />
              <Badge variante="severidade" severidade="MEDIA" />
              <Badge variante="severidade" severidade="BAIXA" />
              <Badge variante="natureza" natureza="EXTRACONCURSAL" />
              <Badge variante="natureza" natureza="CONCURSAL" />
              <Badge variante="status" status="nova" />
              <Badge variante="status" status="analisada" />
              <Badge variante="status" status="resolvida" />
              <Badge variante="fonte" fonte="DATAJUD_CNJ" />
              <Badge variante="simulado" />
            </Amostra>
            <Amostra rotulo="RatingBadge — tamanhos">
              {(['A', 'B', 'C', 'D'] as Rating[]).map((rating) => (
                <RatingBadge key={rating} rating={rating} tamanho="lg" />
              ))}
              {(['A', 'B', 'C', 'D'] as Rating[]).map((rating) => (
                <RatingBadge key={`md-${rating}`} rating={rating} tamanho="md" />
              ))}
              {(['A', 'B', 'C', 'D'] as Rating[]).map((rating) => (
                <RatingBadge key={`sm-${rating}`} rating={rating} tamanho="sm" />
              ))}
            </Amostra>
            <Amostra rotulo="RatingBadge — veto (calculado → final)">
              <RatingBadge rating="D" calculado="B" tamanho="md" />
              <RatingBadge rating="C" calculado="A" tamanho="lg" />
            </Amostra>
            <Amostra rotulo="TrendIndicator">
              <TrendIndicator tendencia="melhorando" delta={24} periodo="90d" />
              <TrendIndicator tendencia="estavel" delta={0} periodo="90d" />
              <TrendIndicator tendencia="deteriorando" delta={-42} periodo="90d" />
              <TrendIndicator tendencia="deterioracao_acelerada" delta={-108} periodo="90d" />
              <TrendIndicator tendencia="deteriorando" somenteIcone />
            </Amostra>
          </Card>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao
          titulo="ScoreGauge"
          descricao="O número central nunca é colorido. Em modo veto, o score calculado e a classificação final aparecem lado a lado — o calculado nunca é escondido."
        >
          <div className="flex flex-wrap items-start gap-6">
            <Card className="flex flex-col items-center gap-2">
              <p className="type-eyebrow">lg · com delta</p>
              <ScoreGauge
                score={604}
                ratingCalculado="B"
                ratingFinal="B"
                scoreAnterior={712}
                periodoDelta="90d"
                tendencia="deterioracao_acelerada"
                tamanho="lg"
              />
            </Card>
            <Card className="flex flex-col items-center gap-2">
              <p className="type-eyebrow">md · estável</p>
              <ScoreGauge score={812} ratingCalculado="A" ratingFinal="A" tendencia="estavel" />
            </Card>
            <Card className="flex flex-col items-center gap-2">
              <p className="type-eyebrow">sm</p>
              <ScoreGauge score={318} ratingCalculado="D" ratingFinal="D" tamanho="sm" />
            </Card>
            <Card destaque="d" className="flex flex-col items-center gap-2">
              <p className="type-eyebrow">lg · modo veto</p>
              <ScoreGauge
                score={520}
                ratingCalculado="C"
                ratingFinal="D"
                tamanho="lg"
                vetos={[
                  {
                    id: 'v1',
                    rotulo: 'RJ deferida',
                    efeito: 'FORCA_D',
                    justificativa:
                      'Recuperação judicial deferida em 02/09/2026; Stay Period ativo até 01/03/2027.',
                    evidenciaIds: ['e1'],
                  },
                ]}
              />
            </Card>
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="KpiTile">
          <div className="grid grid-cols-4 gap-4">
            <KpiTile rotulo="Exposição total a prazo" valor={formatarMoedaCompacta(148_300_000)} />
            <KpiTile
              rotulo="PD 12 meses"
              valor={formatarPercentual(0.1713, 1)}
              familia="c"
              termo="PD"
              rodape="Método: curva logística sobre o score"
            />
            <KpiTile
              rotulo="Score"
              valor={formatarScore(604)}
              unidade="/ 1000"
              variacao={{ delta: '−108', tendencia: 'deterioracao_acelerada', periodo: '90d' }}
            />
            <KpiTile rotulo="Cobertura extraconcursal" valor="—" carregando />
            <KpiTile
              rotulo="Risco de RJ"
              valor={formatarPercentual(0.41, 1)}
              familia="d"
              termo="RJ"
              tamanho="sm"
            />
            <KpiTile
              rotulo="Clientes em carteira"
              valor="18"
              aoClicar={() => undefined}
              tamanho="sm"
            />
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="DataTable" descricao="Ordenação por clique no cabeçalho; setas navegam entre as linhas; Enter e Espaço abrem.">
          <Card semPadding>
            <div className="flex items-center justify-between gap-3 px-4 py-3">
              <SearchInput
                valor={busca}
                aoMudar={setBusca}
                atalho="/"
                aria-label="Buscar cliente"
                className="w-80"
              />
              <FilterChips
                rotulo="Filtrar por rating"
                limparRotulo="Limpar"
                selecionados={filtros}
                aoMudar={(proximos) => setFiltros(proximos)}
                opcoes={[
                  { valor: 'A', rotulo: 'Rating A', contagem: 4, familia: 'a' },
                  { valor: 'B', rotulo: 'Rating B', contagem: 7, familia: 'b' },
                  { valor: 'C', rotulo: 'Rating C', contagem: 5, familia: 'c' },
                  { valor: 'D', rotulo: 'Rating D', contagem: 2, familia: 'd' },
                  { valor: 'alerta', rotulo: 'Com alerta', contagem: 6 },
                ]}
              />
            </div>
            <DataTable
              aria-label="Clientes da carteira"
              colunas={COLUNAS}
              linhas={LINHAS}
              obterId={(linha) => linha.id}
              ordenacaoInicial={{ colunaId: 'score', direcao: 'asc' }}
              aoClicarLinha={() => setDrawerAberto(true)}
              linhaAtiva="c1"
              familiaLinha={(linha) => (linha.rating === 'D' ? 'd' : null)}
              selecao={{
                modo: 'multipla',
                selecionados,
                aoMudar: (ids) => setSelecionados(ids),
              }}
              rodape={`Exposição total: ${formatarMoedaCompacta(76_350_000)}`}
            />
          </Card>

          <div className="grid grid-cols-2 gap-4">
            <Card semPadding>
              <p className="type-eyebrow px-4 pt-3">Carregando</p>
              <DataTable
                aria-label="Tabela carregando"
                colunas={COLUNAS.slice(0, 4)}
                linhas={[]}
                obterId={(linha: LinhaDemo) => linha.id}
                carregando
                linhasEsqueleto={4}
              />
            </Card>
            <Card semPadding>
              <p className="type-eyebrow px-4 pt-3">Vazio</p>
              <DataTable
                aria-label="Tabela vazia"
                colunas={COLUNAS.slice(0, 4)}
                linhas={[]}
                obterId={(linha: LinhaDemo) => linha.id}
                vazio={
                  <EmptyState
                    compacto
                    titulo="Nenhum cliente com esses filtros"
                    descricao="Remova um filtro ou amplie a busca."
                  />
                }
              />
            </Card>
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Drawer e Modal">
          <Card className="flex flex-wrap gap-3">
            <Button ref={botaoDrawer} variante="secundario" onClick={() => setDrawerAberto(true)}>
              Abrir drawer
            </Button>
            <Button variante="secundario" onClick={() => setModalAberto(true)}>
              Registrar decisão
            </Button>
          </Card>

          <Drawer
            aberto={drawerAberto}
            aoFechar={() => setDrawerAberto(false)}
            titulo="Vale do Araguaia Agropecuária Ltda."
            subtitulo="12.345.678/0001-90 · Luís Eduardo Magalhães/BA"
            cabecalhoExtra={<RatingBadge rating="B" tamanho="sm" />}
            rodape={
              <>
                <Button variante="fantasma" onClick={() => setDrawerAberto(false)}>
                  Fechar
                </Button>
                <Button variante="primario">Abrir página do cliente</Button>
              </>
            }
          >
            <div className="flex flex-col gap-4">
              <ScoreGauge
                score={604}
                ratingCalculado="B"
                ratingFinal="B"
                tendencia="deterioracao_acelerada"
                scoreAnterior={712}
                periodoDelta="90d"
              />
              <p className="type-body text-fg-secondary">
                Pré-visualização do cliente. A URL não muda ao abrir o drawer: a página do cliente
                continua sendo a rota.
              </p>
            </div>
          </Drawer>

          <Modal
            aberto={modalAberto}
            aoFechar={() => setModalAberto(false)}
            titulo="Registrar decisão do analista"
            descricao="A recomendação do motor não substitui a decisão humana."
            fecharAoClicarFora={false}
            acoes={
              <>
                <Button variante="fantasma" onClick={() => setModalAberto(false)}>
                  Cancelar
                </Button>
                <Button variante="primario" onClick={() => setModalAberto(false)}>
                  Registrar
                </Button>
              </>
            }
          >
            <p className="type-body text-fg-secondary">
              Aprovar, aprovar com restrições, revisar, suspender ou recusar — sempre com
              justificativa.
            </p>
          </Modal>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Barras: cobertura, exposição e fatores">
          <div className="grid grid-cols-2 gap-4">
            <Card className="flex flex-col gap-4">
              <ProgressBar
                rotulo="Cobertura extraconcursal"
                valor={0.42}
                termo="EXTRACONCURSAL"
                marcas={[{ valor: 1, rotulo: '100%' }]}
              />
              <ProgressBar rotulo="Cobertura total" valor={1.32} marcas={[{ valor: 1, rotulo: '100%' }]} />
              <ProgressBar rotulo="Utilização do limite" valor={0.68} familia="neutral" altura={6} />
            </Card>

            <Card className="flex flex-col gap-3">
              <StackedBar
                aria-label="Composição da exposição"
                total={14_800_000}
                destaque="risco"
                segmentos={[
                  { id: 'extra', rotulo: 'Extraconcursal', valor: 6_200_000, familia: 'a' },
                  { id: 'concursal', rotulo: 'Concursal', valor: 4_100_000, familia: 'c' },
                  {
                    id: 'risco',
                    rotulo: 'Em risco em RJ',
                    valor: 4_500_000,
                    familia: 'd',
                    padrao: 'hachurado',
                  },
                ]}
              />
            </Card>
          </div>

          <Card className="flex flex-col gap-6">
            <FactorBar
              modo="contribuicao"
              mostrarDimensao
              somaEsperada={-86}
              aoSelecionar={() => undefined}
              selecionado="f2"
              fatores={[
                { id: 'f1', rotulo: 'Certidões negativas completas', direcao: 'protecao', dimensao: 'fiscal', impacto: 34 },
                { id: 'f2', rotulo: 'Execuções fiscais ativas', detalhe: '4 processos · R$ 2,1 mi', direcao: 'risco', dimensao: 'juridico', impacto: -72 },
                { id: 'f3', rotulo: 'CNDT positiva', direcao: 'risco', dimensao: 'juridico', impacto: -48 },
                { id: 'f4', rotulo: 'Pontualidade histórica', direcao: 'protecao', dimensao: 'comportamental', impacto: 28 },
                { id: 'f5', rotulo: 'Risco climático ZARC elevado', direcao: 'risco', dimensao: 'agroclimatico', impacto: -28 },
              ]}
            />
            <FactorBar
              modo="delta"
              limite={2}
              fatores={[
                { id: 'd1', rotulo: 'Novas execuções', direcao: 'risco', impacto: -52 },
                { id: 'd2', rotulo: 'Dívida ativa PGFN', direcao: 'risco', impacto: -31 },
                { id: 'd3', rotulo: 'Deterioração climática', direcao: 'risco', impacto: -15 },
                { id: 'd4', rotulo: 'Pagamento em dia no período', direcao: 'protecao', impacto: 12 },
              ]}
            />
          </Card>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Timeline, alertas e evidências">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <SectionHeader titulo="Linha do tempo" nivel={3} />
              <div className="pt-3">
                <Timeline
                  limite={3}
                  aoSelecionarEvidencia={() => undefined}
                  itens={[
                    {
                      id: 't1',
                      data: '2026-09-10',
                      titulo: 'Recuperação judicial deferida',
                      severidade: 'CRITICA',
                      fonte: 'DJE',
                      deltaScore: -84,
                      scoreApos: 520,
                      evidenciaIds: ['e1'],
                      destaque: true,
                    },
                    {
                      id: 't2',
                      data: '2026-08-22',
                      titulo: 'Nova execução fiscal distribuída',
                      descricao: 'R$ 1,2 mi · Vara de Execuções Fiscais de Barreiras/BA',
                      severidade: 'ALTA',
                      fonte: 'DATAJUD_CNJ',
                      deltaScore: -31,
                    },
                    {
                      id: 't3',
                      data: '2026-07-15',
                      titulo: 'CNDT passou a positiva',
                      severidade: 'MEDIA',
                      fonte: 'TST_CNDT',
                      deltaScore: -18,
                    },
                    {
                      id: 't4',
                      data: '2026-06-30',
                      titulo: 'Atualização cadastral',
                      severidade: 'BAIXA',
                      fonte: 'RECEITA_FEDERAL',
                    },
                  ]}
                />
              </div>
            </Card>

            <Card semPadding>
              <p className="type-eyebrow px-4 pt-3 pb-2">Central de alertas</p>
              {ALERTAS.map((alerta) => (
                <AlertRow
                  key={alerta.id}
                  alerta={alerta}
                  referencia={HOJE}
                  aoAbrirCliente={() => undefined}
                />
              ))}
            </Card>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <EvidenceCard
              evidencia={EVIDENCIA}
              expandida={evidenciaAberta}
              aoAlternar={() => setEvidenciaAberta((anterior) => !anterior)}
              aoClicarFator={() => undefined}
              fatoresRelacionados={[{ id: 'f_cndt', rotulo: 'CNDT positiva', impacto: -48 }]}
            />
            <EvidenceCard evidencia={{ ...EVIDENCIA, id: 'e2' }} />
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="StreamingText" descricao="Os números da prosa são texto: a fonte de verdade é o motor determinístico.">
          <Card className="flex flex-col gap-4">
            <FilterChips
              rotulo="Estado do streaming"
              modo="unico"
              selecionados={new Set([estadoStream])}
              aoMudar={(proximos) => {
                const [primeiro] = Array.from(proximos);
                setEstadoStream((primeiro as EstadoStreaming) ?? 'aguardando');
              }}
              opcoes={[
                { valor: 'aguardando', rotulo: 'Aguardando' },
                { valor: 'transmitindo', rotulo: 'Transmitindo' },
                { valor: 'concluido', rotulo: 'Concluído' },
                { valor: 'degradado', rotulo: 'Degradado' },
                { valor: 'erro', rotulo: 'Erro' },
              ]}
            />
            <StreamingText
              estado={estadoStream}
              origem={estadoStream === 'degradado' ? 'deterministico' : 'llm'}
              modelo="gpt-5.4-mini"
              aoTentarNovamente={() => setEstadoStream('transmitindo')}
              texto={
                'O score caiu de **712 para 604** em 60 dias, e a deterioração é jurídica, não financeira: o cliente segue pagando em dia.\n\n- Quatro novas execuções fiscais somando R$ 2,1 milhões\n- Inscrição em dívida ativa federal\n- CNDT positiva desde agosto'
              }
            />
          </Card>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Estados de ausência e de falha">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <EmptyState
                titulo="Nenhum alerta no período"
                descricao="Amplie a janela para 90 dias ou remova os filtros de severidade."
                acao={{ rotulo: 'Limpar filtros', aoClicar: () => undefined, icone: RotateCcw }}
              />
            </Card>
            <Card>
              <ErrorState
                detalhe="GET http://localhost:5001/api/clientes — ECONNREFUSED"
                aoTentarNovamente={() => undefined}
              />
            </Card>
          </div>
        </Secao>

        {/* ---------------------------------------------------------------- */}
        <Secao titulo="Faixa de dados simulados, contador de custo e glossário">
          <Card className="flex flex-col gap-4">
            <Amostra rotulo="SimulatedDataBanner">
              <div className="w-full">
                <SimulatedDataBanner variante="impressao" />
              </div>
            </Amostra>

            <Amostra rotulo="CostCounter">
              <CostCounter
                tokensEntrada={14_200}
                tokensSaida={4_100}
                custoUsd={0.42}
                orcamentoUsd={10}
                llmAtivo
                chamadas={6}
              />
              <CostCounter
                tokensEntrada={280_000}
                tokensSaida={90_000}
                custoUsd={8.4}
                orcamentoUsd={10}
                llmAtivo
                chamadas={112}
              />
              <CostCounter
                tokensEntrada={340_000}
                tokensSaida={120_000}
                custoUsd={10.4}
                orcamentoUsd={10}
                llmAtivo
                chamadas={148}
              />
              <CostCounter
                tokensEntrada={0}
                tokensSaida={0}
                custoUsd={0}
                orcamentoUsd={10}
                llmAtivo={false}
                chamadas={0}
              />
            </Amostra>

            <Amostra rotulo="Glossário — passe o mouse ou navegue por teclado">
              <p className="type-body flex flex-wrap gap-x-1.5 gap-y-1">
                <Termo sigla="PD" />
                <Termo sigla="RJ" />
                <Termo sigla="CNDT" />
                <Termo sigla="CAR" />
                <Termo sigla="ZARC" />
                <Termo sigla="CPR" />
                <Termo sigla="EXTRACONCURSAL" />
                <Termo sigla="CONCURSAL" />
                <Termo sigla="STAY_PERIOD" />
                <Termo sigla="PGFN" />
                <Termo sigla="CRF_FGTS" />
                <Termo sigla="COVENANT" />
                <Termo sigla="BARTER" />
                <Termo sigla="HAIRCUT" />
                <Termo sigla="INADIMPLENCIA_TECNICA" />
              </p>
            </Amostra>

            <Amostra rotulo="Tooltip livre">
              <Tooltip conteudo="Texto curto de apoio, até 240 caracteres." lado="direita">
                <Button variante="secundario">Com tooltip à direita</Button>
              </Tooltip>
            </Amostra>
          </Card>
        </Secao>
      </main>
    </div>
  );
}
