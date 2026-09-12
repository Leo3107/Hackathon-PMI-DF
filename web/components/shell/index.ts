/** Shell do Lastro — navegação persistente, identidade, custo e simulação de evento. */

export { Shell } from './Shell';
export { BarraLateral } from './BarraLateral';
export { BarraSuperior } from './BarraSuperior';
export { BuscaGlobal } from './BuscaGlobal';
export { CopilotoFlutuante } from './CopilotoFlutuante';
export { CustoDoLlm } from './CustoDoLlm';
export { FaixaMotorIndisponivel } from './FaixaMotorIndisponivel';
export { IdentidadeDoAnalista } from './IdentidadeDoAnalista';
export { Popover } from './Popover';
export { SimularEvento } from './SimularEvento';
export { Trilha } from './Trilha';
export { useClientes, useRazaoSocial, recarregarClientes } from './usar-clientes';
export { PERSONA } from './persona';
export {
  GRUPO_OPERACAO,
  itemAtivo,
  rotaSemShell,
  rotuloDaRota,
  type ItemDeNavegacao,
} from './rotas';
export { useCopiloto, type Copiloto, type TurnoCopiloto } from './usar-copiloto';
export { useSessao, useSessaoParaApi } from './usar-sessao';
