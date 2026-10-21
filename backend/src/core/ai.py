"""
AI Engine service for MailMind AI.
Handles draft generation using the official Google GenAI SDK (google-genai).

Provider selection is controlled by the AI_PROVIDER environment variable.
  - "gemini"  → uses google-genai (google.genai.Client)  with GEMINI_API_KEY
  - "openai"  → uses openai                               with OPENAI_API_KEY
  - anything else / missing key → smart-draft fallback (no API required)

Drafts are NEVER sent automatically; they are saved with is_sent=False
and is_approved=False, requiring explicit user approval before any action.
"""
import logging
from typing import Optional

from src.config import settings

logger = logging.getLogger("mailmind-ai.engine")

# ---------------------------------------------------------------------------
# Tone configuration
# ---------------------------------------------------------------------------
_TONE_CONFIG: dict = {
    "professional": {
        "greeting": "Dear Sender,",
        "closing": "Best regards,\nMailMind AI User",
        "prompt_style": (
            "Write a concise, professional email reply. "
            "Use formal vocabulary, avoid contractions, and maintain a respectful tone."
        ),
    },
    "friendly": {
        "greeting": "Hi there,",
        "closing": "Cheers,\nMailMind AI User",
        "prompt_style": (
            "Write a warm and friendly email reply. "
            "Use a conversational tone, light contractions, and a positive, engaging style."
        ),
    },
    "formal": {
        "greeting": "Dear Sir/Madam,",
        "closing": "Sincerely,\nMailMind AI User",
        "prompt_style": (
            "Write a strictly formal email reply. "
            "Use no contractions, highly formal vocabulary, and an official, courteous tone."
        ),
    },
}

_DEFAULT_TONE = "professional"


def _resolve_tone(tone: str) -> dict:
    """Return tone config for the given tone string (case-insensitive, defaults to professional)."""
    return _TONE_CONFIG.get(tone.strip().lower(), _TONE_CONFIG[_DEFAULT_TONE])


def _build_smart_draft(subject: str, body: str, tone: str) -> str:
    """
    Locally-generated smart draft — no API key required.
    Used as fallback when no provider is configured or any API call fails.
    """
    cfg = _resolve_tone(tone)
    body_snippet = body[:150].strip() if body else "your message"
    return (
        f"{cfg['greeting']}\n\n"
        f"Thank you for reaching out regarding \"{subject}\". "
        f"I have reviewed {body_snippet}... and would love to move forward.\n\n"
        f"Please let me know your availability for a brief discussion this week.\n\n"
        f"{cfg['closing']}"
    )


class AIEngine:
    """
    Central AI engine for MailMind AI draft generation.

    Priority order:
      1. Gemini via google-genai  (AI_PROVIDER=gemini, GEMINI_API_KEY set)
      2. OpenAI                   (AI_PROVIDER=openai, OPENAI_API_KEY set)
      3. Smart-draft fallback     (always available)

    No method in this class ever transmits an email.
    """

    def __init__(self) -> None:
        self.provider: str = (settings.AI_PROVIDER or "gemini").strip().lower()
        self.gemini_key: str = settings.GEMINI_API_KEY or ""
        self.gemini_model: str = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.openai_key: str = settings.OPENAI_API_KEY or ""
        self.openai_model: str = settings.OPENAI_MODEL or "gpt-4o"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_reply(
        self,
        email_subject: str,
        email_body: str,
        tone: str = "professional",
    ) -> str:
        """
        Generate a draft reply for an email.

        Args:
            email_subject: Subject of the incoming email.
            email_body:    Body text of the incoming email.
            tone:          "professional" | "friendly" | "formal".
                           Unknown values silently default to "professional".

        Returns:
            Draft text string. Never raises — falls back to smart draft on any error.
        """
        tone_key = tone.strip().lower() if tone else _DEFAULT_TONE

        # 1. Gemini (official google-genai SDK)
        if self.provider == "gemini" and self.gemini_key:
            result = await self._generate_with_gemini(email_subject, email_body, tone_key)
            if result is not None:
                return result

        # 2. OpenAI
        if self.provider == "openai" and self.openai_key:
            result = await self._generate_with_openai(email_subject, email_body, tone_key)
            if result is not None:
                return result

        # 3. Smart-draft fallback
        logger.info("Falling back to smart draft (provider=%s, tone=%s)", self.provider, tone_key)
        return _build_smart_draft(email_subject, email_body, tone_key)

    # ------------------------------------------------------------------
    # Private: Gemini via google-genai
    # ------------------------------------------------------------------

    async def _generate_with_gemini(
        self, subject: str, body: str, tone: str
    ) -> Optional[str]:
        """
        Call Google Gemini using the official google-genai SDK.

        Uses google.genai.Client with GEMINI_API_KEY.
        Returns None on any failure so the caller can fall through.
        """
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types as genai_types  # type: ignore[import]

            client = genai.Client(api_key=self.gemini_key)
            tone_cfg = _resolve_tone(tone)

            prompt = (
                f"You are MailMind AI, an intelligent email assistant.\n"
                f"{tone_cfg['prompt_style']}\n\n"
                f"Original email:\n"
                f"Subject: {subject}\n"
                f"Body: {body}\n\n"
                f"Write only the reply body (no subject line). "
                f"Begin with: {tone_cfg['greeting']}\n"
                f"End with: {tone_cfg['closing']}\n"
                f"Keep the reply under 200 words."
            )

            response = client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=400,
                    temperature=0.7,
                ),
            )

            text = (response.text or "").strip()
            if text:
                logger.info("Gemini draft generated (tone=%s, chars=%d)", tone, len(text))
                return text

            logger.warning("Gemini returned empty response (tone=%s)", tone)
            return None

        except ImportError:
            logger.warning(
                "google-genai package not found. Install: pip install google-genai"
            )
            return None
        except Exception as exc:  # pylint: disable=broad-except
            exc_type = type(exc).__name__
            exc_str = str(exc)
            if "ClientError" in exc_type or "404" in exc_str:
                logger.error(
                    "Gemini model '%s' not found or API key invalid. "
                    "Check GEMINI_MODEL in .env. Error: %s",
                    self.gemini_model, exc,
                )
            elif "ServerError" in exc_type or "503" in exc_str or "UNAVAILABLE" in exc_str:
                logger.warning(
                    "Gemini API temporarily unavailable (503/quota). "
                    "Falling back to smart draft. Error: %s", exc,
                )
            elif "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                logger.warning(
                    "Gemini API rate limit / quota exceeded. "
                    "Falling back to smart draft. Error: %s", exc,
                )
            else:
                logger.error("Gemini API error (%s): %s", exc_type, exc)
            return None

    # ------------------------------------------------------------------
    # Private: OpenAI (preserved from original)
    # ------------------------------------------------------------------

    async def _generate_with_openai(
        self, subject: str, body: str, tone: str
    ) -> Optional[str]:
        """
        Call the OpenAI Chat Completions API.
        Returns None on any failure.
        """
        try:
            import openai  # type: ignore[import]

            tone_cfg = _resolve_tone(tone)
            client = openai.OpenAI(api_key=self.openai_key)
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are MailMind AI, an intelligent email assistant. "
                            f"{tone_cfg['prompt_style']}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Subject: {subject}\n\nBody: {body}",
                    },
                ],
                max_tokens=300,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                logger.info("OpenAI draft generated (tone=%s, chars=%d)", tone, len(text))
                return text
            return None
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("OpenAI API error: %s", exc)
            return None


# Module-level singleton imported by endpoint handlers
ai_engine = AIEngine()
