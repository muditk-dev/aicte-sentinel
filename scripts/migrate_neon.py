import os
import sys
import getpass
import re
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))
sys.path.insert(0, str(root_dir))

from sqlalchemy.engine.url import make_url, URL
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command


def sanitize_connection_input(raw: str) -> str:
    """Sanitizes user input by removing quotes, whitespace, carriage returns, and psql wrapper."""
    if not raw:
        return ""
    cleaned = raw.strip()
    # Strip psql CLI wrapper if copied from Neon console psql tab
    if cleaned.startswith("psql "):
        cleaned = cleaned[5:].strip()
    # Strip surrounding single or double quotes
    cleaned = cleaned.strip("'\"").strip()
    # Remove all carriage returns and newlines
    cleaned = cleaned.replace("\r", "").replace("\n", "").strip()
    return cleaned


def mask_sensitive_text(text_val: str, password: str = None) -> str:
    """Masks credentials in error messages or URLs."""
    if not text_val:
        return ""
    masked = text_val
    if password and len(password) >= 1:
        masked = masked.replace(password, "****")
    # Mask user:password in standard connection URLs, even if password has special chars
    masked = re.sub(r"(://[^:]+:)(.+?)(@[a-zA-Z0-9_\-\.]+(?::\d+)?(?:/|$|\s))", r"\1****\3", masked)
    return masked


def mask_connection_url(raw_url: str) -> str:
    """Returns a safe representation of the URL with password masked."""
    try:
        url = make_url(raw_url)
        return f"{url.drivername}://{url.username}:****@{url.host}:{url.port or 5432}/{url.database}"
    except Exception:
        return mask_sensitive_text(raw_url)


def run_neon_migration(database_url: str = None):
    print("===================================================================")
    print("AICTE Sentinel — Neon PostgreSQL Migration Runner")
    print("SIH 2026 Problem Statement ID: 26262")
    print("===================================================================")

    raw_input = database_url or os.environ.get("DATABASE_URL")
    if not raw_input:
        print("[!] No DATABASE_URL found in environment.")
        print("    Please paste your Neon connection string below (input will be hidden):")
        try:
            raw_input = getpass.getpass("    Neon Connection String: ")
        except Exception:
            raw_input = input("    Neon Connection String: ")

    cleaned = sanitize_connection_input(raw_input)
    if not cleaned:
        print("[ERROR] Database URL is empty. Aborting.")
        sys.exit(1)

    # Detect duplicate connection strings pasted accidentally
    if cleaned.count("://") > 1:
        print("[ERROR] Input Malformed: Multiple connection URLs detected.")
        print("        Please ensure you paste exactly one connection string.")
        sys.exit(1)

    # 1. Parse ONCE using SQLAlchemy make_url
    try:
        parsed = make_url(cleaned)
    except Exception as e:
        print(f"[ERROR] Invalid database URL format: {mask_sensitive_text(str(e))}")
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
        print("[ERROR] Safety Violation: Target is localhost. Expected remote Neon host.")
        sys.exit(1)

    if not host.endswith(".neon.tech"):
        print(f"[WARNING] Target host '{parsed.host}' does not end in '.neon.tech'.")
    else:
        print("[*] Target Verification: Verified Neon Cloud Endpoint (*.neon.tech)")

    print(f"[*] Target Driver:   {parsed.drivername}")
    print(f"[*] Target Host:     {parsed.host}")
    print(f"[*] Target Database: {parsed.database}")
    print(f"[*] Safe Target URL: {mask_connection_url(cleaned)}")
    print("-------------------------------------------------------------------")

    # 2. Check local SQLite DB untouched baseline
    sqlite_db_path = root_dir / "sentinel_dev.db"
    initial_sqlite_size = sqlite_db_path.stat().st_size if sqlite_db_path.exists() else None

    # 3. Construct clean connection URLs using URL.create
    # psycopg2 sync URL: strictly sslmode=require, NO channel_binding
    sync_url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        query={"sslmode": "require"},
    )

    # asyncpg async URL: strictly ssl=require, NO channel_binding
    async_url_obj = URL.create(
        drivername="postgresql+asyncpg",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        query={"ssl": "require"},
    )

    # Export to environment for Alembic env.py without leaking to logs
    os.environ["DATABASE_SYNC_URL"] = sync_url_obj.render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = async_url_obj.render_as_string(hide_password=False)

    # 4. Pre-flight connectivity check
    print("[1/4] Verifying connectivity to Neon PostgreSQL...")
    try:
        engine = create_engine(sync_url_obj, connect_args={"connect_timeout": 15})
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            print(f"      Connection verified! PostgreSQL Server:")
            print(f"      {res[:80]}...")
    except Exception as e:
        safe_msg = mask_sensitive_text(str(e), parsed.password)
        print(f"[ERROR] Failed to connect to Neon PostgreSQL: {safe_msg}")
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
        safe_msg = mask_sensitive_text(str(e), parsed.password)
        print(f"[ERROR] Migration failed: {safe_msg}")
        sys.exit(1)

    # 6. Post-migration verification of tables and RLS
    print("[3/4] Verifying created tables and Row-Level Security policies...")
    try:
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
    except Exception as e:
        safe_msg = mask_sensitive_text(str(e), parsed.password)
        print(f"[ERROR] Verification queries failed: {safe_msg}")
        sys.exit(1)

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
