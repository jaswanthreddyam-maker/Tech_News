import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// E2E — Semantic Search → Open Article
// ---------------------------------------------------------------------------

test.describe('Search → Article Flow @e2e', () => {

  test('should perform semantic search and navigate to article', async ({ page }) => {
    // 1. Navigate to homepage
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();

    // 2. Navigate to search page
    await page.goto('/search');
    

    // 3. Find and use the search input
    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('artificial intelligence');
    await searchInput.press('Enter');

    // 4. Wait for search results to appear
    await page.waitForTimeout(2000); // Allow for semantic search latency

    // 5. Check that results are rendered (articles or "no results" message)
    const hasResults = await page.locator('article, [data-testid="article-card"], a[href*="/articles/"]').count();
    const hasNoResults = await page.locator('text=/no results|no articles|nothing found/i').count();
    expect(hasResults > 0 || hasNoResults > 0).toBeTruthy();

    // 6. If results exist, click the first article
    if (hasResults > 0) {
      const firstArticleLink = page.locator('a[href*="/articles/"]').first();
      await expect(firstArticleLink).toBeVisible();

      const articleHref = await firstArticleLink.getAttribute('href');
      await firstArticleLink.click();

      // 7. Verify navigation to article page
      
      expect(page.url()).toContain('/articles/');

      // 8. Verify article content is rendered
      const articleHeading = page.locator('h1').first();
      await expect(articleHeading).toBeVisible({ timeout: 10000 });
    }
  });

  test('should clear search and return to default state', async ({ page }) => {
    await page.goto('/search');
    

    const searchInput = page.locator('input[type="text"], input[type="search"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Perform search
    await searchInput.fill('machine learning');
    await searchInput.press('Enter');
    await page.waitForTimeout(2000);

    // Clear search
    const clearButton = page.locator('button:has-text("Clear"), button[aria-label*="clear"]').first();
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await expect(searchInput).toHaveValue('');
    }
  });
});
