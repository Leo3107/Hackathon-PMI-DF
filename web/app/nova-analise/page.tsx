import type { Metadata } from 'next';

import { PaginaNovaAnalise } from '@/components/nova-analise';

export const metadata: Metadata = {
  title: 'Nova análise',
  description:
    'Due diligence de um CPF ou CNPJ antes de conceder crédito a prazo, barter ou CPR: coleta cadastral, jurídica, fiscal, ambiental, agroclimática e histórico interno.',
};

/**
 * Rota 4 do mapa de `03-ux-e-telas.md` §1.1. As três etapas (entrada, pipeline, resultado)
 * vivem nesta única rota, por transição de estado — por isso o conteúdo é cliente e a rota em
 * si permanece server component, só para carregar os metadados.
 */
export default function RotaNovaAnalise() {
  return (
    <section aria-label="Nova análise">
      <PaginaNovaAnalise />
    </section>
  );
}
