import type { Metadata } from 'next';

import { PaginaDaArquitetura } from '@/components/arquitetura';
import { listarClientes } from '@/lib/api';

import './arquitetura.css';

/** Nada aqui é cacheável: a página afirma o que está de pé **agora** (`specs/07` §2.1). */
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Arquitetura',
  description:
    'O pipeline do Lastro da fonte pública à decisão do analista, com a fronteira entre o modelo quantitativo e a camada de linguagem desenhada em tela. Dados de carteira simulados.',
};

/**
 * Uma única função de busca, e ela pode falhar sem derrubar nada: a página é sobre a
 * arquitetura, não sobre a carteira. Sem motor, o contador cai no tamanho do dataset e a
 * pastilha viva diz, ela mesma, que o Flask não respondeu.
 */
async function contarClientes(): Promise<number> {
  try {
    const clientes = await listarClientes();
    return clientes.length > 0 ? clientes.length : 18;
  } catch {
    return 18;
  }
}

export default async function RotaArquitetura() {
  return <PaginaDaArquitetura totalDeClientes={await contarClientes()} />;
}
