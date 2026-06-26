# Cryptographic Key Rotation Runbook

This document defines the policies and step-by-step procedures for rotating the platform's backup encryption and signing keys.

---

## 1. Key Separation Policy

To enforce robust security practices, the system uses two separate secrets defined in the environment:
1. `BACKUP_ENCRYPTION_KEY`: A 32-byte key (Base64-encoded) used for payload encryption (AES-256-GCM).
2. `BACKUP_SIGNING_KEY`: A 32-byte key (Base64-encoded) used for manifest signature verification (HMAC-SHA256).

---

## 2. Generating New Keys

Generate strong 32-byte (256-bit) cryptographically secure random keys and encode them to Base64:

```bash
# Generate Encryption Key
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Generate Signing Key
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

---

## 3. Rotating the Signing Key (`BACKUP_SIGNING_KEY`)

Since the signing key is only used to verify manifest contents, rotating it does not require modifying the encrypted payload. However, existing signatures (`manifest.sig`) on disk will fail verification if the key is updated without resigns.

### Rotation Procedure
1. **Prepare the New Key**: Generate a new base64 key string.
2. **Resign Existing Manifests**:
   Run a script to load manifests and rewrite `.sig` files with the new key.
   ```python
   # Example resign snippet:
   import hmac, hashlib
   from app.backup.storage import get_storage
   
   storage = get_storage()
   new_key = b"..." # decoded new key
   
   for bid in storage.list_backups():
       manifest = storage.read_file(bid, "manifest.json").decode("utf-8")
       h = hmac.new(new_key, manifest.encode("utf-8"), hashlib.sha256)
       storage.write_file(bid, "manifest.sig", h.hexdigest().encode("utf-8"))
   ```
3. **Update Environment**: Replace `BACKUP_SIGNING_KEY` value in production `.env` files.
4. **Restart Services**: Restart the backend, workers, and beat.

---

## 4. Rotating the Encryption Key (`BACKUP_ENCRYPTION_KEY`)

Rotating the encryption key requires decrypting old backups and re-encrypting them with the new key if you wish to keep historical backups accessible.

### Rotation Procedure
1. **Keep Old Key Accessible**: Record the current `BACKUP_ENCRYPTION_KEY` value (Old Key).
2. **Generate New Key**: Generate the new key (New Key).
3. **Execute Re-encryption Script**:
   Write a migration script that loads each package, decrypts with the old key, and re-encrypts with the new key:
   ```python
   # Example re-encryption migration snippet:
   from app.backup.storage import get_storage
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   import os
   
   storage = get_storage()
   old_aes = AESGCM(old_key_bytes)
   new_aes = AESGCM(new_key_bytes)
   
   for bid in storage.list_backups():
       # Read old payload
       payload = storage.read_file(bid, "backup.enc")
       nonce = payload[:12]
       ciphertext = payload[12:]
       
       # Decrypt
       decrypted = old_aes.decrypt(nonce, ciphertext, None)
       
       # Re-encrypt
       new_nonce = os.urandom(12)
       new_payload = new_nonce + new_aes.encrypt(new_nonce, decrypted, None)
       
       # Save back
       storage.write_file(bid, "backup.enc", new_payload)
   ```
4. **Update Manifest Checksums**:
   Since the payload bytes changed, calculate the new SHA-256 checksum, update `checksum.sha256`, update `manifest.json`, and resign.
5. **Update Environment**: Update `BACKUP_ENCRYPTION_KEY` in `.env`.
6. **Restart Services**.
