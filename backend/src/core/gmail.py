"""
Google Gmail API client for MailMind AI.
Handles OAuth authentication, inbox fetching, MIME message decoding,
and user-authorized email dispatch.
"""
import base64
from email.mime.text import MIMEText
import logging
from typing import Any, Dict, List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("mailmind-ai.gmail")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """Wrapper around Google Gmail API service."""

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=GMAIL_SCOPES,
        )
        self.service = build("gmail", "v1", credentials=self.creds)

    def list_messages(self, user_id: str = "me", max_results: int = 15, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List messages from Gmail inbox matching optional query."""
        try:
            req = self.service.users().messages().list(
                userId=user_id, maxResults=max_results, q=query
            )
            results = req.execute()
            return results.get("messages", [])
        except HttpError as error:
            logger.error("Gmail list_messages HTTP error: %s", error)
            return []
        except Exception as error:
            logger.error("Gmail list_messages error: %s", error)
            return []

    def get_message(self, message_id: str, user_id: str = "me") -> Optional[Dict[str, Any]]:
        """Get full raw message details by ID."""
        try:
            return self.service.users().messages().get(
                userId=user_id, id=message_id, format="full"
            ).execute()
        except HttpError as error:
            logger.error("Gmail get_message HTTP error: %s", error)
            return None
        except Exception as error:
            logger.error("Gmail get_message error: %s", error)
            return None

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        user_id: str = "me",
        in_reply_to: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send an email via Gmail API.
        SAFETY RULE: Must only be called after explicit user approval.
        """
        try:
            mime_msg = MIMEText(body, "plain", "utf-8")
            mime_msg["to"] = to
            mime_msg["subject"] = subject
            if in_reply_to:
                mime_msg["In-Reply-To"] = in_reply_to
                mime_msg["References"] = in_reply_to

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
            send_body: Dict[str, Any] = {"raw": raw}
            if thread_id:
                send_body["threadId"] = thread_id

            sent = self.service.users().messages().send(
                userId=user_id, body=send_body
            ).execute()
            logger.info("Email sent successfully via Gmail API (ID: %s)", sent.get("id"))
            return sent
        except HttpError as error:
            logger.error("Gmail send_message HTTP error: %s", error)
            raise
        except Exception as error:
            logger.error("Gmail send_message error: %s", error)
            raise

    @staticmethod
    def parse_message_headers_and_body(msg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sender, recipient, subject, date, and body snippet from Gmail message object."""
        payload = msg.get("payload", {})
        headers_list = payload.get("headers", [])
        headers = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

        subject = headers.get("subject", "(No Subject)")
        sender_raw = headers.get("from", "")
        to_raw = headers.get("to", "")
        date_raw = headers.get("date", "")

        # Extract name and email address from "From" header
        from_name = sender_raw
        from_email = sender_raw
        if "<" in sender_raw and ">" in sender_raw:
            parts = sender_raw.split("<")
            from_name = parts[0].strip().strip('"')
            from_email = parts[1].replace(">", "").strip()

        # Extract text body
        body_text = ""
        snippet = msg.get("snippet", "")

        def _decode_part(part):
            nonlocal body_text
            mime_type = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if data and mime_type == "text/plain":
                try:
                    decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
                    body_text += decoded
                except Exception:
                    pass
            for sub_part in part.get("parts", []):
                _decode_part(sub_part)

        _decode_part(payload)
        final_body = body_text.strip() or snippet

        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from_name": from_name or from_email,
            "from_email": from_email,
            "to": to_raw,
            "subject": subject,
            "body": final_body,
            "preview": snippet or final_body[:120],
            "date_str": date_raw,
        }
