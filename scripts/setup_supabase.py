"""Supabase Database Setup & Migration Script for Tech News Today.

This script:
1. Connects to the new Supabase PostgreSQL database.
2. Enables the `vector` (pgvector) extension.
3. Applies all Alembic migrations (`alembic upgrade head`).
4. Seeds default roles, permissions, categories, sources, feature flags, and initial admin (`app.core.init_db`).
5. Optionally seeds live news from RSS feeds (`seed_and_ingest_live`).
6. Updates `.env` and `backend/.env` with the new connection details.
"""

import argparse
import asyncio
import io
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import asyncpg


def parse_db_url(url: str):
    """Normalize SQLAlchemy or PostgreSQL connection string for asyncpg and alembic."""
    clean_url = url.strip().strip("'\"")
    parse_target = clean_url
    if parse_target.startswith("postgresql+asyncpg://"):
        parse_target = parse_target.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif parse_target.startswith("postgres://"):
        parse_target = parse_target.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(parse_target)
    
    sqlalchemy_url = clean_url
    if not sqlalchemy_url.startswith("postgresql+asyncpg://"):
        if sqlalchemy_url.startswith("postgresql://"):
            sqlalchemy_url = sqlalchemy_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif sqlalchemy_url.startswith("postgres://"):
            sqlalchemy_url = sqlalchemy_url.replace("postgres://", "postgresql+asyncpg://", 1)

    return {
        "raw": clean_url,
        "sqlalchemy_url": sqlalchemy_url,
        "parsed": parsed,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else "postgres",
        "password": unquote(parsed.password) if parsed.password else "",
        "database": parsed.path.lstrip("/") or "postgres"
    }


async def test_and_enable_vector(db_info):
    """Test connection and enable the pgvector extension."""
    print(f"\n[1/5] Testing connection to Supabase host: {db_info['host']}:{db_info['port']} (database: {db_info['database']})...")
    try:
        conn = await asyncpg.connect(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            password=db_info["password"],
            database=db_info["database"],
            timeout=15,
            statement_cache_size=0
        )
        print("  [OK] Successfully connected to Supabase PostgreSQL!")
        
        version = await conn.fetchval("SELECT version();")
        print(f"  [OK] Postgres version: {version.split(',')[0]}")

        print("  Enabling 'vector' extension (pgvector)...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("  [OK] 'vector' extension is active.")
        await conn.close()
        return True
    except Exception as e:
        print(f"\n[ERROR] Could not connect to Supabase: {e}")
        return False


def run_alembic_migrations(sqlalchemy_url: str):
    """Run alembic upgrade head using the provided database URL."""
    print("\n[2/5] Running Alembic migrations to apply full database schema...")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    
    try:
        from app.core.config import settings
        settings.DATABASE_URL = sqlalchemy_url
    except Exception:
        pass

    from alembic import command
    from alembic.config import Config

    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    # Escape % for configparser interpolation (e.g. %40 -> %%40)
    alembic_cfg.set_main_option("sqlalchemy.url", sqlalchemy_url.replace("%", "%%"))

    try:
        command.upgrade(alembic_cfg, "head")
        print("  [OK] All migrations successfully applied up to head revision!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        return False


async def run_initial_seeding(sqlalchemy_url: str):
    """Run init_db to seed roles, permissions, categories, sources, and admin."""
    print("\n[3/5] Seeding core platform data (roles, categories, sources, feature flags, admin)...")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    
    try:
        from app.core.config import settings
        settings.DATABASE_URL = sqlalchemy_url
        from app.core.database import configure_database_pool
        configure_database_pool()
    except Exception as e:
        print(f"  Note configuring pool: {e}")

    try:
        from app.core.init_db import main as init_db_main
        await init_db_main()
        print("  [OK] Core platform data seeded successfully!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Initial seeding failed: {e}")
        return False


async def run_news_ingestion(sqlalchemy_url: str):
    """Optionally run live RSS feed ingestion to populate real articles."""
    print("\n[4/5] Ingesting initial live news articles from RSS sources...")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    try:
        from app.services.ingestion.pipeline import run_source_ingestion_pipeline
        from app.core.database import AsyncSessionLocal
        from app.models.source import Source
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            sources = (await session.execute(select(Source).where(Source.is_active.is_(True)).limit(3))).scalars().all()
            if not sources:
                print("  No active sources found to crawl.")
                return True

            for src in sources:
                print(f"  Crawling {src.name} ({src.url})...")
                try:
                    await run_source_ingestion_pipeline(src.id)
                    print(f"  [OK] {src.name} ingestion complete.")
                except Exception as ex:
                    print(f"  ! Warning: {src.name} crawl issue: {ex}")

        print("  [OK] Initial live articles ingested.")
        return True
    except Exception as e:
        print(f"  ! Ingestion note: {e}")
        return True


def update_env_files(sqlalchemy_url: str, db_info):
    """Update DATABASE_URL and Postgres credentials in .env and backend/.env."""
    print("\n[5/5] Updating environment configuration files...")
    
    env_paths = [project_root / ".env", backend_dir / ".env"]
    for p in env_paths:
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        updated_lines = []
        has_db_url = False
        
        for line in lines:
            if line.startswith("DATABASE_URL="):
                updated_lines.append(f"DATABASE_URL={sqlalchemy_url}")
                has_db_url = True
            elif line.startswith("POSTGRES_SERVER="):
                updated_lines.append(f"POSTGRES_SERVER={db_info['host']}")
            elif line.startswith("POSTGRES_PORT="):
                updated_lines.append(f"POSTGRES_PORT={db_info['port']}")
            elif line.startswith("POSTGRES_USER="):
                updated_lines.append(f"POSTGRES_USER={db_info['user']}")
            elif line.startswith("POSTGRES_PASSWORD="):
                updated_lines.append(f"POSTGRES_PASSWORD={db_info['password']}")
            elif line.startswith("POSTGRES_DB="):
                updated_lines.append(f"POSTGRES_DB={db_info['database']}")
            else:
                updated_lines.append(line)
                
        if not has_db_url:
            updated_lines.append(f"DATABASE_URL={sqlalchemy_url}")

        p.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        print(f"  [OK] Updated {p.relative_to(project_root)}")


def main():
    parser = argparse.ArgumentParser(description="Migrate Tech News Today database to a new Supabase project.")
    parser.add_argument("--db-url", required=True, help="Supabase database connection string URI")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip crawling live RSS news articles")
    args = parser.parse_args()

    db_info = parse_db_url(args.db_url)
    
    # 1. Test & vector extension
    ok = asyncio.run(test_and_enable_vector(db_info))
    if not ok:
        sys.exit(1)

    # 2. Update environment variables early so all subsequent modules use Supabase
    update_env_files(db_info["sqlalchemy_url"], db_info)

    # 3. Alembic migrations (synchronous, runs its own event loop internally)
    ok = run_alembic_migrations(db_info["sqlalchemy_url"])
    if not ok:
        sys.exit(1)

    # 4. Seed core data
    ok = asyncio.run(run_initial_seeding(db_info["sqlalchemy_url"]))
    if not ok:
        sys.exit(1)

    # 5. Ingest live articles
    if not args.skip_ingest:
        asyncio.run(run_news_ingestion(db_info["sqlalchemy_url"]))

    print("\n" + "="*70)
    print(">> SUCCESS! Tech News Today database has been migrated to Supabase!")
    print("="*70)


if __name__ == "__main__":
    main()
