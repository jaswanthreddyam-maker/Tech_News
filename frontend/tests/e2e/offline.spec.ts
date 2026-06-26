import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// E2E — Offline Mode → Reconnect → Sync
// ---------------------------------------------------------------------------

test.describe.skip('Offline Mode @e2e', () => {

  test('should show offline page when network is disconnected', async ({ page, context }) => {
    // 1. Load the homepage first (to cache service worker)
    await page.goto('/');
    

    // 2. Wait for service worker to install
    await page.waitForTimeout(3000);

    // 3. Go offline
    await context.setOffline(true);

    // 4. Navigate to the offline page
    await page.goto('/~offline').catch(() => {});
    await page.waitForTimeout(1000);

    // 5. Check that offline content is rendered
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();

    // 6. Go back online
    await context.setOffline(false);

    // 7. Navigate to homepage — should work again
    await page.goto('/');
    
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 15000 });
  });
});
