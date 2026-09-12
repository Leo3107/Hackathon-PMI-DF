import type { Metadata } from 'next';

import { PaginaDeAlertas } from '@/components/alertas';

export const metadata: Metadata = {
  title: 'Alertas',
  description:
    'O que mudou na carteira e o que fazer a respeito: alertas críticos, altos, médios e informativos, com impacto financeiro e ação recomendada. Dados simulados.',
};

/** Rota 5 do mapa de `03-ux-e-telas.md` §1.1. */
export default function RotaAlertas() {
  return (
    <section aria-label="Central de alertas">
      <PaginaDeAlertas />
    </section>
  );
}
