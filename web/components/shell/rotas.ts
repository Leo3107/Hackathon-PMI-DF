/**
 * Mapa de rotas e navegação persistente (`03-ux-e-telas.md` §1.1 e §1.3).
 *
 * **Nenhuma outra rota existe.** Não criar `/configuracoes`, `/perfil`, `/login`,
 * `/relatorios` nem `/dashboard` — o dashboard *é* `/carteira`.
 *
 * A ordem da sidebar segue o dia do analista: panorama → triagem → concessão → reação →
 * registro. O segundo grupo é de superfícies de banca, não de trabalho, e por isso vem por
 * último e visualmente atenuado.
 */

import {
  CheckCircle2,
  Cpu,
  LayoutGrid,
  LayoutPanelLeft,
  PlusCircle,
  Table2,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';

export interface ItemDeNavegacao {
  href: string;
  rotulo: string;
  Icone: LucideIcon;
  /** `true` para o item que exibe o badge de alertas não lidos. */
  contaAlertas?: boolean;
}

export const GRUPO_OPERACAO: ItemDeNavegacao[] = [
  { href: '/carteira', rotulo: 'Carteira', Icone: LayoutGrid },
  { href: '/clientes', rotulo: 'Clientes', Icone: Table2 },
  { href: '/nova-analise', rotulo: 'Nova análise', Icone: PlusCircle },
  { href: '/alertas', rotulo: 'Alertas', Icone: TriangleAlert, contaAlertas: true },
  { href: '/auditoria', rotulo: 'Auditoria', Icone: CheckCircle2 },
];

export const GRUPO_DOCUMENTACAO: ItemDeNavegacao[] = [
  { href: '/arquitetura', rotulo: 'Arquitetura', Icone: Cpu },
  { href: '/canvas', rotulo: 'Project Canvas', Icone: LayoutPanelLeft },
];

/**
 * Rotas que renderizam **sem** sidebar e sem topbar: são documentos, não telas de trabalho
 * (§1.1). Mantêm o banner de dados simulados na variante de impressão, por conta própria.
 */
export function rotaSemShell(pathname: string): boolean {
  return pathname === '/canvas' || /^\/clientes\/[^/]+\/parecer\/?$/.test(pathname);
}

/** Rótulo do primeiro nível da trilha, quando a rota tem um. */
export function rotuloDaRota(pathname: string): string | null {
  const todos = [...GRUPO_OPERACAO, ...GRUPO_DOCUMENTACAO];
  const item = todos.find((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));
  return item?.rotulo ?? null;
}

export function itemAtivo(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
