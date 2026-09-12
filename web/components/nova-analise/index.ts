/**
 * Due diligence de novo cliente — ponto único de importação.
 *
 * ```ts
 * import { PaginaNovaAnalise } from '@/components/nova-analise';
 * ```
 *
 * Especificação: `specs/03-ux-e-telas.md` §6.
 */

export { PaginaNovaAnalise } from './PaginaNovaAnalise';
export { Entrada, type EntradaProps } from './Entrada';
export { PainelDoPipeline, type PainelDoPipelineProps } from './PainelDoPipeline';
export {
  JaNaCarteira,
  NaoEncontrado,
  type JaNaCarteiraProps,
  type NaoEncontradoProps,
} from './Desvios';

export {
  PLACEHOLDER_DOCUMENTO,
  TAMANHO_CNPJ,
  TAMANHO_CPF,
  analisarDocumento,
  cnpjValido,
  cpfValido,
  documentoValido,
  mascararDocumento,
  mensagemDoDocumento,
  somenteDigitos,
  type EstadoDocumento,
  type TipoDocumento,
} from './documento';

export {
  ESTAGIOS,
  INDICE_SCORE,
  PISO_ESTAGIO_MS,
  SEM_REGISTRO,
  TETO_ESTAGIO_MS,
  TOLERANCIA_FECHAMENTO,
  achadosDoEstagio,
  contadorDoEstagio,
  contarEvidencias,
  dadoDisponivel,
  duracaoDeExibicao,
  horaDoRegistro,
  linhasDoRegistro,
  resultadoDoEstagio,
  statusAposRevelar,
  type DefinicaoEstagio,
  type ItemDeRegistro,
  type StatusEstagio,
} from './pipeline';

export {
  ROTULO_PERFIL,
  perfilDoRating,
  perfisDemonstrativos,
  type PerfilDeCredito,
  type PerfilDemonstrativo,
} from './perfis';

export { useAnalise, type Analise, type EstadoDeEstagio, type EtapaAnalise } from './usar-analise';
