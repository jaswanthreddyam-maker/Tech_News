import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  reporter: 'list',
  timeout: 60000, // 60 seconds test timeout
  use: {
    baseURL: 'http://localhost',
    trace: 'off',
    screenshot: 'off',
    navigationTimeout: 45000, // 45 seconds page load/navigation timeout
  },
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 }
      },
    },
  ],
});
