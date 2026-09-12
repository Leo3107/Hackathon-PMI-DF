import type { Metadata } from 'next';

import { PaginaDeAuditoria } from '@/components/auditoria';

export const metadata: Metadata = {
  title: 'Auditoria',
  description:
    'Trilha de decisão humana: quem analisou, quando, com qual score, o que o motor recomendou e o que a pessoa decidiu — com destaque para as decisões divergentes. Dados simulados.',
};

/** Rota 6 do mapa de `03-ux-e-telas.md` §1.1. */
export default function RotaAuditoria() {
  return (
    <section aria-label="Trilha de auditoria">
      <PaginaDeAuditoria />
    </section>
  );
}
