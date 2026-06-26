import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Accessibility Certification Gate — WCAG AA
// ---------------------------------------------------------------------------
// Tests every major page for axe-core violations.
// Zero violations required for release.
// ---------------------------------------------------------------------------

test.describe('Accessibility Certification Gate', () => {
  test.beforeEach(async ({ page }) => {
    // Disable animations to prevent mid-flight opacity causing contrast failures
    await page.emulateMedia({ reducedMotion: 'reduce' });
  });

  test('homepage should not have any accessibility issues', async ({ page }) => {
    await page.goto('/');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('search page should not have any accessibility issues', async ({ page }) => {
    await page.goto('/search');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('article page should not have any accessibility issues', async ({ page }) => {
    // Navigate to a test article (may 404, which should also be accessible)
    await page.goto('/articles/a11y-test-article');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('login page should not have any accessibility issues', async ({ page }) => {
    await page.goto('/login');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('404 page should not have any accessibility issues', async ({ page }) => {
    await page.goto('/this-does-not-exist-404-test');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('offline page should not have any accessibility issues', async ({ page }) => {
    await page.goto('/~offline');
    
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
