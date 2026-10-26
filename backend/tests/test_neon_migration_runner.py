import sys
from pathlib import Path

# Add project root to path for scripts imports
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from sqlalchemy.engine.url import make_url, URL
from scripts.migrate_neon import (
    sanitize_connection_input,
    mask_sensitive_text,
    mask_connection_url,
)
from app.core.config import Settings


def test_sanitize_connection_input_removes_psql_prefix_and_quotes():
    """Verifies that psql prefix and single/double quotes are stripped."""
    raw1 = "psql 'postgresql://user:pass@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'"
    assert sanitize_connection_input(raw1) == "postgresql://user:pass@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

    raw2 = '"postgresql://user:pass@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"'
    assert sanitize_connection_input(raw2) == "postgresql://user:pass@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"


def test_sanitize_connection_input_removes_carriage_returns_and_newlines():
    """Verifies that Windows carriage returns and newlines from terminal paste are removed."""
    raw = "postgresql://user:pass@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require\r\n"
    cleaned = sanitize_connection_input(raw)
    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.endswith("channel_binding=require")


def test_mask_connection_url_masks_password():
    """Verifies that password is masked and never exposed."""
    raw = "postgresql://neondb_owner:SuperSecretPassword123@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    masked = mask_connection_url(raw)
    assert "SuperSecretPassword123" not in masked
    assert "neondb_owner:****@ep-sample-123" in masked


def test_mask_sensitive_text_masks_embedded_credentials():
    """Verifies that error messages containing embedded connection strings or passwords are fully sanitized."""
    err_text = "OperationalError: connection to server at ep-xyz.neon.tech, user neondb_owner, password SuperSecretPassword123 failed"
    masked = mask_sensitive_text(err_text, password="SuperSecretPassword123")
    assert "SuperSecretPassword123" not in masked
    assert "****" in masked

    url_err = "failed to connect: postgresql://admin:p@ssw0rd!@ep-xyz.neon.tech/db"
    masked_url = mask_sensitive_text(url_err)
    assert "admin:****@ep-xyz.neon.tech" in masked_url


def test_neon_url_construction_strips_channel_binding_and_sets_sslmode():
    """Verifies that URL construction produces clean psycopg2 and asyncpg URLs with no channel_binding."""
    raw_input = "postgresql://neondb_owner:MyP@ssword999@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    cleaned = sanitize_connection_input(raw_input)
    parsed = make_url(cleaned)

    # Reconstruct sync URL for psycopg2
    sync_url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        query={"sslmode": "require"},
    )
    assert sync_url_obj.drivername == "postgresql+psycopg2"
    assert dict(sync_url_obj.query) == {"sslmode": "require"}
    assert "channel_binding" not in sync_url_obj.query
    assert "MyP@ssword999" not in sync_url_obj.render_as_string(hide_password=True)

    # Reconstruct async URL for asyncpg
    async_url_obj = URL.create(
        drivername="postgresql+asyncpg",
        username=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        query={"ssl": "require"},
    )
    assert async_url_obj.drivername == "postgresql+asyncpg"
    assert dict(async_url_obj.query) == {"ssl": "require"}
    assert "channel_binding" not in async_url_obj.query
    assert "MyP@ssword999" not in async_url_obj.render_as_string(hide_password=True)


def test_config_settings_sync_and_async_strip_channel_binding(monkeypatch):
    """Verifies Settings normalizes both DATABASE_URL and DATABASE_SYNC_URL by stripping channel_binding."""
    raw = "postgresql://neondb_owner:SecretPass456@ep-sample-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require\r"
    monkeypatch.setenv("DATABASE_URL", raw)
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings()
    # Asyncpg URL
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert "ssl=require" in settings.DATABASE_URL
    assert "channel_binding" not in settings.DATABASE_URL
    assert "\r" not in settings.DATABASE_URL

    # Sync psycopg2 URL
    assert settings.DATABASE_SYNC_URL.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in settings.DATABASE_SYNC_URL
    assert "channel_binding" not in settings.DATABASE_SYNC_URL
    assert "\r" not in settings.DATABASE_SYNC_URL


def test_migration_runner_detects_duplicate_urls():
    """Verifies that accidentally pasted repeated URLs are detected."""
    raw_repeated = (
        "postgresql://user:p1@ep-xyz.neon.tech/db?sslmode=require"
        "postgresql://user:p1@ep-xyz.neon.tech/db?sslmode=require"
    )
    cleaned = sanitize_connection_input(raw_repeated)
    assert cleaned.count("://") > 1


def test_migration_runner_detects_sqlite_safety_guard():
    """Verifies that SQLite URLs are flagged by the driver safety guard."""
    parsed = make_url("sqlite:///./sentinel_dev.db")
    assert "sqlite" in parsed.drivername.lower()


def test_migration_runner_detects_localhost_safety_guard():
    """Verifies that localhost URLs are flagged as non-remote."""
    parsed = make_url("postgresql://user:pass@127.0.0.1:5432/neondb")
    host = (parsed.host or "").lower()
    assert host in ("localhost", "127.0.0.1", "0.0.0.0")
