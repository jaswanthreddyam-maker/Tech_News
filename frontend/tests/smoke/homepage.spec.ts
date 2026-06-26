import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Smoke Tests — Homepage & Search
// ---------------------------------------------------------------------------

test.describe('Homepage & Search @smoke', () => {

  test('should display landing page and support searching/filtering', async ({ page }) => {
    // 1. Visit landing page
    await page.goto('/');
    
    // Check main title
    await expect(page.locator('h1').first()).toContainText('Tech News Today');
    
    // Check search input presence
    const searchButton = page.locator('button:has-text("Search...")').first();
    await expect(searchButton).toBeVisible();
    await searchButton.click();
    
    // The GlobalSearchOverlay uses an input
    const searchInput = page.locator('input[placeholder="Type a command or search..."]');
    await expect(searchInput).toBeVisible();
    
    // Perform search
    await searchInput.fill('AI');
    await expect(searchInput).toHaveValue('AI');
    
    // Clear input
    await searchInput.fill('');
    await expect(searchInput).toHaveValue('');
    
    // Close the search dialog so the background is interactive again
    await page.locator('button', { hasText: 'Close' }).click();
    
    // Check newsletter section exists
    const newsletterHeader = page.locator('h2:has-text("Daily AI Briefing")');
    await expect(newsletterHeader).toBeVisible();
  });
});
