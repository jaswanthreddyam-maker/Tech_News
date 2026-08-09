# Phase 2 — Live Infrastructure Verification

> **Tech Ambiance StudioHQ**  
> **Scope**: Verify live Vercel + Supabase infrastructure before first production deploy  
> **Prerequisite**: Phase 1 (Codebase Verification) ✅ Complete

---

## What was done before this checklist

| Item | Status |
|---|---|
| `vercel.json` created with SPA rewrites | ✅ Done |
| Edge Function proxy rewrite (`/functions/v1/*` → Supabase) | ✅ Done |
| Security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) | ✅ Done |
| Static asset cache headers (`Cache-Control: immutable` for `/assets/*`) | ✅ Done |

---

## Section 1 — Vercel Project Setup

> **Requires**: Vercel Dashboard → Project Settings

| # | Check | How to verify | Expected | Status |
|---|---|---|---|---|
| 1.1 | Project exists on Vercel | Vercel Dashboard → Projects | `tech-ambiance` or similar | ⬜ |
| 1.2 | GitHub repo connected | Settings → Git | `jaswanthreddyam-maker/Tech-Ambiance` | ⬜ |
| 1.3 | Production branch | Settings → Git → Production Branch | `main` | ⬜ |
| 1.4 | Framework preset | Settings → General → Framework Preset | `Vite` | ⬜ |
| 1.5 | Build command | Settings → General → Build Command | `npm run build` | ⬜ |
| 1.6 | Output directory | Settings → General → Output Directory | `dist` | ⬜ |
| 1.7 | Install command | Settings → General → Install Command | `npm install` (default) | ⬜ |
| 1.8 | Node.js version | Settings → General → Node.js Version | 20.x or 22.x | ⬜ |
| 1.9 | Root directory | Settings → General → Root Directory | `.` (empty/default) | ⬜ |

---

## Section 2 — Environment Variables

> **Requires**: Vercel Dashboard → Settings → Environment Variables

| # | Variable | Scope | How to verify | Status |
|---|---|---|---|---|
| 2.1 | `VITE_SUPABASE_URL` | Production + Preview | Must equal `https://ndgavkrtxkyubjrnczny.supabase.co` | ⬜ |
| 2.2 | `VITE_SUPABASE_ANON_KEY` | Production + Preview | Must start with `sb_publishable_` or `eyJ` | ⬜ |
| 2.3 | No `RESEND_API_KEY` in Vercel | Verify NOT present | This belongs in Supabase secrets, not Vercel | ⬜ |
| 2.4 | No `.env` committed to git | `git status` — check `.gitignore` | `.env` and `.env.*` excluded | ⬜ |

### Verification command (run locally)
```bash
# Confirm .env is not tracked
git ls-files --cached | findstr ".env"
# Should return nothing
```

---

## Section 3 — Supabase Project Linkage

> **Requires**: Supabase Dashboard → Project Settings

| # | Check | How to verify | Expected | Status |
|---|---|---|---|---|
| 3.1 | Project is on the **Pro** or **Free** plan | Supabase Dashboard → Settings → Subscription | Verify plan limits are sufficient | ⬜ |
| 3.2 | Project region | Settings → General | Note the region (for latency) | ⬜ |
| 3.3 | Database password accessible | Settings → Database | You'll need this for `supabase link` | ⬜ |
| 3.4 | API URL matches `.env` | Settings → API | `https://ndgavkrtxkyubjrnczny.supabase.co` | ⬜ |
| 3.5 | Anon key matches `.env` | Settings → API | Compare with `VITE_SUPABASE_ANON_KEY` | ⬜ |

### Verify migrations are applied

```bash
# Link to your production project (if not already linked)
supabase link --project-ref ndgavkrtxkyubjrnczny

# Check migration status
supabase db push --dry-run
# This will show which migrations need to be applied without executing them
```

| # | Check | Status |
|---|---|---|
| 3.6 | `supabase link` succeeds | ⬜ |
| 3.7 | All 19 migrations applied (or dry-run shows 0 pending) | ⬜ |
| 3.8 | No schema drift detected | ⬜ |

---

## Section 4 — Edge Function Deployment

> **Requires**: Terminal + Supabase CLI

### Deploy commands
```bash
# Deploy admin-auth
supabase functions deploy admin-auth --project-ref ndgavkrtxkyubjrnczny

# Deploy outbox-processor
supabase functions deploy outbox-processor --project-ref ndgavkrtxkyubjrnczny
```

### Set secrets
```bash
# CORS configuration
supabase secrets set ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,https://techambiance.in,https://www.techambiance.in" --project-ref ndgavkrtxkyubjrnczny

# Vercel preview pattern
supabase secrets set VERCEL_PROJECT_PREFIX="tech-ambiance" --project-ref ndgavkrtxkyubjrnczny

# Resend (for outbox-processor email notifications)
supabase secrets set RESEND_API_KEY="re_placeholder_resend_api_key" --project-ref ndgavkrtxkyubjrnczny

supabase secrets set RESEND_DEFAULT_FROM="StudioHQ <onboarding@resend.dev>" --project-ref ndgavkrtxkyubjrnczny
```

| # | Check | Status |
|---|---|---|
| 4.1 | `admin-auth` deployed successfully | ⬜ |
| 4.2 | `outbox-processor` deployed successfully | ⬜ |
| 4.3 | `ALLOWED_ORIGINS` secret set | ⬜ |
| 4.4 | `VERCEL_PROJECT_PREFIX` secret set | ⬜ |
| 4.5 | `RESEND_API_KEY` secret set | ⬜ |
| 4.6 | `RESEND_DEFAULT_FROM` secret set | ⬜ |

### Verify deployment
```bash
# List deployed functions
supabase functions list --project-ref ndgavkrtxkyubjrnczny

# Test admin-auth health (should return 400 "Unknown action", not 500)
curl -X POST https://ndgavkrtxkyubjrnczny.supabase.co/functions/v1/admin-auth/health \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

| # | Check | Status |
|---|---|---|
| 4.7 | Both functions appear in `functions list` | ⬜ |
| 4.8 | admin-auth responds (not 500/404) | ⬜ |

---

## Section 5 — Authentication & OAuth

> **Requires**: Supabase Dashboard → Authentication → URL Configuration  
> **Requires**: Google Cloud Console → APIs & Services → Credentials

### Supabase Auth URLs

| # | Setting | Where | Value to add | Status |
|---|---|---|---|---|
| 5.1 | Site URL | Auth → URL Configuration | `https://techambiance.in` (your production URL) | ⬜ |
| 5.2 | Redirect URLs | Auth → URL Configuration | Add all of these: | ⬜ |

**Redirect URLs to add:**
```
https://techambiance.in/**
https://www.techambiance.in/**
https://tech-ambiance-*.vercel.app/**
http://localhost:5173/**
```

### Google OAuth (if using Google login)

| # | Setting | Where | Value | Status |
|---|---|---|---|---|
| 5.3 | Authorized redirect URI | Google Cloud Console → Credentials → OAuth Client | `https://ndgavkrtxkyubjrnczny.supabase.co/auth/v1/callback` | ⬜ |
| 5.4 | Authorized JavaScript origins | Google Cloud Console | `https://techambiance.in` | ⬜ |
| 5.5 | Google Client ID in Supabase | Auth → Providers → Google | Configured and enabled | ⬜ |

### Email (Supabase Auth)

| # | Check | Status |
|---|---|---|
| 5.6 | Email OTP enabled | ⬜ |
| 5.7 | Email templates customized (or acceptable defaults) | ⬜ |
| 5.8 | Rate limits configured | ⬜ |

---

## Section 6 — Domain & DNS

> **Requires**: Domain registrar (where you bought `techambiance.in`)

| # | Check | How to verify | Status |
|---|---|---|---|
| 6.1 | You own `techambiance.in` | Check domain registrar | ⬜ |
| 6.2 | Domain added to Vercel | Vercel → Settings → Domains | ⬜ |
| 6.3 | DNS records configured | Add CNAME or A records as Vercel instructs | ⬜ |
| 6.4 | DNS propagated | `nslookup techambiance.in` resolves to Vercel | ⬜ |
| 6.5 | HTTPS certificate issued | Vercel auto-provisions Let's Encrypt | ⬜ |
| 6.6 | `www` redirect configured | `www.techambiance.in` → `techambiance.in` (or vice versa) | ⬜ |

> [!TIP]
> If you're not ready with the custom domain yet, you can deploy first to the default `*.vercel.app` domain and add the custom domain later. The CORS and auth configs support both.

---

## Section 7 — Pre-Deploy Verification

Run these locally before triggering the first deploy:

```bash
# 1. Final build check
npm run build

# 2. Preview the production build locally
npm run preview
# Visit http://localhost:4173 and verify:
#   - Landing page loads
#   - /experience page works
#   - /auth page loads
#   - /admin redirects to /auth/admin
```

| # | Check | Status |
|---|---|---|
| 7.1 | `npm run build` — zero errors | ⬜ |
| 7.2 | `npm run preview` — landing page loads | ⬜ |
| 7.3 | Client-side routing works (click between pages) | ⬜ |
| 7.4 | No console errors in browser DevTools | ⬜ |
| 7.5 | `vercel.json` committed to git | ⬜ |

---

## Section 8 — First Deploy Procedure

### Option A: Auto-deploy via Git push
```bash
git add .
git commit -m "chore: Phase 1 deployment readiness — CORS, vercel.json, mock data removal"
git push origin main
```
Vercel will automatically build and deploy.

### Option B: Manual deploy via Vercel CLI
```bash
npx vercel --prod
```

### Post-deploy immediate checks

| # | Check | How to verify | Status |
|---|---|---|---|
| 8.1 | Deployment succeeded | Vercel Dashboard → Deployments | ⬜ |
| 8.2 | Build logs show no errors | Click deployment → Build Logs | ⬜ |
| 8.3 | Landing page loads at production URL | Visit `https://techambiance.in` or `*.vercel.app` | ⬜ |
| 8.4 | `/experience` loads (marketing site) | Direct URL navigation | ⬜ |
| 8.5 | Page refresh on `/experience` works | F5 on the page | ⬜ |
| 8.6 | `/auth` page loads | Direct URL navigation | ⬜ |
| 8.7 | `/admin` redirects to `/auth/admin` | Direct URL navigation (unauthenticated) | ⬜ |
| 8.8 | Security headers present | Browser DevTools → Network → Response Headers | ⬜ |
| 8.9 | No mixed content warnings | Browser DevTools → Console | ⬜ |
| 8.10 | Static assets cached correctly | Check `Cache-Control: immutable` on `.js` and `.css` | ⬜ |

---

## After Phase 2

Once every checkbox above is ✅, you're ready for **Phase 3 — Production Gate Review**:

- Smoke tests (auth flow end-to-end)
- Admin login with real credentials
- Client portal access
- Multi-tenant isolation testing
- Realtime subscription verification
- Email delivery testing
- Rollback verification
- Lighthouse audit on live site

That's the final gate before **GO**.
