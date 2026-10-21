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
        """Get accurate count of emails per folder/flag."""
        inbox_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.folder == "inbox")) or 0
        starred_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.is_starred == True)) or 0
        important_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.is_important == True)) or 0
        snoozed_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.folder == "snoozed")) or 0
        sent_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.folder == "sent")) or 0
        drafts_c = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id, Email.folder == "drafts")) or 0
        return {
            "inbox": inbox_c,
            "starred": starred_c,
            "important": important_c,
            "snoozed": snoozed_c,
            "sent": sent_c,
            "drafts": drafts_c,
        }

    async def seed_demo_emails_if_needed(self, db: AsyncSession, user_id: int) -> int:
        """Seed demo emails if user inbox is empty in DEMO_MODE."""
        count = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user_id)) or 0
        if count > 0:
            return 0

        from datetime import datetime, timezone, timedelta
        from src.models import AIAnalysisSentiment

        now = datetime.now(timezone.utc)
        demo_items = [
            {
                "user_id": user_id,
                "message_id": f"demo-msg-001-{user_id}",
                "from_name": "John Smith",
                "from_email": "john@techcorp.com",
                "to": "roshan@gmail.com",
                "subject": "Website Project Inquiry",
                "preview": "Hi, I want to develop a website for my company. Please share your pricing, timeline and services.",
                "body": "Hi,\n\nI want to develop a website for my company. Please share your pricing, timeline and the services you offer.\n\nLooking forward to your response.\n\nBest regards,\nJohn",
                "received_at": now - timedelta(minutes=14),
                "category": EmailCategory.CLIENT,
                "urgency": EmailUrgency.HIGH,
                "requires_reply": True,
                "is_read": False,
                "is_starred": True,
                "is_important": True,
                "folder": "inbox",
                "ai_confidence": 95,
                "ai_category": "Client Inquiry",
                "ai_priority": "High",
                "ai_sentiment": AIAnalysisSentiment.NEUTRAL,
                "ai_key_points": [
                    "Interested in website development",
                    "Asking for pricing, timeline and services",
                    "High business priority new client"
                ],
                "ai_extracted_tasks": ["Prepare website pricing proposal", "Send portfolio"],
                "ai_suggested_reply": "Hi John,\n\nThank you for reaching out. We specialize in modern web development and would love to help you build your company website. Our typical timeline is 2-4 weeks.\n\nCould we schedule a brief 15-minute call this week to discuss your requirements?\n\nBest regards,\nRoshan Kumar",
            },
            {
                "user_id": user_id,
                "message_id": f"demo-msg-002-{user_id}",
                "from_name": "ABC College",
                "from_email": "admin@abccollege.edu",
                "to": "roshan@gmail.com",
                "subject": "Project Submission Deadline",
                "preview": "Dear Students, submit your project report before the deadline to avoid late submission penalties.",
                "body": "Dear Students,\n\nThis is a reminder that the project submission deadline is October 20, 2026. Please submit your project report before the deadline to avoid late submission penalties.\n\nBest regards,\nAdmin Office",
                "received_at": now - timedelta(hours=1, minutes=10),
                "category": EmailCategory.COLLEGE,
                "urgency": EmailUrgency.URGENT,
                "requires_reply": False,
                "is_read": False,
                "is_starred": False,
                "is_important": True,
                "folder": "inbox",
                "ai_confidence": 92,
                "ai_category": "College",
                "ai_priority": "High",
                "ai_sentiment": AIAnalysisSentiment.NEUTRAL,
                "ai_key_points": ["Project submission deadline: Oct 20, 2026", "Late penalty applies"],
                "ai_extracted_tasks": ["Submit project report by Oct 20"],
                "ai_extracted_deadlines": ["October 20, 2026"],
            },
            {
                "user_id": user_id,
                "message_id": f"demo-msg-003-{user_id}",
                "from_name": "Google Security",
                "from_email": "no-reply@google.com",
                "to": "roshan@gmail.com",
                "subject": "Security Alert - New Sign-in",
                "preview": "A new sign-in was detected on your account from a Windows device in Mumbai.",
                "body": "Hi Roshan,\n\nA new sign-in was detected on your Google Account from a new Windows device in Mumbai.\n\nIf this was you, you do not need to do anything. If not, please review your account activity.\n\nGoogle Security Team",
                "received_at": now - timedelta(hours=2, minutes=45),
                "category": EmailCategory.SECURITY,
                "urgency": EmailUrgency.HIGH,
                "requires_reply": False,
                "is_read": True,
                "is_starred": False,
                "is_important": True,
                "folder": "inbox",
                "ai_confidence": 88,
                "ai_category": "Security",
                "ai_priority": "High",
                "ai_sentiment": AIAnalysisSentiment.ALERT,
                "ai_key_points": ["Sign-in from new device in Mumbai", "Verify unauthorized access if not recognized"],
                "ai_extracted_tasks": ["Verify if sign-in was authorized"],
            },
            {
                "user_id": user_id,
                "message_id": f"demo-msg-004-{user_id}",
                "from_name": "Sarah (Engineering)",
                "from_email": "sarah@myteam.io",
                "to": "roshan@gmail.com",
                "subject": "Team Meeting Confirmation",
                "preview": "The meeting is scheduled for tomorrow at 11 AM via Google Meet. Please confirm your attendance.",
                "body": "Hi Roshan,\n\nThe team meeting is scheduled for tomorrow at 11:00 AM via Google Meet.\n\nAgenda:\n- Sprint review\n- Q4 planning\n- Product roadmap\n\nPlease let me know if you can make it!\n\nBest,\nSarah",
                "received_at": now - timedelta(hours=3, minutes=15),
                "category": EmailCategory.WORK,
                "urgency": EmailUrgency.MEDIUM,
                "requires_reply": True,
                "is_read": True,
                "is_starred": False,
                "is_important": True,
                "folder": "inbox",
                "ai_confidence": 97,
                "ai_category": "Work",
                "ai_priority": "Medium",
                "ai_sentiment": AIAnalysisSentiment.POSITIVE,
                "ai_key_points": ["Team meeting tomorrow 11 AM", "Google Meet", "Sprint review + roadmap"],
                "ai_extracted_tasks": ["Confirm meeting attendance"],
                "ai_extracted_deadlines": ["Tomorrow, 11:00 AM"],
                "ai_suggested_reply": "Hi Sarah,\n\nConfirmed, I will be attending the meeting tomorrow at 11:00 AM. Looking forward to the roadmap discussion.\n\nBest,\nRoshan",
            },
            {
                "user_id": user_id,
                "message_id": f"demo-msg-005-{user_id}",
                "from_name": "Amazon Orders",
                "from_email": "orders@amazon.in",
                "to": "roshan@gmail.com",
                "subject": "Your Order Has Been Shipped",
                "preview": "Your order #12345 has been shipped and will be delivered by Oct 15.",
                "body": "Hello Roshan,\n\nYour package with order ID #12345 has been dispatched and is out for transit.\nEstimated Delivery: October 15, 2026.\n\nThank you for shopping on Amazon.",
                "received_at": now - timedelta(hours=6),
                "category": EmailCategory.PROMOTIONS,
                "urgency": EmailUrgency.LOW,
                "requires_reply": False,
                "is_read": True,
                "is_starred": False,
                "is_important": False,
                "folder": "inbox",
                "ai_confidence": 99,
                "ai_category": "Promotions",
                "ai_priority": "Low",
                "ai_sentiment": AIAnalysisSentiment.POSITIVE,
                "ai_key_points": ["Order #12345 shipped", "Delivery scheduled for Oct 15"],
            },
            {
                "user_id": user_id,
                "message_id": f"demo-msg-006-{user_id}",
                "from_name": "LinkedIn Jobs",
                "from_email": "jobs-listings@linkedin.com",
                "to": "roshan@gmail.com",
                "subject": "New Job Recommendations for You",
                "preview": "Based on your search history: Senior Full-Stack Engineer, AI Solutions Architect, and more.",
                "body": "Hi Roshan,\n\nTop opportunities matching your experience:\n1. Senior Full-Stack AI Engineer @ Stripe\n2. Staff Backend Architect @ Anthropic\n3. Lead Frontend Developer @ Vercel\n\nView jobs and apply directly on LinkedIn.",
                "received_at": now - timedelta(hours=8),
                "category": EmailCategory.CAREER,
                "urgency": EmailUrgency.LOW,
                "requires_reply": False,
                "is_read": True,
                "is_starred": False,
                "is_important": False,
                "folder": "inbox",
                "ai_confidence": 91,
                "ai_category": "Career",
                "ai_priority": "Low",
                "ai_sentiment": AIAnalysisSentiment.NEUTRAL,
                "ai_key_points": ["3 matching tech roles recommended on LinkedIn"],
            },
        ]

        for item in demo_items:
            if "created_at" not in item:
                item["created_at"] = now
            if "updated_at" not in item:
                item["updated_at"] = now
            db_obj = Email(**item)
            db.add(db_obj)
        await db.commit()
        return len(demo_items)

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