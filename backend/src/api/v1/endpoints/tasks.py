"""
Task endpoints for MailMind AI.
Manages tasks extracted from emails and manual user tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.api.deps import get_current_user
from src.database import get_session
from src.crud.task import task_crud
from src.schemas import TaskCreate, APIResponse
from src.models import TaskPriority, User

router = APIRouter()


@router.get("", response_model=APIResponse, summary="List User Tasks")
async def list_tasks(
    include_completed: bool = True,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve all tasks for current user."""
    tasks = await task_crud.get_by_user(db, user_id=user.id, include_completed=include_completed)

    # If no tasks exist yet in DB, populate initial demo tasks from UI state
    if not tasks:
        demo_tasks = [
            {"title": "Submit Project Report", "priority": TaskPriority.HIGH, "done": False},
            {"title": "Follow up with Client", "priority": TaskPriority.MEDIUM, "done": False},
            {"title": "Team Meeting", "priority": TaskPriority.MEDIUM, "done": False},
            {"title": "Send Proposal", "priority": TaskPriority.LOW, "done": False},
        ]
        for dt in demo_tasks:
            t = await task_crud.create(db, user_id=user.id, **dt)
            tasks.append(t)

    task_items = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "due_date": t.due_date.isoformat() if t.due_date else "Today",
            "priority": t.priority.value if t.priority else "medium",
            "done": t.done,
            "email_id": t.email_id,
        }
        for t in tasks
    ]

    return APIResponse(success=True, data=task_items, message="Tasks fetched successfully")


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Create Task")
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Create a new task."""
    new_task = await task_crud.create(
        db,
        user_id=user.id,
        title=task_in.title,
        description=task_in.description,
        due_date=task_in.due_date,
        priority=task_in.priority,
        email_id=task_in.email_id,
    )
    return APIResponse(
        success=True,
        data={
            "id": new_task.id,
            "title": new_task.title,
            "priority": new_task.priority.value,
            "done": new_task.done,
        },
        message="Task created successfully",
    )


@router.patch("/{task_id}/toggle", response_model=APIResponse, summary="Toggle Task Completion")
async def toggle_task_done(
    task_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Toggle completed status on a task."""
    task = await task_crud.toggle_done(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return APIResponse(
        success=True,
        data={"id": task.id, "done": task.done},
        message="Task status updated",
    )


@router.delete("/{task_id}", response_model=APIResponse, summary="Delete Task")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a task."""
    task = await task_crud.delete(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return APIResponse(success=True, message="Task deleted successfully")
