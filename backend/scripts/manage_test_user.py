import asyncio
import sys

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password

# Import all models to register metadata
from app.models.user import (
    Role,
    User,
)


async def create_user(email: str, password: str, role_name: str):
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalars().first()

        # Find role
        role_res = await db.execute(select(Role).where(Role.name == role_name))
        role = role_res.scalars().first()
        if not role:
            print(f"Error: Role '{role_name}' not found.", file=sys.stderr)
            sys.exit(1)

        hashed_pw = hash_password(password)
        if user:
            user.password_hash = hashed_pw
            user.role_id = role.id
            user.status = "active"
            print(f"Updated existing user: {email}")
        else:
            new_user = User(
                name="Test Admin User", email=email, password_hash=hashed_pw, role_id=role.id, status="active"
            )
            db.add(new_user)
            print(f"Created new user: {email}")
        await db.commit()


async def delete_user(email: str):
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == email))
        await db.commit()
        print(f"Deleted user: {email}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python manage_test_user.py [create|delete] [email] [password] [role]", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    email = sys.argv[2]

    if action in ("create", "ensure"):
        if len(sys.argv) < 5:
            print(
                "Usage for create/ensure: python manage_test_user.py create|ensure [email] [password] [role]",
                file=sys.stderr,
            )
            sys.exit(1)
        password = sys.argv[3]
        role = sys.argv[4]
        asyncio.run(create_user(email, password, role))
    elif action == "delete":
        asyncio.run(delete_user(email))
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
