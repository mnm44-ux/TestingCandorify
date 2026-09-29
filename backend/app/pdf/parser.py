"""PDF text extraction and line-item parsing (local, no network).

Real itemized bills vary wildly in layout, so parsing is best-effort and the
user is expected to review/correct the parsed lines before checks run. We look
for lines that contain a recognizable CPT/HCPCS code plus dollar amounts.

Codes:
  CPT   : 5 digits (e.g. 85025)
  HCPCS : 1 letter + 4 digits (e.g. J1885)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_CODE_RE = re.compile(r"\b([A-Z]\d{4}|\d{5})\b")
_MONEY_RE = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})")
_QTY_RE = re.compile(r"\b(?:qty|quantity|units?|x)\s*[:=]?\s*(\d+(?:\.\d+)?)\b", re.I)


@dataclass
class ParsedLine:
    code: str
    code_system: str
    description: str
    quantity: float
    unit_price: float
    line_total: float


@dataclass
class ParsedBill:
    provider_name: str
    line_items: list[ParsedLine] = field(default_factory=list)
    raw_line_count: int = 0


def extract_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF's bytes using pypdf (lazy import)."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _money_to_float(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def _guess_provider(text: str) -> str:
    """Heuristic: first non-empty line that looks like an org name."""
    for line in text.splitlines():
        s = line.strip()
        if len(s) >= 4 and not _CODE_RE.search(s) and not _MONEY_RE.search(s):
            # crude: prefer lines with words like Hospital/Medical/Health/Clinic
            if re.search(r"(?i)hospital|medical|health|clinic|center|physicians?", s):
                return s[:120]
    # fallback: first meaningful line
    for line in text.splitlines():
        s = line.strip()
        if len(s) >= 4:
            return s[:120]
    return "Uploaded Provider"


def parse_line_items(text: str) -> ParsedBill:
    """Parse candidate line items from extracted text. Best-effort."""
    provider = _guess_provider(text)
    lines: list[ParsedLine] = []
    raw = 0
    for raw_line in text.splitlines():
        s = raw_line.strip()
        if not s:
            continue
        code_m = _CODE_RE.search(s)
        if not code_m:
            continue
        amounts = [_money_to_float(m) for m in _MONEY_RE.findall(s)]
        # A real charge line has a code AND at least one dollar amount. This
        # filters out ZIP codes, MRNs and other bare 5-digit numbers.
        if not amounts:
            continue
        raw += 1
        code = code_m.group(1).upper()
        code_system = "HCPCS" if code[0].isalpha() else "CPT"
        qty_m = _QTY_RE.search(s)
        quantity = float(qty_m.group(1)) if qty_m else 1.0

        # Heuristics for unit price / line total from the amounts found.
        if len(amounts) >= 2:
            unit_price, line_total = amounts[0], amounts[-1]
        elif len(amounts) == 1:
            unit_price = amounts[0]
            line_total = round(unit_price * quantity, 2)
        else:
            unit_price = line_total = 0.0

        # Description: text after the code, minus the money tokens.
        after = s[code_m.end():]
        desc = _MONEY_RE.sub("", after).strip(" -:\t")
        desc = re.sub(r"(?i)\b(?:qty|quantity|units?|x)\s*[:=]?\s*\d+(?:\.\d+)?\b", "", desc).strip()

        lines.append(ParsedLine(
            code=code, code_system=code_system, description=desc or "(no description found)",
            quantity=quantity, unit_price=unit_price, line_total=line_total,
        ))
    return ParsedBill(provider_name=provider, line_items=lines, raw_line_count=raw)
