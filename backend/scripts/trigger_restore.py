import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backup.service import restore_backup


async def main():
    backup_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not backup_id:
        print("Usage: python trigger_restore.py <backup_id>")
        sys.exit(1)

    print(f"Triggering restore for backup: {backup_id}...")
    try:
        preview = await restore_backup(backup_id, dry_run=False)
        print("Restore completed successfully.")
    except Exception as e:
        print(f"Error restoring backup: {e}")


if __name__ == "__main__":
    asyncio.run(main())
