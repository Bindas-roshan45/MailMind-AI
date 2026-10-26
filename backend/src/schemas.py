"""
Pydantic 2.0 schemas for MailMind AI API.
Defines request/response models with validation.
"""
from datetime import datetime, date
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, EmailStr
import enum

# Re-use enums from models for consistency
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


# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseSchema):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    avatar_url: Optional[str] = None
    plan: UserPlan = UserPlan.FREE


class UserCreate(UserBase):
    pass


class UserUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = None
    plan: Optional[UserPlan] = None


class UserInDBBase(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class User(UserInDBBase):
    pass


class UserProfile(BaseSchema):
    id: int
    email: EmailStr
    name: str
    avatar_url: Optional[str]
    plan: UserPlan
    is_active: bool
    connected_accounts_count: int = 0


# Connected Account schemas
class ConnectedAccountBase(BaseSchema):
    email: EmailStr
    provider: str = "gmail"
    status: str = "connected"


class ConnectedAccountCreate(ConnectedAccountBase):
    pass


class ConnectedAccountUpdate(BaseSchema):
    status: Optional[str] = None
    last_sync: Optional[datetime] = None


class ConnectedAccountInDB(ConnectedAccountBase):
    id: int
    user_id: int
    last_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ConnectedAccount(ConnectedAccountInDB):
    pass


ConnectedAccountResponse = ConnectedAccount


# Email schemas
class EmailBase(BaseSchema):
    from_name: str
    from_email: EmailStr
    to: EmailStr
    subject: str = Field(..., max_length=500)
    preview: Optional[str] = None
    body: Optional[str] = None
    received_at: datetime
    date: Optional[date] = None
    category: EmailCategory
    urgency: EmailUrgency
    requires_reply: bool = False
    is_read: bool = False
    is_starred: bool = False
    is_important: bool = False
    folder: str = "inbox"
    has_attachments: bool = False
    attachment_count: int = 0
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    ai_confidence: Optional[int] = Field(None, ge=0, le=100)
    ai_category: Optional[str] = None
    ai_priority: Optional[str] = None
    ai_sentiment: Optional[AIAnalysisSentiment] = None
    ai_requires_reply: Optional[bool] = None
    ai_key_points: Optional[List[str]] = None
    ai_extracted_tasks: Optional[List[str]] = None
    ai_extracted_deadlines: Optional[List[str]] = None
    ai_suspicious_flag: Optional[bool] = None
    ai_suggested_reply: Optional[str] = None


class EmailCreate(EmailBase):
    user_id: int


class EmailUpdate(BaseSchema):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    is_important: Optional[bool] = None
    folder: Optional[str] = None
    requires_reply: Optional[bool] = None


class EmailInDBBase(EmailBase):
    id: int
    user_id: int
    message_id: Optional[str]
    ai_confidence: Optional[int]
    ai_category: Optional[str]
    ai_priority: Optional[str]
    ai_sentiment: Optional[AIAnalysisSentiment]
    ai_requires_reply: Optional[bool]
    ai_key_points: Optional[List[str]]
    ai_extracted_tasks: Optional[List[str]]
    ai_extracted_deadlines: Optional[List[str]]
    ai_suspicious_flag: Optional[bool]
    ai_suggested_reply: Optional[str]
    created_at: datetime
    updated_at: datetime


class Email(EmailInDBBase):
    pass


class EmailWithThreads(Email):
    thread: List["Email"] = []


EmailResponse = Email
EmailListResponse = List[Email]


# Task schemas
class TaskBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    done: bool = False


class TaskCreate(TaskBase):
    user_id: Optional[int] = None
    email_id: Optional[int] = None


class TaskUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    done: Optional[bool] = None


class TaskInDBBase(TaskBase):
    id: int
    user_id: int
    email_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class Task(TaskInDBBase):
    pass


TaskResponse = Task


# Calendar Event schemas
class CalendarEventBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    category: EmailCategory = EmailCategory.WORK
    event_type: Optional[str] = None
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    detected_from_email: bool = False


class CalendarEventCreate(CalendarEventBase):
    user_id: Optional[int] = None
    email_id: Optional[int] = None


class CalendarEventUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    category: Optional[EmailCategory] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    meeting_url: Optional[str] = None


class CalendarEventInDBBase(CalendarEventBase):
    id: int
    user_id: int
    email_id: Optional[int]
    detected_from_email_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class CalendarEvent(CalendarEventInDBBase):
    pass


CalendarEventResponse = CalendarEvent


# Notification schemas
class NotificationBase(BaseSchema):
    type: NotificationType
    title: str = Field(..., min_length=1, max_length=255)
    body: Optional[str] = None
    is_read: bool = False


class NotificationCreate(NotificationBase):
    user_id: int
    email_id: Optional[int] = None
    task_id: Optional[int] = None


class NotificationUpdate(BaseSchema):
    is_read: Optional[bool] = None


class NotificationInDBBase(NotificationBase):
    id: int
    user_id: int
    email_id: Optional[int]
    task_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime] = None


class Notification(NotificationInDBBase):
    pass


# User Preferences schemas
class UserPreferencesBase(BaseSchema):
    theme: str = "light"
    layout_density: str = "comfortable"
    ai_model: str = "gemini-1.5-pro"
    default_reply_tone: str = "professional"
    auto_draft_enabled: bool = False
    phishing_shield_enabled: bool = True
    ai_confidence_threshold: int = Field(80, ge=0, le=100)
    auto_sync_enabled: bool = True
    sync_interval_minutes: int = 5
    push_notifications_enabled: bool = True
    sound_alerts_enabled: bool = True
    daily_digest_enabled: bool = False
    email_notifications_enabled: bool = True
    # Automation & Personalization
    automation_paused: bool = False
    automation_mode: str = "draft_only"
    daily_reply_limit: int = 20
    min_confidence_score: int = 85
    sender_allowlist: Optional[List[str]] = None
    sender_blocklist: Optional[List[str]] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    timezone: str = "UTC"
    custom_instructions: Optional[str] = None


class UserPreferencesCreate(UserPreferencesBase):
    user_id: int


class UserPreferencesUpdate(BaseSchema):
    theme: Optional[str] = None
    layout_density: Optional[str] = None
    ai_model: Optional[str] = None
    default_reply_tone: Optional[str] = None
    auto_draft_enabled: Optional[bool] = None
    phishing_shield_enabled: Optional[bool] = None
    ai_confidence_threshold: Optional[int] = Field(None, ge=0, le=100)
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    push_notifications_enabled: Optional[bool] = None
    sound_alerts_enabled: Optional[bool] = None
    daily_digest_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    # Automation & Personalization updates
    automation_paused: Optional[bool] = None
    automation_mode: Optional[str] = None
    daily_reply_limit: Optional[int] = None
    min_confidence_score: Optional[int] = None
    sender_allowlist: Optional[List[str]] = None
    sender_blocklist: Optional[List[str]] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    custom_instructions: Optional[str] = None


class UserPreferencesInDBBase(UserPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class UserPreferences(UserPreferencesInDBBase):
    pass


# Analytics schemas
class AnalyticsWeeklyData(BaseSchema):
    day: str
    received: int
    replied: int


class AnalyticsResponse(BaseSchema):
    weekly_data: List[AnalyticsWeeklyData]
    total_received: int
    total_replied: int
    pending: int
    urgent: int


# Report schemas (simplified for Phase 1)
class ReportSection(BaseSchema):
    title: str
    content: dict


class ReportResponse(BaseSchema):
    date_range: str
    sections: List[ReportSection]
    generated_at: datetime


# Folder count schemas
class FolderCount(BaseSchema):
    folder: str
    count: int


class FolderCountsResponse(BaseSchema):
    folders: List[FolderCount]


# Demo mode indicator
class DemoInfo(BaseSchema):
    demo_mode: bool = True
    message: str = "Running in demo mode - using mock data"


# Auto-reply rule schemas
class AutoReplyRuleBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[EmailCategory] = None
    sender_pattern: Optional[str] = None
    keywords: Optional[List[str]] = None
    reply_template: str
    is_active: bool = True
    auto_send: bool = False


class AutoReplyRuleCreate(AutoReplyRuleBase):
    pass


class AutoReplyRuleUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[EmailCategory] = None
    sender_pattern: Optional[str] = None
    keywords: Optional[List[str]] = None
    reply_template: Optional[str] = None
    is_active: Optional[bool] = None
    auto_send: Optional[bool] = None


class AutoReplyRuleResponse(AutoReplyRuleBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# AI reply draft schemas
class AIReplyDraftBase(BaseSchema):
    email_id: int
    tone: str = "professional"
    language: str = "english"
    content: str


class AIReplyDraftCreate(AIReplyDraftBase):
    pass


class AIReplyDraftUpdate(BaseSchema):
    content: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None
    is_approved: Optional[bool] = None
    is_sent: Optional[bool] = None


class AIReplyDraftResponse(AIReplyDraftBase):
    id: int
    user_id: int
    is_approved: bool
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# API Response wrapper
class APIResponse(BaseSchema):
    success: bool = True
    data: Union[dict, list, BaseSchema, None] = None
    message: Optional[str] = None
    demo_mode: bool = True


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class AuthTokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[UserProfile] = None