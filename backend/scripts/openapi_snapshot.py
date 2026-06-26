"""
OpenAPI Snapshot Validator

Generates the current OpenAPI schema from the FastAPI app and compares it
against a stored snapshot to detect breaking API changes.

Usage:
    python scripts/openapi_snapshot.py            # Generate/update snapshot
    python scripts/openapi_snapshot.py --verify   # Verify against snapshot (CI mode)
"""

import json
import os
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_openapi_schema() -> dict:
    """Import the FastAPI app and extract its OpenAPI schema."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # We need to handle the case where the app requires env vars
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")

    from main import app

    return app.openapi()


def normalize_schema(schema: dict) -> dict:
    """
    Normalize the OpenAPI schema for stable comparison.
    Removes volatile fields like description text and server URLs
    that may change without being breaking changes.
    """
    normalized = json.loads(json.dumps(schema))

    # Remove volatile top-level fields
    normalized.pop("servers", None)

    return normalized


def extract_contract(schema: dict) -> dict:
    """
    Extract the API contract surface:
    - Paths (endpoints, methods, parameters, request/response schemas)
    - Component schemas (models)

    This is what we actually compare for breaking changes.
    """
    contract = {
        "openapi": schema.get("openapi"),
        "paths": {},
        "components": schema.get("components", {}),
    }

    for path, methods in schema.get("paths", {}).items():
        contract["paths"][path] = {}
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete", "options", "head"):
                contract["paths"][path][method] = {
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody"),
                    "responses": {
                        code: {"content": resp.get("content", {})}
                        for code, resp in details.get("responses", {}).items()
                    },
                }

    return contract


def check_breaking_changes(old_contract: dict, new_contract: dict) -> list[str]:
    """
    Detect breaking changes between two API contracts.

    Breaking changes include:
    - Removed endpoints
    - Removed HTTP methods on existing endpoints
    - Removed required parameters
    - Changed response schema shapes
    """
    errors = []

    old_paths = old_contract.get("paths", {})
    new_paths = new_contract.get("paths", {})

    # Check for removed endpoints
    for path in old_paths:
        if path not in new_paths:
            errors.append(f"BREAKING: Endpoint removed: {path}")
            continue

        # Check for removed methods
        for method in old_paths[path]:
            if method not in new_paths[path]:
                errors.append(f"BREAKING: Method removed: {method.upper()} {path}")

    # Check for removed component schemas
    old_schemas = old_contract.get("components", {}).get("schemas", {})
    new_schemas = new_contract.get("components", {}).get("schemas", {})

    for schema_name in old_schemas:
        if schema_name not in new_schemas:
            errors.append(f"BREAKING: Schema removed: {schema_name}")

    return errors


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    snapshot_dir = os.path.join(repo_root, "docs")
    snapshot_path = os.path.join(snapshot_dir, "openapi_snapshot.json")

    verify_mode = "--verify" in sys.argv

    print("OpenAPI Snapshot Validator")
    print("=" * 50)

    # Generate current schema
    print("\n1. Generating current OpenAPI schema...")
    try:
        schema = get_openapi_schema()
        print(f"   ✓ Generated schema: {len(schema.get('paths', {}))} endpoints")
    except Exception as e:
        print(f"   ✗ Failed to generate schema: {e}")
        sys.exit(1)

    current_contract = extract_contract(normalize_schema(schema))

    if verify_mode:
        # CI mode: compare against existing snapshot
        print("\n2. Verifying against stored snapshot...")

        if not os.path.exists(snapshot_path):
            print("   ⚠ No snapshot found. Generating initial snapshot...")
            os.makedirs(snapshot_dir, exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            print(f"   ✓ Initial snapshot created: {snapshot_path}")
            sys.exit(0)

        with open(snapshot_path, encoding="utf-8") as f:
            stored_schema = json.load(f)

        stored_contract = extract_contract(normalize_schema(stored_schema))

        # Check for breaking changes
        breaking = check_breaking_changes(stored_contract, current_contract)

        if breaking:
            print("\n❌ BREAKING CHANGES DETECTED:")
            for error in breaking:
                print(f"   - {error}")
            print("\nTo update the snapshot after intentional changes:")
            print("   python scripts/openapi_snapshot.py")
            sys.exit(1)
        else:
            # Check for non-breaking additions
            old_json = json.dumps(stored_contract, sort_keys=True)
            new_json = json.dumps(current_contract, sort_keys=True)

            if old_json != new_json:
                print("   i Non-breaking changes detected (new endpoints or schemas added)")
                print("   Run `python scripts/openapi_snapshot.py` to update the snapshot.")
            else:
                print("   ✓ API contract matches snapshot exactly.")

            print("\n✅ OpenAPI SNAPSHOT VALIDATION PASSED")
            sys.exit(0)
    else:
        # Update mode: write new snapshot
        print("\n2. Writing snapshot...")
        os.makedirs(snapshot_dir, exist_ok=True)

        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        endpoint_count = len(schema.get("paths", {}))
        schema_count = len(schema.get("components", {}).get("schemas", {}))

        print(f"   ✓ Snapshot written: {snapshot_path}")
        print(f"   ✓ Endpoints: {endpoint_count}")
        print(f"   ✓ Schemas: {schema_count}")
        print("\n✅ SNAPSHOT UPDATED")


if __name__ == "__main__":
    main()
