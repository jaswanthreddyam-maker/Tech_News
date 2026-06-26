# Release Checklist — v1.0.0

> This checklist applies to **shipping a version**, not completing a feature.
> For per-feature requirements, see the Definition of Done in
> [CONTRIBUTING.md](CONTRIBUTING.md).
>
> Copy this checklist into the release PR description and check items as they
> are verified. Every box must be checked before merging to `main` and tagging.

---

## CI / Quality Gates

- [ ] All GitHub Actions checks passing (no skipped required jobs)
- [ ] `ruff check .` — zero warnings
- [ ] `mypy` — zero errors
- [ ] `eslint` — zero warnings
- [ ] TypeScript compilation — zero errors
- [ ] `pytest` — all tests green
- [ ] `playwright test` — all smoke + E2E tests green
- [ ] `alembic check` — no ORM/migration drift
- [ ] `python scripts/generate_schema.py --verify` — generated schema is current
- [ ] Code coverage ≥ threshold (no regression from previous release)

## Security

- [ ] `npm audit --audit-level=critical` — zero critical vulnerabilities
- [ ] `pip-audit` — zero critical vulnerabilities
- [ ] `gitleaks` — zero secret leaks detected
- [ ] Dependency pins verified (no unpinned transitive deps in production)

## API Contract

- [ ] `python scripts/openapi_snapshot.py --verify` — no breaking API changes
- [ ] OpenAPI snapshot updated if endpoints were intentionally added/changed

## Certification

- [ ] Bundle Certification passes (`certify_application.ts`)
- [ ] Bundle budgets met (Homepage < 200KB, Article < 250KB, Search < 250KB, Dashboard < 250KB)
- [ ] Thumbnail certification passes — A+ grade maintained
- [ ] No new fallback thumbnails introduced
- [ ] No duplicate thumbnail regressions (pHash)

## Accessibility

- [ ] `axe-core` accessibility tests pass — zero violations
- [ ] WCAG AA compliance verified on key pages (Homepage, Search, Article, Dashboard)

## Performance

- [ ] Lighthouse Performance ≥ 95
- [ ] Lighthouse Accessibility ≥ 95
- [ ] Lighthouse Best Practices ≥ 95
- [ ] Lighthouse SEO ≥ 95

## SLO Targets (Load Testing)

- [ ] Homepage p95 < 500ms
- [ ] Search p95 < 700ms
- [ ] Recommendations p95 < 600ms
- [ ] Article p95 < 400ms
- [ ] AI Summary p95 < 8s
- [ ] Availability ≥ 99.9%

## Infrastructure

- [ ] `docker compose build` succeeds for all services
- [ ] `docker compose up` — all health checks pass (db, redis, backend, worker, beat, frontend, nginx)
- [ ] No container restart loops in 60-second observation window

## PWA

- [ ] `manifest.json` present and valid
- [ ] Service Worker generated (`sw.js`)
- [ ] Offline page renders at `/~offline`
- [ ] PWA icons present (192px, 512px)
- [ ] Install prompt functional

## Operations

- [ ] Monitoring dashboard loads — all services show healthy
- [ ] Health check history populating (Redis sparklines)
- [ ] SSE telemetry stream connects and delivers events
- [ ] Structured logging emitting valid JSON (production mode)
- [ ] Sentry error tracking verified
- [ ] Alert routing verified (Sentry → Slack/Discord/Email)

## Backup & Recovery

- [ ] Backup completes successfully
- [ ] Backup checksum verified
- [ ] Restore tested on clean environment
- [ ] Post-restore data integrity validated

## Database Evolution

- [ ] All schema changes originate from SQLAlchemy model and Alembic migration updates
- [ ] `database/schema.sql` regenerated, not manually edited
- [ ] Migration drift checks pass in CI

## Documentation

- [ ] `PROJECT_STATE.md` updated (version, maturity scores, checklist)
- [ ] `ARCHITECTURE_DECISIONS.md` updated (new/changed ADRs if applicable)
- [ ] `CONTRIBUTING.md` updated (if public interfaces or processes changed)
- [ ] `CHANGELOG.md` updated with user-facing changes
- [ ] `PRODUCTION_RUNBOOK.md` reviewed and current

## Release Artifacts

- [ ] Source tarball generated
- [ ] SHA-256 checksums generated
- [ ] SBOM generated (CycloneDX) — backend + frontend
- [ ] Release notes extracted from CHANGELOG

## Release Sign-off

- [ ] Version bumped in `PROJECT_STATE.md`
- [ ] Version bumped in `package.json` (frontend)
- [ ] All CI gate checks passing (`pr-gate-status` job green)
- [ ] Release gate script passes (`npx tsx scripts/release_gate.ts`)
- [ ] Git tag created (`vX.Y.Z`)
- [ ] Release notes published (link to CHANGELOG entry)
- [ ] Previous release tag verified as ancestor of new tag

---

> **Release Gate Enforcement**: The `release.yml` GitHub Actions workflow
> will automatically re-run ALL gate checks when a `v*` tag is pushed.
> The release is only published if every gate passes. No exceptions.
