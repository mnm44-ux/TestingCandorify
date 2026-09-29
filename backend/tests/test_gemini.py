"""Tests for the optional Gemini AI provider (translation + email drafting).

These use fake clients — no network calls — and verify both the AI path and
the graceful fallback when Gemini is unavailable.
"""
from __future__ import annotations

from app.llm import LLMUnavailable
from app.templates_engine.engine import render_template
from app.translation.service import TranslationService


class FakeLLM:
    """Stand-in for GeminiClient that returns a canned response."""
    def __init__(self, response: str):
        self._response = response

    def generate(self, prompt: str, **kwargs) -> str:
        return self._response


class DownLLM:
    """Stand-in that behaves as if Gemini is unavailable."""
    def generate(self, prompt: str, **kwargs) -> str:
        raise LLMUnavailable("down")


# ---- translation ----
def test_translation_uses_gemini_when_available():
    fake = FakeLLM("ENGLISH: A blood test panel.\nTRANSLATION: Un panel de análisis de sangre.")
    svc = TranslationService(llm_client=fake)
    r = svc.translate_code("80053", "CPT", "es")
    assert r.source == "gemini"
    assert r.plain_english == "A blood test panel."
    assert r.translated == "Un panel de análisis de sangre."


def test_translation_english_target_repeats_english():
    fake = FakeLLM("ENGLISH: A blood test panel.\nTRANSLATION: A blood test panel.")
    svc = TranslationService(llm_client=fake)
    r = svc.translate_code("80053", "CPT", "en")
    assert r.source == "gemini"
    assert r.translated == r.plain_english


def test_translation_falls_back_when_gemini_down():
    svc = TranslationService(llm_client=DownLLM())
    r = svc.translate_code("85025", "CPT", "es")
    # Falls back to the offline dataset path.
    assert r.source in {"offline", "nlm", "none"}
    assert "blood count" in r.plain_english.lower()


# ---- email drafting ----
def test_email_uses_ai_when_available():
    fake = FakeLLM("Dear Billing Team,\n\nCould you please send an itemized bill? Thank you.")
    t = render_template(
        "request_itemized_bill",
        {"provider_name": "Acme", "patient_name": "Jane Doe"},
        use_ai=True,
        llm_client=fake,
    )
    assert "Could you please send an itemized bill" in t.body


def test_email_falls_back_to_template_when_ai_down():
    t = render_template(
        "request_itemized_bill",
        {"provider_name": "Acme", "patient_name": "Jane Doe"},
        use_ai=True,
        llm_client=DownLLM(),
    )
    # Falls back to the fixed template content.
    assert "itemized bill" in t.body.lower()
    assert "Acme" in t.body


def test_email_no_ai_by_default():
    # Without use_ai the template is used verbatim (no client touched).
    t = render_template("request_itemized_bill", {"provider_name": "Acme", "patient_name": "Jane"})
    assert "itemized bill" in t.body.lower()
