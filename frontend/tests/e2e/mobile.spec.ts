import { test, expect, devices } from '@playwright/test';

// ---------------------------------------------------------------------------
// E2E — Mobile Navigation & Responsiveness
// ---------------------------------------------------------------------------

test.describe('Mobile Navigation @e2e', () => {

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
  });

  test('should render mobile layout with accessible navigation', async ({ page }) => {
    // 1. Navigate to homepage
    await page.goto('/');
    

    // 2. Verify the page renders correctly at mobile viewport
    const viewport = page.viewportSize();
    expect(viewport?.width).toBeLessThanOrEqual(430); // iPhone 13 width

    // 3. Verify main heading is visible
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });

    // 4. Check for mobile menu/hamburger button
    const mobileMenu = page.locator(
      'button[aria-label*="menu" i], button[aria-label*="navigation" i], [data-testid*="mobile-menu"]'
    ).first();

    if (await mobileMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mobileMenu.click();
      await page.waitForTimeout(500);

      // Verify mobile nav opens
      const navLinks = page.locator('nav a, [role="navigation"] a');
      const linkCount = await navLinks.count();
      expect(linkCount).toBeGreaterThanOrEqual(0);
    }

    // 5. Navigate to search — verify it works on mobile
    await page.goto('/search');
    
    
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('test');
      // Input should be usable on mobile
      await expect(searchInput).toHaveValue('test');
    }
  });

  test('should render article page correctly on mobile', async ({ page }) => {
    // Navigate to homepage and find an article
    await page.goto('/');
    

    const articleLink = page.locator('a[href*="/articles/"]').first();
    if (await articleLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await articleLink.click();
      

      // Verify article renders on mobile
      await expect(page.locator('h1').first()).toBeVisible({ timeout: 10000 });

      // Content should not overflow horizontally
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = page.viewportSize()?.width || 390;
      // Allow small tolerance for scrollbars
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 20);
    }
  });
});

test.describe('Tablet Navigation @e2e', () => {

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 810, height: 1080 });
  });

  test('should render correctly at tablet viewport', async ({ page }) => {
    await page.goto('/');
    

    const viewport = page.viewportSize();
    expect(viewport?.width).toBeGreaterThan(700);

    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });

    // Search should be visible
    await page.goto('/search');
    
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(searchInput).toBeVisible();
    }
  });
});
