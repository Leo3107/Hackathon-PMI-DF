/**
 * Blocos das telas de carteira e de lista de clientes.
 *
 * ```ts
 * import { KpisDaCarteira, MatrizDeRisco } from '@/components/carteira';
 * ```
 *
 * Nada aqui é primitivo de design system: tudo é composição de `@/components/ui` a serviço das
 * seções §2 e §3 de `specs/03-ux-e-telas.md`.
 */

export { ALTURA_GRAFICO, CHART, ChartTooltip, LegendaGrafico, MolduraDeGrafico } from './grafico';
export type { ChartTooltipProps, ItemDeLegenda, ItemDeTooltip } from './grafico';

export { ListaDeBarras } from './barras';
export type { ItemDeBarra, ListaDeBarrasProps } from './barras';

export { FaixaDeAtencao } from './atencao-imediata';
export type { FaixaDeAtencaoProps } from './atencao-imediata';

export { KpisDaCarteira } from './kpis';
export type { KpisDaCarteiraProps } from './kpis';

export { MatrizDeRisco } from './matriz-de-risco';
export type { MatrizDeRiscoProps } from './matriz-de-risco';

export { CardDeConcentracao, Concentracao, ExposicaoPorRating } from './visualizacoes';
export type { ConcentracaoProps, ExposicaoPorRatingProps } from './visualizacoes';

export { DinheiroEmRisco } from './dinheiro-em-risco';
export type { DinheiroEmRiscoProps } from './dinheiro-em-risco';

export { EsqueletoDaCarteira, EstadoDeFalha } from './estados';
export type { EstadoDeFalhaProps } from './estados';

export { ListaDeClientes } from './lista-de-clientes';

export {
  DIRECAO_PADRAO,
  FILTROS,
  LIMIAR_DETERIORACAO,
  ORDENS,
  ROTULO_FAIXA_RJ,
  ROTULO_FILTRO,
  aplicarCriterios,
  atendeABusca,
  atendeAoFiltro,
  contarFiltros,
  faixaDeRJ,
  limiarAltaExposicao,
  normalizar,
  ordenarLinhas,
  paraLinha,
  somenteDigitos,
  valorDeOrdem,
} from './linha-cliente';
export type {
  ChaveOrdem,
  CriteriosDeLista,
  Direcao,
  FaixaRJ,
  LinhaCliente,
  ValorFiltro,
} from './linha-cliente';
