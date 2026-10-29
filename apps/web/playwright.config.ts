import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../..', import.meta.url));
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1,
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  webServer: [
    { command: 'node scripts/python.mjs -m scripts.e2e_server', cwd: root, url: 'http://127.0.0.1:8001/health', timeout: 60000, reuseExistingServer: false },
    { command: 'pnpm --filter web exec vite dev --host 127.0.0.1 --port 5174 --strictPort', cwd: root,
      url: 'http://127.0.0.1:5174', env: { PUBLIC_API_BASE_URL: 'http://127.0.0.1:8001' }, timeout: 60000, reuseExistingServer: false }
  ]
});
