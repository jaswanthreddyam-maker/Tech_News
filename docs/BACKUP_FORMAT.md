# Backup Archive & Directory Format Specification

This document details the on-disk storage layout, cryptographic structure, and metadata manifest schema of the backup packages.

---

## 1. Directory Structure

Backups are structured in folders grouped by year and month to prevent directories from containing too many files.

```
storage/backups/
└── YYYY/
    └── MM/
        └── backup_YYYYMMDDTHHMMSSZ_XXXXXX/    # Unique Backup ID
            ├── backup.enc                      # Encrypted payload (tarball)
            ├── manifest.json                   # Unencrypted metadata manifest
            ├── manifest.sig                    # HMAC-SHA256 signature of manifest.json
            └── checksum.sha256                 # Plain SHA-256 hash of backup.enc
```

---

## 2. Encrypted Payload (`backup.enc`)

The payload contains the compressed database dump and Dynamic static upload assets. To protect confidentiality and authenticity, it is encrypted using **AES-256-GCM**.

### Binary Layout
The `backup.enc` byte stream is structured sequentially:

```
+-------------------+--------------------------------+-----------------------------+
| Nonce (12 bytes)  |      Ciphertext (Variable)     |  Auth Tag (16 bytes)        |
+-------------------+--------------------------------+-----------------------------+
```

1. **Nonce (12 bytes)**: Cryptographically secure random bytes generated uniquely per backup to prevent replay attacks.
2. **Ciphertext (Variable size)**: Gzip-compressed tarball package (`archive.tar.gz`).
3. **Authentication Tag (16 bytes)**: The GCM authenticity tag appended automatically by the AEAD cipher during encryption.

### Unencrypted Tarball Archive Structure
When decrypted, the tarball contains the following structure:
```
archive.tar.gz
├── database.sql        # Standard PostgreSQL plain SQL text dump
└── assets/            # Static media uploads directory (e.g. thumbnails)
```

---

## 3. Metadata Manifest (`manifest.json`)

The manifest file is stored in cleartext JSON to allow administrators and monitoring tools to inspect backup details without requiring decryption keys. To prevent tampering, a matching `.sig` file is generated containing its HMAC signature.

### Schema Specification
```json
{
  "manifest_version": 1,
  "backup_format": 1,
  "backup_tool_version": "1.0.0",
  "backup_id": "backup_20260610T020000Z_3fa9b1",
  "created_at": "2026-06-10T02:00:00Z",
  "status": "completed",
  "app_version": "0.10.0-beta",
  "schema_version": "1.0",
  "compression": "gzip",
  "encryption": "AES-256-GCM",
  "key_id": "default",
  "metrics": {
    "database": {
      "tables": 18,
      "rows": 16542
    },
    "storage": {
      "files": 45,
      "bytes": 73492
    }
  },
  "payload_size_bytes": 1048576,
  "checksum_sha256": "8f42a1bfd672...3fca"
}
```

### Fields Description
- `manifest_version`: Version of this manifest format (currently `1`).
- `backup_format`: Version of the payload layout (currently `1`).
- `backup_tool_version`: Version of the backup software tool.
- `backup_id`: Unique identifier string formatted as `backup_YYYYMMDDTHHMMSSZ_XXXXXX`.
- `created_at`: UTC ISO-8601 timestamp when the backup was initialized.
- `status`: Execution state: `creating`, `archiving`, `compressing`, `encrypting`, `signing`, `verifying`, `completed`, or `failed`.
- `app_version`: The software platform version when the backup was created.
- `schema_version`: Active DB database schema migration revision.
- `compression`: Compression algorithm used (e.g., `gzip`).
- `encryption`: Cryptographic algorithm used (e.g., `AES-256-GCM`).
- `key_id`: Identifier of the encryption key used (supports rotation).
- `metrics.database`: Table count and row count metrics.
- `metrics.storage`: Dynamic files count and raw bytes count.
- `payload_size_bytes`: Raw byte size of the encrypted `backup.enc` file.
- `checksum_sha256`: Plain SHA-256 hexadecimal hash of the encrypted payload.
