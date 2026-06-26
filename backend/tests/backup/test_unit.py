import pytest

from app.backup.archive import GzipCompression, get_compression
from app.backup.encryption import (
    decrypt_payload,
    encrypt_payload,
    get_encryption_key,
    get_signing_key,
    sign_manifest,
    verify_manifest_signature,
)
from app.backup.manifest import format_manifest, parse_manifest, validate_manifest_dict
from app.backup.retention import get_gfs_retention, parse_backup_date
from app.backup.storage.local import LocalStorage
from app.backup.storage.service import get_storage


def test_key_separation():
    """Assert that encryption and signing keys are derived/loaded differently and are not identical."""
    enc_key = get_encryption_key()
    sig_key = get_signing_key()

    assert len(enc_key) == 32
    assert len(sig_key) == 32
    # Ensure they are not the same key
    assert enc_key != sig_key


def test_payload_gcm_encryption():
    """Verify AES-256-GCM encryption/decryption, payload structure, and corruption resilience."""
    secret_data = b"Hello, Tech News! This is a secret backup payload."

    # Encrypt
    encrypted = encrypt_payload(secret_data)

    # Structure: 12 bytes nonce + ciphertext + 16 bytes tag
    # Minimum size: 12 (nonce) + len(secret_data) + 16 (tag)
    assert len(encrypted) == 12 + len(secret_data) + 16

    # Decrypt
    decrypted = decrypt_payload(encrypted)
    assert decrypted == secret_data

    # Test failure on too short payload
    with pytest.raises(ValueError, match="Invalid encrypted payload size"):
        decrypt_payload(b"short_payload")

    # Test decryption failure on tampered data
    tampered = bytearray(encrypted)
    tampered[-1] ^= 0x01  # Flip a bit in the authentication tag
    from cryptography.exceptions import InvalidTag

    with pytest.raises(InvalidTag):
        decrypt_payload(bytes(tampered))


def test_manifest_signature():
    """Test HMAC-SHA256 signature generation, validation, and tamper detection."""
    manifest_content = '{"backup_id": "backup_123", "status": "completed"}'

    sig = sign_manifest(manifest_content)
    assert len(sig) == 64  # SHA-256 hex digest is 64 chars

    # Valid verification
    assert verify_manifest_signature(manifest_content, sig) is True

    # Tampered manifest content
    tampered_content = '{"backup_id": "backup_123", "status": "failed"}'
    assert verify_manifest_signature(tampered_content, sig) is False

    # Tampered signature
    tampered_sig = sig[:-1] + "0" if sig[-1] != "0" else sig[:-1] + "1"
    assert verify_manifest_signature(manifest_content, tampered_sig) is False


def test_gfs_retention_logic():
    """Verify the Grandfather-Father-Son retention filtering logic."""
    # Build list of daily backups stretching across weeks/months
    # backup_id format: backup_YYYYMMDDTHHMMSSZ_XXXXXX
    backup_ids = [
        "backup_20260610T020000Z_abcdef",  # Today
        "backup_20260609T020000Z_abcdef",  # Yesterday
        "backup_20260608T020000Z_abcdef",  # 2 days ago
        "backup_20260607T020000Z_abcdef",  # 3 days ago
        "backup_20260606T020000Z_abcdef",  # 4 days ago
        "backup_20260605T020000Z_abcdef",  # 5 days ago
        "backup_20260604T020000Z_abcdef",  # 6 days ago
        "backup_20260603T020000Z_abcdef",  # 7 days ago
        "backup_20260527T020000Z_abcdef",  # 2 weeks ago (weekly)
        "backup_20260520T020000Z_abcdef",  # 3 weeks ago (weekly)
        "backup_20260513T020000Z_abcdef",  # 4 weeks ago (weekly)
        "backup_20260506T020000Z_abcdef",  # 5 weeks ago (should delete or monthly)
        "backup_20260401T020000Z_abcdef",  # April (monthly)
        "backup_20260301T020000Z_abcdef",  # March (monthly)
        "backup_20250601T020000Z_abcdef",  # June last year (monthly)
    ]

    keep, delete = get_gfs_retention(backup_ids)

    # Assert today (newest) is kept
    assert "backup_20260610T020000Z_abcdef" in keep

    # Total daily kept should be up to 7
    # Total weekly kept should be up to 4
    # Total monthly kept should be up to 12
    # Verify that backups are correctly distributed
    assert len(keep) > 0
    assert len(delete) > 0

    # No duplicate keeping of the same backup ID
    assert len(keep) == len(set(keep))

    # Verify parse_backup_date helper
    parsed_date = parse_backup_date("backup_20260610T020000Z_abcdef")
    assert parsed_date is not None
    assert parsed_date.year == 2026
    assert parsed_date.month == 6
    assert parsed_date.day == 10

    assert parse_backup_date("invalid_format") is None


def test_pluggable_storage_and_compression_resolvers(monkeypatch):
    """Test resolution factory functions for storage and compression."""
    # Storage
    storage = get_storage()
    assert isinstance(storage, LocalStorage)

    # Compression
    compression = get_compression("gzip")
    assert isinstance(compression, GzipCompression)

    with pytest.raises(ValueError, match="Unsupported backup compression algorithm"):
        get_compression("lzma")


def test_manifest_validation():
    """Verify manifest parsing, formatting, and schema validation."""
    valid_manifest = {
        "manifest_version": 1,
        "backup_format": 1,
        "backup_tool_version": "1.0.0",
        "backup_id": "backup_20260610T020000Z_abcdef",
        "created_at": "2026-06-10T02:00:00Z",
        "status": "completed",
        "app_version": "0.10.0-beta",
        "schema_version": "1.0",
        "compression": "gzip",
        "encryption": "AES-256-GCM",
        "key_id": "default",
        "metrics": {"database": {"tables": 10, "rows": 100}, "storage": {"files": 5, "bytes": 1000}},
        "payload_size_bytes": 1048576,
        "checksum_sha256": "abc123sha256",
    }

    # Verify formatting to json string and parsing back
    formatted = format_manifest(valid_manifest)
    parsed = parse_manifest(formatted)

    assert parsed["backup_id"] == valid_manifest["backup_id"]
    assert parsed["metrics"]["database"]["rows"] == 100

    # Missing required field
    invalid_manifest = valid_manifest.copy()
    del invalid_manifest["checksum_sha256"]
    with pytest.raises(ValueError, match="Missing required manifest field: checksum_sha256"):
        validate_manifest_dict(invalid_manifest)

    # Invalid versions
    invalid_version_manifest = valid_manifest.copy()
    invalid_version_manifest["manifest_version"] = 2
    with pytest.raises(ValueError, match="Unsupported manifest_version"):
        validate_manifest_dict(invalid_version_manifest)
