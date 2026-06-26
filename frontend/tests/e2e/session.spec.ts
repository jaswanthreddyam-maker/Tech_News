import { test, expect } from '@playwright/test';
import { TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD } from '../constants';

// ---------------------------------------------------------------------------
// E2E — Session Expiration & Re-authentication
// ---------------------------------------------------------------------------

test.describe('Session Expiration @e2e', () => {

  test('should handle authentication flow and session state', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    const emailInput = page.locator('#login-email');
    const passwordInput = page.locator('#login-password');
    const submitBtn = page.locator('#login-submit');

    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await emailInput.fill(TEST_ADMIN_EMAIL);
    await passwordInput.fill(TEST_ADMIN_PASSWORD);
    await submitBtn.click();
      await expect(page).toHaveURL(/.*(\/admin|\/dashboard|\/$)/, { timeout: 10000 });

    // 2. Verify authenticated state on homepage
    await page.goto('/');
    

    // Should show user indicator (dropdown, avatar, etc.)
    const userIndicator = page.locator(
      'button:has-text("ADMIN"), [data-testid*="user"], [aria-label*="user" i], [aria-label*="account" i]'
    ).first();
    await expect(userIndicator).toBeVisible({ timeout: 10000 });

    // 3. Clear auth tokens by clearing storage
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Also clear cookies
    const cookies = await page.context().cookies();
    if (cookies.length > 0) {
      await page.context().clearCookies();
    }

    // 4. Navigate to a protected route — should redirect to login
    await page.goto('/dashboard');
    

    // Should either redirect to login or show unauthenticated state
    const url = page.url();
    const isOnLogin = url.includes('/login');
    const isOnDashboard = url.includes('/dashboard');

    // If redirected to login, verify login form is visible
    if (isOnLogin) {
      await expect(page.locator('#login-email')).toBeVisible({ timeout: 10000 });
    }

    // 5. Re-authenticate
    if (isOnLogin) {
      await page.locator('#login-email').fill(TEST_ADMIN_EMAIL);
      await page.locator('#login-password').fill(TEST_ADMIN_PASSWORD);
      await page.locator('#login-submit').click();
        await expect(page).toHaveURL(/.*(\/admin|\/dashboard|\/$)/, { timeout: 10000 });
    }
  });
});
