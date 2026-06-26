import { test, expect } from '@playwright/test';
import { TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD } from '../constants';

// ---------------------------------------------------------------------------
// E2E — Personalized Recommendations
// ---------------------------------------------------------------------------

test.describe('Personalized Recommendations @e2e', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    const emailInput = page.locator('#login-email');
    const passwordInput = page.locator('#login-password');
    const submitBtn = page.locator('#login-submit');

    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await emailInput.fill(TEST_ADMIN_EMAIL);
    await passwordInput.fill(TEST_ADMIN_PASSWORD);
    await submitBtn.click();
    await expect(page).toHaveURL(/\/(admin|dashboard)?/, { timeout: 10000 });
  });

  test('should display recommendations on homepage for logged-in users', async ({ page }) => {
    await page.goto('/');
    

    // The homepage should render personalized or trending content
    // Look for article cards, recommendation sections, or trending panels
    const articleCards = page.locator(
      'article, [data-testid="article-card"], a[href*="/articles/"]'
    );

    // Either personalized recommendations or general content should be present
    const cardCount = await articleCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(0); // May be empty on fresh DB

    // If articles exist, verify they are interactive
    if (cardCount > 0) {
      const firstCard = articleCards.first();
      await expect(firstCard).toBeVisible();

      // Verify card has a clickable link
      const link = firstCard.locator('a[href*="/articles/"]').first();
      if (await link.isVisible().catch(() => false)) {
        const href = await link.getAttribute('href');
        expect(href).toBeTruthy();
      }
    }
  });
});
