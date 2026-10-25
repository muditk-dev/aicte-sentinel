import asyncio
import os
import sys
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db
from app.models.institution import Institution
from app.models.user import User, Role, Permission
from app.models.workflow import WorkflowTemplate, WorkflowVersion
from app.models.application import Application
from app.security.password import hash_password
from app.security.tokens import create_access_token
from app.workflows.engine import DEFAULT_STATE_MACHINE
import json

# In-memory SQLite engine for fast, isolated test suite
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def seed_test_data(db_session: AsyncSession):
    # Create institution
    inst = Institution(
        id="inst-test-uuid-1",
        name="Apex Institute of Technology",
        code="1-99998888",
        region="Northern",
        state="Delhi",
        district="New Delhi",
        institution_type="Government",
        contact_email="admin@apex.edu.in",
        contact_phone="+91-11-99998888",
    )
    db_session.add(inst)
    await db_session.flush()

    # Permissions & Roles
    p1 = Permission(code="app:create", name="Create App")
    p2 = Permission(code="scrutiny:execute", name="Scrutiny")
    db_session.add_all([p1, p2])
    await db_session.flush()

    r_admin = Role(code="SUPER_ADMIN", name="Super Admin", permissions=[p1, p2])
    r_inst = Role(code="INSTITUTION_ADMIN", name="Institution Admin", permissions=[p1])
    r_scrutiny = Role(code="SCRUTINY_OFFICER", name="Scrutiny Officer", permissions=[p2])
    db_session.add_all([r_admin, r_inst, r_scrutiny])
    await db_session.flush()

    # Users
    u_admin = User(
        id="user-admin-1",
        email="superadmin@aicte-india.org",
        hashed_password=hash_password("Sentinel@Admin2026!"),
        full_name="Admin Test",
        roles=[r_admin],
    )
    u_inst = User(
        id="user-inst-1",
        email="inst@apex.edu.in",
        hashed_password=hash_password("College@2026!"),
        full_name="College Signatory",
        institution_id=inst.id,
        roles=[r_inst],
    )
    u_scrutiny = User(
        id="user-scrutiny-1",
        email="scrutiny@aicte-india.org",
        hashed_password=hash_password("Scrutiny@2026!"),
        full_name="Scrutiny Officer Test",
        roles=[r_scrutiny],
    )
    db_session.add_all([u_admin, u_inst, u_scrutiny])
    await db_session.flush()

    # Workflow Template & Version
    tmpl = WorkflowTemplate(
        id="tmpl-test-1",
        code="EXTENSION_OF_APPROVAL",
        name="Extension of Approval",
        category="Engineering",
    )
    db_session.add(tmpl)
    await db_session.flush()

    version = WorkflowVersion(
        id="ver-test-1",
        template_id=tmpl.id,
        version_number=1,
        aph_edition="APH 2026-27",
        state_machine_json=json.dumps(DEFAULT_STATE_MACHINE),
        checklist_rules_json="{}",
        is_published=True,
    )
    db_session.add(version)
    await db_session.flush()

    # Application
    application = Application(
        id="app-test-1",
        application_number="AICTE-2026-TEST-001",
        institution_id=inst.id,
        template_id=tmpl.id,
        version_id=version.id,
        current_status="SUBMITTED",
        academic_year="2026-2027",
        applicant_user_id=u_inst.id,
    )
    db_session.add(application)
    await db_session.commit()

    return {
        "institution": inst,
        "users": {"admin": u_admin, "inst": u_inst, "scrutiny": u_scrutiny},
        "template": tmpl,
        "version": version,
        "application": application,
    }
