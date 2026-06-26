from app.backup.storage.base import BaseStorage
from app.backup.storage.local import LocalStorage
from app.core.config import settings


def get_storage() -> BaseStorage:
    """Factory resolver to get the configured backup storage backend."""
    backend_type = settings.BACKUP_STORAGE_BACKEND.lower()

    if backend_type == "local":
        return LocalStorage()
    else:
        raise ValueError(f"Unsupported backup storage backend: {settings.BACKUP_STORAGE_BACKEND}")
