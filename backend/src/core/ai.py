"""
AI Engine service for MailMind AI.
Handles draft generation, summarization, analysis, extraction, and rewriting
using the official Google GenAI SDK (google-genai) with non-blocking async execution.

Provider selection is controlled by the AI_PROVIDER environment variable:
  - "gemini"  → uses google-genai (google.genai.Client) with GEMINI_API_KEY
  - "openai"  → uses openai with OPENAI_API_KEY
  - fallback  → rule-based smart draft & heuristic analysis (no API required)

Drafts are NEVER sent automatically; they are saved with is_sent=False
and is_approved=False, requiring explicit user approval before any action.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

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
    Central AI engine for MailMind AI draft generation, summarization,
    classification, task extraction, and content rewriting.

    No method in this class ever transmits an email.
    """

    def __init__(self) -> None:
        self.provider: str = (settings.AI_PROVIDER or "gemini").strip().lower()
        self.gemini_key: str = settings.GEMINI_API_KEY or ""
        self.gemini_model: str = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.gemini_fallback_model: str = "gemini-3.8-flash"
        self.openai_key: str = settings.OPENAI_API_KEY or ""
        self.openai_model: str = settings.OPENAI_MODEL or "gpt-4o"

    # ------------------------------------------------------------------
    # Public API: Reply Generation
    # ------------------------------------------------------------------

    async def generate_reply(
        self,
        email_subject: str,
        email_body: str,
        tone: str = "professional",
    ) -> str:
        """
        Generate a draft reply for an email (returns string).
        Falls back to smart draft if API is unavailable or keys missing.
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
    # Public API: Summarization
    # ------------------------------------------------------------------

    async def summarize_email(
        self, email_subject: str, email_body: str
    ) -> Dict[str, Any]:
        """Summarize an email into high-level summary and bullet points."""
        prompt = (
            f"You are MailMind AI. Analyze this email and return a JSON object with two fields:\n"
            f"- summary: a 1-2 sentence executive summary\n"
            f"- key_points: a list of 2-4 key takeaways\n\n"
            f"Subject: {email_subject}\n"
            f"Body:\n{email_body[:2500]}\n\n"
            f"Output ONLY valid JSON."
        )

        res_text = await self._call_llm(prompt)
        parsed = self._extract_json(res_text)
        if parsed and "summary" in parsed:
            return {
                "summary": parsed["summary"],
                "key_points": parsed.get("key_points", []),
                "provider": self.provider,
            }

        # Fallback heuristic summary
        first_lines = [l.strip() for l in email_body.splitlines() if l.strip()][:2]
        snippet = " ".join(first_lines)[:180] or "No body content available."
        return {
            "summary": f"Discussion regarding '{email_subject}': {snippet}",
            "key_points": [
                f"Subject: {email_subject}",
                "Review message details for pending action items"
            ],
            "provider": "smart_fallback",
        }

    # ------------------------------------------------------------------
    # Public API: Task & Deadline Extraction
    # ------------------------------------------------------------------

    async def extract_tasks_and_deadlines(
        self, email_subject: str, email_body: str
    ) -> Dict[str, Any]:
        """Extract actionable tasks and dates/deadlines from email content."""
        prompt = (
            f"You are MailMind AI. Extract action items and dates from this email.\n"
            f"Return a JSON object with:\n"
            f"- tasks: list of objects with 'title' (actionable summary), 'priority' ('low'|'medium'|'high'), and 'due_date' (date or null)\n"
            f"- deadlines: list of strings mentioning explicit dates/times\n\n"
            f"Subject: {email_subject}\n"
            f"Body:\n{email_body[:2500]}\n\n"
            f"Output ONLY valid JSON."
        )

        res_text = await self._call_llm(prompt)
        parsed = self._extract_json(res_text)
        if parsed and "tasks" in parsed:
            return {
                "tasks": parsed["tasks"],
                "deadlines": parsed.get("deadlines", []),
                "provider": self.provider,
            }

        # Heuristic fallback: check for date/urgency keywords
        tasks = []
        body_lower = (email_body or "").lower()
        if "submit" in body_lower or "report" in body_lower or "deadline" in body_lower:
            tasks.append({"title": f"Review submission requirements for: {email_subject[:40]}", "priority": "high", "due_date": "Soon"})
        elif "call" in body_lower or "meeting" in body_lower or "sync" in body_lower:
            tasks.append({"title": f"Confirm meeting time regarding: {email_subject[:40]}", "priority": "medium", "due_date": "Today"})
        else:
            tasks.append({"title": f"Follow up on '{email_subject[:40]}'", "priority": "medium", "due_date": "This week"})

        return {
            "tasks": tasks,
            "deadlines": [],
            "provider": "smart_fallback",
        }

    # ------------------------------------------------------------------
    # Public API: Comprehensive Analysis & Phishing Detection
    # ------------------------------------------------------------------

    async def analyze_email(
        self, email_subject: str, email_body: str, sender: str = ""
    ) -> Dict[str, Any]:
        """Comprehensive classification, priority, sentiment, and phishing detection."""
        prompt = (
            f"You are MailMind AI Security & Email Intelligence.\n"
            f"Analyze this email and return a JSON object with:\n"
            f"- category: one of ['Work', 'College', 'Personal', 'Client', 'Finance', 'Promotions', 'Security', 'Career', 'Meeting']\n"
            f"- priority: 'High', 'Medium', or 'Low'\n"
            f"- urgency: 'low', 'medium', 'high', or 'urgent'\n"
            f"- sentiment: 'Positive', 'Negative', 'Neutral', or 'Alert'\n"
            f"- confidence: integer between 70 and 99\n"
            f"- requires_reply: boolean\n"
            f"- importance_reason: brief explanation of why this email is or is not important\n"
            f"- is_suspicious: boolean (flag if phishing, deceptive links, or scam)\n"
            f"- suspicious_reason: string explanation if suspicious, or null\n"
            f"- suggested_reminder: string recommendation for follow-up timing, or null\n\n"
            f"Sender: {sender}\n"
            f"Subject: {email_subject}\n"
            f"Body:\n{email_body[:2500]}\n\n"
            f"Output ONLY valid JSON."
        )

        res_text = await self._call_llm(prompt)
        parsed = self._extract_json(res_text)
        if parsed and "category" in parsed:
            parsed["provider"] = self.provider
            return parsed

        # Rule-based fallback
        subj_lower = email_subject.lower()
        body_lower = (email_body or "").lower()
        is_suspicious = any(w in body_lower or w in subj_lower for w in ["password reset", "urgent wire", "bitcoin", "verify account immediately"])
        category = "Work"
        if "inquiry" in subj_lower or "client" in subj_lower:
            category = "Client"
        elif "deadline" in subj_lower or "exam" in subj_lower or "college" in subj_lower:
            category = "College"
        elif "security" in subj_lower or "sign-in" in subj_lower:
            category = "Security"

        return {
            "category": category,
            "priority": "High" if "urgent" in subj_lower or category in ("Client", "College") else "Normal",
            "urgency": "high" if "urgent" in subj_lower else "medium",
            "sentiment": "Alert" if is_suspicious else "Neutral",
            "confidence": 88,
            "requires_reply": "inquiry" in subj_lower or "?" in body_lower,
            "importance_reason": f"Classified under {category} based on subject context.",
            "is_suspicious": is_suspicious,
            "suspicious_reason": "Contains urgent credential or action flags" if is_suspicious else None,
            "suggested_reminder": "Follow up within 24 hours" if "inquiry" in subj_lower else None,
            "provider": "smart_fallback",
        }

    # ------------------------------------------------------------------
    # Public API: Content Rewriting & Tone Polishing
    # ------------------------------------------------------------------

    async def rewrite_draft(self, content: str, mode: str = "improve") -> Dict[str, Any]:
        """
        Rewrite an email draft.
        Modes: 'shorten', 'expand', 'improve' (grammar/polish), 'formal', 'friendly'
        """
        mode_instructions = {
            "shorten": "Make this email draft significantly more concise and direct while preserving core intent.",
            "expand": "Elaborate politely on this email draft with professional context and clearer explanations.",
            "improve": "Polish the grammar, flow, professional tone, and clarity of this email draft.",
            "formal": "Rewrite this email draft in a strictly formal, courteous, and executive tone.",
            "friendly": "Rewrite this email draft in a warm, welcoming, friendly, and conversational tone.",
        }
        inst = mode_instructions.get(mode.lower(), mode_instructions["improve"])
        prompt = (
            f"You are MailMind AI. {inst}\n\n"
            f"Original draft:\n{content}\n\n"
            f"Output ONLY the revised email text with no markdown commentary."
        )

        res_text = await self._call_llm(prompt)
        if res_text:
            return {
                "rewritten_content": res_text.strip(),
                "mode": mode,
                "provider": self.provider,
            }

        # Fallback simple modifiers
        if mode == "shorten":
            lines = [l for l in content.splitlines() if l.strip()]
            rewritten = "\n\n".join(lines[:3]) if len(lines) > 3 else content
        elif mode == "expand":
            rewritten = f"{content}\n\nPlease let me know if you have any questions or require additional details."
        else:
            rewritten = content.strip()

        return {
            "rewritten_content": rewritten,
            "mode": mode,
            "provider": "smart_fallback",
        }

    # ------------------------------------------------------------------
    # Public API: Subject Line Generator
    # ------------------------------------------------------------------

    async def generate_subject(self, body: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate an engaging, concise email subject line."""
        user_prompt = f"Additional user instruction: {prompt}\n" if prompt else ""
        query = (
            f"You are MailMind AI. Generate 1 clear, concise, professional email subject line for this email body.\n"
            f"{user_prompt}"
            f"Body:\n{body[:1500]}\n\n"
            f"Output ONLY the subject line text (no quotes, no prefix)."
        )

        res_text = await self._call_llm(query)
        if res_text:
            subject = res_text.strip().replace("Subject:", "").strip().strip('"')
            return {"subject": subject, "provider": self.provider}

        # Fallback
        first_line = body.strip().split("\n")[0][:45] if body else "Message"
        return {"subject": f"Regarding: {first_line}", "provider": "smart_fallback"}

    # ------------------------------------------------------------------
    # Private Helper: Call LLM with non-blocking execution & fallback
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Execute prompt against active provider asynchronously without blocking event loop."""
        if self.provider == "gemini" and self.gemini_key:
            res = await self._call_gemini_raw(prompt, self.gemini_model)
            if res is None and self.gemini_fallback_model:
                res = await self._call_gemini_raw(prompt, self.gemini_fallback_model)
            if res:
                return res

        if self.provider == "openai" and self.openai_key:
            return await self._call_openai_raw(prompt)

        return None

    async def _call_gemini_raw(self, prompt: str, model_name: str) -> Optional[str]:
        """Run google-genai generate_content inside asyncio.to_thread."""
        try:
            from google import genai
            from google.genai import types as genai_types

            def _sync_generate():
                client = genai.Client(api_key=self.gemini_key)
                return client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=600,
                        temperature=0.7,
                    ),
                )

            response = await asyncio.to_thread(_sync_generate)
            text = (response.text or "").strip()
            if text:
                return text
            return None
        except ImportError:
            logger.warning("google-genai package not found")
            return None
        except Exception as exc:
            logger.warning("Gemini model %s error: %s", model_name, exc)
            return None

    async def _call_openai_raw(self, prompt: str) -> Optional[str]:
        """Run OpenAI chat completion in asyncio.to_thread."""
        try:
            import openai

            def _sync_openai():
                client = openai.OpenAI(api_key=self.openai_key)
                return client.chat.completions.create(
                    model=self.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                )

            resp = await asyncio.to_thread(_sync_openai)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("OpenAI error: %s", exc)
            return None

    def _extract_json(self, text: Optional[str]) -> Optional[Dict[str, Any]]:
        """Safely extract and parse JSON from LLM output (including markdown-fenced blocks)."""
        if not text:
            return None
        clean = text.strip()
        # Remove ```json ... ``` fences
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        try:
            return json.loads(clean)
        except Exception:
            # Try regex match for innermost {...}
            match = re.search(r"(\{.*\})", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None

    # ------------------------------------------------------------------
    # Compatibility Methods for existing tests
    # ------------------------------------------------------------------

    async def _generate_with_gemini(
        self, subject: str, body: str, tone: str
    ) -> Optional[str]:
        """Call Google Gemini for reply generation."""
        try:
            from google import genai
            from google.genai import types as genai_types

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

            def _sync_gemini():
                client = genai.Client(api_key=self.gemini_key)
                return client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=400,
                        temperature=0.7,
                    ),
                )

            response = await asyncio.to_thread(_sync_gemini)
            text = (response.text or "").strip()
            if text:
                logger.info("Gemini draft generated (tone=%s, chars=%d)", tone, len(text))
                return text
            return None
        except ImportError:
            logger.warning("google-genai package not found")
            return None
        except Exception as exc:
            logger.warning("Gemini generation error: %s", exc)
            return None

    async def _generate_with_openai(
        self, subject: str, body: str, tone: str
    ) -> Optional[str]:
        """Call OpenAI chat completion for reply generation."""
        try:
            import openai

            tone_cfg = _resolve_tone(tone)

            def _sync_openai():
                client = openai.OpenAI(api_key=self.openai_key)
                return client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"You are MailMind AI, an intelligent email assistant. "
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

            response = await asyncio.to_thread(_sync_openai)
            text = (response.choices[0].message.content or "").strip()
            if text:
                return text
            return None
        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            return None


ai_engine = AIEngine()
