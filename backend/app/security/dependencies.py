from typing import List, Callable
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.models.user import User
from app.security.tokens import decode_token
from app.security.tenant import TenantContext


async def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that authenticates the Bearer JWT and returns the User object."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Authorization header with Bearer token is required")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise AuthenticationError("Malformed token payload")

    # Fetch user with roles
    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User account not found or disabled")

    # Apply tenant RLS context if user belongs to an institution
    role_code = user.roles[0].code if user.roles else "PUBLIC"
    tenant_context = TenantContext(
        tenant_id=user.institution_id,
        user_id=user.id,
        role=role_code
    )
    await tenant_context.apply(db)

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory checking if the user holds at least one required statutory role."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = [r.code for r in current_user.roles]
        # SUPER_ADMIN always has administrative access
        if "SUPER_ADMIN" in user_roles:
            return current_user

        if not any(role in user_roles for role in allowed_roles):
            raise PermissionDeniedError(
                f"Statutory authority required: one of {list(allowed_roles)}. User has: {user_roles}"
            )
        return current_user

    return role_checker
