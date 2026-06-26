import datetime
import os
import shutil
from pathlib import Path

from app.backup.storage.base import BaseStorage
from app.core.config import settings


class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.BACKUP_STORAGE_PATH)

    def _get_backup_dir(self, backup_id: str) -> Path:
        # Expected backup_id format: backup_YYYYMMDDTHHMMSSZ_XXXXXX
        # Extract YYYY/MM from the ID if possible
        parts = backup_id.split("_")
        if len(parts) >= 2 and len(parts[1]) >= 6:
            year = parts[1][:4]
            month = parts[1][4:6]
        else:
            now = datetime.datetime.now(datetime.timezone.utc)
            year = now.strftime("%Y")
            month = now.strftime("%m")
        return self.base_dir / year / month / backup_id

    def write_file(self, backup_id: str, filename: str, data: bytes) -> str:
        backup_dir = self._get_backup_dir(backup_id)
        backup_dir.mkdir(parents=True, exist_ok=True)
        file_path = backup_dir / filename
        file_path.write_bytes(data)
        return str(file_path.resolve())

    def read_file(self, backup_id: str, filename: str) -> bytes:
        backup_dir = self._get_backup_dir(backup_id)
        file_path = backup_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Backup file not found: {file_path}")
        return file_path.read_bytes()

    def list_backups(self) -> list[str]:
        """List all backup IDs by walking the base directory."""
        if not self.base_dir.exists():
            return []

        backup_ids = []
        # Walk directory looking for folders matching backup_ pattern
        for root, dirs, files in os.walk(str(self.base_dir)):
            for d in dirs:
                if d.startswith("backup_"):
                    # We check if manifest.json exists in this folder to verify it is a backup directory
                    manifest_path = Path(root) / d / "manifest.json"
                    if manifest_path.exists():
                        backup_ids.append(d)

        # Sort by creation time (parsed from backup_id timestamp)
        # backup_YYYYMMDDTHHMMSSZ_XXXXXX
        # Splitting and sorting by the middle timestamp part
        def sort_key(bid):
            parts = bid.split("_")
            if len(parts) >= 2:
                return parts[1]
            return bid

        return sorted(backup_ids, key=sort_key)

    def delete_backup(self, backup_id: str) -> None:
        backup_dir = self._get_backup_dir(backup_id)
        if backup_dir.exists() and backup_dir.is_dir():
            shutil.rmtree(backup_dir)
            # Optionally clean up parent directories (year/month) if they are empty
            month_dir = backup_dir.parent
            if month_dir.exists() and not os.listdir(month_dir):
                month_dir.rmdir()
                year_dir = month_dir.parent
                if year_dir.exists() and not os.listdir(year_dir):
                    year_dir.rmdir()

    def exists(self, backup_id: str) -> bool:
        backup_dir = self._get_backup_dir(backup_id)
        manifest_path = backup_dir / "manifest.json"
        return manifest_path.exists()
