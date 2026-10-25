from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile, RoleBrief
from app.security.password import verify_password
from app.security.tokens import create_access_token
from app.security.dependencies import get_current_user
from app.audit.service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with Argon2id password verification and emit JWT."""
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Record failed attempt in audit log
        await record_audit_event(
            db=db,
            actor_id=payload.email,
            action="AUTH_LOGIN_FAILED",
            resource_type="User",
            resource_id=payload.email,
            details={"reason": "Invalid credentials"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        await db.commit()
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("This user account has been deactivated by administration.")

    role_codes = [r.code for r in user.roles]
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_codes,
        institution_id=user.institution_id,
        assigned_region=user.assigned_region,
    )

    # Record successful login event
    await record_audit_event(
        db=db,
        actor_id=user.id,
        action="AUTH_LOGIN_SUCCESS",
        resource_type="User",
        resource_id=user.id,
        details={"roles": role_codes},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()

    inst_name = user.institution.name if user.institution else None

    return TokenResponse(
        access_token=access_token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            designation=user.designation,
            institution_id=user.institution_id,
            institution_name=inst_name,
            assigned_region=user.assigned_region,
            roles=[RoleBrief(code=r.code, name=r.name) for r in user.roles],
        ),
    )


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated user details and active statutory roles."""
    inst_name = current_user.institution.name if current_user.institution else None
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        designation=current_user.designation,
        institution_id=current_user.institution_id,
        institution_name=inst_name,
        assigned_region=current_user.assigned_region,
        roles=[RoleBrief(code=r.code, name=r.name) for r in current_user.roles],
    )
