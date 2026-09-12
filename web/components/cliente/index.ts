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
export { BlocoCopiloto, RODAPE_COPILOTO } from './Copiloto';
export { BlocoDecisao } from './Decisao';
export { BlocoEvidencias, DrawerDeEvidencia, DrawerDeFator } from './Evidencias';
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
  useCopiloto,
  useDossie,
  useIndiceDeEvidencias,
  useIndiceDeFatores,
  useNarrativa,
  type Copiloto,
  type Dossie,
  type Narrativa,
  type PontoDaSerie,
  type TurnoCopiloto,
} from './dados';
