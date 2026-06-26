import json
from typing import Any

REQUIRED_FIELDS = [
    "manifest_version",
    "backup_format",
    "backup_tool_version",
    "backup_id",
    "created_at",
    "status",
    "app_version",
    "schema_version",
    "compression",
    "encryption",
    "key_id",
    "metrics",
    "payload_size_bytes",
    "checksum_sha256",
]


def validate_manifest_dict(manifest: dict[str, Any]) -> None:
    """Validate that manifest contains all required keys and correct versions."""
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            raise ValueError(f"Missing required manifest field: {field}")

    if manifest["manifest_version"] != 1:
        raise ValueError(f"Unsupported manifest_version: {manifest['manifest_version']}")

    if manifest["backup_format"] != 1:
        raise ValueError(f"Unsupported backup_format: {manifest['backup_format']}")


def parse_manifest(content: str) -> dict[str, Any]:
    """Parse JSON manifest text and validate its schema."""
    try:
        manifest = json.loads(content)
    except Exception as e:
        raise ValueError(f"Invalid JSON in manifest: {e}")

    validate_manifest_dict(manifest)
    return manifest


def format_manifest(manifest: dict[str, Any]) -> str:
    """Format manifest dictionary as a clean pretty-printed JSON string."""
    return json.dumps(manifest, indent=2, sort_keys=True)
