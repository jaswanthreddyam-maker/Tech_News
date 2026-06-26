import hashlib
from pathlib import Path


def calculate_sha256(filepath: Path) -> str:
    """Calculate the SHA-256 digest of a file by reading it in chunks."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in chunks of 65536 bytes
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_sha256(filepath: Path, expected_sha: str) -> bool:
    """Verify that a file matches the expected SHA-256 digest."""
    actual_sha = calculate_sha256(filepath)
    return actual_sha.lower() == expected_sha.lower()
