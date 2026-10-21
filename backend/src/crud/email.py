"""
Email CRUD operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import Email, EmailCategory, EmailUrgency
from src.schemas import EmailCreate, EmailUpdate


class CRUDEmail(CRUDBase):
    """CRUD for Email model."""

    def __init__(self):
        super().__init__(Email)

    async def get_by_message_id(
        self, db: AsyncSession, message_id: str
    ) -> Optional[Email]:
        """Get email by Gmail message ID."""
        result = await db.execute(select(Email).where(Email.message_id == message_id))
        return result.scalar_one_or_none()

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        folder: Optional[str] = None,
        filter_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Email]:
        """Get emails for a user with filtering."""
        query = select(Email).where(Email.user_id == user_id)

        if folder:
            if folder == "all":
                pass  # Show all emails
            elif folder == "unread":
                query = query.where(Email.is_read == False)
            elif folder == "starred":
                query = query.where(Email.is_starred == True)
            elif folder == "important":
                query = query.where(Email.is_important == True)
            elif folder == "sent":
                query = query.where(Email.folder == "sent")
            elif folder == "drafts":
                query = query.where(Email.folder == "drafts")
            elif folder == "snoozed":
                query = query.where(Email.folder == "snoozed")
            else:
                query = query.where(Email.folder == folder)

        # Additional filter options
        if filter_type == "unread":
            query = query.where(Email.is_read == False)
        elif filter_type == "important":
            query = query.where(Email.is_important == True)
        elif filter_type == "needs_reply":
            query = query.where(Email.requires_reply == True)

        # Search
        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                or_(
                    Email.subject.ilike(search_term),
                    Email.from_name.ilike(search_term),
                    Email.from_email.ilike(search_term),
                    Email.preview.ilike(search_term) if Email.preview else False,
                )
            )

        query = query.order_by(Email.received_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        folder: Optional[str] = None,
        category: Optional[EmailCategory] = None,
        is_read: Optional[bool] = None,
        is_starred: Optional[bool] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Email]:
        """List emails for a user with optional folder/category/read/star/search filters."""
        query = select(Email).where(Email.user_id == user_id)

        if folder:
            if folder == "starred":
                query = query.where(Email.is_starred == True)  # noqa: E712
            elif folder == "important":
                query = query.where(Email.is_important == True)  # noqa: E712
            elif folder not in ("all", "unread"):
                query = query.where(Email.folder == folder)
            if folder == "unread":
                query = query.where(Email.is_read == False)  # noqa: E712

        if category:
            query = query.where(Email.category == category)
        if is_read is not None:
            query = query.where(Email.is_read == is_read)
        if is_starred is not None:
            query = query.where(Email.is_starred == is_starred)
        if search_query:
            search_term = f"%{search_query.lower()}%"
            query = query.where(
                or_(
                    Email.subject.ilike(search_term),
                    Email.from_name.ilike(search_term),
                    Email.from_email.ilike(search_term),
                    Email.preview.ilike(search_term),
                )
            )

        query = query.order_by(Email.received_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_folder_counts(
        self, db: AsyncSession, user_id: int
    ) -> dict:
        """Get count of emails per folder."""
        result = await db.execute(
            select(Email.folder, func.count()).where(Email.user_id == user_id)
            .group_by(Email.folder)
        )
        counts = {row[0]: row[1] for row in result.fetchall()}
        # Return standard folder counts
        return {
            "inbox": counts.get("inbox", 0),
            "starred": counts.get("starred", 0) if "starred" in counts else 0,
            "important": counts.get("important", 0),
            "snoozed": counts.get("snoozed", 0),
            "sent": counts.get("sent", 0),
            "drafts": counts.get("drafts", 0),
        }

    async def _resolve(self, db: AsyncSession, email_or_id) -> Optional[Email]:
        if isinstance(email_or_id, Email):
            return email_or_id
        return await self.get(db, email_or_id)

    async def mark_as_read(
        self, db: AsyncSession, db_obj_or_id
    ) -> Optional[Email]:
        """Mark email as read by model or id."""
        db_obj = await self._resolve(db, db_obj_or_id)
        if not db_obj:
            return None
        db_obj.is_read = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def toggle_star(
        self, db: AsyncSession, db_obj_or_id
    ) -> Optional[Email]:
        """Toggle email starred status by model or id."""
        db_obj = await self._resolve(db, db_obj_or_id)
        if not db_obj:
            return None
        db_obj.is_starred = not db_obj.is_starred
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_ai_analysis(
        self,
        db: AsyncSession,
        db_obj: Email,
        *,
        confidence: Optional[int] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        sentiment: Optional[str] = None,
        requires_reply: Optional[bool] = None,
        key_points: Optional[List[str]] = None,
        suspicious_flag: Optional[bool] = None,
        suggested_reply: Optional[str] = None,
        extracted_tasks: Optional[List[str]] = None,
        extracted_deadlines: Optional[List[str]] = None,
    ) -> Email:
        """Update AI analysis fields."""
        if confidence is not None:
            db_obj.ai_confidence = confidence
        if category is not None:
            db_obj.ai_category = category
        if priority is not None:
            db_obj.ai_priority = priority
        if sentiment is not None:
            db_obj.ai_sentiment = sentiment
        if requires_reply is not None:
            db_obj.requires_reply = requires_reply
        if key_points is not None:
            db_obj.ai_key_points = key_points
        if suspicious_flag is not None:
            db_obj.ai_suspicious_flag = suspicious_flag
        if suggested_reply is not None:
            db_obj.ai_suggested_reply = suggested_reply
        if extracted_tasks is not None:
            db_obj.ai_extracted_tasks = extracted_tasks
        if extracted_deadlines is not None:
            db_obj.ai_extracted_deadlines = extracted_deadlines

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


email_crud = CRUDEmail()