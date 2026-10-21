"""
CRUD module exports.
"""
from src.crud.base import CRUDBase
from src.crud.user import user_crud
from src.crud.connected_account import connected_account_crud
from src.crud.email import email_crud
from src.crud.task import task_crud
from src.crud.calendar_event import calendar_event_crud
from src.crud.notification import notification_crud
from src.crud.user_preferences import user_preferences_crud

__all__ = [
    "CRUDBase",
    "user_crud",
    "connected_account_crud",
    "email_crud",
    "task_crud",
    "calendar_event_crud",
    "notification_crud",
    "user_preferences_crud",
]