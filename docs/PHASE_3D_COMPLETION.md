# Phase 3D Completion: Database Schema & Migration Hardening

Phase 3D closed the schema drift found during the Phase 3C disaster recovery drill. SQLAlchemy models and Alembic migrations are now the authoritative source for database evolution, with `database/schema.sql` generated from the migration state.

The canonical workflow is defined in [DATABASE_WORKFLOW.md](../DATABASE_WORKFLOW.md).

## Scope

Phase 3D covers schema source-of-truth hardening, Alembic checks, generated schema verification, maintenance mode, and migration drift prevention. Backup packaging and disaster recovery operations are tracked separately in [PHASE_3C_COMPLETION.md](PHASE_3C_COMPLETION.md).

## Source Of Truth

The database evolution workflow is:

1. SQLAlchemy models define intended schema.
2. Alembic migrations encode schema changes.
3. PostgreSQL receives migrations through `alembic upgrade head`.
4. [database/schema.sql](../database/schema.sql) is generated from the migrated database.

This removes manual `schema.sql` drift from the operational recovery path.

## Key Accomplishments

### Schema Generation

- Added [backend/scripts/generate_schema.py](../backend/scripts/generate_schema.py).
- Generates `database/schema.sql` from a temporary database migrated to Alembic head.
- Supports `--verify` mode so CI can fail on committed schema drift.
- Normalizes generated output to reduce noisy diffs.

### Alembic Hardening

- Loaded all SQLAlchemy models in [backend/alembic/env.py](../backend/alembic/env.py) so autogeneration sees full metadata.
- Resolved model/database drift found during restore validation.
- Added CI coverage for `alembic check`, which fails when autogeneration would produce unexpected migration operations.
- Added CI coverage for `python scripts/generate_schema.py --verify`.

### Maintenance Mode

- Added [backend/app/core/middleware.py](../backend/app/core/middleware.py) to fast-fail state-changing requests while Redis key `settings:maintenance_mode` is set to `1`.
- `POST`, `PUT`, `PATCH`, and `DELETE` requests return `503 Service Unavailable` with error code `MAINTENANCE_MODE`.
- Read-only operational endpoints remain available by method, including health checks, telemetry metrics, and SSE streams.
- `/api/v1/backup` is explicitly bypassed for restore workflows if backup endpoints are exposed through the API later.
- Added [backend/tests/test_maintenance_middleware.py](../backend/tests/test_maintenance_middleware.py) to lock this behavior.

## Validation

Phase 3D validation covered:

- `alembic upgrade head`.
- `alembic check`.
- `python scripts/generate_schema.py --verify`.
- Containerized restore against a seeded PostgreSQL database.
- Post-restore health checks.
- Authentication after restore.
- Celery worker execution after restore.
- Upload/thumbnail asset restoration.
- Async test stability fixes for loop scope, SSE generator testing, and transport deadlocks.

## Future Enhancement

If the platform needs broader PostgreSQL compatibility, add migration validation against multiple supported PostgreSQL versions, such as the current production version and the next supported version.

## Certification

Phase 3D is complete. The platform now has a hardened database evolution workflow and is ready to begin Phase 4 real AI integration.
