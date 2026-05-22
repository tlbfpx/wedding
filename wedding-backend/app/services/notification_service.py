from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.utils.pagination import PageResponse


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        title: str,
        content: str,
        type: str,
        related_id: int | None = None,
        related_type: str | None = None,
    ) -> Notification:
        """Create a notification. Does NOT commit — caller manages the transaction."""
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=type,
            related_id=related_id,
            related_type=related_type,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def list_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse:
        query = select(Notification).where(Notification.user_id == user_id)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        if type is not None:
            query = query.where(Notification.type == type)

        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        notifications = result.scalars().all()

        return PageResponse(
            items=[notification_to_dict(n) for n in notifications],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def get_unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one()

    async def mark_as_read(self, user_id: int, ids: list[int]) -> None:
        """Mark specified notifications as read. Does NOT commit."""
        if not ids:
            return
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id.in_(ids),
                    Notification.user_id == user_id,
                )
            )
        )
        for notification in result.scalars().all():
            notification.is_read = True
        await self.db.flush()

    async def mark_all_as_read(self, user_id: int) -> None:
        """Mark all unread notifications as read. Does NOT commit."""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
        )
        for notification in result.scalars().all():
            notification.is_read = True
        await self.db.flush()


# ── Serialization helpers ────────────────────────────────────────────────────

def notification_to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "type": n.type,
        "is_read": n.is_read,
        "related_id": n.related_id,
        "related_type": n.related_type,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }
