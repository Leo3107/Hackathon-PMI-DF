import type { Metadata } from 'next';

import { PainelDaCarteira } from './painel';

export const metadata: Metadata = {
  title: 'Carteira',
  description:
    'Onde está o risco da carteira agora: exposição total, exposição em risco, cobertura por garantia e as maiores exposições desprotegidas em cenário de recuperação judicial. Dados simulados.',
};

/**
 * Rota 2 do mapa de `03-ux-e-telas.md` §1.1 — e o destino do redirect 308 de `/`.
 *
 * O conteúdo depende do motor e do estado de sessão do navegador (eventos simulados), então o
 * painel é cliente. A rota em si permanece server component para carregar metadados sem
 * arrastar o `<head>` para o bundle.
 */
export default function RotaCarteira() {
  return (
    <section aria-label="Carteira">
      <PainelDaCarteira />
    </section>
  );
}
