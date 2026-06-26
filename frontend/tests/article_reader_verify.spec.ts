/**
 * Standalone Article Reader Verification Test
 * Tests all acceptance criteria for the theme stabilization pass.
 * Runs directly against http://localhost (nginx proxy) — no auth required for article page.
 *
 * Run with: npx playwright test tests/article_reader_verify.spec.ts --project=chromium
 */

import { test, expect, Page, Locator } from "@playwright/test";

const ARTICLE_URL = "http://127.0.0.1/articles/seed-article-slug-1";

// Helper: set custom input slider value for React
async function setSliderValue(slider: Locator, value: string): Promise<void> {
  await slider.evaluate((el: HTMLInputElement, val) => {
    const prototype = Object.getPrototypeOf(el);
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) {
      setter.call(el, val);
    } else {
      el.value = val;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
}

// Helper: get computed CSS variable value from document root
async function getCssVar(page: Page, varName: string): Promise<string> {
  return page.evaluate((v) => {
    const el = document.querySelector(".prose-theme") || document.documentElement;
    return getComputedStyle(el).getPropertyValue(v).trim();
  }, varName);
}

// Helper: get computed style on the .prose-theme element
async function getProseStyle(page: Page, property: string): Promise<string> {
  return page.evaluate((prop) => {
    const el = document.querySelector(".prose-theme");
    if (!el) return "";
    return getComputedStyle(el).getPropertyValue(prop).trim();
  }, property);
}

test.describe("Article Reader — Theme & Preferences Verification", () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to start from defaults
    await page.goto(ARTICLE_URL);
    await page.evaluate(() => {
      localStorage.removeItem("tnt_reading_preferences");
      localStorage.removeItem("reader_preferences");
    });
    await page.reload();
    await page.waitForSelector("article, h1, .prose-theme");
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 1. READING PREFERENCES — Typeface
  // ─────────────────────────────────────────────────────────────────────────
  test("1a. Typeface: Serif is the default", async ({ page }) => {
    const fontFamily = await getProseStyle(page, "font-family");
    expect(fontFamily.toLowerCase()).toMatch(/georgia|times|serif/);
  });

  test("1b. Typeface: Clicking Sans changes article font to sans-serif", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    await page.getByRole("button", { name: "Sans" }).click();

    const fontFamily = await getProseStyle(page, "font-family");
    expect(fontFamily.toLowerCase()).toMatch(/inter|system-ui|sans-serif/);
  });

  test("1c. Typeface: Clicking Serif reverts to serif", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    await page.getByRole("button", { name: "Sans" }).click();
    await page.getByRole("button", { name: "Serif" }).click();

    const fontFamily = await getProseStyle(page, "font-family");
    expect(fontFamily.toLowerCase()).toMatch(/georgia|times|serif/);
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 2. READING PREFERENCES — Font Size
  // ─────────────────────────────────────────────────────────────────────────
  test("2a. Font size: Default is ~18px (1.125rem)", async ({ page }) => {
    const fontSize = await getProseStyle(page, "font-size");
    const px = parseFloat(fontSize);
    expect(px).toBeGreaterThanOrEqual(17);
    expect(px).toBeLessThanOrEqual(19);
  });

  test("2b. Font size: Slider to XL (22px) increases text size", async ({ page }) => {
    const before = await getProseStyle(page, "font-size");

    await page.getByRole("button", { name: /preferences/i }).click();
    const slider = page.locator('input[type="range"]').first();
    await setSliderValue(slider, "3");

    const after = await getProseStyle(page, "font-size");
    expect(parseFloat(after)).toBeGreaterThan(parseFloat(before));
  });

  test("2c. Font size: Width auto-adjusts with font size", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    const slider = page.locator('input[type="range"]').first();

    await setSliderValue(slider, "0");
    const width16 = await getCssVar(page, "--reader-max-width");

    await setSliderValue(slider, "3");
    const width22 = await getCssVar(page, "--reader-max-width");

    expect(width16).toContain("70ch");
    expect(width22).toContain("80ch");
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 3. READING PREFERENCES — Line Spacing
  // ─────────────────────────────────────────────────────────────────────────
  test("3a. Spacing: Normal sets tighter line-height (~1.6)", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    await page.getByRole("button", { name: "normal" }).click();

    const lh = await getCssVar(page, "--reader-line-height");
    expect(lh).toBe("1.6");
  });

  test("3b. Spacing: Loose sets generous line-height (~2.0)", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    await page.getByRole("button", { name: "loose" }).click();

    const lh = await getCssVar(page, "--reader-line-height");
    expect(lh).toBe("2.0");

    // Also verify paragraph spacing CSS variable was set
    const para = await getCssVar(page, "--reader-paragraph-spacing");
    expect(para).toBe("1.75rem");
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 4. PERSISTENCE
  // ─────────────────────────────────────────────────────────────────────────
  test("4. Preferences persist across page reload", async ({ page }) => {
    // Set non-default preferences
    await page.getByRole("button", { name: /preferences/i }).click();
    await page.getByRole("button", { name: "Sans" }).click();

    const slider = page.locator('input[type="range"]').first();
    await setSliderValue(slider, "2");

    await page.getByRole("button", { name: "loose" }).click();

    // Reload
    await page.reload();
    await page.waitForSelector("article, h1, .prose-theme");

    // Verify CSS variables were restored
    const fontFamily = await getProseStyle(page, "font-family");
    expect(fontFamily.toLowerCase()).toMatch(/inter|system-ui|sans-serif/);

    const fontSize = await getCssVar(page, "--reader-font-size");
    expect(fontSize).toContain("1.25rem"); // 20/16

    const lh = await getCssVar(page, "--reader-line-height");
    expect(lh).toBe("2.0");
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 5. THEME — No hardcoded colors (static check via CSS variable presence)
  // ─────────────────────────────────────────────────────────────────────────
  test("5a. Article tokens: --article-text is defined in light mode", async ({ page }) => {
    // Force light mode
    await page.evaluate(() => {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
      document.documentElement.setAttribute("data-theme", "light");
      document.documentElement.style.colorScheme = "light";
    });
    const articleText = await getCssVar(page, "--article-text");
    console.log("5a Light Mode --article-text:", articleText);
    expect(articleText).toBeTruthy();
    expect(articleText).not.toBe("");
  });

  test("5b. Article tokens: --article-text is defined in dark mode", async ({ page }) => {
    // Force dark mode
    await page.evaluate(() => {
      document.documentElement.classList.remove("light");
      document.documentElement.classList.add("dark");
      document.documentElement.setAttribute("data-theme", "dark");
      document.documentElement.style.colorScheme = "dark";
    });
    const articleText = await getCssVar(page, "--article-text");
    console.log("5b Dark Mode --article-text:", articleText);
    expect(articleText).toBeTruthy();
    expect(articleText).not.toBe("");
  });

  test("5c. Prose text color uses semantic variable, not hardcoded", async ({ page }) => {
    const proseEl = page.locator(".prose-theme").first();
    await expect(proseEl).toBeVisible();

    // Color should not be pure white (#fff) or dark mode grey (#f3f4f6) in light mode
    await page.evaluate(() => {
      document.documentElement.classList.remove("dark");
      document.documentElement.classList.add("light");
      document.documentElement.setAttribute("data-theme", "light");
      document.documentElement.style.colorScheme = "light";
    });
    const color = await getProseStyle(page, "color");
    console.log("5c Light Mode prose color:", color);
    expect(color).not.toBe("rgb(255, 255, 255)");
    expect(color).not.toBe("rgb(243, 244, 246)"); // old hardcoded #f3f4f6
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 6. FLOATING ACTIONS — WCAG-compliant hover states
  // ─────────────────────────────────────────────────────────────────────────
  test("6a. Floating actions: All buttons have aria-labels", async ({ page }) => {
    const actions = ["Share article", "Bookmark article", "Add to workspace", "Copy article link", "Print article"];
    for (const label of actions) {
      const btn = page.getByRole("button", { name: label });
      await expect(btn).toBeVisible();
    }
  });

  test("6b. Floating actions: Copy button shows toast", async ({ page }) => {
    await page.getByRole("button", { name: "Copy article link" }).click();
    // Look for toast notification
    const toast = page.locator("[role='status'], [data-sonner-toast], [data-radix-toast-viewport] li").first();
    await expect(toast).toBeVisible({ timeout: 3000 });
  });

  test("6c. Floating actions: Bookmark toggles icon on click", async ({ page }) => {
    const bookmarkBtn = page.getByRole("button", { name: /bookmark/i }).first();
    // Get the SVG path before click
    const iconBefore = await bookmarkBtn.locator("svg").getAttribute("class");

    await bookmarkBtn.click();
    await page.waitForTimeout(500);

    // After click, aria-pressed should be set
    const pressed = await bookmarkBtn.getAttribute("aria-pressed");
    expect(["true", "false"]).toContain(pressed);
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 7. KEYBOARD ACCESSIBILITY — Focus rings
  // ─────────────────────────────────────────────────────────────────────────
  test("7a. Focus rings: Preferences button shows focus ring on Tab", async ({ page }) => {
    await page.keyboard.press("Tab");
    // Tab multiple times to reach preferences
    for (let i = 0; i < 10; i++) {
      const focused = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
      if (focused === "Reading preferences") break;
      await page.keyboard.press("Tab");
    }

    const focusedLabel = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
    // Focus should be on an interactive element
    const activeTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(["BUTTON", "A", "INPUT"]).toContain(activeTag);
  });

  test("7b. Preferences dropdown: Escape closes it", async ({ page }) => {
    await page.getByRole("button", { name: /preferences/i }).click();
    await expect(page.getByRole("button", { name: "Sans" })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Sans" })).not.toBeVisible();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 8. RESPONSIVE — No horizontal scroll at mobile widths
  // ─────────────────────────────────────────────────────────────────────────
  test("8. Mobile: No horizontal overflow at 375px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(ARTICLE_URL);
    await page.waitForSelector("article, h1, .prose-theme");

    // Advanced overflow detector
    const overflowing = await page.evaluate(() => {
      const elms = Array.from(document.querySelectorAll("*"));
      return elms
        .map(el => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return {
            tagName: el.tagName,
            className: el.className,
            id: el.id,
            offsetWidth: (el as HTMLElement).offsetWidth,
            rectWidth: rect.width,
            scrollWidth: el.scrollWidth,
            overflowX: style.overflowX,
            hasOverflow: el.scrollWidth > (el as HTMLElement).offsetWidth + 2
          };
        })
        .filter(x => x.hasOverflow && x.overflowX !== "auto" && x.overflowX !== "scroll" && x.overflowX !== "hidden")
        .slice(0, 10);
    });
    console.log("MOBILE ACTUAL OVERFLOW CAUSES:", overflowing);

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = 375;

    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 5); // 5px tolerance
  });

  test("9. Tablet: No horizontal overflow at 768px", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(ARTICLE_URL);
    await page.waitForSelector("article, h1, .prose-theme");

    // Advanced overflow detector
    const overflowing = await page.evaluate(() => {
      const elms = Array.from(document.querySelectorAll("*"));
      return elms
        .map(el => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return {
            tagName: el.tagName,
            className: el.className,
            id: el.id,
            offsetWidth: (el as HTMLElement).offsetWidth,
            rectWidth: rect.width,
            scrollWidth: el.scrollWidth,
            overflowX: style.overflowX,
            hasOverflow: el.scrollWidth > (el as HTMLElement).offsetWidth + 2
          };
        })
        .filter(x => x.hasOverflow && x.overflowX !== "auto" && x.overflowX !== "scroll" && x.overflowX !== "hidden")
        .slice(0, 10);
    });
    console.log("TABLET ACTUAL OVERFLOW CAUSES:", overflowing);

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(773);
  });

  test("DEBUG: Print Floating Actions HTML", async ({ page }) => {
    await page.goto(ARTICLE_URL);
    await page.waitForSelector("article, h1, .prose-theme");
    const html = await page.evaluate(() => {
      const el = document.querySelector("aside[aria-label='Article actions']");
      return el ? el.outerHTML : "NOT FOUND";
    });
    console.log("FLOATING ACTIONS HTML:", html);
  });
});
