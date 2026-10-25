import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))
sys.path.insert(0, str(root_dir))

import asyncio
from alembic.config import Config
from alembic import command
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.audit.service import verify_audit_chain
from scripts.seed_data import seed


def run_alembic_migrations():
    """Applies all Alembic migrations up to head."""
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    print("[1/4] Applying database migrations to latest revision (head)...")
    command.upgrade(alembic_cfg, "head")
    print("      Migrations applied successfully.")


async def reset_demo_database(force: bool = False):
    """
    Safely resets the local development database to the clean demo state.
    1. For SQLite development fallback: removes old database file.
    2. Runs Alembic migrations up to head.
    3. Seeds idempotent statutory reference data, institutions, roles, and personas.
    4. Cryptographically verifies the audit hash chain.
    """
    print("===================================================================")
    print("AICTE Sentinel — SIH 2026 Demo Environment Reset Utility")
    print("Problem Statement ID: 26262")
    print("===================================================================")

    db_path = Path(__file__).resolve().parent.parent / "sentinel_dev.db"
    if db_path.exists():
        print(f"[0/4] Removing existing development SQLite database: {db_path.name}")
        try:
            db_path.unlink()
            print("      Old database removed cleanly.")
        except Exception as e:
            print(f"      Warning: Could not remove database file directly: {e}")

    # 1. Run Migrations
    run_alembic_migrations()

    # 2. Seed Data
    print("[2/4] Seeding statutory institutions, workflow templates, users, and obligations...")
    await seed()
    print("      Seed data population complete.")

    # 3. Cryptographic Ledger Verification
    print("[3/4] Verifying cryptographic SHA-256 audit ledger integrity...")
    async with AsyncSessionLocal() as db:
        verification = await verify_audit_chain(db)
        if verification.is_valid:
            print(f"      Audit ledger verified: UNTAMPERED ({verification.total_events_checked} events, chain head: {verification.chain_head_hash[:16]}...)")
        else:
            print(f"      CRITICAL: Audit ledger verification failed: {verification.verification_message}")
            sys.exit(1)

    print("[4/4] Demo Environment Status: READY")
    print("===================================================================")
    print("DEMO CREDENTIALS CHEAT-SHEET:")
    print("-------------------------------------------------------------------")
    print("1. Central AICTE Super Admin:")
    print("   Email:    superadmin@aicte-india.org")
    print("   Password: Sentinel@Admin2026!")
    print("   Persona:  Dr. Rajesh V. Sharma (Member Secretary)")
    print("")
    print("2. Regional Officer (Northern Region):")
    print("   Email:    ro.delhi@aicte-india.org")
    print("   Password: Regional@2026!")
    print("   Persona:  Prof. Anita Deshmukh (Regional Director)")
    print("")
    print("3. Senior Scrutiny Officer:")
    print("   Email:    scrutiny.lead@aicte-india.org")
    print("   Password: Scrutiny@2026!")
    print("   Persona:  Shri K. Sundaram")
    print("")
    print("4. EVC Expert Committee Chairperson:")
    print("   Email:    evc.prof@iitd.ac.in")
    print("   Password: Expert@2026!")
    print("   Persona:  Prof. Manas Ranjan Pradhan")
    print("")
    print("5. Institution Authorized Signatory (DITM Delhi):")
    print("   Email:    director@ditm-delhi.edu.in")
    print("   Password: College@2026!")
    print("   Persona:  Dr. Sunita Aggarwal (Director)")
    print("===================================================================")


if __name__ == "__main__":
    asyncio.run(reset_demo_database())
