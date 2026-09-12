import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

const raiz = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': raiz },
  },
  test: {
    // jsdom para os primitivos de UI; as funções puras (lib/format, geometria do
    // gauge) rodam igualmente bem nele e o fuso é fixado para determinismo.
    environment: 'jsdom',
    // Sem `globals`: cada teste importa de 'vitest' explicitamente, para não
    // depender de `types: ["vitest/globals"]` no tsconfig compartilhado.
    globals: false,
    include: ['**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/**', '.next/**', 'e2e/**', 'tests-e2e/**', 'playwright/**'],
    restoreMocks: true,
  },
});
