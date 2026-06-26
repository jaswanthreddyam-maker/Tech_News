# Contributing to Tech News Today

> **Architecture Decisions** — See [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md)
> before introducing new architectural patterns. For database changes, also see
> [DATABASE_WORKFLOW.md](DATABASE_WORKFLOW.md).

## Development Setup

### Prerequisites
- Python 3.13+ (backend)
- Node.js 18+ (frontend)
- PostgreSQL 15+ (database)
- Redis 7+ (caching, rate limiting, queues)
- Docker & Docker Compose (containerized development)

### Local Setup
```bash
# Clone and navigate
git clone <repo-url> && cd tech_news

# Backend virtual environment
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Start infrastructure
docker compose up -d
```

### Frontend Dependency Resolution

The frontend includes a project-local `.npmrc` with `legacy-peer-deps=true`.
This is intentional: React 19 currently creates peer dependency friction with
some ecosystem packages, including icon and framework-adjacent packages. Keep
this setting until those dependencies officially support React 19 without peer
resolution overrides.

### Running Tests

```bash
# Backend unit/integration tests (inside venv)
cd backend
python -m pytest tests/ -v

# Individual test files
python -m pytest tests/test_unit_auth.py -v
python -m pytest tests/test_shutdown.py -v
python -m pytest tests/test_init_db.py -v

# Playwright E2E smoke tests (requires backend + frontend running)
cd frontend
npx playwright test

# Playwright with specific folder
npx playwright test tests/smoke/

# Thumbnail certification
cd backend
python -m tests.thumbnail_validation.validate_snapshots
```

### Docker Commands
```bash
make start          # Start all containers
make stop           # Stop all containers
make rebuild        # Rebuild and start
make logs           # Stream active logs
make test           # Run pytest inside backend container
make lint           # Run ruff (backend) + eslint (frontend)
make clean          # Clear __pycache__ and .pyc files
```

---

## Coding Standards

### Python (Backend)
- **Formatter/Linter**: Ruff
- **Type checking**: MyPy
- **Async-first**: All database operations use async SQLAlchemy with `AsyncSession`
- **Avoid N+1**: Use `selectinload()` for relationship loading
- **Response wrappers**: All API endpoints return `StandardResponse[T]` or `PaginatedResponse[T]`
- **Error handling**: Use the centralized exception handlers — do not return raw `JSONResponse` from routes
- **Logging**: Use `logging.getLogger("tech_news.<module>")` — never `print()`
- **Imports**: Group as stdlib → third-party → local, separated by blank lines

### TypeScript (Frontend)
- **Framework**: Next.js App Router
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Validation**: Zod for API response schemas
- **Linter**: ESLint

### Quality Ratchet

Static analysis starts with a pragmatic v0.9.x profile and tightens over time.
See [QUALITY_RATCHET.md](QUALITY_RATCHET.md) for the versioned plan, warning
policy, and security audit policy.

---

## Branch Naming

```
feature/<short-description>    # New functionality
fix/<short-description>        # Bug fixes
test/<short-description>       # New or updated tests
ci/<short-description>         # CI/CD pipeline changes
docs/<short-description>       # Documentation updates
refactor/<short-description>   # Code restructuring (no behavior change)
```

Examples:
```
feature/ai-summarization-pipeline
fix/sse-keepalive-timing
test/shutdown-regression
ci/github-actions-pytest
```

---

## Commit Conventions

Use conventional commits:

```
<type>(<scope>): <description>

[optional body]
```

**Types**: `feat`, `fix`, `test`, `ci`, `docs`, `refactor`, `perf`, `chore`

**Scopes**: `auth`, `api`, `db`, `crawler`, `thumbnail`, `telemetry`, `dashboard`, `frontend`, `infra`

Examples:
```
feat(api): add article revision history endpoint
fix(thumbnail): handle SVG fallback in strict pass
test(shutdown): add SSE graceful shutdown regression test
ci(github): add pytest + playwright workflow
```

---

## Definition of Done

A feature or fix is considered **done** when:

- [ ] Code compiles/runs without errors
- [ ] All existing tests pass (`pytest`, Playwright smoke)
- [ ] New tests written for new behavior
- [ ] No regressions in thumbnail certification (if touching extraction/HTML)
- [ ] API endpoints return `StandardResponse` or `PaginatedResponse` wrappers
- [ ] Structured logging added for observable paths
- [ ] No hardcoded secrets or credentials in source
- [ ] Documentation updated if public interfaces changed

---

## Architecture Overview

```
tech_news/
├── backend/                  # FastAPI + Celery backend
│   ├── app/
│   │   ├── api/v1/routes/    # Versioned API endpoints
│   │   ├── core/             # Config, DB, Redis, Security, Shutdown
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic (ingestion, ranking)
│   ├── scripts/              # Management scripts
│   ├── tests/                # Pytest suite
│   └── main.py               # FastAPI app + lifespan
├── frontend/                 # Next.js frontend
│   ├── src/                  # App router, components, stores
│   └── tests/
│       ├── smoke/            # Playwright smoke tests
│       ├── global-setup.ts   # Test user seeding
│       └── global-teardown.ts
├── database/                 # DB migrations/scripts
├── nginx.conf                # Reverse proxy config
├── docker-compose.yml        # Multi-container orchestration
└── PROJECT_STATE.md          # Living project status document
```

### Key Patterns
- **SSE Streams**: Use `shutdown_event` (asyncio.Event) for graceful termination
- **Database Sessions**: Context-managed `AsyncSessionLocal()` — never hold sessions across await boundaries
- **Redis PubSub**: Always cleanup in `finally` blocks (`pubsub.unsubscribe()` + `pubsub.close()`)
- **Test Isolation**: `conftest.py` fixtures reset `shutdown_event` and dispose connection pools between tests

---

## Frozen Systems Policy

> The following subsystems are **architecture-frozen** as of v0.10.0-beta.
> Changes must be evolutionary (bug fixes, test additions), not structural redesigns.

| System | Status |
|---|---|
| Authentication (JWT, OAuth, RBAC) | 🔒 Frozen |
| Security (rate limiting, headers, CORS) | 🔒 Frozen |
| Database Evolution Workflow | 🔒 Frozen |
| API Layer (StandardResponse) | 🔒 Frozen |
| HTML Preservation | 🔒 Frozen |
| Thumbnail Pipeline | 🔒 Frozen + Certified |
| Backup & Disaster Recovery | 🔒 Frozen + Certified |
| Observability (health, telemetry, SSE) | 🔒 Frozen |
| Dashboard APIs | 🔒 Frozen |
| SSE Architecture | 🔒 Frozen |
| CI/CD Architecture | 🔒 Frozen |

**To unfreeze**: Requires a documented justification, a failing test or certification regression, and explicit approval before any structural change.

---

## CI Expectations (Phase 3B)

Every PR must pass the active quality gates:

1. `ruff check .` — Python linting
2. `mypy` — Type checking
3. `eslint` — TypeScript linting
4. `pytest` — Backend test suite
5. `playwright test` — E2E smoke tests
6. `docker build` — Container build validation
7. `alembic check` — ORM/migration drift detection
8. `python scripts/generate_schema.py --verify` — generated schema verification
9. Thumbnail certification — No regression in A+ grade

---

## Test Commands Quick Reference

| Command | Scope |
|---|---|
| `pytest tests/ -v` | Full backend suite |
| `pytest tests/test_unit_auth.py -v` | Auth unit tests |
| `pytest tests/test_shutdown.py -v` | Shutdown regression |
| `pytest tests/test_init_db.py -v` | DB seeding + idempotency |
| `npx playwright test` | Full E2E suite |
| `npx playwright test tests/smoke/` | Smoke tests only |
| `npx playwright test --list` | List discovered tests |
