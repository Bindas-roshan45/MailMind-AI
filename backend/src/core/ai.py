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
from typing import Any, Dict, List, Optional, Tuple

from src.config import settings

logger = logging.getLogger("mailmind-ai.engine")

# ---------------------------------------------------------------------------
# Tone configuration
# ---------------------------------------------------------------------------
_TONE_CONFIG: dict = {
    "professional": {
        "greeting": "Dear Sender,",
        "closing": "Best regards",
        "sign_off": "Best regards",
        "prompt_style": (
            "Write a concise, natural, professional email reply. "
            "Use clear vocabulary, respectful tone, and sound like a genuine professional."
        ),
    },
    "friendly": {
        "greeting": "Hi there,",
        "closing": "Cheers",
        "sign_off": "Cheers",
        "prompt_style": (
            "Write a warm, approachable, and friendly email reply. "
            "Use a conversational, polite, and engaging style."
        ),
    },
    "formal": {
        "greeting": "Dear Sir/Madam,",
        "closing": "Sincerely",
        "sign_off": "Sincerely",
        "prompt_style": (
            "Write a strictly formal email reply. "
            "Use dignified vocabulary, no slang, and an official, courteous tone."
        ),
    },
    "short": {
        "greeting": "Hi,",
        "closing": "Best",
        "sign_off": "Best",
        "prompt_style": (
            "Write a brief, direct, to-the-point email reply under 60 words."
        ),
    },
}

_DEFAULT_TONE = "professional"


def _resolve_tone(tone: str) -> dict:
    """Return tone config for the given tone string (case-insensitive, defaults to professional)."""
    return _TONE_CONFIG.get(tone.strip().lower(), _TONE_CONFIG[_DEFAULT_TONE])


def _format_signature(
    sign_off: str,
    signature_text: Optional[str] = None,
    user_name: Optional[str] = None,
) -> str:
    """
    Format closing signature using configured signature_text or user_name.
    Never falls back to hardcoded robotic persona names.
    """
    if signature_text and signature_text.strip():
        return signature_text.strip()
    clean_name = (user_name or "").strip()
    if clean_name:
        return f"{sign_off},\n{clean_name}"
    return sign_off


def _attach_signature_once(body: str, signature_str: str) -> str:
    """Ensure signature is attached cleanly to the body without duplication."""
    if not signature_str or not signature_str.strip():
        return body.rstrip()

    clean_body = body.rstrip()
    clean_sig = signature_str.strip()

    # If the body already ends with the signature or contains its significant lines, do not duplicate
    sig_lines = [l.strip() for l in clean_sig.splitlines() if l.strip()]
    if not sig_lines:
        return clean_body

    tail = clean_body[-200:].lower()
    last_line = sig_lines[-1].lower()
    if last_line in tail:
        return clean_body

    return f"{clean_body}\n\n{clean_sig}"


def _build_smart_draft(
    subject: str,
    body: str,
    tone: str = "professional",
    sender_name: Optional[str] = None,
    language: str = "english",
    signature_text: Optional[str] = None,
    user_name: Optional[str] = None,
) -> str:
    """
    Locally-generated smart draft — no API key required.
    Contextually tailored to the actual email subject, sender, and content.
    Never roleplays as an AI; speaks directly on behalf of the recipient.
    """
    cfg = _resolve_tone(tone)
    first_name = sender_name.split()[0].capitalize() if sender_name and sender_name.strip() else None

    greeting = (
        f"Dear {first_name}," if first_name and tone.lower() in ("professional", "formal")
        else (f"Hi {first_name}," if first_name else cfg["greeting"])
    )

    clean_subj = subject.strip() if subject else "your message"
    clean_body = (body or "").strip()
    combined_text = f"{clean_subj} {clean_body}".lower()
    closing = _format_signature(cfg.get("sign_off", "Best regards"), signature_text, user_name)

    lang_clean = (language or "english").lower().strip()
    if lang_clean == "hindi":
        salutation = f"नमस्ते {first_name}," if first_name else "नमस्ते,"
        hindi_closing = signature_text.strip() if signature_text else f"सादर,\n{user_name}" if user_name else "सादर"
        return (
            f"{salutation}\n\n"
            f"\"{clean_subj}\" के संबंध में आपके संदेश के लिए धन्यवाद। "
            f"मैंने आपका संदेश प्राप्त कर लिया है और विवरण की समीक्षा कर रहा हूँ।\n\n"
            f"मैं शीघ्र ही इस विषय पर आपसे आवश्यक अपडेट साझा करूँगा।\n\n"
            f"{hindi_closing}"
        )
    elif lang_clean == "hinglish":
        salutation = f"Hi {first_name}," if first_name else "Hi,"
        hinglish_closing = signature_text.strip() if signature_text else f"Best regards,\n{user_name}" if user_name else "Best regards"
        return (
            f"{salutation}\n\n"
            f"Thank you for reaching out regarding \"{clean_subj}\". "
            f"Maine aapka message receive kar liya hai aur main iski details check kar raha hoon.\n\n"
            f"Main jald hi aapse is regarding update share karta hoon.\n\n"
            f"{hinglish_closing}"
        )

    # 1. Financial assistance / Loan / Grant / Funding / Sponsorship / Refund request
    financial_keywords = [
        "financial assistance", "monetary", "loan", "grant", "funding", "donation",
        "financial support", "wire transfer", "bank assistance", "sponsorship",
        "financial aid", "need money", "urgent funds", "fund transfer"
    ]
    if any(k in combined_text for k in financial_keywords):
        core_message = (
            f"Thank you for reaching out regarding \"{clean_subj}\".\n\n"
            f"I have received your request and am currently reviewing the details provided. "
            f"I will follow up with you as soon as I have completed this review."
        )
        draft = f"{greeting}\n\n{core_message}"
        return _attach_signature_once(draft, closing)

    # 2. Empty or very short body
    if not clean_body or len(clean_body) < 12:
        core_message = (
            f"Thank you for your message regarding \"{clean_subj}\".\n\n"
            f"Could you please share some additional details or context regarding your request? "
            f"This will help me assist you as effectively as possible."
        )
        draft = f"{greeting}\n\n{core_message}"
        return _attach_signature_once(draft, closing)

    # 3. Decision / Policy / Proposal requiring review
    decision_keywords = ["contract", "agreement", "proposal", "partnership", "decision", "policy", "legal", "terms"]
    if any(k in combined_text for k in decision_keywords):
        core_message = (
            f"Thank you for reaching out regarding \"{clean_subj}\".\n\n"
            f"I have received your note and the information shared. I am currently going through the "
            f"details and will get back to you with next steps shortly."
        )
        draft = f"{greeting}\n\n{core_message}"
        return _attach_signature_once(draft, closing)

    # 4. Standard business inquiry / Meeting / Follow-up
    core_message = (
        f"Thank you for reaching out regarding \"{clean_subj}\".\n\n"
        f"I have reviewed your message and would be glad to discuss this further. "
        f"Please let me know what times work best for your schedule this week."
    )
    draft = f"{greeting}\n\n{core_message}"
    return _attach_signature_once(draft, closing)


class AIEngine:
    """
    Central AI engine for MailMind AI draft generation, summarization,
    classification, task extraction, and content rewriting.

    No method in this class ever transmits an email.
    """

    def __init__(self) -> None:
        self.gemini_model: str = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.gemini_fallback_model: str = "gemini-2.0-flash"
        self.openai_model: str = settings.OPENAI_MODEL or "gpt-4o"

    @property
    def current_gemini_key(self) -> str:
        import os
        return (settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")).strip()

    @property
    def current_openai_key(self) -> str:
        import os
        return (settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")).strip()

    @property
    def current_provider(self) -> str:
        import os
        return (settings.AI_PROVIDER or os.environ.get("AI_PROVIDER", "gemini")).strip().lower()

    # Legacy attributes for backward compatibility with mock tests
    @property
    def provider(self) -> str:
        return self.current_provider

    @provider.setter
    def provider(self, val: str) -> None:
        self._custom_provider = val

    @property
    def gemini_key(self) -> str:
        return getattr(self, "_custom_gemini_key", None) or self.current_gemini_key

    @gemini_key.setter
    def gemini_key(self, val: str) -> None:
        self._custom_gemini_key = val

    @property
    def openai_key(self) -> str:
        return getattr(self, "_custom_openai_key", None) or self.current_openai_key

    @openai_key.setter
    def openai_key(self, val: str) -> None:
        self._custom_openai_key = val

    @property
    def gemini_fallback_model(self) -> str:
        return getattr(self, "_gemini_fallback_model", "gemini-2.0-flash")

    @gemini_fallback_model.setter
    def gemini_fallback_model(self, val: str) -> None:
        self._gemini_fallback_model = val

    def get_provider_status(self) -> Dict[str, Any]:
        """Check active provider configuration and key availability."""
        prov = self.current_provider
        if prov == "gemini":
            key = self.current_gemini_key
            is_valid = bool(key and not key.startswith("your_"))
            return {
                "provider": "gemini",
                "configured_provider": "gemini",
                "is_available": is_valid,
                "model": getattr(self, "gemini_model", "gemini-2.5-flash"),
                "message": "Google Gemini configured" if is_valid else "Gemini API key is not configured in backend/.env",
            }
        elif prov == "openai":
            key = self.current_openai_key
            is_valid = bool(key and not key.startswith("your_"))
            return {
                "provider": "openai",
                "configured_provider": "openai",
                "is_available": is_valid,
                "model": getattr(self, "openai_model", "gpt-4o"),
                "message": "OpenAI configured" if is_valid else "OpenAI API key is not configured in backend/.env",
            }
        return {
            "provider": prov,
            "configured_provider": prov,
            "is_available": False,
            "message": f"Unsupported AI provider: {prov}",
        }

    # ------------------------------------------------------------------
    # Public API: Reply Generation
    # ------------------------------------------------------------------

    async def generate_reply_with_metadata(
        self,
        email_subject: str,
        email_body: str,
        tone: str = "professional",
        sender_name: Optional[str] = None,
        language: str = "english",
        thread_history: Optional[str] = None,
        signature_text: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a reply with comprehensive provider provenance metadata.
        Falls back gracefully to smart draft if API is unavailable or keys missing.
        """
        tone_key = tone.strip().lower() if tone else _DEFAULT_TONE
        prov = self.current_provider
        g_key = self.current_gemini_key
        o_key = self.current_openai_key

        # 1. Gemini (official google-genai SDK)
        if prov == "gemini" and g_key and not g_key.startswith("your_"):
            result = await self._generate_with_gemini(
                email_subject, email_body, tone_key, sender_name, language, thread_history,
                signature_text=signature_text, user_name=user_name
            )
            if result is not None:
                return result, {
                    "provider": "gemini",
                    "model": self.gemini_model,
                    "is_fallback": False,
                    "notice": None,
                }

        # 2. OpenAI
        if prov == "openai" and o_key and not o_key.startswith("your_"):
            result = await self._generate_with_openai(
                email_subject, email_body, tone_key, sender_name, language, thread_history,
                signature_text=signature_text, user_name=user_name
            )
            if result is not None:
                return result, {
                    "provider": "openai",
                    "model": self.openai_model,
                    "is_fallback": False,
                    "notice": None,
                }

        # 3. Smart-draft fallback
        logger.info("Falling back to contextual smart draft (provider=%s, tone=%s, lang=%s)", prov, tone_key, language)
        fallback_text = _build_smart_draft(
            subject=email_subject,
            body=email_body,
            tone=tone_key,
            sender_name=sender_name,
            language=language,
            signature_text=signature_text,
            user_name=user_name,
        )

        notice = None
        if prov in ("gemini", "openai") and not (g_key or o_key):
            notice = f"{prov.capitalize()} API key not configured. Using rule-based smart draft."
        elif prov in ("gemini", "openai"):
            notice = f"{prov.capitalize()} API temporarily unavailable. Using rule-based smart draft."

        return fallback_text, {
            "provider": "smart_fallback",
            "model": "rule_based",
            "is_fallback": True,
            "notice": notice,
        }

    async def generate_reply(
        self,
        email_subject: str,
        email_body: str,
        tone: str = "professional",
        sender_name: Optional[str] = None,
        language: str = "english",
        thread_history: Optional[str] = None,
        signature_text: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """
        Generate a draft reply for an email (returns string).
        Maintains backward compatibility with all existing test signatures.
        """
        text, _ = await self.generate_reply_with_metadata(
            email_subject=email_subject,
            email_body=email_body,
            tone=tone,
            sender_name=sender_name,
            language=language,
            thread_history=thread_history,
            signature_text=signature_text,
            user_name=user_name,
        )
        return text

    async def generate_reply_draft(
        self,
        subject: str,
        body: str,
        tone: str = "professional",
        sender_name: Optional[str] = None,
        language: str = "english",
        thread_history: Optional[str] = None,
        signature_text: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> str:
        """Alias for generate_reply matching automation engine conventions."""
        return await self.generate_reply(
            email_subject=subject,
            email_body=body,
            tone=tone,
            sender_name=sender_name,
            language=language,
            thread_history=thread_history,
            signature_text=signature_text,
            user_name=user_name,
        )

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
            # pyrefly: ignore[import-missing, missing-import]
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
        self,
        subject: str,
        body: str,
        tone: str,
        sender_name: Optional[str] = None,
        language: str = "english",
        thread_history: Optional[str] = None,
        signature_text: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Optional[str]:
        """Call Google Gemini for reply generation."""
        try:
            from google import genai
            from google.genai import types as genai_types

            tone_cfg = _resolve_tone(tone)
            first_name = sender_name.split()[0].capitalize() if sender_name and sender_name.strip() else None
            greeting = (
                f"Dear {first_name}," if first_name and tone.lower() in ("professional", "formal")
                else (f"Hi {first_name}," if first_name else tone_cfg['greeting'])
            )

            lang_instruction = ""
            lang_clean = (language or "english").lower().strip()
            if lang_clean == "hindi":
                lang_instruction = "\nWrite the reply in clean, professional Hindi (Devanagari script)."
            elif lang_clean == "hinglish":
                lang_instruction = "\nWrite the reply in natural, everyday Hinglish (Hindi written using the English/Latin alphabet, commonly used in business emails)."

            thread_section = f"\n\nConversation context:\n{thread_history}" if thread_history else ""
            closing = _format_signature(tone_cfg.get("closing", "Best regards"), signature_text, user_name)

            prompt = (
                "You are an expert email assistant drafting an email reply ON BEHALF OF THE RECIPIENT.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Write the reply directly from the first-person perspective of the recipient (e.g. 'I received your email', 'Thank you for contacting me').\n"
                "2. NEVER describe yourself as an artificial intelligence, an AI assistant, or MailMind AI. Do NOT say 'As an AI' or 'I am unable to provide monetary funds'.\n"
                "3. Address the sender's actual subject, questions, and context naturally, concisely, and professionally.\n"
                "4. Never invent company policies, fake promises, financial decisions, approvals, or facts not present in the context.\n"
                "5. If the email requests financial assistance, a loan, funding, a grant, a refund, or a sensitive decision, acknowledge receipt politely and state that you have received their request and will review it and follow up.\n"
                "6. If the email body is empty or lacks information, write a polite note acknowledging the subject and asking for more details.\n"
                f"7. Tone: {tone_cfg['prompt_style']}\n"
                f"{lang_instruction}\n\n"
                f"Original email:\n"
                f"Subject: {subject}\n"
                f"Sender: {sender_name or 'Sender'}\n"
                f"Body:\n{body}{thread_section}\n\n"
                f"Write only the email reply body (no subject line).\n"
                f"Begin with: {greeting}\n"
                f"End with: {closing}\n"
                "Keep the reply concise and under 200 words."
            )

            def _sync_gemini():
                client = genai.Client(api_key=self.current_gemini_key)
                models_to_try = [self.gemini_model, self.gemini_fallback_model, "gemini-2.5-flash", "gemini-1.5-flash"]
                last_err = None
                for m in models_to_try:
                    if not m:
                        continue
                    try:
                        return client.models.generate_content(
                            model=m,
                            contents=prompt,
                            config=genai_types.GenerateContentConfig(
                                max_output_tokens=400,
                                temperature=0.7,
                            ),
                        )
                    except Exception as err:
                        last_err = err
                        continue
                if last_err:
                    raise last_err

            response = await asyncio.to_thread(_sync_gemini)
            text = (response.text or "").strip()
            if text:
                logger.info("Gemini draft generated (tone=%s, chars=%d)", tone, len(text))
                if (signature_text or user_name) and closing:
                    return _attach_signature_once(text, closing)
                return text
            return None
        except ImportError:
            logger.warning("google-genai package not found")
            return None
        except Exception as exc:
            logger.warning("Gemini generation error: %s", exc)
            return None

    async def _generate_with_openai(
        self,
        subject: str,
        body: str,
        tone: str,
        sender_name: Optional[str] = None,
        language: str = "english",
        thread_history: Optional[str] = None,
        signature_text: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Optional[str]:
        """Call OpenAI chat completion for reply generation."""
        try:
            # pyrefly: ignore[missing-import]
            import openai

            tone_cfg = _resolve_tone(tone)
            first_name = sender_name.split()[0].capitalize() if sender_name and sender_name.strip() else None
            greeting = (
                f"Dear {first_name}," if first_name and tone.lower() in ("professional", "formal")
                else (f"Hi {first_name}," if first_name else tone_cfg['greeting'])
            )

            lang_instruction = ""
            lang_clean = (language or "english").lower().strip()
            if lang_clean == "hindi":
                lang_instruction = " Write the reply in clean, professional Hindi (Devanagari script)."
            elif lang_clean == "hinglish":
                lang_instruction = " Write the reply in natural, everyday Hinglish (Hindi written using the English/Latin alphabet)."

            thread_section = f"\n\nConversation context:\n{thread_history}" if thread_history else ""
            closing = _format_signature(tone_cfg.get("closing", "Best regards"), signature_text, user_name)

            def _sync_openai():
                client = openai.OpenAI(api_key=self.current_openai_key)
                return client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert email assistant drafting a reply ON BEHALF OF THE RECIPIENT.\n"
                                "CRITICAL RULES:\n"
                                "1. Write the reply directly from the first-person perspective of the recipient.\n"
                                "2. NEVER describe yourself as an artificial intelligence or AI assistant. Do NOT say 'As an AI' or 'I am MailMind AI'.\n"
                                "3. Address the sender's actual subject and questions naturally and professionally.\n"
                                "4. Never invent company policies, financial decisions, approvals, or facts not present in the context.\n"
                                "5. If the email requests financial assistance, a loan, funding, a grant, or a sensitive decision, acknowledge receipt politely and state that you have received their request and will review it and follow up.\n"
                                "6. If the email body is empty or lacks information, write a polite note acknowledging the subject and asking for more details.\n"
                                f"7. Tone: {tone_cfg['prompt_style']}{lang_instruction}\n"
                                f"Start with '{greeting}' and end with '{closing}'."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Subject: {subject}\nSender: {sender_name or 'Sender'}\n\nBody: {body}{thread_section}",
                        },
                    ],
                    max_tokens=350,
                )

            response = await asyncio.to_thread(_sync_openai)
            text = (response.choices[0].message.content or "").strip()
            if text:
                if (signature_text or user_name) and closing:
                    return _attach_signature_once(text, closing)
                return text
            return None
        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            return None


ai_engine = AIEngine()
