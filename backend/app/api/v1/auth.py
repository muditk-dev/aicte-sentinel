from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
)
from app.core.config import settings
from app.models.user import User, Role
from app.models.institution import Institution
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserProfile,
    RoleBrief,
    BootstrapStatusResponse,
    BootstrapRequest,
    ProvisionUserRequest,
)
from app.security.password import verify_password, hash_password
from app.security.tokens import create_access_token
from app.security.dependencies import get_current_user, require_roles
from app.security.bootstrap import ensure_statutory_roles_and_permissions
from app.audit.service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
async def check_bootstrap_status(db: AsyncSession = Depends(get_db)):
    """
    Check whether initial administrator bootstrap is available.
    Returns bootstrap_available=True if and only if zero users exist in the database.
    """
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    available = (total_users == 0)
    msg = (
        "Initial administrator bootstrap is available."
        if available
        else "System has already been bootstrapped. Administrator creation is locked."
    )
    return BootstrapStatusResponse(
        bootstrap_available=available,
        total_users=total_users,
        message=msg,
    )


@router.post("/bootstrap", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_initial_admin(
    payload: BootstrapRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Bootstrap the initial Central AICTE Administrator account.
    Fails with HTTP 409 Conflict if any user already exists.
    """
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    if total_users > 0:
        raise ConflictError(
            "System has already been bootstrapped. Initial administrator creation is locked. "
            "Additional accounts must be provisioned by an existing administrator."
        )

    if len(payload.password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")

    # 1. Initialize statutory permissions & roles
    role_map = await ensure_statutory_roles_and_permissions(db)
    super_admin_role = role_map["SUPER_ADMIN"]

    # 2. Hash password with Argon2id
    hashed = hash_password(payload.password)

    # 3. Create initial Super Admin User
    admin_user = User(
        email=payload.email.lower().strip(),
        hashed_password=hashed,
        full_name=payload.full_name.strip(),
        designation=payload.designation.strip() if payload.designation else "Member Secretary / Central Council",
        assigned_region=payload.assigned_region,
        roles=[super_admin_role],
        is_active=True,
    )
    db.add(admin_user)
    await db.flush()

    # 4. Record audit event
    await record_audit_event(
        db=db,
        actor_id=admin_user.id,
        action="SYSTEM_BOOTSTRAP_SUCCESS",
        resource_type="User",
        resource_id=admin_user.id,
        details={
            "email": admin_user.email,
            "role": "SUPER_ADMIN",
            "message": "Initial Central AICTE Administrator bootstrapped successfully.",
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()

    # 5. Emit JWT
    role_codes = ["SUPER_ADMIN"]
    access_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        roles=role_codes,
        institution_id=None,
        assigned_region=admin_user.assigned_region,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserProfile(
            id=admin_user.id,
            email=admin_user.email,
            full_name=admin_user.full_name,
            designation=admin_user.designation,
            institution_id=None,
            institution_name=None,
            assigned_region=admin_user.assigned_region,
            roles=[RoleBrief(code="SUPER_ADMIN", name="Central AICTE Administrator")],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with Argon2id password verification and emit JWT."""
    stmt = (
        select(User)
        .options(selectinload(User.institution), selectinload(User.roles))
        .where(User.email == payload.email)
    )
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


@router.post("/provision-user", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def provision_user(
    payload: ProvisionUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SUPER_ADMIN", "REGIONAL_OFFICER")),
):
    """
    Provision an authorized user for statutory evaluation or institutional representation.
    Only SUPER_ADMIN and REGIONAL_OFFICER can provision users.
    Regional Officers can only provision users within their assigned jurisdiction.
    """
    current_role_codes = [r.code for r in current_user.roles]
    is_super = "SUPER_ADMIN" in current_role_codes

    # Check target role
    target_role_stmt = select(Role).where(Role.code == payload.role_code)
    target_role = (await db.execute(target_role_stmt)).scalar_one_or_none()
    if not target_role:
        raise NotFoundError(f"Statutory role '{payload.role_code}' does not exist.")

    # Privilege elevation guard
    if payload.role_code in ("SUPER_ADMIN", "REGIONAL_OFFICER") and not is_super:
        raise PermissionDeniedError("Only Central Super Administrators can provision administrative officers.")

    # Region boundary check for Regional Officers
    target_region = payload.assigned_region or current_user.assigned_region
    if not is_super and current_user.assigned_region:
        if payload.assigned_region and payload.assigned_region != current_user.assigned_region:
            raise PermissionDeniedError("Regional Officers cannot provision users in other geographic jurisdictions.")

    # Institution association check
    inst_name = None
    if payload.role_code == "INSTITUTION_ADMIN":
        if not payload.institution_id:
            raise ValidationError("An institution_id is required when provisioning an INSTITUTION_ADMIN.")
        inst_stmt = select(Institution).where(Institution.id == payload.institution_id)
        inst = (await db.execute(inst_stmt)).scalar_one_or_none()
        if not inst:
            raise NotFoundError(f"Institution with ID '{payload.institution_id}' not found.")
        inst_name = inst.name

    # Duplicate check
    clean_email = payload.email.lower().strip()
    dup_stmt = select(User).where(User.email == clean_email)
    existing_user = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing_user:
        raise ConflictError(f"User with email '{clean_email}' already exists.")

    if len(payload.password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")

    # Create User
    new_user = User(
        email=clean_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        designation=payload.designation,
        institution_id=payload.institution_id if payload.role_code == "INSTITUTION_ADMIN" else None,
        assigned_region=target_region,
        roles=[target_role],
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Audit record
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="AUTH_USER_PROVISIONED",
        resource_type="User",
        resource_id=new_user.id,
        details={
            "email": new_user.email,
            "role": payload.role_code,
            "institution_id": new_user.institution_id,
            "provisioned_by": current_user.email,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()

    return UserProfile(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        designation=new_user.designation,
        institution_id=new_user.institution_id,
        institution_name=inst_name,
        assigned_region=new_user.assigned_region,
        roles=[RoleBrief(code=target_role.code, name=target_role.name)],
    )
