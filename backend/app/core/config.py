import os
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "AICTE Sentinel"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://aicte-sentinel-theta.vercel.app",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/.*\.vercel\.app$"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                return []
            if cleaned.startswith("["):
                import json
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        return [str(i).strip().rstrip("/") for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip().rstrip("/") for i in cleaned.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip().rstrip("/") for i in v if str(i).strip()]
        return []

    # Security & JWT
    SECRET_KEY: str = "sentinel-local-dev-secret-key-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel_dev.db"
    DATABASE_SYNC_URL: str = "sqlite:///./sentinel_dev.db"
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_DB_PATH: str = "./sentinel_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "minio"
    LOCAL_STORAGE_PATH: str = "./local_storage"
    STORAGE_ENDPOINT: str = "localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_QUARANTINE: str = "aicte-quarantine"
    STORAGE_BUCKET_VAULT: str = "aicte-vault"
    STORAGE_USE_SSL: bool = False

    # Upload Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png"]

    # Statutory Cure Windows
    DEFICIENCY_DEFAULT_CURE_DAYS: int = 7

    # ClamAV Antivirus
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    # Audit & Cryptographic Verification
    AUDIT_MERKLE_SALT: str = "sentinel-merkle-secret-salt-2026"
    MERKLE_BATCH_INTERVAL_MINUTES: int = 60

    # Demo Seed
    SEED_SUPERADMIN_EMAIL: str = "superadmin@aicte-india.org"
    SEED_SUPERADMIN_PASSWORD: str = "Sentinel@Admin2026!"
    SEED_SYNTHETIC_DATA: bool = True

    @model_validator(mode="after")
    def validate_and_normalize_database_urls(self):
        is_production = (self.ENVIRONMENT.lower() == "production") or (not self.USE_SQLITE_FALLBACK)
        raw_db_url = (self.DATABASE_URL or "").strip().strip("'\"").replace("\r", "").replace("\n", "").strip()
        if raw_db_url.startswith("psql "):
            raw_db_url = raw_db_url[5:].strip().strip("'\"")

        # Production fail-fast guard
        if is_production:
            if not raw_db_url or raw_db_url.startswith("sqlite"):
                raise ValueError(
                    "CRITICAL: Production deployment requires a valid PostgreSQL DATABASE_URL. "
                    "Silent fallback to SQLite is strictly forbidden in production."
                )

        # Normalize async DATABASE_URL (for async SQLAlchemy / asyncpg)
        normalized_async = raw_db_url
        if normalized_async.startswith("postgres://"):
            normalized_async = "postgresql+asyncpg://" + normalized_async[len("postgres://"):]
        elif normalized_async.startswith("postgresql://") and not normalized_async.startswith("postgresql+asyncpg://"):
            normalized_async = "postgresql+asyncpg://" + normalized_async[len("postgresql://"):]
        elif normalized_async.startswith("sqlite://") and not normalized_async.startswith("sqlite+aiosqlite://"):
            normalized_async = "sqlite+aiosqlite:///" + normalized_async[len("sqlite:///"):].lstrip("/")

        # asyncpg requires 'ssl=' instead of 'sslmode=' and rejects unsupported libpq params like 'channel_binding'
        if "postgresql+asyncpg://" in normalized_async:
            parsed = urlparse(normalized_async)
            query_params = parse_qsl(parsed.query, keep_blank_values=True)
            clean_params = []
            has_ssl = False
            for k, v in query_params:
                if k == "sslmode":
                    clean_params.append(("ssl", v))
                    has_ssl = True
                elif k == "ssl":
                    clean_params.append((k, v))
                    has_ssl = True
                elif k in ("channel_binding", "gssencmode", "target_session_attrs"):
                    # asyncpg connect() does not accept these libpq query params
                    continue
                else:
                    clean_params.append((k, v))
            if not has_ssl and "neon.tech" in parsed.netloc:
                clean_params.append(("ssl", "require"))
            new_query = urlencode(clean_params)
            normalized_async = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

        self.DATABASE_URL = normalized_async

        # Normalize sync DATABASE_SYNC_URL (for Alembic migrations / psycopg2)
        raw_sync = (self.DATABASE_SYNC_URL or "").strip().strip("'\"").replace("\r", "").replace("\n", "").strip()
        if raw_sync.startswith("psql "):
            raw_sync = raw_sync[5:].strip().strip("'\"")

        # If DATABASE_SYNC_URL is empty or default SQLite while DATABASE_URL is PostgreSQL, derive from DATABASE_URL
        if not raw_sync or (raw_sync.startswith("sqlite") and not raw_db_url.startswith("sqlite")):
            raw_sync = raw_db_url

        normalized_sync = raw_sync
        if normalized_sync.startswith("postgres://"):
            normalized_sync = "postgresql+psycopg2://" + normalized_sync[len("postgres://"):]
        elif normalized_sync.startswith("postgresql://") and not normalized_sync.startswith("postgresql+psycopg2://"):
            normalized_sync = "postgresql+psycopg2://" + normalized_sync[len("postgresql://"):]
        elif normalized_sync.startswith("postgresql+asyncpg://"):
            normalized_sync = "postgresql+psycopg2://" + normalized_sync[len("postgresql+asyncpg://"):]
        elif normalized_sync.startswith("sqlite+aiosqlite:///"):
            normalized_sync = "sqlite:///" + normalized_sync[len("sqlite+aiosqlite:///"):].lstrip("/")

        if "postgresql+psycopg2://" in normalized_sync:
            parsed_sync = urlparse(normalized_sync)
            sync_query_params = parse_qsl(parsed_sync.query, keep_blank_values=True)
            clean_sync_params = []
            has_sslmode = False
            for k, v in sync_query_params:
                if k == "sslmode":
                    clean_sync_params.append(("sslmode", v))
                    has_sslmode = True
                elif k == "ssl":
                    clean_sync_params.append(("sslmode", v))
                    has_sslmode = True
                elif k in ("channel_binding", "gssencmode", "target_session_attrs"):
                    # Strip unsupported/unneeded parameters to prevent driver mismatches
                    continue
                else:
                    clean_sync_params.append((k, v))
            if not has_sslmode and "neon.tech" in parsed_sync.netloc:
                clean_sync_params.append(("sslmode", "require"))
            new_sync_query = urlencode(clean_sync_params)
            normalized_sync = urlunparse((
                parsed_sync.scheme,
                parsed_sync.netloc,
                parsed_sync.path,
                parsed_sync.params,
                new_sync_query,
                parsed_sync.fragment
            ))

        self.DATABASE_SYNC_URL = normalized_sync
        return self


settings = Settings()
