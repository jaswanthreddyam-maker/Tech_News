# Disaster Recovery & System Restoration Runbook

This runbook describes the step-by-step procedures for restoring the **Tech News Today** platform during a disaster scenario (e.g. data corruption, database server failure, or file system loss).

---

## 1. Initial Assessment & Target Resolution

Before performing a restore, identify the target state and verify which backup package to recover from.

1. **Access the Backup Storage**:
   Check the configured backup directory (default: `storage/backups`) or query the CLI to list all completed backups:
   ```bash
   python -m app.cli.backup list
   ```

2. **Select the Target Backup**:
   Locate the newest completed backup ID that precedes the disaster timestamp (e.g. `backup_20260610T020000Z_3fa9b1`).

---

## 2. Integrity Verification (Gate 1)

Always verify the integrity of the chosen backup prior to execution to avoid restoring corrupted or compromised data.

Run the verification tool on the target backup ID:
```bash
python -m app.cli.backup verify backup_20260610T020000Z_3fa9b1
```

**Expected Output Checklist**:
- `[PASS] Manifest HMAC signature validation.`
- `[PASS] Payload SHA-256 integrity check.`
- `[PASS] Payload AES-256-GCM decryption check.`
- `[PASS] Backup completion state check.`

> [!WARNING]
> If any check returns `[FAIL]`, **DO NOT** attempt restoration from this backup. The manifest or payload has been tampered with or corrupted. Locate an older healthy backup instead.

---

## 3. Dry-Run Restoring Validation (Gate 2)

Validate migration compatibility and extract the preview data to verify stats:
```bash
python -m app.cli.backup restore backup_20260610T020000Z_3fa9b1 --dry-run
```
Ensure the printed tables, rows, files, and versions correspond to expectations.

---

## 4. Full Staged Restoration Execution

Executing a restore is **destructive** to current DB contents and upload folders. The restore command executes transactionally:

1. **Initiate the Restore**:
   ```bash
   python -m app.cli.backup restore backup_20260610T020000Z_3fa9b1
   ```
   *Type `y` / `yes` to confirm when prompted.*

2. **Internal Execution Steps (Automated)**:
   - System sets `settings:maintenance_mode = 1` in Redis, routing public requests to maintenance pages.
   - Wait for in-flight database requests to settle.
   - Terminate all active database connections using `pg_terminate_backend`.
   - Recreate the staging database: `<prod_db>_restore_temp`.
   - Extract files to `uploads_temp`.
   - Import the decrypted database SQL dump into the staging database.
   - Validate database migrations.
   - Perform atomic rename swap of database and directories.
   - Execute verification health checks.
   - Disable maintenance mode in Redis.

3. **Restoration Log Audit**:
   Monitor restoration logs in real time to verify steps:
   ```bash
   tail -f logs/restore.log
   ```

---

## 5. Post-Restore Health Verification

Once the restore reports success, perform basic checks:
1. Access the status ready API and assert a `200 OK` response:
   ```bash
   curl -I http://localhost:8000/api/v1/health/ready
   ```
2. Verify Redis and Celery workers are processing tasks.
3. Check that dynamic images load correctly on the front-end dashboard.

---

## 6. Emergency Recovery Rollback

If any step in the restoration sequence fails, the system executes an automated rollback:
- Drops the temporary staging DB and deletes temporary staging folder assets.
- Renames the original production database `_old` back to its active name.
- Restores original asset directories.

If a manual revert is ever required:
1. Stop all containers.
2. Rename `tech_news_today_old` database to `tech_news_today` via psql.
3. Move `storage/uploads_old` back to `storage/uploads`.
4. Restart services.

---

## 7. Recovery Validation History

### 2026-06-10
- **Scenario**: Complete loss of PostgreSQL volume, Redis volume, and uploads media storage.
- **Actions**:
  - Removed Docker volumes (`docker compose down -v`)
  - Deleted uploaded assets (`c:\Users\HP\Downloads\tech_news\storage\uploads\*`)
  - Recreated infrastructure (`docker compose up -d`)
  - Verified empty baseline DB and file state
  - Restored backup package (`backup_20260609T203024Z_3401e2`)
  - Verified integrity, database rows count, and dynamic thumbnail files
  - Executed FastAPI health checks and successfully logged in restored users
  - Triggered Celery tasks successfully
- **Result**: `PASS`
- **Notes**:
  - Resolved schema drift by updating `users` table definition in `database/schema.sql` (added `given_name`, `family_name`, `profile_picture`, `last_login`).
  - Added `postgresql-client` to `backend/Dockerfile.dev` to support native `pg_dump` and `psql` execution inside the container.
  - Implemented content-based directory swapping for assets in `service.py` to correctly handle Docker bind mounts without "Device or resource busy" failures.
  - Preloaded all SQLAlchemy models in `celery_app.py` to prevent registry mapper errors during task execution.
