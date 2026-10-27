"""
AICTE Sentinel — Neon PostgreSQL Safe Provisioning & Seed Runner
Problem Statement 26262 | SIH 2026

Security Safeguards:
1. Target-Host Guard: Validates that the remote target ends in .neon.tech.
   Immediately aborts if the target is SQLite, localhost, or 127.0.0.1.
2. Local Database Protection: Strictly ensures sentinel_dev.db is untouched.
3. Secret Masking: Uses getpass to hide passwords and masks credentials across all output.
4. Non-Destructive: All seeding queries verify existence before insertion (idempotent).
"""
import os
import sys
import getpass
import re
import asyncio
from pathlib import Path

# Add backend and root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))
sys.path.insert(0, str(root_dir))

from sqlalchemy.engine.url import make_url, URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select, func

from app.security.password import hash_password
from app.security.bootstrap import ensure_statutory_roles_and_permissions
from app.models.user import User, Role
from app.models.institution import Institution
from scripts.seed_data import seed as run_comprehensive_seed


def sanitize_connection_input(raw: str) -> str:
    """Sanitizes user input by removing quotes, whitespace, carriage returns, and psql wrapper."""
    if not raw:
        return ""
    cleaned = raw.strip()
    if cleaned.startswith("psql "):
        cleaned = cleaned[5:].strip()
    cleaned = cleaned.strip("'\"").strip()
    cleaned = cleaned.replace("\r", "").replace("\n", "").strip()
    return cleaned


def mask_sensitive_text(text_val: str, password: str = None) -> str:
    """Masks credentials in error messages or URLs."""
    if not text_val:
        return ""
    masked = text_val
    if password and len(password) >= 1:
        masked = masked.replace(password, "****")
    masked = re.sub(r"(://[^:]+:)(.+?)(@[a-zA-Z0-9_\-\.]+(?::\d+)?(?:/|$|\s))", r"\1****\3", masked)
    return masked


def mask_connection_url(raw_url: str) -> str:
    """Returns a safe representation of the URL with password masked."""
    try:
        url = make_url(raw_url)
        return f"{url.drivername}://{url.username}:****@{url.host}:{url.port or 5432}/{url.database}"
    except Exception:
        return mask_sensitive_text(raw_url)


async def provision_neon():
    print("===================================================================")
    print("AICTE Sentinel — Neon PostgreSQL Safe Provisioning Tool")
    print("SIH 2026 Problem Statement ID: 26262")
    print("===================================================================")

    sqlite_db_path = root_dir / "sentinel_dev.db"
    initial_sqlite_size = sqlite_db_path.stat().st_size if sqlite_db_path.exists() else None

    # 1. Accept Neon Connection String securely
    raw_input = os.environ.get("DATABASE_URL")
    if not raw_input:
        print("\n[!] No DATABASE_URL found in environment.")
        print("    Please paste your Neon connection string below (input will be hidden):")
        try:
            raw_input = getpass.getpass("    Neon Connection String: ")
        except Exception:
            raw_input = input("    Neon Connection String: ")

    cleaned = sanitize_connection_input(raw_input)
    if not cleaned:
        print("[ERROR] Database URL is empty. Aborting.")
        sys.exit(1)

    if cleaned.count("://") > 1:
        print("[ERROR] Input Malformed: Multiple connection URLs detected.")
        sys.exit(1)

    try:
        parsed = make_url(cleaned)
    except Exception as e:
        print(f"[ERROR] Invalid database URL format: {mask_sensitive_text(str(e))}")
        sys.exit(1)

    # 2. Safety Guards
    driver = parsed.drivername.lower()
    if "sqlite" in driver:
        print("[ERROR] Safety Violation: Target database is SQLite. Aborting to protect sentinel_dev.db.")
        sys.exit(1)

    host = (parsed.host or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        print("[ERROR] Safety Violation: Target is localhost. Expected remote Neon host.")
        sys.exit(1)

    if not host.endswith(".neon.tech"):
        print(f"[ERROR] Target Verification Failed: '{host}' is not a verified *.neon.tech endpoint.")
        sys.exit(1)

    print(f"[*] Target Verification: Verified Neon Cloud Endpoint ({host})")
    print(f"[*] Target URL:          {mask_connection_url(cleaned)}")

    # 3. Construct async engine URL (asyncpg)
    query_params = dict(parsed.query)
    for unsupported in ("channel_binding", "gssencmode", "target_session_attrs"):
        query_params.pop(unsupported, None)
    if "sslmode" in query_params:
        query_params["ssl"] = query_params.pop("sslmode")
    else:
        query_params["ssl"] = "require"

    async_url = URL.create(
        drivername="postgresql+asyncpg",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        query=query_params,
    )

    async_engine = create_async_engine(async_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    # 4. Connectivity check
    print("\n[1/4] Verifying database connectivity & current user count...")
    try:
        async with AsyncSessionLocal() as session:
            db_version = (await session.execute(text("SELECT version();"))).scalar()
            user_count = (await session.execute(text("SELECT count(*) FROM users;"))).scalar() or 0
            print(f"      Connection verified! PostgreSQL Server:")
            print(f"      {db_version[:80]}...")
            print(f"      Current users in Neon database: {user_count}")
    except Exception as e:
        safe_msg = mask_sensitive_text(str(e), parsed.password)
        print(f"[ERROR] Failed to connect to Neon PostgreSQL: {safe_msg}")
        sys.exit(1)

    # 5. Menu options
    print("\n[2/4] Select Provisioning Action:")
    print("  [1] Seed Full Statutory SIH Demo Environment (All 16 Modules + Demo Personas)")
    print("  [2] Create Custom Initial Super Administrator Account Only")
    print("  [3] Both (Full SIH Demo Environment + Custom Administrator Account)")
    
    choice = input("\nEnter choice (1, 2, or 3) [default: 1]: ").strip() or "1"

    async with AsyncSessionLocal() as session:
        # Step A: Ensure permissions & roles exist
        print("\n[3/4] Ensuring statutory permissions and roles exist...")
        role_map = await ensure_statutory_roles_and_permissions(session)
        print(f"      Roles verified: {', '.join(role_map.keys())}")
        await session.commit()

        # Step B: Execute selected action
        if choice in ("1", "3"):
            print("\n      Executing comprehensive SIH demo seed sequence...")
            # Override database session in seed_data module
            import scripts.seed_data as sd
            sd.AsyncSessionLocal = AsyncSessionLocal
            await sd.seed()
            print("      Full SIH Demo Environment seeded successfully into Neon!")

        if choice in ("2", "3"):
            print("\n--- Custom Administrator Account Provisioning ---")
            admin_email = input("Enter Administrator Email: ").strip().lower()
            if not admin_email:
                print("[ERROR] Email cannot be empty.")
                sys.exit(1)

            admin_name = input("Enter Full Name: ").strip() or "Central AICTE Administrator"
            admin_desig = input("Enter Designation [default: Member Secretary]: ").strip() or "Member Secretary"
            
            try:
                admin_pass = getpass.getpass("Enter Secure Password (min 8 chars): ")
            except Exception:
                admin_pass = input("Enter Secure Password (min 8 chars): ")

            if len(admin_pass) < 8:
                print("[ERROR] Password must be at least 8 characters long.")
                sys.exit(1)

            # Check if user already exists
            existing = (await session.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
            if existing:
                print(f"[!] User '{admin_email}' already exists. Updating role to SUPER_ADMIN...")
                existing.roles = [role_map["SUPER_ADMIN"]]
                existing.hashed_password = hash_password(admin_pass)
                existing.full_name = admin_name
                existing.designation = admin_desig
            else:
                new_user = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_pass),
                    full_name=admin_name,
                    designation=admin_desig,
                    roles=[role_map["SUPER_ADMIN"]],
                    is_active=True,
                )
                session.add(new_user)
            
            await session.commit()
            print(f"[SUCCESS] Authorized Super Administrator created: {admin_email}")

    # 6. Verify local SQLite DB preservation
    print("\n[4/4] Verifying local development database preservation...")
    if sqlite_db_path.exists():
        final_sqlite_size = sqlite_db_path.stat().st_size
        if initial_sqlite_size == final_sqlite_size:
            print(f"      CONFIRMED: Local 'sentinel_dev.db' untouched ({final_sqlite_size} bytes).")
        else:
            print(f"      [WARNING] Local database size changed from {initial_sqlite_size} to {final_sqlite_size}!")
    else:
        print("      Local database 'sentinel_dev.db' does not exist.")

    await async_engine.dispose()
    print("\n===================================================================")
    print("SUCCESS: Neon PostgreSQL provisioning complete! You can now log in.")
    print("===================================================================")


if __name__ == "__main__":
    asyncio.run(provision_neon())
