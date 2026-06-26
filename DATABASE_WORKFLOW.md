# Database Workflow

This document defines the canonical database evolution workflow for Tech News Today.

## Status

The database evolution process is frozen as of `v0.10.0-beta`.

SQLAlchemy models, Alembic migrations, and the generated `database/schema.sql` file now constitute the canonical database workflow. Direct manual edits to the generated schema section are prohibited.

## Canonical Flow

1. Update SQLAlchemy models in `backend/app/models`.
2. Generate or edit an Alembic migration in `backend/alembic/versions`.
3. Apply migrations with `alembic upgrade head`.
4. Verify ORM/migration parity with `alembic check`.
5. Regenerate `database/schema.sql` with `python scripts/generate_schema.py`.
6. Verify committed schema output with `python scripts/generate_schema.py --verify`.

## Rules

- All schema changes must originate from ORM model updates and Alembic migrations.
- The generated section of `database/schema.sql` must not be manually edited.
- Migration files must be reviewed as production data-change artifacts, not just code diffs.
- Every pull request that changes models, migrations, or generated schema output must pass the schema drift CI gate.
- Restore drills must validate the migrated database state before accepting a backup as operationally restorable.

## CI Gates

The `schema-migrations` job in `.github/workflows/quality.yml` runs:

```bash
alembic upgrade head
alembic check
python scripts/generate_schema.py --verify
```

These gates ensure the ORM, Alembic migrations, and committed schema artifact remain aligned.

## Unfreezing

Changing this workflow requires a documented architectural decision, a concrete regression or operational requirement, and explicit approval before structural changes are made.
