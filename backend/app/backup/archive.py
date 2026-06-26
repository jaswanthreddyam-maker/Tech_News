import tarfile
from abc import ABC, abstractmethod
from pathlib import Path


class BaseCompression(ABC):
    @abstractmethod
    def compress(self, source_paths: dict[str, Path], output_archive_path: Path) -> None:
        """
        Compresses files/directories in source_paths into output_archive_path.
        source_paths is a dict mapping archive-relative path to actual filesystem Path.
        """
        pass

    @abstractmethod
    def extract(self, archive_path: Path, target_dir: Path) -> None:
        """Extracts the archive to target_dir."""
        pass


class GzipCompression(BaseCompression):
    def compress(self, source_paths: dict[str, Path], output_archive_path: Path) -> None:
        with tarfile.open(output_archive_path, "w:gz") as tar:
            for arcname, filepath in source_paths.items():
                if filepath.exists():
                    tar.add(filepath, arcname=arcname)
                else:
                    raise FileNotFoundError(f"Source file/folder not found: {filepath}")

    def extract(self, archive_path: Path, target_dir: Path) -> None:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=target_dir)


def get_compression(algorithm: str) -> BaseCompression:
    """Retrieve compression interface based on settings configuration."""
    algo = algorithm.lower()
    if algo == "gzip":
        return GzipCompression()
    else:
        raise ValueError(f"Unsupported backup compression algorithm: {algorithm}")
