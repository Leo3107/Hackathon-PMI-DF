/**
 * Mapa de rotas e navegação persistente.
 *
 * **Nenhuma outra rota existe.** Só duas telas de trabalho: consultar um CPF/CNPJ antes de
 * conceder crédito, e a carteira de clientes já avaliados.
 */

import { PlusCircle, Table2, type LucideIcon } from 'lucide-react';

export interface ItemDeNavegacao {
  href: string;
  rotulo: string;
  Icone: LucideIcon;
}

export const GRUPO_OPERACAO: ItemDeNavegacao[] = [
  { href: '/nova-analise', rotulo: 'Nova análise', Icone: PlusCircle },
  { href: '/clientes', rotulo: 'Clientes', Icone: Table2 },
];

/**
 * Rotas que renderizam **sem** sidebar e sem topbar: são documentos, não telas de trabalho.
 * Mantêm o banner de dados simulados na variante de impressão, por conta própria.
 */
export function rotaSemShell(pathname: string): boolean {
  return /^\/clientes\/[^/]+\/parecer\/?$/.test(pathname);
}

/** Rótulo do primeiro nível da trilha, quando a rota tem um. */
export function rotuloDaRota(pathname: string): string | null {
  const item = GRUPO_OPERACAO.find((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));
  return item?.rotulo ?? null;
}

export function itemAtivo(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
