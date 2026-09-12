/**
 * Blocos da tela de lista de clientes.
 *
 * ```ts
 * import { ListaDeClientes } from '@/components/clientes';
 * ```
 */

export { EstadoDeFalha } from './estados';
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
