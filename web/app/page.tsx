import { permanentRedirect } from 'next/navigation';

/**
 * `/` → `/carteira` (D11.8 · `03-ux-e-telas.md` §1.1, linha 1).
 *
 * O jurado cai direto no "onde está o risco". Esta rota não renderiza nada, nem um flash de
 * layout: `permanentRedirect` responde 308 antes de qualquer paint.
 */
export default function Raiz(): never {
  permanentRedirect('/carteira');
}
