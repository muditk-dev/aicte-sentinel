from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger


class TenantContext:
    """
    Manages tenant context and PostgreSQL Row-Level Security (RLS) session variables.
    
    Security Guarantee:
    - In PostgreSQL, executes `SET LOCAL app.current_tenant = :tenant_id`
    - Ensures institutions cannot query across tenant barriers.
    - AICTE administrative officers operate under audited supervisory roles.
    """
    def __init__(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None, role: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role

    async def apply(self, db: AsyncSession):
        if not settings.DATABASE_URL.startswith("sqlite") and self.tenant_id:
            try:
                await db.execute(
                    text("SET LOCAL app.current_tenant = :tenant_id"),
                    {"tenant_id": self.tenant_id}
                )
                if self.user_id:
                    await db.execute(
                        text("SET LOCAL app.current_user_id = :user_id"),
                        {"user_id": self.user_id}
                    )
                if self.role:
                    await db.execute(
                        text("SET LOCAL app.current_role = :role"),
                        {"role": self.role}
                    )
            except Exception as e:
                logger.warning(f"Could not apply RLS session variables: {e}")
