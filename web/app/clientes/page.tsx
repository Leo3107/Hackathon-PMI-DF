import type { Metadata } from 'next';
import { Suspense } from 'react';

import { ListaDeClientes } from '@/components/clientes';

export const metadata: Metadata = {
  title: 'Clientes',
  description:
    'Lista completa da carteira com score, rating, PD 12m, risco de recuperação judicial, tendência e alertas por cliente. Filtros, busca e ordenação com estado na URL. Dados simulados.',
};

/**
 * Rota 3 do mapa de `03-ux-e-telas.md` §1.1.
 *
 * Rota própria, e não seção da carteira, pela decisão de §1.2: são duas perguntas diferentes,
 * o estado de filtro precisa viver na URL, e o drill-down dos KPIs e gráficos precisa de um
 * destino para onde navegar.
 *
 * `Suspense` é obrigatório: `ListaDeClientes` lê `useSearchParams`, e sem a fronteira o Next
 * recusa a pré-renderização da rota.
 */
export default function RotaClientes() {
  return (
    <section aria-label="Clientes">
      <Suspense fallback={<EsqueletoDaLista />}>
        <ListaDeClientes />
      </Suspense>
    </section>
  );
}

/** Cabeçalho e filtros reais são do componente cliente; aqui só a forma, como pede §9.2. */
function EsqueletoDaLista() {
  return (
    <div className="flex flex-col gap-4" aria-hidden="true">
      <div className="esqueleto h-8 w-64 rounded-md" />
      <div className="esqueleto h-8 w-full rounded-md" />
      <div className="esqueleto h-[520px] w-full rounded-md" />
    </div>
  );
}
