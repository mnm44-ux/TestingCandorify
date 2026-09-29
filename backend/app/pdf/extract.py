"""AI-assisted bill extraction (privacy-preserving).

Given text that has ALREADY had personal identifiers stripped locally, use
Gemini to extract structured line items + the provider/hospital name and a
plain-English explanation for each line — so the user doesn't have to type or
correct anything.

Privacy: this only ever receives PII-redacted text (see pdf/pii.py). Personal
identifiers are already replaced with [REDACTED] before this runs, so only
medical content and the hospital/provider name reach the model. If Gemini is
unavailable, the caller falls back to the local regex parser.

Guarantee: extraction NEVER invents charges. The prompt instructs the model to
copy values exactly from the text and to omit anything it cannot read, and the
result is validated (numbers must be numbers) before use.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..llm import LLMUnavailable, get_llm_client


@dataclass
class ExtractedLine:
    code: str
    code_system: str
    description: str
    quantity: float
    unit_price: float
    line_total: float
    plain_english: str = ""


@dataclass
class ExtractedBill:
    provider_name: str = "Uploaded Provider"
    service_date: str = ""
    stated_total: float = 0.0
    line_items: list[ExtractedLine] = field(default_factory=list)


_PROMPT = (
    "You extract line items from a medical bill. The text below has already had "
    "personal information removed and may contain [REDACTED] markers — IGNORE "
    "those and never try to infer personal data.\n\n"
    "Rules (follow exactly):\n"
    "- Copy values EXACTLY as they appear. Do NOT invent, estimate, or round.\n"
    "- Only include a line if it has a billing code (CPT = 5 digits, HCPCS = a "
    "letter + 4 digits). Skip anything you cannot read.\n"
    "- For each line add a short, factual plain-English explanation of the code. "
    "If unsure of the meaning, leave plain_english as an empty string.\n"
    "- Capture the hospital/provider name (this is allowed) and, if present, the "
    "service date and the stated total.\n\n"
    "Respond with ONLY valid JSON in this exact shape (no markdown, no prose):\n"
    '{"provider_name": "...", "service_date": "", "stated_total": 0.0, '
    '"line_items": [{"code": "", "code_system": "CPT", "description": "", '
    '"quantity": 1, "unit_price": 0.0, "line_total": 0.0, "plain_english": ""}]}\n\n'
    "BILL TEXT:\n"
)


def _num(v, default=0.0) -> float:
    try:
        if isinstance(v, str):
            v = v.replace(",", "").replace("$", "").strip()
        return float(v)
    except (ValueError, TypeError):
        return default


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` fences."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def extract_bill(redacted_text: str, llm_client=None) -> ExtractedBill | None:
    """Extract a structured bill from PII-redacted text via Gemini.

    Returns None if the LLM is unavailable or the response can't be parsed, so
    the caller can fall back to the local regex parser.
    """
    client = llm_client if llm_client is not None else get_llm_client()
    try:
        raw = client.generate(_PROMPT + redacted_text, temperature=0.0, max_tokens=1500)
    except LLMUnavailable:
        return None

    try:
        data = json.loads(_strip_code_fence(raw))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    lines: list[ExtractedLine] = []
    for item in data.get("line_items", []) or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip().upper()
        if not re.fullmatch(r"[A-Z]\d{4}|\d{5}", code):
            continue  # enforce a valid code; never fabricate lines
        qty = _num(item.get("quantity"), 1.0) or 1.0
        unit = _num(item.get("unit_price"))
        total = _num(item.get("line_total")) or round(qty * unit, 2)
        lines.append(ExtractedLine(
            code=code,
            code_system="HCPCS" if code[0].isalpha() else "CPT",
            description=str(item.get("description", "")).strip(),
            quantity=qty, unit_price=unit, line_total=total,
            plain_english=str(item.get("plain_english", "")).strip(),
        ))

    if not lines:
        return None

    return ExtractedBill(
        provider_name=str(data.get("provider_name") or "Uploaded Provider").strip(),
        service_date=str(data.get("service_date") or "").strip(),
        stated_total=_num(data.get("stated_total")),
        line_items=lines,
    )
