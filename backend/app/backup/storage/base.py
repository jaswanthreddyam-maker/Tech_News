from abc import ABC, abstractmethod


class BaseStorage(ABC):
    @abstractmethod
    def write_file(self, backup_id: str, filename: str, data: bytes) -> str:
        """Write data to a file inside the backup folder. Returns the path or reference."""
        pass

    @abstractmethod
    def read_file(self, backup_id: str, filename: str) -> bytes:
        """Read data from a file inside the backup folder."""
        pass

    @abstractmethod
    def list_backups(self) -> list[str]:
        """List all backup IDs."""
        pass

    @abstractmethod
    def delete_backup(self, backup_id: str) -> None:
        """Delete all files associated with a backup ID."""
        pass

    @abstractmethod
    def exists(self, backup_id: str) -> bool:
        """Check if a backup ID exists."""
        pass
