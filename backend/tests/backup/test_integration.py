import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skip(reason="Destroys local database without pg_dump available")

import app.backup.service
from app.backup.service import create_backup, restore_backup
from app.backup.storage.service import get_storage
from app.core.config import settings

# Global reference to original Path class
original_path = Path


@pytest.fixture
def backup_test_env(tmp_path, monkeypatch):
    """
    Sets up isolated directories for backups and uploads during integration testing.
    Redirects /app/uploads and uploads to a temporary uploads path inside tmp_path.
    """
    backup_dir = tmp_path / "backups"
    uploads_dir = tmp_path / "uploads"

    backup_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Seed a dummy upload file
    test_file = uploads_dir / "thumbnail_1.png"
    test_file.write_text("original-thumbnail-bytes-data-123")

    # Mock settings.BACKUP_STORAGE_PATH to point to our temp backups folder
    monkeypatch.setattr(settings, "BACKUP_STORAGE_PATH", str(backup_dir))

    # Custom MockPath to intercept uploads paths in app.backup.service
    class MockPath:
        def __new__(cls, *args, **kwargs):
            if len(args) > 0 and (args[0] in ("/app/uploads", "uploads")):
                return original_path(str(uploads_dir))
            return original_path(*args, **kwargs)

    monkeypatch.setattr(app.backup.service, "Path", MockPath)

    yield backup_dir, uploads_dir

    # Cleanup
    shutil.rmtree(backup_dir, ignore_errors=True)
    shutil.rmtree(uploads_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_create_and_restore_success(backup_test_env):
    """Tests the full successful backup creation, dry-run validation, and restore sequence."""
    backup_dir, uploads_dir = backup_test_env

    # Verify pre-backup state of uploads
    test_file = uploads_dir / "thumbnail_1.png"
    assert test_file.read_text() == "original-thumbnail-bytes-data-123"

    # 1. Run Backup Creation
    backup_id = await create_backup()
    assert backup_id is not None
    assert backup_id.startswith("backup_")

    # Assert backup files exist in storage
    storage = get_storage()
    assert storage.exists(backup_id) is True

    manifest_bytes = storage.read_file(backup_id, "manifest.json")
    assert b"completed" in manifest_bytes

    # 2. Modify uploads to simulate data changes/corruption
    test_file.write_text("corrupted-or-modified-upload-file-content")
    assert test_file.read_text() == "corrupted-or-modified-upload-file-content"

    # 3. Perform Dry-run Restore (Preview validation)
    preview = await restore_backup(backup_id, dry_run=True)
    assert preview["backup_id"] == backup_id
    assert preview["checksum_ok"] is True
    assert preview["signature_ok"] is True

    # Upload file should NOT be restored yet in dry run
    assert test_file.read_text() == "corrupted-or-modified-upload-file-content"

    # 4. Perform Real Restore Swapping DB and Files
    restore_result = await restore_backup(backup_id, dry_run=False)
    assert restore_result["backup_id"] == backup_id

    # 5. Assert uploads file has been successfully restored
    assert test_file.read_text() == "original-thumbnail-bytes-data-123"

    # Ensure restore.log was created and populated
    log_path = Path("logs/restore.log")
    assert log_path.exists() is True
    log_content = log_path.read_text()
    assert "RESTORE TRANSACTION LOG STARTED" in log_content
    assert f"Restoring backup: {backup_id}" in log_content
    assert "RESTORE TRANSACTION LOG ENDED" in log_content


@pytest.mark.asyncio
async def test_restore_tampered_manifest_fails(backup_test_env):
    """Verify restore fails when the manifest file or signature has been tampered with."""
    backup_dir, uploads_dir = backup_test_env

    # 1. Create a backup
    backup_id = await create_backup()

    # 2. Tamper with the manifest file in storage
    storage = get_storage()
    manifest_bytes = storage.read_file(backup_id, "manifest.json")
    manifest_str = manifest_bytes.decode("utf-8")

    # Change status to something else
    tampered_manifest = manifest_str.replace('"status": "completed"', '"status": "failed"')
    storage.write_file(backup_id, "manifest.json", tampered_manifest.encode("utf-8"))

    # 3. Attempt restore - should raise verification failure
    with pytest.raises(ValueError, match="HMAC signature verification failed"):
        await restore_backup(backup_id)


@pytest.mark.asyncio
async def test_restore_tampered_payload_fails(backup_test_env):
    """Verify restore fails when payload checksum does not match checksum.sha256."""
    backup_dir, uploads_dir = backup_test_env

    # 1. Create a backup
    backup_id = await create_backup()

    # 2. Overwrite the encrypted payload file with corrupt bytes
    storage = get_storage()
    storage.write_file(backup_id, "backup.enc", b"invalid-corrupt-encrypted-payload-data")

    # 3. Attempt restore - should raise checksum validation failure
    with pytest.raises(ValueError, match="SHA-256 payload integrity check failed"):
        await restore_backup(backup_id)


@pytest.mark.asyncio
async def test_restore_db_import_failure_rollback(backup_test_env):
    """Verify atomic rollback of files and DB if DB import fails."""
    backup_dir, uploads_dir = backup_test_env

    # 1. Create a backup
    backup_id = await create_backup()

    # 2. Modify uploads pre-restore state
    test_file = uploads_dir / "thumbnail_1.png"
    test_file.write_text("pre-restore-current-assets-data")

    # 3. Force database import to fail by mocking _run_psql_import to raise an error
    with patch("app.backup.service._run_psql_import", side_effect=Exception("Database import fatal error")):
        with pytest.raises(Exception, match="Database import fatal error"):
            await restore_backup(backup_id)

    # 4. Verify rollback restored files to the pre-restore state
    assert test_file.read_text() == "pre-restore-current-assets-data"
