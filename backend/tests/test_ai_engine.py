"""
Unit tests for src/core/ai.py — AIEngine with Gemini & OpenAI integration.

All tests are fully hermetic: external SDKs are mocked so no real API keys
or network connections are needed.  Tests cover:

  Helpers
  ───────
  - _resolve_tone: all three tones + case-insensitivity + unknown → professional
  - _build_smart_draft: correct greeting/closing per tone, body truncation, empty body

  Gemini branch
  ─────────────
  - Professional / Friendly / Formal tones → correct prompt content
  - Exception → graceful fallback to smart draft
  - Empty response → graceful fallback
  - ImportError (SDK not installed) → graceful fallback
  - Missing API key → skips Gemini entirely

  OpenAI branch (preserved)
  ─────────────────────────
  - Professional tone → returns content
  - Exception → graceful fallback
  - Missing API key → skips OpenAI

  No provider configured
  ──────────────────────
  - Returns smart draft for all tones
  - Unknown/empty tone → professional smart draft

  Contract: never auto-sends
  ──────────────────────────
  - generate_reply() must return a string and never invoke SMTP
"""
import sys
import pytest
from unittest.mock import MagicMock, patch

from src.core.ai import AIEngine, _resolve_tone, _build_smart_draft, _TONE_CONFIG


# ─── Helpers ────────────────────────────────────────────────────────────────

def _engine(provider="gemini", gemini_key="", openai_key="") -> AIEngine:
    """Create an AIEngine bypassing settings, with explicit values."""
    e = AIEngine.__new__(AIEngine)
    e.provider = provider
    e.gemini_key = gemini_key
    e.gemini_model = "gemini-1.5-pro"
    e.openai_key = openai_key
    e.openai_model = "gpt-4o"
    return e


def _genai_response(text: str) -> MagicMock:
    """Mock google.genai generate_content response."""
    r = MagicMock()
    r.text = text
    return r


def _openai_response(text: str) -> MagicMock:
    """Mock openai ChatCompletion response."""
    msg = MagicMock(); msg.content = text
    choice = MagicMock(); choice.message = msg
    r = MagicMock(); r.choices = [choice]
    return r


# ─── _resolve_tone ──────────────────────────────────────────────────────────

def test_resolve_tone_professional():
    cfg = _resolve_tone("professional")
    assert cfg["greeting"] == "Dear Sender,"
    assert "Best regards" in cfg["closing"]


def test_resolve_tone_friendly():
    cfg = _resolve_tone("friendly")
    assert cfg["greeting"] == "Hi there,"
    assert "Cheers" in cfg["closing"]


def test_resolve_tone_formal():
    cfg = _resolve_tone("formal")
    assert cfg["greeting"] == "Dear Sir/Madam,"
    assert "Sincerely" in cfg["closing"]


def test_resolve_tone_case_insensitive():
    assert _resolve_tone("FRIENDLY") == _resolve_tone("friendly")
    assert _resolve_tone("Professional") == _resolve_tone("professional")
    assert _resolve_tone("  FORMAL  ") == _resolve_tone("formal")


def test_resolve_tone_unknown_defaults_to_professional():
    assert _resolve_tone("sarcastic") == _TONE_CONFIG["professional"]
    assert _resolve_tone("") == _TONE_CONFIG["professional"]


# ─── _build_smart_draft ─────────────────────────────────────────────────────

def test_smart_draft_professional():
    d = _build_smart_draft("Test Subject", "Some body text", "professional")
    assert "Dear Sender," in d
    assert "Best regards" in d
    assert "Test Subject" in d


def test_smart_draft_friendly():
    d = _build_smart_draft("Meetup", "Want to grab coffee?", "friendly")
    assert "Hi there," in d
    assert "Cheers" in d


def test_smart_draft_formal():
    d = _build_smart_draft("Contract", "Please sign.", "formal")
    assert "Dear Sir/Madam," in d
    assert "Sincerely" in d


def test_smart_draft_empty_body_uses_placeholder():
    d = _build_smart_draft("Subject", "", "professional")
    assert "your message" in d


def test_smart_draft_body_truncated_to_150():
    body = "A" * 300
    d = _build_smart_draft("S", body, "professional")
    assert "A" * 300 not in d  # full 300-char body not present


# ─── Gemini integration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gemini_professional_tone():
    e = _engine(provider="gemini", gemini_key="real-key")
    reply = "Dear Sender,\n\nThank you.\n\nBest regards,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _genai_response(reply)

    with patch("google.genai.Client", return_value=mock_client):
        result = await e.generate_reply("Project Update", "Please review.", "professional")

    assert result == reply
    # Check the prompt included the professional style hint
    call_prompt = mock_client.models.generate_content.call_args[1]["contents"]
    assert "professional" in call_prompt.lower() or "formal vocabulary" in call_prompt.lower()


@pytest.mark.asyncio
async def test_gemini_friendly_tone():
    e = _engine(provider="gemini", gemini_key="real-key")
    reply = "Hi there,\n\nThanks for reaching out!\n\nCheers,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _genai_response(reply)

    with patch("google.genai.Client", return_value=mock_client):
        result = await e.generate_reply("Coffee Chat", "Want to catch up?", "friendly")

    assert result == reply
    call_prompt = mock_client.models.generate_content.call_args[1]["contents"]
    assert "friendly" in call_prompt.lower() or "conversational" in call_prompt.lower()


@pytest.mark.asyncio
async def test_gemini_formal_tone():
    e = _engine(provider="gemini", gemini_key="real-key")
    reply = "Dear Sir/Madam,\n\nI write to confirm.\n\nSincerely,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _genai_response(reply)

    with patch("google.genai.Client", return_value=mock_client):
        result = await e.generate_reply("Contract Notice", "See document.", "formal")

    assert result == reply
    call_prompt = mock_client.models.generate_content.call_args[1]["contents"]
    assert "formal" in call_prompt.lower()


@pytest.mark.asyncio
async def test_gemini_exception_falls_back_to_smart_draft():
    e = _engine(provider="gemini", gemini_key="bad-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API quota exceeded")

    with patch("google.genai.Client", return_value=mock_client):
        result = await e.generate_reply("Budget Report", "Please review.", "professional")

    assert "Dear Sender," in result
    assert "Budget Report" in result


@pytest.mark.asyncio
async def test_gemini_empty_response_falls_back():
    e = _engine(provider="gemini", gemini_key="key")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _genai_response("")

    with patch("google.genai.Client", return_value=mock_client):
        result = await e.generate_reply("Empty Reply", "body", "friendly")

    # Falls back to smart draft
    assert "Hi there," in result


@pytest.mark.asyncio
async def test_gemini_import_error_falls_back():
    """If google-genai is not installed, engine falls back to smart draft."""
    e = _engine(provider="gemini", gemini_key="key")

    # Simulate ImportError by temporarily removing google.genai from sys.modules
    saved = sys.modules.pop("google.genai", None)
    saved_types = sys.modules.pop("google.genai.types", None)
    try:
        result = await e.generate_reply("Import Test", "body", "professional")
    finally:
        if saved is not None:
            sys.modules["google.genai"] = saved
        if saved_types is not None:
            sys.modules["google.genai.types"] = saved_types

    assert "Dear Sender," in result


@pytest.mark.asyncio
async def test_gemini_no_key_skips_to_fallback():
    """Missing GEMINI_API_KEY → skip Gemini entirely → smart draft."""
    e = _engine(provider="gemini", gemini_key="")

    result = await e.generate_reply("No Key Test", "body", "professional")

    assert "Dear Sender," in result
    assert "No Key Test" in result


# ─── OpenAI integration ──────────────────────────────────────────────────────

try:
    import openai  # noqa: F401
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

_requires_openai = pytest.mark.skipif(not _HAS_OPENAI, reason="openai package not installed")


@_requires_openai
@pytest.mark.asyncio
async def test_openai_professional_tone():
    e = _engine(provider="openai", openai_key="sk-test")
    reply = "Dear Sender,\n\nThank you.\n\nBest regards,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _openai_response(reply)

    with patch("openai.OpenAI", return_value=mock_client):
        result = await e.generate_reply("Q4 Report", "Please review.", "professional")

    assert result == reply


@_requires_openai
@pytest.mark.asyncio
async def test_openai_friendly_tone():
    e = _engine(provider="openai", openai_key="sk-test")
    reply = "Hi there,\n\nHappy to help!\n\nCheers,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _openai_response(reply)

    with patch("openai.OpenAI", return_value=mock_client):
        result = await e.generate_reply("Quick Question", "Can you help?", "friendly")

    assert result == reply


@_requires_openai
@pytest.mark.asyncio
async def test_openai_formal_tone():
    e = _engine(provider="openai", openai_key="sk-test")
    reply = "Dear Sir/Madam,\n\nAcknowledged.\n\nSincerely,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _openai_response(reply)

    with patch("openai.OpenAI", return_value=mock_client):
        result = await e.generate_reply("Legal Notice", "See enclosed.", "formal")

    assert result == reply


@_requires_openai
@pytest.mark.asyncio
async def test_openai_exception_falls_back():
    e = _engine(provider="openai", openai_key="sk-bad")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Invalid API key")

    with patch("openai.OpenAI", return_value=mock_client):
        result = await e.generate_reply("OpenAI Fail", "body", "formal")

    assert "Dear Sir/Madam," in result


@pytest.mark.asyncio
async def test_openai_no_key_skips_to_fallback():
    e = _engine(provider="openai", openai_key="")
    result = await e.generate_reply("No OpenAI Key", "body", "friendly")
    assert "Hi there," in result


# ─── No provider ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_provider_configured_returns_smart_draft():
    e = _engine(provider="none", gemini_key="", openai_key="")
    result = await e.generate_reply("No Provider", "Just a test.", "professional")
    assert "Dear Sender," in result
    assert "No Provider" in result


@pytest.mark.asyncio
async def test_unknown_tone_falls_back_to_professional_draft():
    e = _engine(provider="none", gemini_key="", openai_key="")
    result = await e.generate_reply("Tone Test", "body", "sarcastic")
    assert "Dear Sender," in result
    assert "Best regards" in result


@pytest.mark.asyncio
async def test_empty_tone_string_defaults_to_professional():
    e = _engine(provider="none", gemini_key="", openai_key="")
    result = await e.generate_reply("Empty Tone", "body", "")
    assert "Dear Sender," in result


# ─── Contract: never auto-sends ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_reply_never_sends_email_via_smtp():
    """
    Contract test: generate_reply() must return a string draft and
    must never invoke SMTP or any send mechanism.
    """
    e = _engine(provider="gemini", gemini_key="key")
    reply = "Dear Sender,\n\nTest.\n\nBest regards,\nMailMind AI User"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _genai_response(reply)
    smtp_spy = MagicMock()

    with patch("google.genai.Client", return_value=mock_client), \
         patch("smtplib.SMTP", smtp_spy), \
         patch("smtplib.SMTP_SSL", smtp_spy):
        result = await e.generate_reply("Subject", "Body", "professional")

    assert isinstance(result, str)
    assert len(result) > 0
    smtp_spy.assert_not_called()


@pytest.mark.asyncio
async def test_all_three_tones_return_strings():
    """Smoke test: all three tones produce a non-empty string draft."""
    e = _engine(provider="none")
    for tone in ["professional", "friendly", "formal"]:
        result = await e.generate_reply("Subject", "Body.", tone)
        assert isinstance(result, str), f"tone={tone} returned non-string"
        assert len(result) > 10, f"tone={tone} returned too-short draft"
