# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke\authentication.spec.ts >> Authentication Flow @smoke >> should complete Admin Login, Command Center navigation, and Logout flow
- Location: tests\smoke\authentication.spec.ts:10:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /\/admin/
Received string:  "http://localhost:3000/login"
Timeout: 10000ms

Call log:
  - Expect "toHaveURL" with timeout 10000ms
    23 × unexpected value "http://localhost:3000/login"

```

```yaml
- link "Tech News Today":
  - /url: /
  - img
  - text: Tech News Today
- text: TECH NEWS TODAY • AUTONOMOUS NEWSROOM ACCESS
- img
- heading "TECH NEWS TODAY" [level=1]
- paragraph: SECURE OPERATIONS PORTAL
- paragraph: Protected access for authorized operators only.
- text: EMAIL ADDRESS
- img
- textbox "EMAIL ADDRESS":
  - /placeholder: operator@technews.today
  - text: test_admin_playwright@example.com
- text: PASSWORD
- img
- textbox "PASSWORD":
  - /placeholder: ••••••••••••
  - text: test_password_secure_123!
- button "SHOW"
- checkbox "Remember Session"
- text: Remember Session
- button "Forgot Password?"
- button "SECURE LOGIN":
  - img
  - text: SECURE LOGIN
- text: OR
- iframe
- text: Don't have an account?
- link "Create Account":
  - /url: /signup
- 'heading "SYSTEM STATUS: OPERATIONAL" [level=3]'
- paragraph: All systems secure and monitored
- img
- region "Notifications (F8)":
  - list
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD } from '../constants';
  3  | 
  4  | // ---------------------------------------------------------------------------
  5  | // Smoke Tests — Authentication Flow
  6  | // ---------------------------------------------------------------------------
  7  | 
  8  | test.describe('Authentication Flow @smoke', () => {
  9  | 
  10 |   test('should complete Admin Login, Command Center navigation, and Logout flow', async ({ page }) => {
  11 |     page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  12 |     page.on('pageerror', err => console.error('BROWSER ERROR:', err.message));
  13 |     page.on('request', req => console.log('REQUEST:', req.method(), req.url()));
  14 |     page.on('response', res => console.log('RESPONSE:', res.status(), res.url()));
  15 | 
  16 |     // 1. Navigate to login page
  17 |     await page.goto('/login');
  18 |     
  19 |     // Check login page elements
  20 |     const emailInput = page.locator('#login-email');
  21 |     const passwordInput = page.locator('#login-password');
  22 |     const submitBtn = page.locator('#login-submit');
  23 |     
  24 |     await expect(emailInput).toBeVisible();
  25 |     await expect(passwordInput).toBeVisible();
  26 |     await expect(submitBtn).toBeVisible();
  27 |     
  28 |     // Fill credentials (using seeded admin credentials from constants.ts)
  29 |     await emailInput.fill(TEST_ADMIN_EMAIL);
  30 |     await passwordInput.fill(TEST_ADMIN_PASSWORD);
  31 |     await submitBtn.click();
  32 |     
  33 |     // Wait for redirect to /admin to ensure login process completes
> 34 |     await expect(page).toHaveURL(/\/admin/, { timeout: 10000 });
     |                        ^ Error: expect(page).toHaveURL(expected) failed
  35 |     
  36 |     // Navigate to homepage to test user dropdown header
  37 |     await page.goto('/');
  38 |     
  39 |     // After login, should redirect to home page, and user dropdown should appear
  40 |     // The user menu trigger uses an avatar with initials
  41 |     const userDropdown = page.locator('#user-menu-trigger');
  42 |     await expect(userDropdown).toBeVisible({ timeout: 10000 });
  43 |     
  44 |     // 2. Open dropdown and navigate to Admin Command Center
  45 |     await userDropdown.click();
  46 |     const dashboardLink = page.locator('a:has-text("Admin Dashboard")');
  47 |     await expect(dashboardLink).toBeVisible();
  48 |     await dashboardLink.click();
  49 |     
  50 |     // Wait for the admin page to load and check title
  51 |     await expect(page).toHaveURL(/\/admin/);
  52 |     const commandCenterHeader = page.locator('h1:has-text("COMMAND CENTER")');
  53 |     await expect(commandCenterHeader).toBeVisible();
  54 |     
  55 |     // Verify telemetry metrics and infrastructure checkers are rendered
  56 |     const sourceHealthHeader = page.locator('h3:has-text("SOURCE HEALTH")');
  57 |     const articlePipelineHeader = page.locator('h3:has-text("ARTICLE PIPELINE")');
  58 |     const aiQueueHeader = page.locator('h3:has-text("AI QUEUE")');
  59 |     const infraHeader = page.locator('h3:has-text("INFRASTRUCTURE")');
  60 |     
  61 |     await expect(sourceHealthHeader).toBeVisible();
  62 |     await expect(articlePipelineHeader).toBeVisible();
  63 |     await expect(aiQueueHeader).toBeVisible();
  64 |     await expect(infraHeader).toBeVisible();
  65 |     
  66 |     // Click manual REFRESH button
  67 |     const refreshBtn = page.locator('button:has-text("REFRESH")');
  68 |     await expect(refreshBtn).toBeVisible();
  69 |     await refreshBtn.click();
  70 |     
  71 |     // 3. Logout flow
  72 |     await page.goto('/');
  73 |     await userDropdown.click();
  74 |     
  75 |     const logoutBtn = page.locator(':text("Sign Out")');
  76 |     await expect(logoutBtn).toBeVisible();
  77 |     await logoutBtn.click();
  78 |     
  79 |     // Verify redirect to login page after logging out
  80 |     await expect(page).toHaveURL(/\/login/);
  81 |     await expect(page.locator('#login-email')).toBeVisible();
  82 |   });
  83 | });
  84 | 
```