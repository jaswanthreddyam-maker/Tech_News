import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from app.backup.checksum import verify_sha256
from app.backup.encryption import decrypt_payload, verify_manifest_signature
from app.backup.manifest import parse_manifest
from app.backup.service import create_backup, restore_backup
from app.backup.storage import get_storage


def handle_create(args):
    """Command handler for creating a new backup."""
    print("Initiating backup creation...")
    try:
        backup_id = asyncio.run(create_backup())
        print(f"\n[SUCCESS] Backup successfully created. Backup ID: {backup_id}")
    except Exception as e:
        print(f"\n[ERROR] Backup creation failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_list(args):
    """Command handler for listing available backups."""
    print("Fetching available backups...")
    try:
        storage = get_storage()
        backup_ids = storage.list_backups()

        if not backup_ids:
            print("No backups found.")
            return

        print(
            f"{'Backup ID':<38} | {'Created At':<24} | {'Status':<10} | {'DB Rows':<8} | {'Assets (Files)':<14} | {'Size (MB)':<9}"
        )
        print("-" * 115)

        for bid in backup_ids:
            try:
                manifest_bytes = storage.read_file(bid, "manifest.json")
                manifest = parse_manifest(manifest_bytes.decode("utf-8"))

                # Filter out failed backups if requested (or default behavior)
                if manifest.get("status") != "completed" and not args.all:
                    continue

                created_at = manifest.get("created_at", "Unknown")
                status = manifest.get("status", "Unknown")
                metrics = manifest.get("metrics", {})
                db_rows = metrics.get("database", {}).get("rows", 0)
                assets_files = metrics.get("storage", {}).get("files", 0)
                size_bytes = manifest.get("payload_size_bytes", 0)
                size_mb = round(size_bytes / (1024 * 1024), 2)

                print(
                    f"{bid:<38} | {created_at[:22]:<24} | {status:<10} | {db_rows:<8} | {assets_files:<14} | {size_mb:<9}"
                )
            except Exception as ex:
                if args.all:
                    print(
                        f"{bid:<38} | {'Corrupted Manifest':<24} | {'corrupt':<10} | {'N/A':<8} | {'N/A':<14} | {'N/A':<9}"
                    )
    except Exception as e:
        print(f"[ERROR] Failed to list backups: {e}", file=sys.stderr)
        sys.exit(1)


def handle_verify(args):
    """Command handler for verifying backup integrity."""
    backup_id = args.backup_id
    print(f"Starting integrity verification for backup: {backup_id}\n")

    try:
        storage = get_storage()
        if not storage.exists(backup_id):
            print(f"[FAIL] Backup ID does not exist: {backup_id}")
            sys.exit(1)

        # 1. Read files
        manifest_bytes = storage.read_file(backup_id, "manifest.json")
        manifest_sig_bytes = storage.read_file(backup_id, "manifest.sig")
        checksum_bytes = storage.read_file(backup_id, "checksum.sha256")
        payload_bytes = storage.read_file(backup_id, "backup.enc")

        manifest_content = manifest_bytes.decode("utf-8")
        expected_sig = manifest_sig_bytes.decode("utf-8").strip()
        expected_checksum = checksum_bytes.decode("utf-8").strip()

        # 2. Verify Signature
        sig_ok = verify_manifest_signature(manifest_content, expected_sig)
        sig_status = "[PASS]" if sig_ok else "[FAIL]"
        print(f"{sig_status} Manifest HMAC signature validation.")

        # Parse manifest for verification
        manifest = parse_manifest(manifest_content)

        # 3. Verify Checksum
        # Write to temp file for calculate_sha256
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(payload_bytes)
            temp_path = Path(tf.name)

        try:
            checksum_ok = verify_sha256(temp_path, expected_checksum)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        checksum_status = "[PASS]" if checksum_ok else "[FAIL]"
        print(f"{checksum_status} Payload SHA-256 integrity check.")

        # 4. Decrypt capability test
        try:
            decrypted = decrypt_payload(payload_bytes)
            decrypt_ok = len(decrypted) > 0
        except Exception:
            decrypt_ok = False

        decrypt_status = "[PASS]" if decrypt_ok else "[FAIL]"
        print(f"{decrypt_status} Payload AES-256-GCM decryption check.")

        # 5. Manifest Status Check
        status_ok = manifest.get("status") == "completed"
        status_status = "[PASS]" if status_ok else "[FAIL]"
        print(f"{status_status} Backup completion state check.")

        if sig_ok and checksum_ok and decrypt_ok and status_ok:
            print("\n[SUCCESS] Backup integrity fully verified. All validation gates passed.")
        else:
            print(
                "\n[CRITICAL] Backup verification failed! Corrupted or compromised backup files detected.",
                file=sys.stderr,
            )
            sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR] Verification aborted due to error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_restore(args):
    """Command handler for restoring from a backup."""
    backup_id = args.backup_id

    if args.dry_run:
        print(f"Starting dry-run validation for backup restore: {backup_id}...")
        try:
            preview = asyncio.run(restore_backup(backup_id, dry_run=True))
            print("\n=== DRY-RUN PREVIEW METADATA ===")
            print(f"Backup ID:          {preview['backup_id']}")
            print(f"Created At:         {preview['created_at']}")
            print(f"App Version:        {preview['app_version']}")
            print(f"Schema Version:     {preview['schema_version']}")
            print(f"Payload Size:       {preview['payload_size_bytes']} bytes")
            print("Database Metrics:")
            print(f"  - Tables:         {preview['metrics'].get('database', {}).get('tables', 0)}")
            print(f"  - Rows:           {preview['metrics'].get('database', {}).get('rows', 0)}")
            print("Assets Metrics:")
            print(f"  - Files:          {preview['metrics'].get('storage', {}).get('files', 0)}")
            print(f"  - Bytes:          {preview['metrics'].get('storage', {}).get('bytes', 0)}")
            print("[PASS] Dry-run preview verification completed. Integrity and decrypt check passed.")
        except Exception as e:
            print(f"\n[ERROR] Dry-run restore check failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Normal restore flow
    if not args.yes:
        confirm = input(
            f"WARNING: This will overwrite the database and thumbnails folders. Are you sure you want to restore backup {backup_id}? [y/N]: "
        )
        if confirm.lower() not in ("y", "yes"):
            print("Restore operation aborted by user.")
            return

    print(f"Initiating full transactional restore from backup: {backup_id}...")
    try:
        asyncio.run(restore_backup(backup_id, dry_run=False))
        print("\n[SUCCESS] Transactional restore completed successfully. Maintenance mode disabled.")
    except Exception as e:
        print(f"\n[CRITICAL] Restore execution failed: {e}. Check logs/restore.log for details.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Tech News Today - Backup & Disaster Recovery CLI", prog="python -m app.cli.backup"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

    # create subcommand
    subparsers.add_parser("create", help="Create a secure, encrypted backup package of current state.")

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List available backup packages.")
    list_parser.add_argument("--all", action="store_true", help="Include failed and diagnostic backups.")

    # verify subcommand
    verify_parser = subparsers.add_parser("verify", help="Verify integrity of an existing backup package.")
    verify_parser.add_argument("backup_id", type=str, help="The unique backup ID to verify.")

    # restore subcommand
    restore_parser = subparsers.add_parser("restore", help="Restore the system state from a backup package.")
    restore_parser.add_argument("backup_id", type=str, help="The unique backup ID to restore.")
    restore_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform verification and preview metadata without swapping databases/directories.",
    )
    restore_parser.add_argument(
        "-y", "--yes", action="store_true", help="Confirm execution without interactive warning prompt."
    )

    args = parser.parse_args()

    if args.command == "create":
        handle_create(args)
    elif args.command == "list":
        handle_list(args)
    elif args.command == "verify":
        handle_verify(args)
    elif args.command == "restore":
        handle_restore(args)


if __name__ == "__main__":
    main()
