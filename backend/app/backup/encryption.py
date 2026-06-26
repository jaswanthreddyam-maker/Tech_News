import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _load_key(key_str: str) -> bytes:
    """Load a 32-byte key from string. Try base64 decoding first, fallback to SHA-256 hash."""
    try:
        decoded = base64.b64decode(key_str)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    # Fallback: Hash the key to get a deterministic 32-byte key
    return hashlib.sha256(key_str.encode("utf-8")).digest()


def get_encryption_key() -> bytes:
    """Retrieve the base64-decoded 32-byte encryption key."""
    return _load_key(settings.BACKUP_ENCRYPTION_KEY)


def get_signing_key() -> bytes:
    """Retrieve the base64-decoded 32-byte signing key."""
    return _load_key(settings.BACKUP_SIGNING_KEY)


def encrypt_payload(data: bytes) -> bytes:
    """Encrypt binary data using AES-256-GCM. Returns nonce + ciphertext + tag."""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    # AEAD encrypt automatically appends the 16-byte authentication tag
    encrypted_data = aesgcm.encrypt(nonce, data, None)
    return nonce + encrypted_data


def decrypt_payload(payload: bytes) -> bytes:
    """Decrypt payload using AES-256-GCM. Expects nonce + ciphertext + tag."""
    if len(payload) < 28:  # 12 bytes nonce + 16 bytes tag + at least 0 bytes ciphertext
        raise ValueError("Invalid encrypted payload size.")

    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = payload[:12]
    encrypted_data = payload[12:]
    return aesgcm.decrypt(nonce, encrypted_data, None)


def sign_manifest(manifest_content: str) -> str:
    """Compute HMAC-SHA256 signature over manifest text content."""
    key = get_signing_key()
    h = hmac.new(key, manifest_content.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def verify_manifest_signature(manifest_content: str, expected_sig: str) -> bool:
    """Verify manifest content matches expected signature using secure compare_digest."""
    actual_sig = sign_manifest(manifest_content)
    return hmac.compare_digest(actual_sig.lower(), expected_sig.lower())
