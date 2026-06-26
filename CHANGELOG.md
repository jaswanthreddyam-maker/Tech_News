# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0-beta] - 2026-06-10

### Added
- Canonical `DATABASE_WORKFLOW.md` with the frozen SQLAlchemy → Alembic → generated schema workflow.
- Database Evolution Freeze in `PROJECT_STATE.md` and ADR-026.
- Operationally Certified Systems section separating certification status from architecture freeze status.

### Changed
- Bumped project status to `v0.10.0-beta` after Phase 3D completion.
- Reset AI Pipeline progress to 0% to reflect that the AI feature work has not started.
- Promoted the platform classification to "production-ready engineering platform with AI functionality pending."

## [0.9.6-beta] - 2026-06-10

### Added
- GitHub Actions CI/CD Pipeline (Phase 3B):
  - `quality.yml` for linting, typing, and formatting gates (Ruff, MyPy, ESLint, TypeScript).
  - `tests.yml` for automated unit, integration, and Playwright smoke tests.
  - `docker.yml` for Docker Compose configuration and build verification.
  - `nightly.yml` for long-running certification, regression Playwright tests, and full test coverage reports.
  - `release.yml` for version, tag, and changelog verification and automated GitHub Release publishing.
- Idempotency updates to test database hooks and user provisioning.
- Step summary report parsing for certification and test outcomes.
- Phase 3C and Phase 3D completion records split into separate audit documents.
- Alembic/schema drift CI gate running `alembic check` and `generate_schema.py --verify`.
- Maintenance-mode middleware regression coverage for read-only operational routes, blocked writes, and backup restore bypasses.

### Fixed
- Fixed validate_snapshots.py console output encoding crash on Windows platforms.
