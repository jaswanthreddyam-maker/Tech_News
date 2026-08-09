# Tech Ambiance — Deployment Readiness Report

> **Audit Date**: July 12, 2026  
> **Auditor**: Antigravity AI  
> **Repository**: [github.com/jaswanthreddyam-maker/Tech-Ambiance](https://github.com/jaswanthreddyam-maker/Tech-Ambiance)  
> **Branch**: `main`

---

## Production Readiness Score: **62 / 100**

| Category | Score | Status |
|---|---|---|
| Project Structure | 9/10 | ✅ Strong |
| Framework & Routing | 8/10 | ⚠️ Missing SPA rewrites |
| Environment Variables | 5/10 | 🔴 Secrets exposed in `.env` |
| Supabase & Migrations | 7/10 | ⚠️ Schema drift risk |
| Authentication | 7/10 | ⚠️ Partial — Mock fallbacks active |
| RLS & Security | 6/10 | ⚠️ `USING (true)` on 4 CRM tables |
| Storage | N/A | Not in use |
| Realtime | 7/10 | ✅ Configured, needs reconnect testing |
| Domain Events | 6/10 | ⚠️ Edge Functions local only |
| Vercel Config | 2/10 | 🔴 No `vercel.json` exists |
| Performance | 4/10 | 🔴 No code-splitting, 1.1MB JS bundle |
| Security | 4/10 | 🔴 No CSP, no bot protection |
| Error Monitoring | 1/10 | 🔴 No Sentry/PostHog/LogRocket |
| Mock Data Cleanup | 3/10 | 🔴 MOCK_ objects still in production paths |

---

## Phase 1 — Project Structure

### Q1. Is this only the frontend?

**No.** This is a **monorepo** containing:
- ✅ Frontend (React + Vite + TailwindCSS v4)
- ✅ Supabase configuration (`supabase/config.toml`)
- ✅ Edge Functions (`supabase/functions/admin-auth`, `supabase/functions/outbox-processor`)
- ✅ SQL Migrations (`supabase/migrations/0001` through `0019`)
- ❌ No separate backend/FastAPI

### Q2. Repository structure?

```text
/
├── src/                    # React frontend
├── supabase/
│   ├── migrations/         # 19+ SQL migrations
│   ├── functions/          # 2 Deno Edge Functions
│   ├── config.toml
│   └── init.sql            # Combined init script
├── public/                 # Static assets
├── scripts/                # SQL seed scripts
├── dist/                   # Production build output
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### Q3. What are you deploying?

You need to deploy **two things separately**:
1. **Frontend → Vercel** (static SPA)
2. **Edge Functions → Supabase** (via `supabase functions deploy`)

---

## Phase 2 — Framework

### Q4. React + Vite? Not Next.js?

**Confirmed: React 19 + Vite 8.** This is a client-side SPA. Not Next.js.

### Q5. BrowserRouter or HashRouter?

**BrowserRouter.** Found in [main.tsx](file:///d:/Tech%20Ambiance/src/main.tsx#L37):
```tsx
<BrowserRouter>
```

> [!IMPORTANT]
> BrowserRouter requires server-side SPA rewrites (all routes → `index.html`). Without this, any direct URL access or page refresh on `/admin/dashboard` will return a **404** on Vercel.

### Q6. Admin routes?

**Yes, all present** in [App.tsx](file:///d:/Tech%20Ambiance/src/App.tsx#L87-L107):

| Route | Component |
|---|---|
| `/admin` | `DashboardPage` |
| `/admin/dashboard` | `DashboardPage` |
| `/admin/timeline` | `TimelinePage` |
| `/admin/workspaces` | `WorkspacesPage` |
| `/admin/workspaces/:slug` | `WorkspacesPage` |
| `/admin/crm` | `CrmPipelinePage` |
| `/admin/cms` | `CmsEditorPage` |
| `/admin/ai-center` | `AiCenterPage` |
| `/admin/media` | `MediaPage` |
| `/admin/settings` | `StudioTeamPage` |
| `/auth/admin` | `AdminAuthPage` |

---

## Phase 3 — Environment Variables

### Q7. Do you have VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY?

**Yes**, defined in [.env](file:///d:/Tech%20Ambiance/.env):
- `VITE_SUPABASE_URL` = `https://ndgavkrtxkyubjrnczny.supabase.co`
- `VITE_SUPABASE_ANON_KEY` = `sb_publishable_Af3Mz...`

> [!CAUTION]
> These must be configured **inside Vercel's Environment Variables settings**, not committed to git. Your `.gitignore` does exclude `.env` and `.env.*`, so this is safe as long as you set them in Vercel's dashboard.

### Q8. Other secrets?

Found in [.env](file:///d:/Tech%20Ambiance/.env):
- `RESEND_API_KEY` = `re_placeholder_key` — **Server-side only**, should be in Supabase Edge Function secrets, NOT in frontend env
- `SUPABASE_SERVICE_ROLE_KEY` = `eyJhbGciOi...` — **Server-side only**, gives full database admin bypass

> [!WARNING]
> `RESEND_API_KEY` is a **server secret**. It should NEVER be prefixed with `VITE_` (which would expose it to the browser). Currently it's not prefixed, so it won't leak to the client bundle. But it needs to be set as a **Supabase Edge Function secret** via:
> ```bash
> supabase secrets set RESEND_API_KEY=re_placeholder_key
> ```

### Q9. Env file setup?

| File | Purpose | Status |
|---|---|---|
| `.env` | Production Supabase credentials | ✅ Present |
| `.env.local` | Local dev override (localhost:54321) | ✅ Present |
| `.env.production` | Dedicated production overrides | ❌ **Missing** |
| `.env.example` | Template for new developers | ✅ Present |

> [!TIP]
> `.env.local` correctly overrides `.env` for local development. Vite's priority is `.env.local` > `.env`. No `.env.production` file exists, but this is fine if you set env vars in Vercel directly.

---

## Phase 4 — Supabase

### Q10. Have all migrations been applied to Production Supabase?

**Unknown — requires verification.** You have migrations locally but I cannot verify if they've been pushed to your production Supabase project.

### Q11. How many migrations?

**24 files** in `supabase/migrations/`, covering migrations `0001` through `0019` plus hotfix files (`00051`, `00081`, `00101`, `grant_owner.sql`, `init.sql`).

### Q12. Did every migration execute successfully?

**Cannot verify remotely.** You need to run:
```bash
supabase db push --linked
```
or check the `supabase_migrations.schema_migrations` table in your production database.

### Q13. Any manual SQL executed in SQL Editor?

**Yes — evidence found.** Loose SQL files exist at root level:
- [fix_members.sql](file:///d:/Tech%20Ambiance/fix_members.sql) (277 bytes)
- [temp.sql](file:///d:/Tech%20Ambiance/temp.sql) (141 bytes)
- [test_rls.sql](file:///d:/Tech%20Ambiance/test_rls.sql) (181 bytes)
- [scripts/seed_outbox.sql](file:///d:/Tech%20Ambiance/scripts/seed_outbox.sql)

> [!WARNING]
> If any of these were run directly in the SQL Editor without a corresponding migration, you have **schema drift**.

### Q14. Schema drift?

**High risk.** The presence of hotfix migrations (`00051`, `00081`, `00101`) and ad-hoc SQL files strongly suggests manual schema changes were made.

---

## Phase 5 — Authentication

### Q15. Email OTP working?

**Yes.** Implemented in [authService.ts](file:///d:/Tech%20Ambiance/src/auth/authService.ts#L34-L54) via `supabase.auth.signInWithOtp()`.

### Q16. Google OAuth working?

**Yes.** Implemented in [authService.ts](file:///d:/Tech%20Ambiance/src/auth/authService.ts) via `supabase.auth.signInWithOAuth({ provider: 'google' })`.

> [!IMPORTANT]
> Google OAuth requires the Vercel production URL to be added to:
> 1. Supabase Auth → Redirect URLs
> 2. Google Cloud Console → Authorized redirect URIs

### Q17. Magic Link working?

**Yes.** Part of the OTP flow — Supabase sends magic links alongside OTP.

### Q18. Admin OTP working?

**Yes.** Separate admin auth flow in [AdminAuthPage](file:///d:/Tech%20Ambiance/src/routes/auth/admin/page.tsx) with email verification.

### Q19. Client Login working?

**Yes.** Standard auth flow through [AuthPage](file:///d:/Tech%20Ambiance/src/routes/auth/page.tsx).

### Q20. Admin Login working?

**Yes.** Protected by [AdminGuard](file:///d:/Tech%20Ambiance/src/auth/AdminGuard.tsx) which validates via Edge Function `/functions/v1/admin-auth/validate`.

### Q21. Admin PIN implemented?

**Migration exists** ([0019_admin_pin_security.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0019_admin_pin_security.sql)) with tables `admin_security`, `admin_pin_history`, `executive_sessions`. However, **the frontend PIN input UI integration needs verification**.

> [!WARNING]
> The AuthProvider has **mock fallbacks** when Supabase is not configured (token `"000000"` auto-authenticates). This MUST be removed or disabled for production.

---

## Phase 6 — RLS

### Q22. RLS enabled on every table?

**Yes.** Found `ENABLE ROW LEVEL SECURITY` on **35+ tables** across all migrations including: `organizations`, `workspaces`, `profiles`, `projects`, `milestones`, `credentials`, `admin_users`, `admin_sessions`, etc.

### Q23. Client cannot read another organization?

**Needs testing.** RLS policies are defined per-organization using `auth.uid()` checks, but no automated test suite exists.

### Q24. Admin cannot see another tenant?

**Needs testing.** Admin policies exist but manual verification is required.

### Q25. Any table still using USING (true)?

> [!CAUTION]
> **Yes — 4 CRM tables have wide-open RLS policies:**

| Table | Policy | Risk |
|---|---|---|
| `crm_pipeline_stages` | `SELECT USING (true)` | Medium — stages are generic |
| `lead_consultations` | `ALL USING (true)` | 🔴 **HIGH** — leads contain PII |
| `lead_events` | `ALL USING (true)` | 🔴 **HIGH** — events contain PII |
| `crm_stage_history` | `ALL USING (true)` | Medium |

Found in [0003_crm_pipeline_refactor.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0003_crm_pipeline_refactor.sql#L199-L202).

---

## Phase 7 — Storage

### Q26-28. Supabase Storage?

**Not in use.** No storage bucket references, no bucket policies. Static assets are served from the `public/` directory via Vercel CDN.

---

## Phase 8 — Realtime

### Q29. Realtime enabled?

**Yes.** Found in [0013_ceo_dashboard_projections.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0013_ceo_dashboard_projections.sql#L91-L96).

### Q30. Which tables use Realtime?

| Table |
|---|
| `finance_dashboard_projection` |
| `delivery_dashboard_projection` |
| `crm_dashboard_projection` |
| `top_projects_projection` |
| `studio_activity_projection` |
| `operations_health_projection` |

### Q31. Subscriptions reconnect after refresh?

**Needs manual testing.** Realtime subscriptions are set up in repositories like [ceoDashboardRepository.ts](file:///d:/Tech%20Ambiance/src/repositories/ceoDashboardRepository.ts), but reconnection behavior depends on Supabase client configuration (which has `autoRefreshToken: true`).

---

## Phase 9 — Domain Events

### Q32. Outbox implemented?

**Yes.** Full transactional outbox pattern with [outbox-processor Edge Function](file:///d:/Tech%20Ambiance/supabase/functions/outbox-processor/index.ts).

### Q33. Projection workers implemented?

**Yes.** Migration [0013_ceo_dashboard_projections.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0013_ceo_dashboard_projections.sql) creates 6 materialized projection tables.

### Q34. Edge Functions deployed?

> [!CAUTION]
> **Local only.** Edge Functions have NOT been deployed to production Supabase. You must run:
> ```bash
> supabase functions deploy admin-auth --project-ref ndgavkrtxkyubjrnczny
> supabase functions deploy outbox-processor --project-ref ndgavkrtxkyubjrnczny
> ```

### Q35. Communication pipeline deployed?

**Migration exists** ([0016_communication_pipeline.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0016_communication_pipeline.sql)). But the outbox-processor Edge Function that drives it is **not deployed** to production.

---

## Phase 10 — Vercel

### Q36-37. Custom domain?

`index.html` references `https://techambiance.com/` in OG tags. Whether you own this domain is **unknown** — requires your confirmation.

### Q38. Preview Deployments?

**Not configured.** No `vercel.json` exists. Vercel auto-enables previews for PRs by default once connected.

### Q39. Production Branch?

**`main`** — confirmed via `git branch --show-current`.

---

## Phase 11 — Routing

### Q40. SPA rewrites configured?

> [!CAUTION]
> **No.** No `vercel.json` file exists. Without it:
> - Direct navigation to `/admin/dashboard` → **404**
> - Page refresh on `/portal` → **404**
> - Deep links shared via Slack/email → **404**
>
> This is a **critical deployment blocker**.

### Q41-42. Deep links and browser refresh tested?

**Not testable without Vercel deployment.** Locally, Vite dev server handles this. Production will fail without rewrites.

---

## Phase 12 — Performance

### Q43. Lighthouse score?

**Not measured.** Requires a deployed instance.

### Q44. Largest JS bundle?

From the last build output:
```
dist/assets/index-B85Rbgp4.js   1,108.03 kB | gzip: 305.59 kB
```

> [!WARNING]
> **1.1 MB single JS bundle.** Vite itself warned about this. This exceeds the 500KB recommended limit.

### Q45-46. Lazy loading / Route splitting?

> [!CAUTION]
> **None.** Zero usage of `React.lazy()` or dynamic `import()` for route splitting. Every admin page, client portal page, and marketing page is bundled into a single file.
>
> **Impact**: First load downloads the entire app (admin portal, CRM, client portal) even if the user is just viewing the marketing landing page.

---

## Phase 13 — Security

### Q47. HTTPS only?

**Yes.** Vercel enforces HTTPS by default. Supabase APIs are HTTPS only.

### Q48. CSP configured?

**No.** No `Content-Security-Policy` headers found anywhere.

### Q49. Rate Limiting?

**Partial.** Database-level rate limiting exists for admin auth via `check_auth_rate_limit()` function in [0004_admin_auth.sql](file:///d:/Tech%20Ambiance/supabase/migrations/0004_admin_auth.sql#L45). No application-level or Vercel edge rate limiting.

### Q50. Bot protection?

**No.** No CAPTCHA, no bot detection, no Cloudflare integration.

---

## Phase 14 — Error Monitoring

### Q51-54.

| Tool | Status |
|---|---|
| Sentry | ❌ Not installed |
| PostHog | ❌ Not installed |
| LogRocket | ❌ Not installed |
| Any client error reporting | ❌ Only `console.error` (15 files) |

> [!WARNING]
> There is a basic `ErrorBoundary` in [main.tsx](file:///d:/Tech%20Ambiance/src/main.tsx#L9-L31) that catches crashes and shows them on screen, but errors are NOT reported to any external service.

---

## Phase 15 — Admin Portal

### Q55. Still using MOCK_ objects?

> [!CAUTION]
> **Yes — extensively.** Mock data is imported and used in **production code paths**:

| File | Mock Import |
|---|---|
| [TimelinePage.tsx](file:///d:/Tech%20Ambiance/src/routes/admin/TimelinePage.tsx) | `MOCK_STUDIO_TIMELINE` |
| [CommandPaletteModal.tsx](file:///d:/Tech%20Ambiance/src/components/admin/CommandPaletteModal.tsx) | `MOCK_WORKSPACES` |
| [PortfolioSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/PortfolioSection.tsx) | `MOCK_PROJECTS` |
| [FeaturedCaseStudy.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/FeaturedCaseStudy.tsx) | `MOCK_PROJECTS` |
| [ServicesSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/ServicesSection.tsx) | `MOCK_SERVICES` |
| [TestimonialsSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/TestimonialsSection.tsx) | `MOCK_INSIGHTS` |
| [TeamSection.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/TeamSection.tsx) | `TEAM_MEMBERS` |

### Q56. Any hardcoded "Cafe Vistaara" left?

**Yes — 7 files** still reference "Cafe Vistaara":

| File |
|---|
| [landing/page.tsx](file:///d:/Tech%20Ambiance/src/routes/landing/page.tsx) |
| [mocks/studioHQ.ts](file:///d:/Tech%20Ambiance/src/mocks/studioHQ.ts) |
| [mocks/projects.ts](file:///d:/Tech%20Ambiance/src/mocks/projects.ts) |
| [content/testimonials.ts](file:///d:/Tech%20Ambiance/src/content/testimonials.ts) |
| [organisms/FeaturedCaseStudy.tsx](file:///d:/Tech%20Ambiance/src/components/organisms/FeaturedCaseStudy.tsx) |
| [auth/AuthProvider.tsx](file:///d:/Tech%20Ambiance/src/auth/AuthProvider.tsx) |
| [content/portfolio.ts](file:///d:/Tech%20Ambiance/src/content/portfolio.ts) |

### Q57. Dummy invoices?

**Yes.** Hardcoded in [AuthProvider.tsx](file:///d:/Tech%20Ambiance/src/auth/AuthProvider.tsx#L35-L39):
```ts
invoices: [
  { id: "inv-001", amount: "$5,000.00", date: "2026-06-02", status: "Paid" },
  { id: "inv-002", amount: "$3,750.00", date: "2026-07-01", status: "Paid" },
  { id: "inv-003", amount: "$3,750.00", date: "2026-08-10", status: "Pending" },
]
```

### Q58. Fake analytics?

**Yes.** Mock data in [mocks/studioHQ.ts](file:///d:/Tech%20Ambiance/src/mocks/studioHQ.ts) includes fake workspace metrics, event timelines, and task items.

---

## Phase 16 — Client Portal

### Q59-62.

| Check | Status |
|---|---|
| Empty client sees proper state | ⚠️ Falls back to mock `defaultMockProject` |
| Mock milestones | 🔴 Yes — hardcoded in AuthProvider |
| Mock credentials | ⚠️ Needs verification |
| Mock activity timeline | 🔴 Yes — `MOCK_STUDIO_TIMELINE` used in TimelinePage |

---

## Phase 17 — Production Readiness

### Q63. npm run build zero warnings?

**Build succeeds but has warnings:**
- ⚠️ `[INEFFECTIVE_DYNAMIC_IMPORT]` — supabase.ts dynamic import issue
- ⚠️ Chunk size exceeds 500KB limit (1,108 KB)

### Q64. TypeScript errors?

**Zero.** `tsc -b` passes clean.

### Q65. ESLint warnings?

**16 warnings, 0 errors** after our fixes. Warnings are all non-critical (`only-export-components`, `no-unused-vars` on catch params).

### Q66-67. Console errors/warnings?

**No `console.log` statements** found. **15 files** use `console.error` for legitimate error handling.

---

## Phase 18 — Deployment Strategy

### Q68-70. These require your answers:

- **Environment type**: You tell me — Dev / Staging / Production?
- **Separate Supabase projects**: Currently only one project detected (`ndgavkrtxkyubjrnczny`)
- **Auto-deploy**: GitHub repo exists at `jaswanthreddyam-maker/Tech-Ambiance`. Vercel can auto-deploy on push to `main`.

---

## Phase 19 — Business

### Q71-75. These require your answers:

- Will real clients use this immediately?
- Will StudioHQ remain private?
- Do you own `techambiance.com`?
- Will email notifications use production domain?
- Deployment purpose: Internal testing / Closed beta / Public launch / Production?

---

## Critical Blockers (Must Fix Before Deploy)

| # | Issue | Severity | Fix |
|---|---|---|---|
| 1 | **No `vercel.json`** — all routes except `/` will 404 on refresh | 🔴 Critical | Create `vercel.json` with SPA rewrites |
| 2 | **Edge Functions not deployed** — Admin login will fail | 🔴 Critical | Run `supabase functions deploy` |
| 3 | **Mock auth fallback** — token `"000000"` bypasses auth | 🔴 Critical | Remove mock fallback in authService |
| 4 | **`USING (true)` on lead_consultations** — any authenticated user can read all leads | 🔴 Critical | Restrict to admin roles |
| 5 | **Supabase Auth redirect URLs** — Google OAuth will fail | 🔴 Critical | Add Vercel URL to Supabase + Google Console |

## High Priority Issues

| # | Issue | Fix |
|---|---|---|
| 6 | 1.1MB JS bundle, no code splitting | Add `React.lazy()` route splitting |
| 7 | No error monitoring (Sentry) | Install Sentry |
| 8 | Mock data in production components | Replace with real Supabase queries |
| 9 | "Cafe Vistaara" hardcoded in 7 files | Update to current project names |
| 10 | Edge Function proxy won't work on Vercel | Add Supabase proxy rewrite to `vercel.json` |

## Medium Priority Improvements

| # | Issue | Fix |
|---|---|---|
| 11 | No CSP headers | Add via `vercel.json` headers |
| 12 | No `.env.production` file | Create or use Vercel env vars |
| 13 | Schema drift risk from ad-hoc SQL | Audit and consolidate |
| 14 | No bot protection on consultation form | Add reCAPTCHA or Turnstile |
| 15 | Realtime reconnection not tested | Manual QA |

## Low Priority Polish

| # | Issue | Fix |
|---|---|---|
| 16 | OG image URL assumes `techambiance.com` | Verify domain ownership |
| 17 | Lint warnings (16 remaining) | Clean up over time |
| 18 | Loose SQL files at project root | Move to `scripts/` or delete |
| 19 | `scratch_test.ts` at project root | Delete |
| 20 | `preload="none"` on showreel video | Consider `preload="metadata"` |
