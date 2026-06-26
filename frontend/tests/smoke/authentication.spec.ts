import { test, expect } from '@playwright/test';
import { TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD } from '../constants';

// ---------------------------------------------------------------------------
// Smoke Tests — Authentication Flow
// ---------------------------------------------------------------------------

test.describe('Authentication Flow @smoke', () => {

  test('should complete Admin Login, Command Center navigation, and Logout flow', async ({ page }) => {
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', err => console.error('BROWSER ERROR:', err.message));
    page.on('request', req => console.log('REQUEST:', req.method(), req.url()));
    page.on('response', res => console.log('RESPONSE:', res.status(), res.url()));

    // 1. Navigate to login page
    await page.goto('/login');
    
    // Check login page elements
    const emailInput = page.locator('#login-email');
    const passwordInput = page.locator('#login-password');
    const submitBtn = page.locator('#login-submit');
    
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitBtn).toBeVisible();
    
    // Fill credentials (using seeded admin credentials from constants.ts)
    await emailInput.fill(TEST_ADMIN_EMAIL);
    await passwordInput.fill(TEST_ADMIN_PASSWORD);
    await submitBtn.click();
    
    // Wait for redirect to /admin to ensure login process completes
    await expect(page).toHaveURL(/\/admin/, { timeout: 10000 });
    
    // Navigate to homepage to test user dropdown header
    await page.goto('/');
    
    // After login, should redirect to home page, and user dropdown should appear
    // The user menu trigger uses an avatar with initials
    const userDropdown = page.locator('#user-menu-trigger');
    await expect(userDropdown).toBeVisible({ timeout: 10000 });
    
    // 2. Open dropdown and navigate to Admin Command Center
    await userDropdown.click();
    const dashboardLink = page.locator('a:has-text("Admin Dashboard")');
    await expect(dashboardLink).toBeVisible();
    await dashboardLink.click();
    
    // Wait for the admin page to load and check title
    await expect(page).toHaveURL(/\/admin/);
    const commandCenterHeader = page.locator('h1:has-text("COMMAND CENTER")');
    await expect(commandCenterHeader).toBeVisible();
    
    // Verify telemetry metrics and infrastructure checkers are rendered
    const sourceHealthHeader = page.locator('h3:has-text("SOURCE HEALTH")');
    const articlePipelineHeader = page.locator('h3:has-text("ARTICLE PIPELINE")');
    const aiQueueHeader = page.locator('h3:has-text("AI QUEUE")');
    const infraHeader = page.locator('h3:has-text("INFRASTRUCTURE")');
    
    await expect(sourceHealthHeader).toBeVisible();
    await expect(articlePipelineHeader).toBeVisible();
    await expect(aiQueueHeader).toBeVisible();
    await expect(infraHeader).toBeVisible();
    
    // Click manual REFRESH button
    const refreshBtn = page.locator('button:has-text("REFRESH")');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    
    // 3. Logout flow
    await page.goto('/');
    await userDropdown.click();
    
    const logoutBtn = page.locator(':text("Sign Out")');
    await expect(logoutBtn).toBeVisible();
    await logoutBtn.click();
    
    // Verify redirect to login page after logging out
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('#login-email')).toBeVisible();
  });
});
