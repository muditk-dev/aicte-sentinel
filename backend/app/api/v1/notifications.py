from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.deficiency import Notification
from app.models.user import User
from app.schemas.deficiency import NotificationResponse
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve notifications intended for the user or their institution."""
    conditions = []
    if current_user.institution_id:
        conditions.append(Notification.institution_id == current_user.institution_id)
    conditions.append(Notification.user_id == current_user.id)

    stmt = select(Notification).where(or_(*conditions)).order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    stmt = select(Notification).where(Notification.id == notification_id)
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if not notif:
        raise NotFoundError("Notification", notification_id)

    notif.is_read = True
    await db.commit()
    return {"status": "success", "id": notification_id, "is_read": True}


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read for this user / institution."""
    conditions = []
    if current_user.institution_id:
        conditions.append(Notification.institution_id == current_user.institution_id)
    conditions.append(Notification.user_id == current_user.id)

    stmt = update(Notification).where(or_(*conditions)).values(is_read=True)
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read."}
