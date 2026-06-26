# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke\homepage.spec.ts >> Homepage & Search @smoke >> should display landing page and support searching/filtering
- Location: tests\smoke\homepage.spec.ts:9:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('input[placeholder="Type a command or search..."]')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('input[placeholder="Type a command or search..."]')

```

```yaml
- main:
  - region "Top Stories":
    - heading "OpenAI launches new initiative to help find and patch open source bugs" [level=2]:
      - link "OpenAI launches new initiative to help find and patch open source bugs":
        - /url: /articles/openai-launches-new-initiative-to-help-find-and-patch-open-source-bugs
  - img
  - text: Live Updates
  - link "OpenAI launches new initiative to help find and patch open source bugs TechCrunch 09:38 PM":
    - /url: /articles/openai-launches-new-initiative-to-help-find-and-patch-open-source-bugs
    - heading "OpenAI launches new initiative to help find and patch open source bugs" [level=4]
    - text: TechCrunch
    - img
    - text: 09:38 PM
  - 'link "The running list: major tech layoffs in 2026 where employers cited AI TechCrunch 09:38 PM"':
    - /url: /articles/the-running-list-major-tech-layoffs-in-2026-where-employers-cited-ai
    - 'heading "The running list: major tech layoffs in 2026 where employers cited AI" [level=4]'
    - text: TechCrunch
    - img
    - text: 09:38 PM
  - link "Securing internal systems against increasingly capable and imperfectly aligned AI — Google DeepMind Google DeepMind 09:58 PM":
    - /url: /articles/securing-internal-systems-against-increasingly-capable-and-imperfectly-aligned-ai-google-deepmind
    - heading "Securing internal systems against increasingly capable and imperfectly aligned AI — Google DeepMind" [level=4]
    - text: Google DeepMind
    - img
    - text: 09:58 PM
- dialog "Command Palette":
  - heading "Command Palette" [level=2]
  - img
  - combobox [expanded]
  - listbox "Suggestions":
    - group "Settings":
      - option "Switch to Light Theme" [selected]:
        - img
        - text: Switch to Light Theme
      - option "Switch to Dark Theme":
        - img
        - text: Switch to Dark Theme
    - separator
  - button "Close":
    - img
    - text: Close
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | // ---------------------------------------------------------------------------
  4  | // Smoke Tests — Homepage & Search
  5  | // ---------------------------------------------------------------------------
  6  | 
  7  | test.describe('Homepage & Search @smoke', () => {
  8  | 
  9  |   test('should display landing page and support searching/filtering', async ({ page }) => {
  10 |     // 1. Visit landing page
  11 |     await page.goto('/');
  12 |     
  13 |     // Check main title
  14 |     await expect(page.locator('h1').first()).toContainText('Tech News Today');
  15 |     
  16 |     // Check search input presence
  17 |     const searchButton = page.locator('button:has-text("Search...")').first();
  18 |     await expect(searchButton).toBeVisible();
  19 |     await searchButton.click();
  20 |     
  21 |     // The GlobalSearchOverlay uses an input
  22 |     const searchInput = page.locator('input[placeholder="Type a command or search..."]');
> 23 |     await expect(searchInput).toBeVisible();
     |                               ^ Error: expect(locator).toBeVisible() failed
  24 |     
  25 |     // Perform search
  26 |     await searchInput.fill('AI');
  27 |     await expect(searchInput).toHaveValue('AI');
  28 |     
  29 |     // Clear input
  30 |     await searchInput.fill('');
  31 |     await expect(searchInput).toHaveValue('');
  32 |     
  33 |     // Close the search dialog so the background is interactive again
  34 |     await page.locator('button', { hasText: 'Close' }).click();
  35 |     
  36 |     // Check newsletter section exists
  37 |     const newsletterHeader = page.locator('h2:has-text("Daily AI Briefing")');
  38 |     await expect(newsletterHeader).toBeVisible();
  39 |   });
  40 | });
  41 | 
```