# Quality Ratchet

The first CI quality profile is intentionally pragmatic. Its job is to make static analysis run on every pull request without forcing a broad cleanup pass into the first CI change. This document prevents that starting point from becoming permanent.

## Roadmap

| Version | Goal | Blocking Policy |
|---|---|---|
| v0.9.x | Pragmatic profile: Ruff, MyPy, ESLint, and TypeScript compile are enforced with existing-code allowances. | Errors fail CI; warnings are allowed. |
| v0.10 | Enable additional Ruff rules by removing first-pass ignores that only protect legacy style. | New Ruff errors fail CI. |
| v0.11 | Increase MyPy strictness by enabling selected typed-function and optionality checks module by module. | MyPy failures fail CI for opted-in modules. |
| v0.12 | Treat frontend lint warnings as reported debt with an explicit warning budget. | Warnings are reported but not blocking. |
| v1.0 | Full strict profile for backend and frontend quality gates. | Warnings and errors fail CI unless explicitly waived. |

## Current Profile

The current profile prioritizes high-signal failures:

- Python: Ruff catches undefined names, import errors, common bug patterns, and safe modernization issues.
- Python types: MyPy runs in adoption mode, with dynamic SQLAlchemy/Pydantic patterns temporarily tolerated.
- Frontend: ESLint and TypeScript compilation run on every push and pull request.
- Frontend warnings: allowed for now, but visible in CI logs.
- Next.js 15.5 reports `next lint` as deprecated; migrate the workflow to the ESLint CLI before any Next 16 upgrade.

## Warning Policy

Warnings move through three stages:

| Stage | Behavior | CI Result |
|---|---|---|
| Reported | Warnings appear in logs and PR review notes. | Non-blocking |
| Budgeted | Each category has an allowed maximum count. | Blocks only if the budget increases |
| Blocking | Warnings are treated as failures. | Blocking |

The intended progression is: ESLint warnings become reported debt in v0.12, budgeted before v1.0, and blocking at v1.0.

## Security Audit Policy

Run `npm audit` before starting each CI/CD phase PR.

| Finding Type | Action |
|---|---|
| Development-only dependency | Document and monitor, or update if the fix is low risk. |
| Production dependency, low/moderate | Update if a non-breaking fix exists; otherwise document the constraint and revisit during the next ratchet. |
| Production dependency, high/critical | Fix before beta or explicitly block release. |

Current frontend audit status:

- `next` was upgraded from `15.0.3` to `15.5.19`, removing the critical runtime advisories.
- `npm audit --audit-level=high` passes.
- Two moderate findings remain through Next's bundled `postcss@8.4.31`.
- The app's direct `postcss` dependency is patched at `8.5.x`; the remaining vulnerable copy is nested under `next`.
- `npm audit` currently suggests a semver-major downgrade to `next@9.3.3`, which is not a viable fix path for this App Router application.
- Track this as a monitored production-framework issue until a compatible Next release removes the nested vulnerable PostCSS copy.

## PR Sequence

| PR | Scope | Status |
|---|---|---|
| PR1 | `quality.yml`: Ruff, MyPy, ESLint, TypeScript compile | Complete |
| PR2 | `tests.yml`: Pytest, coverage, Playwright | Next |
| PR3 | `docker.yml`: image build validation | Pending |
| PR4 | `nightly.yml`: scheduled certification and health checks | Pending |
| PR5 | `release.yml`: release packaging and deployment checks | Pending |
