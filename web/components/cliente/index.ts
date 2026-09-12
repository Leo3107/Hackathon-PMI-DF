/**
 * Página do cliente — ponto único de importação.
 *
 * ```ts
 * import { PaginaDoCliente } from '@/components/cliente';
 * ```
 *
 * Especificação: `specs/03-ux-e-telas.md` §4 e §5.
 */

export { PaginaDoCliente, type PaginaDoClienteProps } from './PaginaDoCliente';

export { BlocoDimensoes, BlocoOQueMudou, BlocoPorQue, BlocoRedFlags } from './Analise';
export { BandaDeVeto, CabecalhoDoCliente, PainelStayPeriod } from './Cabecalho';
export { BlocoDecisao } from './Decisao';
export { DrawerDeEvidencia, DrawerDeFator } from './Evidencias';
export { BlocoExposicao, FRASE_RISCO_EM_RJ } from './Exposicao';
export { BlocoLinhaDoTempo } from './LinhaDoTempo';
export {
  AvisoDeDecisaoHumana,
  CardDePd,
  CardDeRecomendacao,
  CardDeRiscoRj,
  CardDeScore,
} from './Lateral';
export {
  comparacaoUtil,
  serieDeScore,
  useDossie,
  useIndiceDeEvidencias,
  useIndiceDeFatores,
  useNarrativa,
  type Dossie,
  type Narrativa,
  type PontoDaSerie,
} from './dados';
