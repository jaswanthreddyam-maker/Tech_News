import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backup.service import create_backup


async def main():
    print("Triggering backup...")
    try:
        backup_id = await create_backup()
        print(f"Backup created successfully: {backup_id}")
    except Exception as e:
        print(f"Error creating backup: {e}")


if __name__ == "__main__":
    asyncio.run(main())
