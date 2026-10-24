"""
MailMind AI — Intelligent Auto-Reply & Email Automation Engine.
Evaluates incoming emails against safety guardrails, sensitivity thresholds,
user automation rules, allowlists/blocklists, daily quotas, and loop prevention.
"""
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ai import ai_engine
from src.core.gmail import GmailClient
from src.crud.connected_account import connected_account_crud
from src.models import (
    AIReplyDraft,
    AuditLog,
    AutoReplyRule,
    Email,
    EmailCategory,
    EmailSignature,
    ProcessedMessageLog,
    User,
    UserPreferences,
)

logger = logging.getLogger("mailmind-ai.automation")

# Sensitive keywords and patterns that MUST require human review
SENSITIVE_PATTERNS = [
    r"\b(wire transfer|bank account|routing number|iban|swift|credit card|cvv|invoice payment)\b",
    r"\b(confidential|nda|attorney|lawsuit|litigation|subpoena|legal notice|breach of contract)\b",
    r"\b(password reset|verification code|2fa|otp|security alert|unauthorized login|compromised)\b",
    r"\b(unacceptable|formal complaint|escalat(e|ing|ion)|demand a refund|sue you|terrible service)\b",
    r"\b(urgent wire|urgent payment|change bank details|payroll account)\b",
]

# Automated bounce and no-reply headers/patterns
BOUNCE_PATTERNS = [
    r"mailer-daemon@",
    r"postmaster@",
    r"no-?reply@",
    r"donotreply@",
    r"automated-notifications?@",
    r"bounce[s]?\.",
    r"notification[s]?@",
]


class AutomationDecision:
    """Represents the structured decision from the automation evaluation."""

    def __init__(
        self,
        action: str,  # "AUTO_SEND", "DRAFT_ONLY", "APPROVAL_REQUIRED", "SKIP"
        category: str,
        confidence: int,
        is_sensitive: bool,
        sensitivity_reason: Optional[str] = None,
        rule_id: Optional[int] = None,
        rule_name: Optional[str] = None,
        reason: str = "",
        reply_content: Optional[str] = None,
    ):
        self.action = action
        self.category = category
        self.confidence = confidence
        self.is_sensitive = is_sensitive
        self.sensitivity_reason = sensitivity_reason
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.reason = reason
        self.reply_content = reply_content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category,
            "confidence": self.confidence,
            "is_sensitive": self.is_sensitive,
            "sensitivity_reason": self.sensitivity_reason,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "reason": self.reason,
            "reply_content": self.reply_content,
        }


class AutomationEngine:
    """Safe, rule-based automation engine for email classification and replies."""

    @staticmethod
    def assess_sensitivity(subject: str, body: str) -> Tuple[bool, Optional[str]]:
        """
        Scan email content for sensitive topics (financial, legal, security, complaints).
        Returns (is_sensitive, reason).
        """
        full_text = f"{subject or ''} {body or ''}".lower()
        for pattern in SENSITIVE_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                matched_term = match.group(0)
                if any(k in matched_term for k in ["wire", "bank", "routing", "iban", "invoice"]):
                    return True, f"Financial matter detected: '{matched_term}'"
                elif any(k in matched_term for k in ["nda", "lawsuit", "attorney", "subpoena", "legal"]):
                    return True, f"Legal topic detected: '{matched_term}'"
                elif any(k in matched_term for k in ["password", "2fa", "otp", "unauthorized", "security"]):
                    return True, f"Security or credential alert detected: '{matched_term}'"
                elif any(k in matched_term for k in ["complaint", "refund", "sue", "unacceptable"]):
                    return True, f"Customer complaint or escalation detected: '{matched_term}'"
                return True, f"Sensitive keyword matched: '{matched_term}'"
        return False, None

    @staticmethod
    def is_automated_sender(sender_email: str) -> bool:
        """Check if sender email matches typical automated or no-reply addresses."""
        clean_email = (sender_email or "").strip().lower()
        for pattern in BOUNCE_PATTERNS:
            if re.search(pattern, clean_email):
                return True
        return False

    @staticmethod
    async def get_user_signature_text(db: AsyncSession, user_id: int, is_reply: bool = True) -> str:
        """Fetch user's default signature for replies or new emails."""
        attr = EmailSignature.is_default_reply if is_reply else EmailSignature.is_default_new
        result = await db.execute(
            select(EmailSignature)
            .where(EmailSignature.user_id == user_id, attr == True)
            .order_by(EmailSignature.id.desc())
        )
        sig = result.scalars().first()
        if not sig:
            # Fall back to any signature
            result = await db.execute(
                select(EmailSignature).where(EmailSignature.user_id == user_id).order_by(EmailSignature.id.asc())
            )
            sig = result.scalars().first()

        if sig:
            sign_off = sig.custom_sign_off if sig.sign_off == "Custom" and sig.custom_sign_off else sig.sign_off
            lines = [sign_off, sig.sender_name]
            if sig.job_title and sig.company:
                lines.append(f"{sig.job_title} | {sig.company}")
            elif sig.job_title:
                lines.append(sig.job_title)
            elif sig.company:
                lines.append(sig.company)
            if sig.phone:
                lines.append(sig.phone)
            return "\n" + "\n".join(lines)
        return ""

    @classmethod
    async def evaluate_email_for_automation(
        cls,
        db: AsyncSession,
        user: User,
        email: Email,
        preferences: Optional[UserPreferences] = None,
    ) -> AutomationDecision:
        """
        Primary decision pipeline. Evaluates incoming email against user settings and rules.
        NEVER sends automatically unless all safety criteria pass and user explicitly configured it.
        """
        subject = email.subject or ""
        body = email.body or email.preview or ""
        sender_email = (email.from_email or "").lower().strip()
        user_email = (user.email or "").lower().strip()

        # 1. Global pause switch check
        if preferences and preferences.automation_paused:
            return AutomationDecision(
                action="DRAFT_ONLY",
                category=str(email.category.value if hasattr(email.category, "value") else email.category),
                confidence=email.ai_confidence or 75,
                is_sensitive=False,
                reason="Automation is globally paused by user.",
            )

        # 2. Check for self-addressed emails
        if sender_email == user_email:
            return AutomationDecision(
                action="SKIP",
                category="Personal",
                confidence=100,
                is_sensitive=False,
                reason="Skipping auto-reply to user's own email address.",
            )

        # 3. Check for automated senders, bounces, no-reply
        if cls.is_automated_sender(sender_email):
            return AutomationDecision(
                action="SKIP",
                category="Notification",
                confidence=95,
                is_sensitive=False,
                reason="Sender appears to be automated or no-reply address.",
            )

        # 4. Check blocklist
        if preferences and preferences.sender_blocklist:
            if any(blocked.lower() in sender_email for blocked in preferences.sender_blocklist if blocked):
                return AutomationDecision(
                    action="SKIP",
                    category="Blocked",
                    confidence=100,
                    is_sensitive=False,
                    reason=f"Sender '{sender_email}' is on user blocklist.",
                )

        # 5. Check if already processed (Idempotency & Loop prevention)
        msg_id = email.message_id or f"local_{email.id}"
        existing_log = await db.execute(
            select(ProcessedMessageLog).where(
                ProcessedMessageLog.user_id == user.id,
                ProcessedMessageLog.message_id == msg_id,
            )
        )
        if existing_log.scalars().first():
            return AutomationDecision(
                action="SKIP",
                category="Duplicate",
                confidence=100,
                is_sensitive=False,
                reason="Message has already been processed by automation engine.",
            )

        # Check thread history to prevent ping-pong loops (max 1 auto-reply per thread per 12h)
        if email.thread_id:
            twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
            recent_thread_reply = await db.execute(
                select(ProcessedMessageLog).where(
                    ProcessedMessageLog.user_id == user.id,
                    ProcessedMessageLog.thread_id == email.thread_id,
                    ProcessedMessageLog.action_taken == "AUTO_REPLIED",
                    ProcessedMessageLog.created_at >= twelve_hours_ago,
                )
            )
            if recent_thread_reply.scalars().first():
                return AutomationDecision(
                    action="DRAFT_ONLY",
                    category="ThreadRateLimit",
                    confidence=90,
                    is_sensitive=False,
                    reason="Thread already received an automatic reply recently. Switched to draft only to prevent loops.",
                )

        # 6. Assess Sensitivity
        is_sensitive, sensitivity_reason = cls.assess_sensitivity(subject, body)
        category_name = email.category.value if hasattr(email.category, "value") else str(email.category)

        if is_sensitive:
            # Sensitive emails MUST require approval / draft only. Never auto-send!
            return AutomationDecision(
                action="APPROVAL_REQUIRED",
                category=category_name,
                confidence=email.ai_confidence or 85,
                is_sensitive=True,
                sensitivity_reason=sensitivity_reason,
                reason=f"Sensitive topic detected: {sensitivity_reason}. Requires human review.",
            )

        # 7. Check user overall automation mode
        user_auto_mode = (preferences.automation_mode if preferences else "draft_only") or "draft_only"

        # 8. Check daily sending quota
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_limit = (preferences.daily_reply_limit if (preferences and preferences.daily_reply_limit is not None) else 20)
        count_query = select(func.count(ProcessedMessageLog.id)).where(
            ProcessedMessageLog.user_id == user.id,
            ProcessedMessageLog.action_taken == "AUTO_REPLIED",
            ProcessedMessageLog.created_at >= today_start,
        )
        daily_count_res = await db.execute(count_query)
        daily_count = daily_count_res.scalar_one_or_none() or 0

        if daily_count >= daily_limit:
            return AutomationDecision(
                action="DRAFT_ONLY",
                category=category_name,
                confidence=email.ai_confidence or 80,
                is_sensitive=False,
                reason=f"Daily auto-reply limit ({daily_limit}) reached. Draft prepared for review.",
            )

        # 9. Evaluate User's Configured AutoReplyRules
        rules_res = await db.execute(
            select(AutoReplyRule)
            .where(AutoReplyRule.user_id == user.id, AutoReplyRule.is_active == True)
            .order_by(AutoReplyRule.id.asc())
        )
        active_rules = rules_res.scalars().all()

        matching_rule: Optional[AutoReplyRule] = None
        for rule in active_rules:
            # Check category match
            if rule.category and rule.category.value != category_name:
                continue

            # Check sender pattern match
            if rule.sender_pattern:
                pat = rule.sender_pattern.lower().replace("*", ".*")
                if not re.search(pat, sender_email):
                    continue

            # Check keywords match
            if rule.keywords and len(rule.keywords) > 0:
                text_corpus = f"{subject} {body}".lower()
                if not any(k.lower() in text_corpus for k in rule.keywords if k):
                    continue

            # Rule matches!
            matching_rule = rule
            break

        # Check confidence threshold
        min_conf = (preferences.min_confidence_score if (preferences and preferences.min_confidence_score is not None) else 85)
        email_conf = email.ai_confidence or 75
        confidence_passed = email_conf >= min_conf

        # Decide Action
        if matching_rule:
            if matching_rule.auto_send and user_auto_mode == "auto_reply" and confidence_passed:
                return AutomationDecision(
                    action="AUTO_SEND",
                    category=category_name,
                    confidence=email_conf,
                    is_sensitive=False,
                    rule_id=matching_rule.id,
                    rule_name=matching_rule.name,
                    reason=f"Matches active rule '{matching_rule.name}' with auto-send authorized.",
                    reply_content=matching_rule.reply_template,
                )
            else:
                return AutomationDecision(
                    action="APPROVAL_REQUIRED" if user_auto_mode == "approval_required" else "DRAFT_ONLY",
                    category=category_name,
                    confidence=email_conf,
                    is_sensitive=False,
                    rule_id=matching_rule.id,
                    rule_name=matching_rule.name,
                    reason=f"Matches rule '{matching_rule.name}'. Saved as draft (auto_send={matching_rule.auto_send}, confidence={email_conf}%).",
                    reply_content=matching_rule.reply_template,
                )

        # Default fallback: Draft Only
        return AutomationDecision(
            action="DRAFT_ONLY",
            category=category_name,
            confidence=email_conf,
            is_sensitive=False,
            reason="No auto-send rule matched. Prepared as draft for user review.",
        )

    @classmethod
    async def process_and_record(
        cls,
        db: AsyncSession,
        user: User,
        email: Email,
        gmail_client: Optional[GmailClient] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> Dict[str, Any]:
        """
        Executes the automation decision: creates draft or dispatches reply if safely permitted,
        attaches user signature, logs to ProcessedMessageLog and AuditLog.
        """
        decision = await cls.evaluate_email_for_automation(db, user, email, preferences)
        msg_id = email.message_id or f"local_{email.id}"

        reply_body = decision.reply_content
        if not reply_body:
            # Generate AI reply draft
            tone = preferences.default_reply_tone if preferences else "professional"
            reply_body = await ai_engine.generate_reply_draft(
                subject=email.subject or "",
                body=email.body or email.preview or "",
                tone=tone,
                sender_name=email.from_name,
            )

        # Append default signature if configured
        sig_text = await cls.get_user_signature_text(db, user.id, is_reply=True)
        if sig_text and sig_text not in reply_body:
            reply_body = f"{reply_body.rstrip()}\n{sig_text}"

        dispatched_message_id = None
        action_recorded = decision.action

        if decision.action == "AUTO_SEND" and gmail_client:
            # Final validation before sending
            try:
                send_res = gmail_client.send_message(
                    to=email.from_email,
                    subject=f"Re: {email.subject}" if not (email.subject or "").startswith("Re:") else email.subject,
                    body=reply_body,
                    thread_id=email.thread_id,
                )
                dispatched_message_id = send_res.get("id")
                action_recorded = "AUTO_REPLIED"
                logger.info("Auto-reply sent for email %s to %s", email.id, email.from_email)
            except Exception as send_err:
                logger.error("Failed to auto-send reply: %s. Falling back to draft.", send_err)
                action_recorded = "DRAFT_CREATED"

        # If not sent, persist as AIReplyDraft
        if action_recorded != "AUTO_REPLIED":
            draft = AIReplyDraft(
                email_id=email.id,
                user_id=user.id,
                tone=preferences.default_reply_tone if preferences else "professional",
                language="english",
                content=reply_body,
                is_approved=False,
                is_sent=False,
            )
            db.add(draft)
            action_recorded = "DRAFT_CREATED"

        # Record in ProcessedMessageLog for duplicate & loop prevention
        log_entry = ProcessedMessageLog(
            user_id=user.id,
            message_id=msg_id,
            thread_id=email.thread_id,
            action_taken=action_recorded,
            rule_id=decision.rule_id,
            reason=decision.reason,
            reply_message_id=dispatched_message_id,
        )
        db.add(log_entry)

        # Record in AuditLog
        audit = AuditLog(
            user_id=user.id,
            action=f"AUTOMATION_{action_recorded}",
            resource_type="email",
            resource_id=str(email.id),
            changes={
                "decision": decision.to_dict(),
                "action_recorded": action_recorded,
                "dispatched_message_id": dispatched_message_id,
            },
        )
        db.add(audit)
        await db.commit()

        return {
            "decision": decision.to_dict(),
            "action_recorded": action_recorded,
            "dispatched_message_id": dispatched_message_id,
        }


automation_engine = AutomationEngine()
