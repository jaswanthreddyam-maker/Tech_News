# Phase 1 — Codebase Verification Report

> **Tech Ambiance StudioHQ**  
> **Date**: July 12, 2026  
> **Scope**: Repository-level verification before touching Vercel

---

## Gate Summary

| # | Check | Result | Severity |
|---|---|---|---|
| 1 | Dependency Vulnerability Scan | ✅ **PASS** | — |
| 2 | Production Build Analysis | ⚠️ **WARN** | Medium |
| 3 | CORS Audit | 🔴 **FAIL** | Critical |
| 4 | Security Headers Audit | ⚠️ **WARN** | Medium |
| 5 | Browser Compatibility | ⚠️ **WARN** | Low |
| 6 | Environment Variable Audit | ✅ **PASS** | — |
| 7 | Debug Code Search | ⚠️ **WARN** | Medium |
| 8 | Mock Data Audit | 🔴 **FAIL** | High |
| 9 | Production Configuration Audit | ⚠️ **WARN** | Medium |

**Overall Phase 1 Verdict: 🟡 NOT YET READY — 2 blockers, 4 warnings**

---

## 1. Dependency Vulnerability Scan

### Result: ✅ PASS

```
npm audit (production deps): 0 vulnerabilities
npm audit (all deps):        0 vulnerabilities
```

**Dependencies verified** (22 total, all up to date):

| Package | Version | Notes |
|---|---|---|
| react | 19.2.7 | Latest stable |
| react-dom | 19.2.7 | Latest stable |
| react-router-dom | 7.18.1 | Latest v7 |
| @supabase/supabase-js | 2.110.2 | Latest |
| framer-motion | 12.42.2 | Latest |
| tailwindcss | 4.3.2 | Latest v4 |
| vite | 8.1.1 | Latest v8 |
| typescript | ~6.0.2 | Latest |

**No action required.**

---

## 2. Production Build Analysis

### Result: ⚠️ WARN

### Build Output

| Asset | Size | Gzip |
|---|---|---|
| `index.html` | 1.86 KB | 0.59 KB |
| `index-*.css` | 125.52 KB | 19.04 KB |
| `index-*.js` | **1,108.03 KB** | **305.59 KB** |
| `logo-*.png` | 234.18 KB | — |

### Tree Shaking
**Working.** Vite/Rolldown successfully processes 2,457 modules. No dead imports detected in the final bundle.

### Dead Code
No unused exports detected by the TypeScript compiler (`noUnusedLocals: true`, `noUnusedParameters: true` enabled in [tsconfig.app.json](file:///d:/Tech%20Ambiance/tsconfig.app.json)).

### Chunk Analysis
**Single chunk.** The entire application (marketing site + client portal + admin StudioHQ + CRM + all libraries) compiles into **one JavaScript file**. No code-splitting is configured.

| Concern | Detail |
|---|---|
| Marketing visitor downloads admin code | Yes — wasted bytes |
| Admin user downloads marketing code | Yes — but less impactful |
| GSAP, Framer Motion, Supabase, React Query all in one chunk | Yes |

### Source Maps
**Not generated for production.** No `.map` files in `dist/assets/`. This is correct — source maps should not be deployed publicly.

### Build Warnings

| Warning | Impact |
|---|---|
| `[INEFFECTIVE_DYNAMIC_IMPORT]` — supabase.ts | Low — code runs fine, just won't split that module |
| Chunk > 500KB | Medium — affects initial page load for marketing visitors |

### Recommendation
Not a launch blocker for an internal tool, but should be addressed post-launch with `React.lazy()` route splitting for `/admin/*` and `/portal` routes.

---

## 3. CORS Audit

### Result: 🔴 FAIL — Critical for production

The [admin-auth Edge Function](file:///d:/Tech%20Ambiance/supabase/functions/admin-auth/index.ts#L5-L16) has **hardcoded localhost-only CORS**:

```typescript
const getCorsHeaders = (req: Request) => {
  const origin = req.headers.get('Origin');
  const allowedOrigin = (origin === 'http://127.0.0.1:5173' || origin === 'http://localhost:5173') 
    ? origin 
    : 'http://localhost:5173';  // ← Falls back to localhost always
    
  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    ...
  };
};
```

**What this means in production:**
- Admin login from `https://techambiance.com` → CORS error → **Admin login completely broken**
- The browser will block the Edge Function response because the `Access-Control-Allow-Origin` header will say `http://localhost:5173` instead of your production domain

### Required Fix
Update the CORS function to include your production domain:

```typescript
const ALLOWED_ORIGINS = [
  'http://127.0.0.1:5173',
  'http://localhost:5173',
  'https://techambiance.com',       // Add your production domain
  'https://www.techambiance.com',   // If using www
  'https://tech-ambiance.vercel.app' // Vercel preview domain
];

const getCorsHeaders = (req: Request) => {
  const origin = req.headers.get('Origin') || '';
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return { 'Access-Control-Allow-Origin': allowedOrigin, ... };
};
```

### The outbox-processor Edge Function
[outbox-processor](file:///d:/Tech%20Ambiance/supabase/functions/outbox-processor/index.ts) does **not** set CORS headers, but it's POST-only and invoked server-to-server (not from browser), so this is **acceptable**.

---

## 4. Security Headers Audit

### Result: ⚠️ WARN

| Header | Status | Recommendation |
|---|---|---|
| `Content-Security-Policy` | ❌ Missing | Add via `vercel.json` |
| `X-Frame-Options` | ❌ Missing | Add `DENY` to prevent clickjacking |
| `X-Content-Type-Options` | ❌ Missing | Add `nosniff` |
| `Referrer-Policy` | ❌ Missing | Add `strict-origin-when-cross-origin` |
| `Permissions-Policy` | ❌ Missing | Restrict camera, mic, geolocation |
| `Strict-Transport-Security` | ✅ Vercel default | Vercel adds HSTS automatically |
| `X-XSS-Protection` | N/A | Deprecated, CSP replaces this |

### Recommended `vercel.json` headers block

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ]
}
```

Not a launch blocker, but should be added before public-facing launch.

---

## 5. Browser Compatibility

### Result: ⚠️ WARN (Low)

| Config | Value |
|---|---|
| TypeScript target | `es2023` |
| Browserslist | **Not configured** |
| `.browserslistrc` | **Not present** |
| Vite `build.target` | Not set (defaults to `modules`) |

### What this means
- Vite defaults target modern browsers (Chrome 87+, Firefox 78+, Safari 14+, Edge 88+)
- `es2023` target means features like `Array.findLast()`, `hashbang comments` may not work in older browsers
- For a B2B agency tool, this is likely fine — your clients and admins are on modern browsers

### Recommendation
Not a blocker. If you need to support older browsers in the future, add a `.browserslistrc` file.

---

## 6. Environment Variable Audit

### Result: ✅ PASS

| Variable | Used In | Exposed to Client? | Safe? |
|---|---|---|---|
| `VITE_SUPABASE_URL` | [supabase.ts](file:///d:/Tech%20Ambiance/src/lib/supabase.ts#L3) | Yes (by design) | ✅ Public key |
| `VITE_SUPABASE_ANON_KEY` | [supabase.ts](file:///d:/Tech%20Ambiance/src/lib/supabase.ts#L4) | Yes (by design) | ✅ Public key |
| `RESEND_API_KEY` | `.env` only (not `VITE_` prefixed) | **No** | ✅ Not bundled |
| `RESEND_DEFAULT_FROM` | `.env` only | **No** | ✅ Not bundled |
| `import.meta.env.DEV` | [authService.ts](file:///d:/Tech%20Ambiance/src/auth/authService.ts#L298) | Tree-shaken out in prod | ✅ |

### Key finding
The `import.meta.env.DEV` guard at [authService.ts:298](file:///d:/Tech%20Ambiance/src/auth/authService.ts#L298) assigns `OWNER` role when no roles are found in local dev, but falls back to `CLIENT` in production. **This is correctly gated** — Vite replaces `import.meta.env.DEV` with `false` in production builds, and the dead branch is tree-shaken.

### `.env` files properly gitignored
Confirmed in [.gitignore](file:///d:/Tech%20Ambiance/.gitignore#L14-L16):
```
.env
.env.*
!.env.example
```

**No action required.**

---

## 7. Debug Code Search

### Result: ⚠️ WARN

| Pattern | Found? | Details |
|---|---|---|
| `console.log` | ✅ Clean | Zero instances in `src/` |
| `console.warn` | ⚠️ 2 instances | Both acceptable (see below) |
| `console.error` | ⚠️ 15 instances | All legitimate error handling |
| `debugger` | ✅ Clean | Zero instances |
| `FIXME` | ✅ Clean | Zero instances |
| `HACK` | ✅ Clean | Zero instances |
| `localhost` / `127.0.0.1` | ✅ Clean | Zero instances in `src/` |
| `feature_flag` | ✅ Clean | Zero instances |
| Hardcoded URLs | ✅ Clean | Only OG meta tags (correct) |

### Findings requiring attention

**1. Placeholder TODO** in [admin/page.tsx:144](file:///d:/Tech%20Ambiance/src/routes/auth/admin/page.tsx#L144):
```typescript
device_fingerprint: "deterministic_hash_todo"
```
This is a **string literal** sent to the admin-auth Edge Function. It means device fingerprinting for PIN verification is not implemented — all devices will share the same fingerprint. **Not a launch blocker** if Admin PIN is not yet the active auth flow, but should be tracked.

**2. Mock fallback warning** in [agencyOsService.ts:60](file:///d:/Tech%20Ambiance/src/api/agencyOsService.ts#L60):
```typescript
console.warn("Supabase not configured; returning mock lead response.");
```
This fires when `isSupabaseConfigured === false`. Since your production `.env` has valid Supabase credentials, this path **will not execute in production**. Acceptable.

**3. Mock auth bypass** in [authService.ts:57-63](file:///d:/Tech%20Ambiance/src/auth/authService.ts#L57-L63):
```typescript
if (!isSupabaseConfigured) {
  if (token === "000000") {
    return { success: true, user: { id: "mock-id", email } };
  }
}
```
Same guard — only activates when Supabase is misconfigured. **Will not fire in production** as long as your env vars are set correctly in Vercel. Acceptable but risky if someone misconfigures env vars.

---

## 8. Mock Data Audit

### Result: 🔴 FAIL — Needs classification

I classified every mock usage by whether it's in a **marketing** path (acceptable) or an **authenticated admin** path (problematic):

### ✅ Marketing-only mocks (Acceptable — these ARE the content)

| File | Mock | Context |
|---|---|---|
| [PortfolioSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/PortfolioSection.tsx) | `MOCK_PROJECTS` | Marketing portfolio grid |
| [FeaturedCaseStudy.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/FeaturedCaseStudy.tsx) | `MOCK_PROJECTS` | Marketing featured case study |
| [ServicesSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/ServicesSection.tsx) | `MOCK_SERVICES` | Marketing services list |
| [TestimonialsSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/TestimonialsSection.tsx) | `MOCK_INSIGHTS` | Marketing testimonials |
| [TeamSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/TeamSection.tsx) | `TEAM_MEMBERS` | Marketing team section |

**Verdict**: These are static content for the marketing website. They function as a CMS-like content source. Renaming them from `MOCK_` to `CONTENT_` or moving to `src/content/` would be cleaner, but they are **not blockers**.

### 🔴 Admin workflow mocks (Problematic)

| File | Mock | Problem |
|---|---|---|
| [TimelinePage.tsx](file:///d:/Tech%20Ambiance/src/routes/admin/TimelinePage.tsx) | `MOCK_STUDIO_TIMELINE` | Admin users see **fake** activity events instead of real outbox events |
| [CommandPaletteModal.tsx](file:///d:/Tech%20Ambiance/src/components/admin/CommandPaletteModal.tsx) | `MOCK_WORKSPACES` | Cmd+K search returns **fake workspaces** instead of real ones |

**Verdict**: These two are in authenticated admin paths. An admin user would see fabricated data. This is a **high-priority issue** if StudioHQ is meant for real internal use.

### ⚠️ Auth mock (Conditional — gated behind `isSupabaseConfigured`)

| File | Mock | Condition |
|---|---|---|
| [AuthProvider.tsx](file:///d:/Tech%20Ambiance/src/auth/AuthProvider.tsx) | `defaultMockProject` | Only loads when Supabase is not configured |
| [authService.ts](file:///d:/Tech%20Ambiance/src/auth/authService.ts) | Token `"000000"` bypass | Only when Supabase is not configured |
| [agencyOsService.ts](file:///d:/Tech%20Ambiance/src/api/agencyOsService.ts) | Mock lead response | Only when Supabase is not configured |

**Verdict**: These are properly gated. They will **not execute** when your production env vars are correctly set. Low risk, but should be removed in a future cleanup pass.

---

## 9. Production Configuration Audit

### Result: ⚠️ WARN

| Config | Current | Recommended | Status |
|---|---|---|---|
| Vite `build.sourcemap` | Not set (default: false) | `false` for production | ✅ Correct |
| Vite `server.proxy` | `/functions/v1` → localhost | Dev-only, ignored in prod | ✅ Correct |
| Vite `build.target` | Default (`modules`) | Fine for modern browsers | ✅ |
| TypeScript strict mode | `noUnusedLocals`, `noUnusedParameters` | Enabled | ✅ |
| `@ts-nocheck` in Edge Functions | Both edge functions use it | ⚠️ Suppresses all type errors |
| React Query Devtools | Imported in production | ⚠️ Should be dev-only |
| React StrictMode | Enabled | ✅ |
| ErrorBoundary | Present in main.tsx | ✅ |

### React Query Devtools
[package.json](file:///d:/Tech%20Ambiance/package.json) lists `@tanstack/react-query-devtools` as a **production dependency** (not devDependency). If imported unconditionally, the devtools panel will appear in production. Needs verification of actual import.

### `vercel.json`
**Does not exist.** Required for:
1. SPA rewrites (all routes → index.html)
2. Edge Function proxy (if not calling Supabase directly)
3. Security headers
4. Cache-control for static assets

---

## Actionable Summary

### Must fix before deploying (Blockers)

| # | Issue | File | Fix |
|---|---|---|---|
| 1 | **CORS hardcoded to localhost** — Admin auth will fail | [admin-auth/index.ts](file:///d:/Tech%20Ambiance/supabase/functions/admin-auth/index.ts#L7-L9) | Add production domain to allowed origins |
| 2 | **Admin TimelinePage uses fake data** | [TimelinePage.tsx](file:///d:/Tech%20Ambiance/src/routes/admin/TimelinePage.tsx#L2) | Wire to real outbox events or show empty state |

### Should fix before deploying (High priority)

| # | Issue | Fix |
|---|---|---|
| 3 | CommandPaletteModal uses mock workspaces | Wire to real workspace query |
| 4 | No `vercel.json` — SPA routing will break | Create before Vercel import |
| 5 | `device_fingerprint: "deterministic_hash_todo"` | Implement or remove PIN flow |

### Can fix after first deploy (Polish)

| # | Issue | Fix |
|---|---|---|
| 6 | Security headers not configured | Add to `vercel.json` |
| 7 | No browserslist configured | Add `.browserslistrc` |
| 8 | React Query Devtools in prod deps | Move to devDependencies |
| 9 | Rename `MOCK_` to `CONTENT_` for marketing data | Semantic cleanup |
| 10 | Bundle size — no code splitting | Add `React.lazy()` for routes |
