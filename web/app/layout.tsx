import type { Metadata, Viewport } from 'next';

import { Shell } from '@/components/shell';
import { classeFontes } from '@/components/ui/fontes';

import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Lastro — inteligência de risco de crédito no agronegócio',
    template: '%s · Lastro',
  },
  description:
    'Protótipo demonstrativo de plataforma de inteligência de risco de crédito e prevenção à inadimplência no agronegócio. Dados simulados.',
};

/** Dark-only (D7): declarado no `<html>` para o navegador pintar os controles nativos certo. */
export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0B0F14',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${classeFontes} h-full antialiased`}>
      <body className="min-h-full bg-surface-page text-fg-primary">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-100 focus:rounded focus:bg-surface-raised focus:px-3 focus:py-2 focus:text-fg-primary"
        >
          Ir para o conteúdo
        </a>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
