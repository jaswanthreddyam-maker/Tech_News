# Backup & Recovery Subsystem Documentation

This document provides a comprehensive operational guide to the Backup & Disaster Recovery Subsystem implemented in **Phase 3C** for the **Tech News Today** platform.

---

## 1. System Overview

The backup subsystem is designed to protect the platform's data (PostgreSQL database and dynamic thumbnail assets) from loss or corruption. It enforces **cryptographic security, signature verification, versioned metadata manifests, and transactional restore rollback mechanics**.

### Key Capabilities
- **AES-256-GCM Payload Encryption**: Protects raw backup contents (tarball of database dump and uploads/ files).
- **HMAC-SHA256 Manifest Signature**: Signs the plain JSON metadata to guarantee it has not been modified or tampered with.
- **Key Separation**: Uses two distinct cryptographic secrets derived from environments (`BACKUP_ENCRYPTION_KEY` and `BACKUP_SIGNING_KEY`).
- **Transactional Swapping & Rollback**: Reconstructs database state in a staging database (`_restore_temp`) and staging folder (`uploads_temp`) before atomic swap. Rollback triggers automatically on staging or health check failures.
- **Grandfather-Father-Son (GFS) Rotation**: Retains 7 Daily, 4 Weekly, and 12 Monthly backups.

---

## 2. Configuration Settings

The following variables are defined in [config.py](file:///c:/Users/HP/Downloads/tech_news/backend/app/core/config.py) and configured via environment variables inside the `.env` file:

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `BACKUP_ENCRYPTION_KEY` | `dev_only...` | 32-byte key (Base64-encoded) for GCM encryption |
| `BACKUP_SIGNING_KEY` | `dev_only...` | 32-byte key (Base64-encoded) for HMAC signatures |
| `BACKUP_STORAGE_BACKEND` | `local` | Storage driver type (`local` filesystem) |
| `BACKUP_COMPRESSION` | `gzip` | Tarball compression algorithm (`gzip`) |
| `BACKUP_STORAGE_PATH` | `storage/backups` | Root path for backups |

> [!CRITICAL]
> In `production` environment settings, the server will **fail fast** and refuse to start if default development values are used for `BACKUP_ENCRYPTION_KEY` or `BACKUP_SIGNING_KEY`.

---

## 3. Automation & Scheduling

Celery Beat triggers background tasks on separate schedules to split creation and cleanup loads:

1. **Daily Backup Execution (`tasks.backup.run_backup_task`)**
   - **Trigger**: Runs daily at **02:00 UTC**.
   - **Action**: Dumps the active database, compiles dynamic upload assets, encrypts the bundle, generates the signed manifest, and writes files to structured monthly directories.

2. **Retention Policy Evaluation (`tasks.backup.run_retention_task`)**
   - **Trigger**: Runs daily at **03:00 UTC**.
   - **Action**: Lists all backups in the storage backend, calculates the GFS keeps/deletes, and purges expired backups from disk.

---

## 4. CLI Operation

The subsystem provides a dedicated management CLI tool. Run it using the Python module syntax:

```bash
# General help
python -m app.cli.backup --help
```

### Subcommands

#### A. Create a Backup
Trigger an immediate, on-demand backup of the current database and assets state:
```bash
python -m app.cli.backup create
```

#### B. List Backups
List all available backups in the storage backend, summarizing their date, rows, size, and health state:
```bash
python -m app.cli.backup list
```
*Pass `--all` to list failed/diagnostic backups too.*

#### C. Verify Backup Integrity
Verify HMAC signature of the manifest, payload SHA-256 checksum, and GCM decrypt validity:
```bash
python -m app.cli.backup verify <backup_id>
```

#### D. Restore from Backup
Restore the system to a specific point-in-time state:
```bash
# Dry-run validation (Highly recommended to preview database rows/files before swapping)
python -m app.cli.backup restore <backup_id> --dry-run

# Execute real restore (prompts for confirmation)
python -m app.cli.backup restore <backup_id>

# Execute real restore and skip interactive prompt
python -m app.cli.backup restore <backup_id> --yes
```
