"""
Task CRUD operations.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import Task, TaskPriority
from src.schemas import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase):
    """CRUD for Task model."""

    def __init__(self):
        super().__init__(Task)

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        filter_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Task]:
        """Get tasks for a user with filtering."""
        query = select(Task).where(Task.user_id == user_id)

        if filter_type == "pending":
            query = query.where(Task.done == False)
        elif filter_type == "completed":
            query = query.where(Task.done == True)
        elif filter_type == "high_priority":
            query = query.where(Task.priority == TaskPriority.HIGH)

        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term) if Task.description else False,
                )
            )

        query = query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_tasks_by_email(
        self, db: AsyncSession, email_id: int
    ) -> List[Task]:
        """Get all tasks associated with an email."""
        result = await db.execute(select(Task).where(Task.email_id == email_id))
        return result.scalars().all()

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        include_completed: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Task]:
        """Get tasks for a user."""
        query = select(Task).where(Task.user_id == user_id)
        if not include_completed:
            query = query.where(Task.done == False)
        query = query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def toggle_completion(
        self, db: AsyncSession, db_obj: Task
    ) -> Task:
        """Toggle task completion status."""
        db_obj.done = not db_obj.done
        if db_obj.done:
            db_obj.completed_at = datetime.now(timezone.utc)
        else:
            db_obj.completed_at = None
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def toggle_done(
        self, db: AsyncSession, task_id_or_obj
    ) -> Optional[Task]:
        """Toggle done by ID or Task model."""
        if isinstance(task_id_or_obj, int):
            db_obj = await self.get(db, task_id_or_obj)
            if not db_obj:
                return None
        else:
            db_obj = task_id_or_obj
        return await self.toggle_completion(db, db_obj)


task_crud = CRUDTask()