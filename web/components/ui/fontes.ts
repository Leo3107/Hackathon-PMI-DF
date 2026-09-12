import { Inter, JetBrains_Mono, Outfit } from 'next/font/google';

/**
 * Famílias do design system (spec §4.1).
 *
 * **Inter** para corpo/tabela/densidade (legibilidade em texto pequeno);
 * **Outfit** para títulos, KPIs e o número do score (`--font-display`) — dá o
 * tom comercial/amigável sem sacrificar densidade onde ela importa;
 * **JetBrains Mono** exclusivamente para identificadores técnicos —
 * CPF/CNPJ, IDs de processo, hashes de evidência, contador de tokens.
 *
 * Todas via `next/font/google`: o Next baixa em build e serve do próprio
 * domínio. Nenhuma requisição a CDN externo em runtime; nunca importar por
 * `<link>` ou `@import url()`.
 *
 * O `app/globals.css` já aponta `--font-sans`/`--font-display`/`--font-mono`
 * para as variáveis abaixo. Ao layout resta uma única linha:
 *
 * ```tsx
 * import { classeFontes } from '@/components/ui/fontes';
 * <html lang="pt-BR" className={classeFontes}>
 * ```
 */
export const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  display: 'swap',
  variable: '--font-inter',
  axes: ['opsz'], // eixo óptico: melhora o número gigante do gauge
});

export const outfit = Outfit({
  subsets: ['latin', 'latin-ext'],
  weight: ['500', '600', '700'],
  display: 'swap',
  variable: '--font-outfit',
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
});

/** Classe única a aplicar no `<html>` — expõe `--font-inter`, `--font-outfit` e `--font-jetbrains-mono`. */
export const classeFontes = `${inter.variable} ${outfit.variable} ${jetbrainsMono.variable}`;
