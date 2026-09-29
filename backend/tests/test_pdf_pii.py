"""Tests for PII stripping and PDF line-item parsing (pure logic, no network)."""
from __future__ import annotations

from app.pdf.parser import parse_line_items
from app.pdf.pii import contains_probable_pii, strip_pii

SAMPLE = """Example Regional Medical Center
Patient Name: Jane A. Doe
Address: 123 Main Street, Springfield 62704
DOB: 04/12/1985   Sex: F   Phone: (555) 123-4567
MRN: 88213   Account Number: ACCT-000123
SSN: 123-45-6789   Email: jane.doe@example.com
85025  COMPLETE CBC W/AUTO DIFF     1    $60.00    $60.00
80053  COMPREHENSIVE METABOLIC PANEL  1  $45.00   $45.00
J1885  KETOROLAC INJECTION  qty: 2   $15.00   $30.00
71046  CHEST X-RAY 2 VIEWS   1   $200.00   $200.00
"""


def test_pii_is_removed():
    report = strip_pii(SAMPLE)
    text = report.redacted_text
    for leaked in ["Jane", "123-45-6789", "jane.doe@example.com", "Main Street", "04/12/1985"]:
        assert leaked not in text, f"PII leaked: {leaked}"
    assert not contains_probable_pii(text)
    assert report.total_redactions >= 5


def test_medical_content_is_preserved():
    text = strip_pii(SAMPLE).redacted_text
    # Codes and procedure descriptions must survive (they are not PII).
    for keep in ["85025", "CBC", "KETOROLAC", "X-RAY"]:
        assert keep in text, f"medical content wrongly removed: {keep}"


def test_parser_extracts_only_charge_lines():
    bill = parse_line_items(SAMPLE)
    codes = {li.code for li in bill.line_items}
    assert codes == {"85025", "80053", "J1885", "71046"}
    # ZIP (62704) and MRN (88213) must NOT be parsed as charges.
    assert "62704" not in codes and "88213" not in codes


def test_parser_reads_amounts_and_quantity():
    bill = parse_line_items(SAMPLE)
    by_code = {li.code: li for li in bill.line_items}
    assert by_code["85025"].unit_price == 60.0
    assert by_code["J1885"].quantity == 2.0
    assert by_code["J1885"].code_system == "HCPCS"


def test_parser_guesses_provider():
    bill = parse_line_items(SAMPLE)
    assert "Medical Center" in bill.provider_name
