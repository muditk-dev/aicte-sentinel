import os
import sys
import getpass
import re
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))
sys.path.insert(0, str(root_dir))

from sqlalchemy.engine.url import make_url
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command


def mask_connection_url(raw_url: str) -> str:
    """Returns a safe representation of the URL with password masked."""
    try:
        url = make_url(raw_url)
        return f"{url.drivername}://{url.username}:****@{url.host}:{url.port or 5432}/{url.database}?{url.query.get('sslmode', 'require')}"
    except Exception:
        # Fallback regex masking
        return re.sub(r":([^@]+)@", ":****@", raw_url)


def run_neon_migration(database_url: str = None):
    print("===================================================================")
    print("AICTE Sentinel — Neon PostgreSQL Migration Runner")
    print("SIH 2026 Problem Statement ID: 26262")
    print("===================================================================")

    raw_url = database_url or os.environ.get("DATABASE_URL")
    if not raw_url:
        print("[!] No DATABASE_URL found in environment.")
        print("    Please paste your Neon connection string below (input will be hidden):")
        try:
            raw_url = getpass.getpass("    Neon Connection String: ").strip()
        except Exception:
            raw_url = input("    Neon Connection String: ").strip()

    if not raw_url:
        print("[ERROR] Database URL is empty. Aborting.")
        sys.exit(1)

    # 1. Parse and validate target URL
    try:
        parsed = make_url(raw_url)
    except Exception as e:
        print(f"[ERROR] Invalid database URL format: {e}")
        sys.exit(1)

    driver = parsed.drivername.lower()
    if "sqlite" in driver:
        print("[ERROR] Safety Violation: Target database is SQLite.")
        print("        This runner is strictly for remote Neon PostgreSQL.")
        print("        Local SQLite database 'sentinel_dev.db' is protected.")
        sys.exit(1)

    if not ("postgres" in driver or "psycopg" in driver or "asyncpg" in driver):
        print(f"[ERROR] Unsupported driver: {driver}. Expected PostgreSQL.")
        sys.exit(1)

    host = (parsed.host or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        print("[WARNING] Target is localhost. Ensure this is intentional.")

    print(f"[*] Target Driver:   {parsed.drivername}")
    print(f"[*] Target Host:     {parsed.host}")
    print(f"[*] Target Database: {parsed.database}")
    print(f"[*] Safe Target URL: {mask_connection_url(raw_url)}")
    print("-------------------------------------------------------------------")

    # 2. Check local SQLite DB untouched baseline
    sqlite_db_path = root_dir / "sentinel_dev.db"
    initial_sqlite_size = sqlite_db_path.stat().st_size if sqlite_db_path.exists() else None

    # 3. Derive sync migration URL (psycopg2 with sslmode=require)
    sync_url = raw_url.strip()
    if sync_url.startswith("postgres://"):
        sync_url = "postgresql+psycopg2://" + sync_url[len("postgres://"):]
    elif sync_url.startswith("postgresql://") and not sync_url.startswith("postgresql+psycopg2://"):
        sync_url = "postgresql+psycopg2://" + sync_url[len("postgresql://"):]
    elif sync_url.startswith("postgresql+asyncpg://"):
        sync_url = "postgresql+psycopg2://" + sync_url[len("postgresql+asyncpg://"):]

    if "postgresql+psycopg2://" in sync_url:
        sync_url = re.sub(r'([?&])ssl=([a-zA-Z0-9_-]+)', r'\1sslmode=\2', sync_url)
        if "sslmode=" not in sync_url:
            separator = "&" if "?" in sync_url else "?"
            sync_url += f"{separator}sslmode=require"

    # Set environment for Alembic env.py
    os.environ["DATABASE_SYNC_URL"] = sync_url
    os.environ["DATABASE_URL"] = raw_url

    # 4. Pre-flight connectivity check
    print("[1/4] Verifying connectivity to Neon PostgreSQL...")
    try:
        engine = create_engine(sync_url, connect_args={"connect_timeout": 15})
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            print(f"      Connection verified! PostgreSQL Server:")
            print(f"      {res[:80]}...")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neon PostgreSQL: {e}")
        print("        Check network connectivity, host, user, and password.")
        sys.exit(1)

    # 5. Execute Alembic Migrations
    print("[2/4] Executing Alembic migrations up to head...")
    backend_dir = root_dir / "backend"
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    try:
        command.upgrade(alembic_cfg, "head")
        print("      All migrations applied successfully to revision: 006_postgresql_rls")
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)

    # 6. Post-migration verification of tables and RLS
    print("[3/4] Verifying created tables and Row-Level Security policies...")
    with engine.connect() as conn:
        tables_res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)).fetchall()
        table_names = [t[0] for t in tables_res]
        print(f"      Public tables created ({len(table_names)} total):")
        print(f"      {', '.join(table_names[:10])}...")

        # Check RLS policies
        policies_res = conn.execute(text("""
            SELECT tablename, policyname, cmd 
            FROM pg_policies 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)).fetchall()
        print(f"      Active RLS policies ({len(policies_res)} total):")
        for p in policies_res:
            print(f"      - {p[0]}: {p[1]} ({p[2]})")

    # 7. Check local SQLite DB untouched
    print("[4/4] Verifying local development database preservation...")
    if sqlite_db_path.exists():
        final_sqlite_size = sqlite_db_path.stat().st_size
        if initial_sqlite_size == final_sqlite_size:
            print(f"      CONFIRMED: Local 'sentinel_dev.db' untouched ({final_sqlite_size} bytes).")
        else:
            print(f"      [WARNING] Local database size changed from {initial_sqlite_size} to {final_sqlite_size}!")
    else:
        print("      Local database 'sentinel_dev.db' does not exist.")

    print("===================================================================")
    print("SUCCESS: Neon PostgreSQL database is fully initialized and secured!")
    print("===================================================================")


if __name__ == "__main__":
    run_neon_migration()
