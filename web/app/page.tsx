import { permanentRedirect } from 'next/navigation';

/**
 * `/` → `/nova-analise` (D11.8).
 *
 * O jurado cai direto na consulta de crédito. Esta rota não renderiza nada, nem um flash de
 * layout: `permanentRedirect` responde 308 antes de qualquer paint.
 */
export default function Raiz(): never {
  permanentRedirect('/nova-analise');
}
