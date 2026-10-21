"""
SQLAlchemy 2.0 models for MailMind AI backend.
All entities from the API surface analysis are defined here.
"""
import enum
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    String,
    Text,
    Integer,
    ForeignKey,
    Enum,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


# Enums for categorization
class EmailCategory(str, enum.Enum):
    WORK = "Work"
    COLLEGE = "College"
    PERSONAL = "Personal"
    CLIENT = "Client"
    FINANCE = "Finance"
    PROMOTIONS = "Promotions"
    SECURITY = "Security"
    CAREER = "Career"
    MEETING = "Meeting"
    NOTIFICATION = "Notification"
    URGENT = "Urgent"


class EmailUrgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationType(str, enum.Enum):
    AI_DRAFT = "ai_draft"
    REMINDER = "reminder"


class AIAnalysisSentiment(str, enum.Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"
    ALERT = "Alert"


class UserPlan(str, enum.Enum):
    FREE = "Free"
    PRO = "Pro Plan"
    ENTERPRISE = "Enterprise"


# Core Models
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    plan: Mapped[UserPlan] = mapped_column(Enum(UserPlan), default=UserPlan.FREE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    connected_accounts: Mapped[List["ConnectedAccount"]] = relationship(
        "ConnectedAccount", back_populates="user", cascade="all, delete-orphan"
    )
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    calendar_events: Mapped[List["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="gmail")  # gmail, outlook, etc.
    status: Mapped[str] = mapped_column(String(20), default="connected")  # connected, disconnected, error
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted token
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted token
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="connected_accounts")


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Email headers
    message_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # Date part only

    # Classification
    category: Mapped[EmailCategory] = mapped_column(Enum(EmailCategory), nullable=False)
    urgency: Mapped[EmailUrgency] = mapped_column(Enum(EmailUrgency), nullable=False)
    requires_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    folder: Mapped[str] = mapped_column(String(50), default="inbox")  # inbox, sent, drafts, spam, trash, etc.
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Threading
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # AI Analysis
    ai_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_sentiment: Mapped[Optional[AIAnalysisSentiment]] = mapped_column(Enum(AIAnalysisSentiment), nullable=True)
    ai_requires_reply: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ai_key_points: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Array of strings
    ai_extracted_tasks: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    ai_extracted_deadlines: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # ISO date strings
    ai_suspicious_flag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ai_suggested_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="emails")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="email")
    calendar_events: Mapped[List["CalendarEvent"]] = relationship(
        "CalendarEvent", foreign_keys="[CalendarEvent.email_id]", back_populates="related_email"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    email: Mapped[Optional["Email"]] = relationship("Email", back_populates="tasks")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    # Classification
    category: Mapped[EmailCategory] = mapped_column(Enum(EmailCategory), nullable=False)
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Meeting, Call, Event, etc.
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Google Meet, Zoom, etc.

    # Source
    detected_from_email: Mapped[bool] = mapped_column(Boolean, default=False)  # True if auto-detected from email
    related_email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendar_events")
    related_email: Mapped[Optional["Email"]] = relationship("Email", foreign_keys=[email_id])
    detected_from: Mapped[Optional["Email"]] = relationship(
        "Email", foreign_keys=[related_email_id], post_update=True
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # Link to source
    email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id"), nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    email: Mapped[Optional["Email"]] = relationship("Email")
    task: Mapped[Optional["Task"]] = relationship("Task")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Appearance
    theme: Mapped[str] = mapped_column(String(20), default="light")  # light, dark, system
    layout_density: Mapped[str] = mapped_column(String(20), default="comfortable")  # comfortable, compact

    # AI & Reply Engine
    ai_model: Mapped[str] = mapped_column(String(50), default="gemini-1.5-pro")
    default_reply_tone: Mapped[str] = mapped_column(String(20), default="professional")
    auto_draft_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    phishing_shield_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_confidence_threshold: Mapped[int] = mapped_column(Integer, default=80)  # 0-100

    # Gmail & Sync
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=5)  # 1, 2, 5, 15, 30, 60

    # Notifications
    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sound_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # email, task, user, etc.
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Changes
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Before/after snapshot

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


class AutoReplyRule(Base):
    __tablename__ = "auto_reply_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[EmailCategory]] = mapped_column(Enum(EmailCategory), nullable=True)
    sender_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    reply_template: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)  # False = save as draft for approval

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


class AIReplyDraft(Base):
    __tablename__ = "ai_reply_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_id: Mapped[int] = mapped_column(Integer, ForeignKey("emails.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    tone: Mapped[str] = mapped_column(String(50), default="professional")
    language: Mapped[str] = mapped_column(String(50), default="english")
    content: Mapped[str] = mapped_column(Text, nullable=False)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    email: Mapped["Email"] = relationship("Email")