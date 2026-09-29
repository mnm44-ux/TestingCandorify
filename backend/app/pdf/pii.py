"""PII detection and stripping.

Before ANY bill content is sent to an external service (Gemini), we remove
personal information. Per product policy we keep only MEDICAL content — codes,
procedure descriptions, hospital/provider name, and amounts — and strip
personal identifiers: patient name, address, sex, birthdate, phone, email,
SSN, medical record number (MRN), account number, and similar.

This is a best-effort redactor using regex patterns. It is intentionally
aggressive (prefers over-redacting a false positive to leaking PII). It is NOT
a guarantee — the terms disclose that redaction is best-effort.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ordered (label, compiled pattern). Order matters: more specific first.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    # Dates of birth (labeled or common formats)
    ("dob", re.compile(r"(?i)\b(?:dob|date of birth|birth\s*date)\b[:\s]*"
                       r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")),
    ("dob", re.compile(r"(?i)\b(?:dob|d\.o\.b\.)\b[:\s]*\S+")),
    # MRN / account / member / policy numbers (labeled)
    ("mrn", re.compile(r"(?i)\b(?:mrn|medical record(?:\s*(?:no|number|#))?)\b[:\s#]*\w+")),
    ("account", re.compile(r"(?i)\b(?:account|acct|member|policy|guarantor|patient)\s*"
                           r"(?:no|number|id|#)\b[:\s#]*\w+")),
    # Sex/gender field (labeled)
    ("sex", re.compile(r"(?i)\b(?:sex|gender)\b[:\s]*\b(?:m|f|male|female|x)\b")),
    # Street address (number + street words)
    ("address", re.compile(r"(?i)\b\d{1,6}\s+[\w.\s]{2,40}\b"
                           r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|"
                           r"drive|dr|court|ct|way|circle|cir|place|pl|terrace|ter)\b\.?")),
    # ZIP+4 (unambiguous) always redacted.
    ("zip", re.compile(r"\b\d{5}-\d{4}\b")),
    # Bare 5-digit ZIP: only when it follows a state abbreviation or a comma
    # (city/state context) so we DON'T redact 5-digit CPT codes like 85025.
    ("zip", re.compile(r"(?i)(?<=,)\s*[A-Z]{0,2}\s*\d{5}\b|\b[A-Z]{2}\s+\d{5}\b")),
    # Patient name (labeled — e.g. "Patient Name: Jane Doe")
    ("name", re.compile(r"(?i)\b(?:patient\s*name|patient|name|guarantor)\b[:\s]*"
                        r"[A-Z][a-z]+(?:\s+[A-Z][a-z.]+){1,3}")),
]

_REDACTION = "[REDACTED]"


@dataclass
class PIIReport:
    redacted_text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_redactions(self) -> int:
        return sum(self.counts.values())


def strip_pii(text: str) -> PIIReport:
    """Redact personal identifiers from raw text. Returns the redacted text and
    a per-category count (no PII values are ever stored in the report)."""
    counts: dict[str, int] = {}
    redacted = text
    for label, pattern in _PATTERNS:
        def _sub(_m, _label=label):
            counts[_label] = counts.get(_label, 0) + 1
            return _REDACTION
        redacted = pattern.sub(_sub, redacted)
    return PIIReport(redacted_text=redacted, counts=counts)


def contains_probable_pii(text: str) -> bool:
    """Quick check used by tests / guards: True if any PII pattern matches."""
    return any(p.search(text) for _, p in _PATTERNS)
