import { defineConfig, devices } from '@playwright/test'

/**
 * El e2e corre contra el stack real levantado con `make up`, no contra un
 * servidor que arranque Playwright: la prueba tiene que ejercitar el mismo
 * backend, la misma base de datos y el mismo proxy que usa una persona.
 */
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'

export default defineConfig({
  testDir: './tests',
  // Un solo worker: los tests comparten la base de datos del stack y se pisan
  // los folios y los estados si corren en paralelo.
  workers: 1,
  fullyParallel: false,
  // En CI un flake es más caro que un reintento; en local, reintentar esconde
  // el problema mientras se depura.
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    locale: 'es-MX',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
