# Architecture Decision Records (ADR)

> This document records key architectural decisions made during the development
> of Tech News Today. Each record is intentionally brief — capturing _what_ was
> decided, _why_, and the current status. When you revisit the project months
> later and wonder "why did we do it this way?", start here.
>
> **Statuses**: `Accepted` · `Superseded` · `Deprecated` · `Proposed`
>
> **See also**: [PROJECT_STATE.md](PROJECT_STATE.md) · [DATABASE_WORKFLOW.md](DATABASE_WORKFLOW.md) · [CONTRIBUTING.md](CONTRIBUTING.md)

---

## ADR-001 — Authentication Strategy

| | |
|---|---|
| **Decision** | JWT access tokens + opaque refresh tokens stored as HttpOnly cookies |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
The platform needs stateless request authentication (scalable across workers)
combined with the ability to revoke sessions server-side.

**Rationale**
- JWT access tokens are stateless — no DB lookup per request.
- Short-lived tokens (configurable `ACCESS_TOKEN_EXPIRE_MINUTES`) limit blast
  radius of leaked tokens.
- Opaque refresh tokens (`secrets.token_hex(64)`) stored in HttpOnly cookies
  prevent XSS theft and enable server-side revocation.
- Refresh token replay detection: reuse of a consumed token revokes the entire
  session family.

**Alternatives Considered**
- Session-based auth (server-side state per request — doesn't scale across
  multiple Uvicorn workers without sticky sessions).
- OAuth-only (eliminates local registration; too restrictive for MVP).

**References**
- [security.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/security.py)

---

## ADR-002 — Role-Based Access Control (RBAC)

| | |
|---|---|
| **Decision** | Database-driven roles and permissions with Redis caching |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Admin, editor, and reader roles need different levels of access. Permission
checks should not add latency to every request.

**Rationale**
- Roles and permissions stored in PostgreSQL (`Role`, `Permission`,
  `RolePermission` tables) — fully auditable and mutable at runtime.
- Permissions cached in Redis with 1-hour TTL to avoid repeated DB joins.
- `require_role()` and `require_permission()` FastAPI dependencies provide
  composable, declarative route protection.

**Alternatives Considered**
- Hardcoded role checks (fragile, not extensible).
- Embedding permissions in JWT claims (stale until token refresh).

**References**
- [security.py — require_role / require_permission](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/security.py#L242-L286)

---

## ADR-003 — API Response Contract

| | |
|---|---|
| **Decision** | `StandardResponse<T>` and `PaginatedResponse<T>` wrappers for all endpoints |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Frontend and external consumers need a predictable, consistent response shape
regardless of which endpoint they call.

**Rationale**
- Single response contract eliminates per-endpoint parsing logic.
- Every response carries `status`, `correlation_id`, and `timestamp` — enabling
  client-side debugging and distributed tracing.
- `ErrorResponse` with structured `ErrorDetails` (code, message, fields) ensures
  validation errors are machine-parseable.
- Pagination uses cursor-based tokens (`next_cursor`, `has_more`) — efficient
  for large datasets, no OFFSET/LIMIT drift.

**Alternatives Considered**
- Raw JSON bodies (inconsistent shapes, no traceability).
- Envelope-less responses with HTTP status only (insufficient for field-level
  error details).

**References**
- [responses.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/schemas/responses.py)

---

## ADR-004 — Monitoring & Health Checks

| | |
|---|---|
| **Decision** | Celery Beat performs scheduled health checks; Decoupled polling intervals per telemetry domain |
| **Date** | Phase 2 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Health checks against PostgreSQL, Redis, Celery, and external services must not
burden FastAPI request workers.

**Rationale**
- Celery Beat runs health checks on a schedule — results stored in Redis.
- FastAPI health endpoints read cached results (zero-cost reads).
- Split endpoints with independent polling rates: Overview (60s), Infrastructure
  (10s), Queue (5s), Logs (live SSE).
- 10 rolling status indicators per service stored in Redis for sparkline-style
  history.

**Alternatives Considered**
- Inline health checks in FastAPI routes (blocks worker threads under load).
- External monitoring only (no internal visibility for the dashboard).

**References**
- [checkers.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/monitoring/checkers.py)
- [observability.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/monitoring/observability.py)

---

## ADR-005 — Database Access Pattern

| | |
|---|---|
| **Decision** | Async SQLAlchemy with `AsyncSession`, context-managed sessions, `selectinload` for relationships |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
The backend is fully async (FastAPI + Uvicorn). Database access must not block
the event loop, and N+1 query problems must be prevented by default.

**Rationale**
- `asyncpg` driver with async SQLAlchemy engine — non-blocking I/O.
- Sessions are context-managed via `get_db()` dependency — automatic
  commit/rollback/close lifecycle.
- `expire_on_commit=False` prevents lazy-load traps after commit.
- `selectinload()` is the default strategy for relationship loading — prevents
  N+1 at the ORM level.
- Connection pool: `pool_size=10`, `max_overflow=20`, `pool_recycle=1800s`,
  `pool_pre_ping=True`.

**Alternatives Considered**
- Synchronous SQLAlchemy (blocks event loop, negates FastAPI async benefits).
- Raw asyncpg without ORM (faster but loses model/schema validation layer).

**References**
- [database.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/database.py)

---

## ADR-006 — Caching & Rate Limiting Infrastructure

| | |
|---|---|
| **Decision** | Redis 7 as unified cache, rate limiter, pub/sub broker, and distributed lock manager |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Multiple subsystems need shared state: rate limiting, permission caching,
health-check history, SSE pub/sub, and distributed locking for scheduled jobs.

**Rationale**
- Single Redis instance serves all use cases — reduces operational complexity.
- Rate limiting uses `INCR` + `EXPIRE` (sliding window per IP + action).
- Distributed locks use `SET NX EX` for mutual exclusion across workers.
- `redis.asyncio` client with `decode_responses=True` — consistent async API.

**Alternatives Considered**
- In-memory caching (not shared across workers, lost on restart).
- Separate Redis instances per concern (operationally expensive for a single-team project).

**References**
- [redis.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/redis.py)
- [security.py — apply_rate_limit](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/security.py#L48-L76)

---

## ADR-007 — Structured Logging & Observability

| | |
|---|---|
| **Decision** | JSON structured logging with correlation IDs, request timing, and rotating file output |
| **Date** | Phase 2 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Debugging production issues requires correlated, searchable, structured logs —
not plain text grepping.

**Rationale**
- `JSONFormatter` emits logs as JSON objects (timestamp, level, logger,
  correlation_id, module, function, line).
- `LoggingMiddleware` generates or propagates `X-Correlation-ID` per request —
  enabling distributed tracing.
- `X-Process-Time-Ms` header on every response for latency visibility.
- Dev: plain-text console. Prod: JSON console + rotating file (10MB × 5 backups).
- Logger hierarchy: `tech_news.<module>` — never `print()`.

**Alternatives Considered**
- Third-party APM (premature complexity and cost at this stage).
- Unstructured logging (unsearchable in production).

**References**
- [logging.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/logging.py)

---

## ADR-008 — SSE Graceful Shutdown

| | |
|---|---|
| **Decision** | Global `asyncio.Event` (`shutdown_event`) coordinated across all SSE streams |
| **Date** | Phase 2 |
| **Status** | ✅ Accepted — Frozen |

**Context**
SSE connections are long-lived. A SIGTERM during deployment must not leave
orphaned connections, leaked Redis pub/sub subscriptions, or hanging workers.

**Rationale**
- `shutdown_event` is an `asyncio.Event` set by signal handlers (SIGTERM/SIGINT).
- All SSE generators check `shutdown_event.is_set()` on each iteration and exit
  cleanly.
- Redis PubSub cleanup is always in `finally` blocks (`unsubscribe()` +
  `close()`).
- Regression test (`test_shutdown.py`) validates cleanup completes under
  simulated shutdown.

**Alternatives Considered**
- Per-connection cancellation tokens (complex to manage, easy to leak).
- Hard kill with no cleanup (orphaned Redis subscriptions, resource leaks).

**References**
- [shutdown.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/shutdown.py)

---

## ADR-009 — Thumbnail Pipeline Strategy

| | |
|---|---|
| **Decision** | Multi-stage extraction → validation → deduplication → WEBP optimization, certified via snapshot framework |
| **Date** | Phase 2 |
| **Status** | ✅ Accepted — Frozen + Certified (A+) |

**Context**
News articles arrive with wildly inconsistent image metadata. The system needs
reliable, high-quality thumbnails without manual curation.

**Rationale**
- **Extraction**: Schema.org → Open Graph → Twitter Cards → domain-specific
  rules → fallback heuristics. Ordered by reliability.
- **Validation**: Minimum size, aspect ratio, format checks reject tracking
  pixels and icons.
- **Deduplication**: Perceptual hashing (pHash) prevents storing visually
  identical images from syndicated articles.
- **Optimization**: All thumbnails converted to WEBP and stored locally.
- **Certification**: `validate_snapshots.py` runs against 45 fixtures. Current
  grade: A+ (0% fallbacks, 0% duplicates). Any change to extraction or HTML
  parsing must pass certification.

**Alternatives Considered**
- External thumbnail service (adds latency, cost, and external dependency).
- First-image heuristic only (unreliable — often selects ads or icons).

**References**
- [image_helper.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/ingestion/image_helper.py)
- [pipeline.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/ingestion/pipeline.py)

---

## ADR-010 — HTML Preservation & Sanitization

| | |
|---|---|
| **Decision** | Store sanitized original HTML alongside extracted plain text; deterministic keyword tagging |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Displaying rich article content requires preserved HTML formatting, but raw HTML
from RSS feeds contains scripts, tracking pixels, and unsafe elements.

**Rationale**
- Sanitize HTML on ingestion (whitelist-based), store as `content_html`.
- Extract plain text for search indexing and AI processing.
- Deterministic keyword tagging operates on plain text — reproducible and
  testable.
- Separation means the display layer can render rich content while the data
  layer operates on clean text.

**Alternatives Considered**
- Store plain text only (loses formatting, images, links).
- Store raw HTML (XSS risk, inconsistent rendering).

**References**
- [filter.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/ingestion/filter.py)
- [processor.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/services/ingestion/processor.py)

---

## ADR-011 — Reverse Proxy Architecture

| | |
|---|---|
| **Decision** | Nginx as single entry point with dynamic DNS resolution for Docker services |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
The frontend (Next.js :3000) and backend (FastAPI :8000) run as separate
containers. A single port 80 entry point is needed for routing, security
headers, and SSE buffering control.

**Rationale**
- Nginx routes `/api/` → backend, `/` → frontend, SSE paths get special
  buffering-disabled config.
- Dynamic DNS resolution (`resolver 127.0.0.11 valid=10s`) with `set $variable`
  prevents static IP caching when containers restart.
- Security headers (X-Frame-Options, CSP, X-XSS-Protection, Referrer-Policy)
  applied at the edge.
- SSE paths explicitly disable `proxy_buffering`, `gzip`, and set 24h read
  timeouts.
- WebSocket passthrough for Next.js HMR in development.

**Alternatives Considered**
- Traefik (more features but heavier config for a single-project setup).
- Direct port exposure (no unified security headers, CORS complexity).

**References**
- [nginx.conf](file:///c:/Users/HP/Downloads/tech_news/nginx.conf)

---

## ADR-012 — Task Queue Architecture

| | |
|---|---|
| **Decision** | Celery with Redis broker; separate `worker` and `beat` containers |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
Background tasks (RSS crawling, thumbnail processing, health checks) must not
block FastAPI request workers.

**Rationale**
- Celery workers execute CPU/IO-bound tasks outside the request cycle.
- Celery Beat handles periodic scheduling (crawl intervals, health checks).
- Redis serves as both broker and result backend — no additional infrastructure.
- Separate Docker containers for worker and beat ensure independent scaling and
  restarts.

**Alternatives Considered**
- FastAPI `BackgroundTasks` (limited to request lifecycle, no persistence).
- APScheduler (single-process, no distributed execution).
- Dramatiq (less ecosystem support than Celery).

**References**
- [docker-compose.yml — worker & beat services](file:///c:/Users/HP/Downloads/tech_news/docker-compose.yml#L70-L118)

---

## ADR-013 — Frontend Architecture

| | |
|---|---|
| **Decision** | Next.js App Router + Tailwind CSS + Zustand + Zod |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
The frontend needs server-side rendering for SEO, a modern component model,
type-safe API consumption, and lightweight state management.

**Rationale**
- **Next.js App Router**: File-based routing, React Server Components, built-in
  SSR/SSG.
- **Tailwind CSS**: Utility-first styling — fast iteration, consistent design
  system.
- **Zustand**: Minimal boilerplate state management (~3 lines to create a store).
- **Zod**: Runtime validation of API responses — catches contract violations
  before they reach components.

**Alternatives Considered**
- Vite + React Router (no SSR out of the box).
- Redux (excessive boilerplate for this project's state complexity).
- No runtime validation (silent contract breakage on API changes).

---

## ADR-014 — Test Strategy

| | |
|---|---|
| **Decision** | Layered testing: Unit (pytest) → Integration → API → E2E (Playwright) + Snapshot certification |
| **Date** | Phase 3A |
| **Status** | ✅ Accepted — Frozen |

**Context**
A single test type is insufficient. Unit tests catch logic bugs, integration
tests catch wiring bugs, E2E tests catch UX bugs, and certification catches
quality regressions.

**Rationale**
- **Unit**: pytest for auth, HTML processing, ranking, thumbnail logic,
  observability.
- **Integration**: Pipeline tests exercise ingestion → storage → retrieval.
- **API**: Telemetry endpoint tests validate contract compliance.
- **E2E**: Playwright smoke tests for homepage rendering and authentication
  flows.
- **Certification**: `validate_snapshots.py` ensures thumbnail pipeline
  maintains A+ grade across 45 fixtures.
- **Isolation**: `conftest.py` resets `shutdown_event` and disposes connection
  pools between tests.

**Alternatives Considered**
- E2E only (slow, flaky, poor fault localization).
- Unit only (misses integration and contract bugs).

---

## ADR-015 — Deduplication Strategy

| | |
|---|---|
| **Decision** | MD5 content hashing for article dedup; perceptual hashing (pHash) for image dedup |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted — Frozen |

**Context**
RSS feeds from multiple sources frequently syndicate the same article with
minor variations in metadata. Images are often re-encoded with different
compression but identical visual content.

**Rationale**
- **Articles**: MD5 hash of normalized content — fast, deterministic, catches
  exact duplicates and minor whitespace variations.
- **Images**: Perceptual hash (pHash) — tolerant to re-encoding, resizing, and
  minor crop differences. Catches visually identical images even when byte
  content differs.

**Alternatives Considered**
- URL-based dedup only (misses syndicated content with different URLs).
- Exact byte comparison for images (misses re-encoded duplicates).

---

## ADR-016 — Container Orchestration

| | |
|---|---|
| **Decision** | Docker Compose with health-check dependency chains |
| **Date** | Phase 1 |
| **Status** | ✅ Accepted |

**Context**
Six services (db, redis, backend, worker, beat, frontend, nginx) must start in
the correct order with verified readiness.

**Rationale**
- `depends_on` with `condition: service_healthy` ensures services only start
  when their dependencies are proven ready.
- Each service has a dedicated healthcheck (pg_isready, redis-cli ping, curl
  /health/live, wget /).
- Alpine-based images minimize attack surface and pull times.
- Named volumes (`postgres_data`, `redis_data`) persist state across restarts.

**Alternatives Considered**
- Kubernetes (premature for a single-server deployment).
- Manual start scripts (fragile, no health gating).

**References**
- [docker-compose.yml](file:///c:/Users/HP/Downloads/tech_news/docker-compose.yml)

---

## ADR-017 — Architecture Freeze Policy

| | |
|---|---|
| **Decision** | Core subsystems frozen at v0.10.0-beta; changes must be evolutionary, not structural |
| **Date** | v0.10.0-beta |
| **Status** | ✅ Accepted |

**Context**
After reaching 10/10 maturity across all core subsystems, ongoing structural
changes create instability and rework. The platform is now mature enough to
treat as a product.

**Rationale**
- Frozen systems (auth, security, DB, API, HTML, thumbnails, observability,
  dashboard, SSE, tests) accept only bug fixes and test additions.
- New capabilities (CI/CD, backups, AI, semantic search) must fit within
  existing contracts — not reshape them.
- Unfreezing requires: documented justification, a failing test or certification
  regression, and explicit approval.
- This policy protects the foundation as increasingly complex features (AI,
  embeddings) are added on top.

**References**
- [CONTRIBUTING.md — Frozen Systems Policy](file:///c:/Users/HP/Downloads/tech_news/CONTRIBUTING.md#L184-L201)
- [PROJECT_STATE.md — Frozen Systems](file:///c:/Users/HP/Downloads/tech_news/PROJECT_STATE.md#L22-L41)

---

## ADR-018 — AI Provider Strategy

| | |
|---|---|
| **Decision** | Provider abstraction layer instead of direct OpenAI/Anthropic calls |
| **Date** | Phase 4 (pending) |
| **Status** | 📋 Proposed |

**Context**
The AI pipeline (summarization, SEO, tagging, sentiment) must not be locked to
a single LLM provider. Provider pricing, rate limits, and model quality shift
frequently.

**Rationale**
- An `AIProvider` abstraction allows swapping providers without touching
  business logic.
- Enables future support for: OpenAI, Anthropic, Google, and local LLMs.
- Cost tracking (`ai_job_history`) remains provider-agnostic.
- Facilitates A/B testing across models.

**Alternatives Considered**
- Direct OpenAI SDK calls (vendor lock-in, expensive to migrate).
- LangChain (heavy abstraction for simple prompt/response workflows).

> ⏳ *To be finalized when Phase 4 begins.*

---

## ADR-019 — Vector Search Infrastructure

| | |
|---|---|
| **Decision** | `pgvector` extension on existing PostgreSQL instance |
| **Date** | Phase 5 (pending) |
| **Status** | 📋 Proposed |

**Context**
Semantic search, duplicate detection, and article recommendations require
vector similarity queries. The choice of vector store is expensive to change
once embeddings are populated.

**Rationale**
- `pgvector` runs inside the existing PostgreSQL instance — no new
  infrastructure to operate.
- Supports HNSW and IVFFlat indexes for approximate nearest neighbor.
- Embeddings live alongside relational data — enabling hybrid queries
  (vector similarity + metadata filters) in a single transaction.
- Backup and recovery inherit the existing PostgreSQL strategy.

**Alternatives Considered**
- Pinecone (managed, but adds external dependency and cost).
- Weaviate (powerful, but operationally heavy for a single-project setup).
- Milvus (designed for massive scale — overkill for this corpus size).

> ⏳ *To be finalized when Phase 5 begins.*

---

## ADR-020 — Backup Strategy

| | |
|---|---|
| **Decision** | Encrypted local backups with optional cloud sync |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
The platform stores articles, user data, thumbnails, and configuration that
must survive hardware failure, accidental deletion, and corruption.

**Rationale**
- Local encrypted backups are simple, portable, and support offline recovery.
- Checksum verification ensures backup integrity before restore.
- Restore validation runs automated checks post-restore to confirm data
  consistency.
- Cloud sync can be layered on later without changing the local backup
  contract.
- Retention policies prevent unbounded storage growth.

**Alternatives Considered*## ADR-021 — Backup & Recovery Architecture

| | |
|---|---|
| **Decision** | Combined database and file asset backup package; versioned metadata manifests stored separately from the encrypted payload. |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
The platform contains PostgreSQL relational state and static static asset storage (thumbnails) that must be backed up as a consistent, atomic unit.

**Rationale**
- Backups are grouped into unified directories `storage/backups/YYYY/MM/backup_ID/` to scale browseability.
- A metadata `manifest.json` is stored unencrypted outside the encrypted binary file (`backup.enc`) to allow status, version, and integrity validation before decryption.
- Manifest schemas are versioned (`manifest_version: 1`, `backup_format: 1`) to support long-term backward-compatible parsing.
- A `status` field tracks backup progress lifecycle state machine.

**Alternatives Considered**
- Flat directory structures (difficult to manage sidecars, lacks scalability).
- Manifest inside encrypted payload (impossible to read metadata without decryption keys).

**References**
- [PROJECT_STATE.md](PROJECT_STATE.md)

---

## ADR-022 — Cryptographic Design

| | |
|---|---|
| **Decision** | Symmetric AES-256-GCM for payloads; HMAC-SHA256 for manifests; Cryptographic key separation. |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
User credentials, logs, and metadata must remain secure at rest, and manifests must be signed to prevent tampering. Cryptographic standards recommend not using the same key for both encryption and signing.

**Rationale**
- **Key Separation**: Exposes distinct environment variables `BACKUP_ENCRYPTION_KEY` and `BACKUP_SIGNING_KEY` (or derived from a master key via HKDF) to isolate contexts.
- **AES-256-GCM**: Payload `backup.enc` is encrypted symmetrically with unique IVs. The GCM authentication tag and nonce are packaged directly inside the payload binary rather than the manifest metadata.
- **HMAC manifest signing**: The unencrypted `manifest.json` is signed to create `manifest.sig` before storage, preventing malicious manifest modification.

**Alternatives Considered**
- Single key for encryption and HMAC signing (cryptographically vulnerable).

---

## ADR-023 — Restore Strategy

| | |
|---|---|
| **Decision** | Multi-gate transactional staging database/file swaps with connection termination, liveness checks, and automated rollback. |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
Restoration is a highly destructive operation. If a restore fails mid-process, the platform must not be left in a broken or inconsistent state.

**Rationale**
- **Validation Gates**: Restore processes sequentially verify HMAC manifest signature, file SHA-256 checksums, and metadata version compatibility.
- **Transactional Staging DB Restore**: Derives staging DB name dynamically (e.g. `tech_news_test_restore_temp`). Terminates all active database connections, runs the restore to staging DB, validates migration state, drops production DB, renames staging DB to production, and resumes traffic.
- **Staging Files Restore**: Extracts files to a temporary asset directory and performs an atomic directory swap upon successful validation.
- **Rollback**: Drops temp objects and reverts to pre-restore state on any failure.
- **Health Verification**: Validates DB, Redis, Celery worker heartbeat, and readiness checks post-restore.

**Alternatives Considered**
- Direct production database overwrite (leads to permanent downtime on restore failure).

---

## ADR-024 — Storage Abstraction

| | |
|---|---|
| **Decision** | Pluggable storage backend interface. |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
While backups are stored on local disks initially, migrating to remote storage backends (S3, GCS, Azure Blobs) in the future should not require rewriting core backup and restore engines.

**Rationale**
- Decouples storage operations via a `BaseStorage` abstract interface.
- Core systems interact only with the interface, while a factory (`get_storage()`) loads the active driver (defaulting to `LocalStorage`).

**Alternatives Considered**
- Coupling backup service to filesystem path methods (requires major code refactoring to migrate to S3).

---

## ADR-025 — Retention & Lifecycle Policy

| | |
|---|---|
| **Decision** | Automated GFS schedule decoupled in execution time. |
| **Date** | June 2026 (Phase 3C) |
| **Status** | ✅ Accepted — Frozen |

**Context**
Continuous backups create unbounded disk growth. Expired backups must be rotated automatically without blocking backup creation runs.

**Rationale**
- **GFS Schedule**: Retain 7 daily, 4 weekly, and 12 monthly backups.
- **Decoupled Tasks**: Runs daily backups at 02:00 UTC and GFS retention cleanup at 03:00 UTC via Celery Beat periodic scheduling.

**Alternatives Considered**
- Running cleanup inside the creation task (increases backup task complexity and duration).

---

## ADR-026 — Database Evolution Workflow Freeze

| | |
|---|---|
| **Decision** | SQLAlchemy models, Alembic migrations, and generated `database/schema.sql` form the canonical database evolution workflow |
| **Date** | v0.10.0-beta |
| **Status** | ✅ Accepted — Frozen |

**Context**
Phase 3D eliminated schema drift discovered during disaster recovery validation.
The project needs a single auditable workflow for future schema changes.

**Rationale**
- SQLAlchemy models define intended application state.
- Alembic migrations encode the production database transition path.
- `database/schema.sql` is generated from a migrated database for restore and audit workflows.
- CI runs `alembic check` and `generate_schema.py --verify` to catch drift before merge.
- Direct edits to generated schema output bypass the source-of-truth workflow and are prohibited.

**Alternatives Considered**
- Manual `schema.sql` edits (caused drift and weakens disaster recovery confidence).
- Database-first schema changes (breaks ORM and migration review guarantees).

**References**
- [DATABASE_WORKFLOW.md](DATABASE_WORKFLOW.md)
- [docs/PHASE_3D_COMPLETION.md](docs/PHASE_3D_COMPLETION.md)

---

> **Adding a new ADR**: Copy the template below, increment the number, and
> append to this file. Keep decisions short — if you need more than a page,
> you're writing a design doc, not an ADR.
>
> ```
> ## ADR-NNN — Title
>
> | | |
> |---|---|
> | **Decision** | What was decided |
> | **Date** | When |
> | **Status** | Accepted / Superseded / Deprecated / Proposed |
>
> **Context** — Why the decision was needed.
>
> **Rationale** — Why this option was chosen.
>
> **Alternatives Considered** — What else was evaluated.
>
> **References** — Links to relevant code or docs.
> ```

