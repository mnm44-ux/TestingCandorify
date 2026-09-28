"""Tests for the translation service (offline path) and template engine."""
from __future__ import annotations

from app.templates_engine.engine import render_template
from app.translation.service import TranslationService


def test_code_to_plain_english_offline():
    svc = TranslationService()
    r = svc.translate_code("85025", "CPT", "en")
    assert "blood count" in r.plain_english.lower()
    assert r.source == "offline"


def test_code_translation_to_spanish_offline():
    svc = TranslationService()
    r = svc.translate_code("99213", "CPT", "es")
    assert r.target_language == "es"
    assert r.translated  # non-empty translation returned


def test_unknown_code_degrades_gracefully():
    svc = TranslationService()
    r = svc.translate_code("00000", "CPT", "en")
    assert r.source == "none"
    assert "00000" in r.plain_english


def test_request_itemized_bill_template():
    t = render_template("request_itemized_bill",
                        {"provider_name": "Acme Health", "patient_name": "Jane Doe"})
    assert "itemized bill" in t.body.lower()
    assert "Acme Health" in t.body
    assert "Jane Doe" in t.body


def test_dispute_template_is_non_accusatory():
    t = render_template("dispute_charge", {
        "provider_name": "Acme Health", "patient_name": "Jane Doe",
        "items": [{"code": "85025", "description": "CBC", "note": "appears twice"}],
    })
    assert "85025" in t.body
    # Must frame as a request to review, not an accusation.
    assert "not asserting that these are errors" in t.body


def test_unknown_template_raises():
    import pytest
    with pytest.raises(KeyError):
        render_template("nonexistent")
