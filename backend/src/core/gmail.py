"""
Google Gmail API client for MailMind AI.
Handles OAuth authentication, token refresh verification, inbox message listing,
thread fetching, MIME message decoding, and user-authorized email dispatch.
"""
import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText
import logging
import re
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


class GmailAuthError(Exception):
    """Base exception for Gmail authentication and authorization failures."""
    pass


class GmailReconnectionRequiredError(GmailAuthError):
    """Raised when Google OAuth refresh token is missing, expired, revoked, or invalid."""
    pass


class GmailClient:
    """Wrapper around Google Gmail API service with automated token lifecycle management."""

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        on_token_refresh: Optional[Any] = None,
    ):
        expiry = None
        if token_expires_at:
            if token_expires_at.tzinfo is not None:
                expiry = token_expires_at.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                expiry = token_expires_at

        self.on_token_refresh = on_token_refresh
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=GMAIL_SCOPES,
            expiry=expiry,
        )
        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)

    def refresh_token(self) -> str:
        """
        Force-refresh the Google OAuth access token using Google's OAuth token endpoint.
        Rebuilds self.service with fresh credentials and calls on_token_refresh callback.
        Raises GmailReconnectionRequiredError if refresh token is missing or revoked.
        """
        if not self.creds or not self.creds.refresh_token:
            raise GmailReconnectionRequiredError(
                "Google refresh token is missing. Please reconnect your Gmail account in Settings."
            )

        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError

        try:
            logger.info("Refreshing Gmail OAuth access token via Google token endpoint...")
            self.creds.refresh(Request())
            new_token = self.creds.token
            new_expiry = self.creds.expiry
            if new_expiry and new_expiry.tzinfo is None:
                new_expiry = new_expiry.replace(tzinfo=timezone.utc)

            self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
            logger.info("Gmail OAuth access token refreshed successfully.")

            if self.on_token_refresh:
                try:
                    self.on_token_refresh(new_token, new_expiry)
                except Exception as cb_err:
                    logger.warning("Error in on_token_refresh callback: %s", cb_err)

            return new_token
        except RefreshError as exc:
            err_msg = str(exc).lower()
            logger.error("Google OAuth token refresh rejected: %s", exc)
            if any(term in err_msg for term in ["invalid_grant", "revoked", "expired", "invalid_request"]):
                raise GmailReconnectionRequiredError(
                    "Google Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings."
                ) from exc
            raise GmailAuthError(f"Could not refresh Google OAuth access token: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error refreshing Google OAuth token: %s", exc)
            raise GmailAuthError(f"Unexpected token refresh error: {exc}") from exc

    def ensure_valid_token(self, force: bool = False) -> Optional[str]:
        """
        Check if credentials are expired or nearing expiration (< 60 seconds).
        Refreshes them if refresh_token is present.
        Returns the new access token string if refreshed, otherwise None.
        Raises GmailReconnectionRequiredError if token expired and refresh fails or is missing.
        """
        try:
            now_utc = datetime.now(timezone.utc)
            expiry_utc = None
            if self.creds and isinstance(getattr(self.creds, "expiry", None), datetime):
                expiry_utc = (
                    self.creds.expiry.replace(tzinfo=timezone.utc)
                    if self.creds.expiry.tzinfo is None
                    else self.creds.expiry
                )

            is_expired_or_imminent = (
                getattr(self.creds, "expired", False)
                or (expiry_utc and (expiry_utc - now_utc).total_seconds() < 60)
            )

            if force or is_expired_or_imminent:
                if self.creds.refresh_token:
                    return self.refresh_token()
                elif is_expired_or_imminent:
                    raise GmailReconnectionRequiredError(
                        "Google access token has expired and no refresh token is stored. Please reconnect Gmail."
                    )
        except (GmailReconnectionRequiredError, GmailAuthError):
            raise
        except Exception as exc:
            logger.warning("Error checking Gmail token validity: %s", exc)
        return None

    def _execute_api_call(self, request_factory: Any) -> Any:
        """
        Execute a Google API request with automatic 401/403 retry.
        If Google rejects the request with HTTP 401 or 403, attempts token refresh once
        and retries with the newly generated service client.
        """
        try:
            req = request_factory(self.service)
            return req.execute()
        except HttpError as error:
            status_code = getattr(error.resp, "status", None)
            if status_code in (401, 403) and self.creds and self.creds.refresh_token:
                logger.info(
                    "Gmail API returned HTTP %s; automatically refreshing OAuth access token and retrying...",
                    status_code,
                )
                self.refresh_token()
                retry_req = request_factory(self.service)
                return retry_req.execute()
            raise

    def list_messages(
        self,
        user_id: str = "me",
        max_results: int = 25,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List messages from Gmail inbox matching optional query or label filters."""
        kwargs: Dict[str, Any] = {"userId": user_id, "maxResults": max_results}
        if query:
            kwargs["q"] = query
        if label_ids:
            kwargs["labelIds"] = label_ids

        try:
            results = self._execute_api_call(
                lambda s: s.users().messages().list(**kwargs)
            )
            return results.get("messages", [])
        except GmailReconnectionRequiredError:
            raise
        except HttpError as error:
            logger.error("Gmail list_messages HTTP error: %s", error)
            return []
        except Exception as error:
            logger.error("Gmail list_messages error: %s", error)
            return []

    def get_message(self, message_id: str, user_id: str = "me") -> Optional[Dict[str, Any]]:
        """Get full raw message details by ID."""
        try:
            return self._execute_api_call(
                lambda s: s.users().messages().get(userId=user_id, id=message_id, format="full")
            )
        except GmailReconnectionRequiredError:
            raise
        except HttpError as error:
            logger.error("Gmail get_message HTTP error: %s", error)
            return None
        except Exception as error:
            logger.error("Gmail get_message error: %s", error)
            return None

    def get_thread(self, thread_id: str, user_id: str = "me") -> Optional[Dict[str, Any]]:
        """Retrieve full thread with all its constituent messages."""
        try:
            return self._execute_api_call(
                lambda s: s.users().threads().get(userId=user_id, id=thread_id, format="full")
            )
        except GmailReconnectionRequiredError:
            raise
        except HttpError as error:
            logger.error("Gmail get_thread HTTP error: %s", error)
            return None
        except Exception as error:
            logger.error("Gmail get_thread error: %s", error)
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

        sent = self._execute_api_call(
            lambda s: s.users().messages().send(userId=user_id, body=send_body)
        )
        logger.info("Email sent successfully via Gmail API (ID: %s)", sent.get("id"))
        return sent

    @staticmethod
    def parse_message_headers_and_body(msg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sender, recipient, subject, date, labels, and body snippet from Gmail message object."""
        payload = msg.get("payload", {})
        headers_list = payload.get("headers", [])
        headers = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

        subject = headers.get("subject", "(No Subject)").strip() or "(No Subject)"
        sender_raw = headers.get("from", "")
        to_raw = headers.get("to", "")
        date_raw = headers.get("date", "")

        # Extract name and email address from "From" header
        from_name = sender_raw
        from_email = sender_raw
        if "<" in sender_raw and ">" in sender_raw:
            parts = sender_raw.split("<")
            from_name = parts[0].strip().strip('"').strip("'")
            from_email = parts[1].replace(">", "").strip()
        elif "@" in sender_raw:
            from_name = sender_raw.split("@")[0].capitalize()
            from_email = sender_raw.strip()

        # Parse received_at datetime: prefer internalDate (ms timestamp)
        received_at = datetime.now(timezone.utc)
        internal_date_ms = msg.get("internalDate")
        if internal_date_ms and str(internal_date_ms).isdigit():
            try:
                received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000, tz=timezone.utc)
            except Exception:
                pass

        # Extract text body and HTML fallback
        body_text = ""
        html_text = ""
        snippet = msg.get("snippet", "")
        attachment_count = 0

        def _decode_part(part):
            nonlocal body_text, html_text, attachment_count
            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            if filename:
                attachment_count += 1

            body_data = part.get("body", {})
            data = body_data.get("data")
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
                    if (mime_type == "text/plain" or not mime_type) and not body_text:
                        body_text += decoded
                    elif mime_type == "text/html" and not html_text:
                        html_text += decoded
                except Exception:
                    pass

            for sub_part in part.get("parts", []):
                _decode_part(sub_part)

        _decode_part(payload)

        # If no plain text was found, clean HTML text
        if not body_text and html_text:
            cleaned = re.sub(r"<style[^>]*>.*?</style>", "", html_text, flags=re.DOTALL)
            cleaned = re.sub(r"<script[^>]*>.*?</script>", "", cleaned, flags=re.DOTALL)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            body_text = cleaned

        final_body = (body_text.strip() or snippet).strip()
        final_preview = (snippet or final_body[:120]).strip()

        # Extract Gmail label attributes
        labels = set(msg.get("labelIds", []))
        is_read = "UNREAD" not in labels
        is_starred = "STARRED" in labels
        is_important = "IMPORTANT" in labels

        folder = "inbox"
        if "SENT" in labels:
            folder = "sent"
        elif "DRAFT" in labels:
            folder = "drafts"
        elif "SPAM" in labels:
            folder = "spam"
        elif "TRASH" in labels:
            folder = "trash"

        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from_name": from_name or from_email or "Unknown Sender",
            "from_email": from_email or "unknown@gmail.com",
            "to": to_raw or "me",
            "subject": subject,
            "body": final_body,
            "preview": final_preview,
            "date_str": date_raw,
            "received_at": received_at,
            "is_read": is_read,
            "is_starred": is_starred,
            "is_important": is_important,
            "folder": folder,
            "has_attachments": attachment_count > 0,
            "attachment_count": attachment_count,
        }
