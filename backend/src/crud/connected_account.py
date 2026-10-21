"""
Connected Account CRUD operations.
Handles encrypted OAuth tokens storage.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import ConnectedAccount
from src.schemas import ConnectedAccountCreate, ConnectedAccountUpdate


class CRUDConnectedAccount(CRUDBase):
    """CRUD for ConnectedAccount model."""

    def __init__(self):
        super().__init__(ConnectedAccount)

    async def get_by_user(
        self, db: AsyncSession, user_id: int
    ) -> List[ConnectedAccount]:
        """Get all connected accounts for a user."""
        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_user_and_provider(
        self, db: AsyncSession, user_id: int, provider: str
    ) -> Optional[ConnectedAccount]:
        """Get connected account by user and provider."""
        result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.user_id == user_id,
                ConnectedAccount.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def create_with_tokens(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        email: str,
        provider: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expires_at: Optional[datetime] = None,
    ) -> ConnectedAccount:
        """Create connected account with encrypted tokens."""
        from cryptography.fernet import Fernet
        import os

        # In production, use a proper key management system
        # Here we just store encrypted tokens
        account = ConnectedAccount(
            user_id=user_id,
            email=email,
            provider=provider,
            status="connected",
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=token_expires_at,
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        return account

    async def update_status(
        self, db: AsyncSession, db_obj: ConnectedAccount, status: str
    ) -> ConnectedAccount:
        """Update account status (e.g., connected, disconnected, error)."""
        db_obj.status = status
        if status == "connected":
            db_obj.last_sync = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_tokens(
        self,
        db: AsyncSession,
        db_obj: ConnectedAccount,
        *,
        access_token_encrypted: Optional[str] = None,
        refresh_token_encrypted: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> ConnectedAccount:
        """Update OAuth tokens."""
        if access_token_encrypted is not None:
            db_obj.access_token_encrypted = access_token_encrypted
        if refresh_token_encrypted is not None:
            db_obj.refresh_token_encrypted = refresh_token_encrypted
        if token_expires_at is not None:
            db_obj.token_expires_at = token_expires_at
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


connected_account_crud = CRUDConnectedAccount()