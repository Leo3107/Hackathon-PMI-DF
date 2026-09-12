import type { Metadata } from 'next';

import { PaginaDoCliente } from '@/components/cliente';

/**
 * `/clientes/[id]` — a maior superfície do produto (`specs/03-ux-e-telas.md` §4).
 *
 * A rota é um componente de servidor fininho de propósito. O conteúdo é cliente porque toda
 * chamada que recalcula risco carrega o **estado de sessão** (eventos simulados, status de red
 * flag), que vive em `localStorage` e não existe no servidor: renderizar no servidor devolveria
 * um score que ignora a simulação que o analista acabou de injetar.
 *
 * `force-dynamic` porque nada aqui é cacheável — o motor recalcula a cada abertura (D4).
 */
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Cliente',
  description:
    'Score, probabilidade de default, risco de recuperação judicial, exposição, garantias e recomendação — com a evidência de cada número. Dados simulados.',
};

export default async function RotaDoCliente({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PaginaDoCliente clienteId={decodeURIComponent(id)} />;
}
