from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.workflow import WorkflowTemplate, WorkflowVersion
from app.models.user import User
from app.schemas.workflow import WorkflowTemplateResponse, WorkflowVersionDetail
from app.security.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/workflows", tags=["Configurable Workflows"])


@router.get("", response_model=List[WorkflowTemplateResponse])
async def list_workflow_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all statutory workflow templates and their version history."""
    stmt = select(WorkflowTemplate).where(WorkflowTemplate.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/templates/{template_id}/versions/current", response_model=WorkflowVersionDetail)
async def get_current_workflow_version(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the active published version and state machine rules for a template."""
    stmt = (
        select(WorkflowVersion)
        .where(WorkflowVersion.template_id == template_id, WorkflowVersion.is_published.is_(True))
        .order_by(WorkflowVersion.version_number.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise NotFoundError("Published WorkflowVersion for Template", template_id)
    return version
