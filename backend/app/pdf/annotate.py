"""Generate a NEW annotated PDF summarizing a reviewed bill.

The original uploaded PDF is NEVER modified — this produces a separate document
the patient can download and share with their provider. It lists each line with
its plain-English translation and any potential discrepancies to review.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnnotatedLine:
    position: int
    code: str
    description: str
    plain_english: str
    quantity: float
    unit_price: float
    line_total: float


DISCLAIMER = (
    "Candorify identifies possible billing discrepancies for review. It does not "
    "verify charges, confirm errors, or guarantee savings, and is not a substitute "
    "for a billing auditor, advocate, or legal/financial advisor. Nothing is "
    "confirmed until the provider or insurance agrees."
)


def _clean(text: str) -> str:
    """fpdf2 core fonts are latin-1; drop characters they can't encode."""
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def build_annotated_pdf(
    provider_name: str,
    service_date: str,
    lines: list[AnnotatedLine],
    flags: list[dict],
    stated_total: float | None = None,
) -> bytes:
    """Return the bytes of a newly generated annotated PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Candorify — Bill Review Summary", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, _clean(f"Provider: {provider_name}"), new_x="LMARGIN", new_y="NEXT")
    if service_date:
        pdf.cell(0, 6, _clean(f"Service date: {service_date}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "This is a review summary generated from your uploaded bill. "
                   "Your original bill is unchanged.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Line items with translations
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Charges (with plain-English explanations)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for ln in lines:
        pdf.set_font("Helvetica", "B", 10)
        header = f"{ln.position + 1}. {ln.code}  —  qty {ln.quantity:g} x ${ln.unit_price:,.2f} = ${ln.line_total:,.2f}"
        pdf.multi_cell(0, 6, _clean(header))
        pdf.set_font("Helvetica", "", 10)
        if ln.description:
            pdf.multi_cell(0, 5, _clean(f"   Billed as: {ln.description}"))
        if ln.plain_english:
            pdf.multi_cell(0, 5, _clean(f"   In plain English: {ln.plain_english}"))
        pdf.ln(1)

    if stated_total is not None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _clean(f"Stated total on bill: ${stated_total:,.2f}"),
                 new_x="LMARGIN", new_y="NEXT")

    # Flags
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 95, 6)
    pdf.cell(0, 8, "Potential discrepancies to review", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    if flags:
        for f in flags:
            pdf.multi_cell(0, 5, _clean(f"- {f.get('message', '')}"))
            pdf.ln(1)
    else:
        pdf.multi_cell(0, 5, "No potential discrepancies were surfaced. This does not "
                            "guarantee the bill is correct; please review each line.")

    # Disclaimer footer
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4, _clean(DISCLAIMER))

    out = pdf.output()
    return bytes(out)
