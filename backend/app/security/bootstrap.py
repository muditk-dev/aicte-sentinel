from typing import Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import Role, Permission

STATUTORY_PERMISSIONS: List[Tuple[str, str, str]] = [
    ("app:create", "Create Application", "Ability to submit initial statutory applications"),
    ("app:view", "View Application", "Ability to inspect applications within tenant context"),
    ("scrutiny:execute", "Perform Scrutiny", "Review academic, physical, and financial documents"),
    ("evc:inspect", "Conduct EVC Inspection", "Submit physical/virtual inspection reports"),
    ("committee:manage", "Manage Standing Committees", "Constitute benches and hearing dockets"),
    ("decision:grant", "Grant Statutory Approval", "Authorized signatory for approvals and rejections"),
    ("audit:inspect", "Inspect Audit Ledger", "Verify cryptographic audit chain"),
    ("policy:configure", "Configure APH Rules", "Maker-checker policy management"),
]


async def ensure_statutory_roles_and_permissions(db: AsyncSession) -> Dict[str, Role]:
    """
    Idempotently seeds statutory permissions and roles required by AICTE Sentinel.
    Safe to execute multiple times against SQLite and PostgreSQL without duplicate key errors.
    """
    perm_map: Dict[str, Permission] = {}
    for code, name, desc in STATUTORY_PERMISSIONS:
        stmt = select(Permission).where(Permission.code == code)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            perm = Permission(code=code, name=name, description=desc)
            db.add(perm)
            perm_map[code] = perm
        else:
            perm_map[code] = existing

    await db.flush()

    roles_data = [
        (
            "SUPER_ADMIN",
            "Central AICTE Administrator",
            "Full statutory governance over all national jurisdictions",
            list(perm_map.values()),
        ),
        (
            "REGIONAL_OFFICER",
            "Regional Office Director",
            "Jurisdiction over regional institutional dockets",
            [
                perm_map["app:view"],
                perm_map["scrutiny:execute"],
                perm_map["committee:manage"],
                perm_map["decision:grant"],
                perm_map["audit:inspect"],
            ],
        ),
        (
            "SCRUTINY_OFFICER",
            "Scrutiny Officer",
            "Scrutiny and deficiency cycle authority",
            [perm_map["app:view"], perm_map["scrutiny:execute"]],
        ),
        (
            "EVC_EXPERT",
            "EVC Expert Committee Member",
            "On-site and hybrid verification expert",
            [perm_map["app:view"], perm_map["evc:inspect"]],
        ),
        (
            "INSTITUTION_ADMIN",
            "Institution Authorized Signatory",
            "Institutional representative for applications and replies",
            [perm_map["app:create"], perm_map["app:view"]],
        ),
    ]

    role_map: Dict[str, Role] = {}
    for code, name, desc, perms in roles_data:
        stmt = select(Role).where(Role.code == code)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            role = Role(code=code, name=name, description=desc, permissions=perms)
            db.add(role)
            role_map[code] = role
        else:
            role_map[code] = existing

    await db.flush()
    return role_map
