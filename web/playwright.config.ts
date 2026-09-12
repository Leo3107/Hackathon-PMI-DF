import { defineConfig, devices } from '@playwright/test';

/**
 * E2E do Lastro.
 *
 * Pressupõe os dois serviços de pé: Flask em :5001 e Next em :3000.
 * O webServer abaixo sobe apenas o Next — o Flask precisa estar rodando antes
 * (`npm run dev:api`), porque a interface não calcula nada por conta própria.
 *
 * Os testes NUNCA devem depender de chamada real à OpenAI: rode com
 * LASTRO_LLM_ENABLED=false para que a camada de linguagem use o gerador
 * determinístico. O orçamento de API é limitado e não pode ser gasto em CI.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  timeout: 30_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: process.env.LASTRO_E2E_BASE_URL ?? 'http://localhost:3000',
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1512, height: 945 } },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
