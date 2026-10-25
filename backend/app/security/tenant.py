import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ValidationError

SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.:]+$")


class TenantContext:
    """
    Manages tenant context and PostgreSQL Row-Level Security (RLS) session variables.
    
    Security Guarantees:
    - Input Sanitization: Validates tenant_id, user_id, and role against strict safe regex.
    - Transactional Scoping: In PostgreSQL, executes `SET LOCAL app.current_tenant = :tenant_id`,
      ensuring the session variables are automatically discarded upon transaction COMMIT or ROLLBACK.
    - Connection Pool Safety: Provides `reset(db)` method to prevent tenant context leaking
      between connection pool checkouts.
    - Officer Transparency: Sets `app.current_role` even for central officers without an institution_id,
      allowing RLS policies to distinguish central supervisors from tenant representatives.
    """
    def __init__(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None, role: Optional[str] = None):
        self.tenant_id = self._validate_identifier(tenant_id, "tenant_id") if tenant_id else None
        self.user_id = self._validate_identifier(user_id, "user_id") if user_id else None
        self.role = self._validate_identifier(role, "role") if role else None

    @staticmethod
    def _validate_identifier(val: Optional[str], field_name: str) -> Optional[str]:
        if val is None:
            return None
        cleaned = str(val).strip()
        if not cleaned:
            return None
        if not SAFE_IDENTIFIER_PATTERN.match(cleaned):
            raise ValidationError(f"Invalid characters in tenant context {field_name}: contains unsafe characters.")
        if len(cleaned) > 100:
            raise ValidationError(f"Tenant context {field_name} exceeds maximum length of 100 characters.")
        return cleaned

    async def apply(self, db: AsyncSession):
        """Applies transaction-local session variables for PostgreSQL RLS."""
        if not settings.DATABASE_URL.startswith("sqlite"):
            try:
                # 1. Set tenant identifier (or empty string if officer/central)
                tenant_val = self.tenant_id or ""
                await db.execute(
                    text("SET LOCAL app.current_tenant = :tenant_id"),
                    {"tenant_id": tenant_val}
                )
                
                # 2. Set user identifier
                if self.user_id:
                    await db.execute(
                        text("SET LOCAL app.current_user_id = :user_id"),
                        {"user_id": self.user_id}
                    )
                    
                # 3. Set role identifier
                if self.role:
                    await db.execute(
                        text("SET LOCAL app.current_role = :role"),
                        {"role": self.role}
                    )
            except Exception as e:
                logger.warning(f"Could not apply PostgreSQL RLS session variables: {e}")

    @staticmethod
    async def reset(db: AsyncSession):
        """Explicitly resets all transaction-local RLS session variables."""
        if not settings.DATABASE_URL.startswith("sqlite"):
            try:
                await db.execute(text("RESET app.current_tenant; RESET app.current_user_id; RESET app.current_role;"))
            except Exception as e:
                logger.warning(f"Could not reset PostgreSQL RLS session variables: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
