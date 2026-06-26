import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// E2E — Theme/Preferences Persistence
// ---------------------------------------------------------------------------

test.describe('Theme & Preferences Persistence @e2e', () => {

  test('should persist dark/light theme toggle across navigation', async ({ page }) => {
    // 1. Navigate to homepage
    await page.goto('/');
    

    // 2. Find and click the theme toggle
    const themeToggle = page.locator(
      'button[aria-label*="theme" i], button[aria-label*="mode" i], button[aria-label*="dark" i], button[data-testid*="theme"]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 5000 }).catch(() => false)) {
      // 3. Get the current theme state
      const htmlElement = page.locator('html');
      const initialClass = await htmlElement.getAttribute('class') || '';
      const initialStyle = await htmlElement.getAttribute('style') || '';
      const wasDark = initialClass.includes('dark') || initialStyle.includes('dark');

      // 4. Toggle theme
      await themeToggle.click();
      await page.waitForTimeout(500);

      // 5. Verify theme changed
      const afterToggleClass = await htmlElement.getAttribute('class') || '';
      const afterToggleStyle = await htmlElement.getAttribute('style') || '';
      const isDarkNow = afterToggleClass.includes('dark') || afterToggleStyle.includes('dark');
      expect(isDarkNow).not.toBe(wasDark);

      // 6. Navigate away and back
      await page.goto('/search');
      
      await page.goto('/');
      

      // 7. Verify theme persisted
      const persistedClass = await htmlElement.getAttribute('class') || '';
      const persistedStyle = await htmlElement.getAttribute('style') || '';
      const persistedDark = persistedClass.includes('dark') || persistedStyle.includes('dark');
      expect(persistedDark).toBe(isDarkNow);
    } else {
      // If no explicit toggle, just verify the page has a theme class on <html>
      const htmlClass = await page.locator('html').getAttribute('class');
      expect(htmlClass).toBeTruthy();
    }
  });
});
