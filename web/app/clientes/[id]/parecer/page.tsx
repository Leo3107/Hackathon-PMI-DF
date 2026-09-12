import type { Metadata } from 'next';

import { PaginaDoParecer } from '@/components/parecer';

import './parecer.css';

/** Nada é cacheável: o motor recalcula a cada abertura (D4). */
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Parecer de Risco',
  description:
    'Relatório Padronizado de Risco de Crédito e Alerta Precoce de RJ/Insolvência, pronto para impressão. Dados simulados.',
};

export default async function RotaDoParecer({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PaginaDoParecer clienteId={decodeURIComponent(id)} />;
}
