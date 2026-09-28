"""Tests for the synthetic bill generator + answer key."""
from __future__ import annotations

from app.generator.synthetic import generate_bill


def test_generator_is_deterministic_with_seed():
    a = generate_bill(seed=42)
    b = generate_bill(seed=42)
    assert [(x.code, x.line_total) for x in a.line_items] == \
           [(y.code, y.line_total) for y in b.line_items]
    assert a.stated_total == b.stated_total


def test_generator_marks_synthetic():
    bill = generate_bill(seed=1)
    assert bill.is_synthetic is True


def test_injected_errors_recorded_in_answer_key():
    bill = generate_bill(num_line_items=8, inject_errors=True, error_rate=0.5, seed=7)
    assert len(bill.answer_key) >= 1
    valid_kinds = {"duplicate", "arithmetic", "quantity", "total_mismatch"}
    for a in bill.answer_key:
        assert a.kind in valid_kinds


def test_no_errors_when_disabled():
    bill = generate_bill(num_line_items=6, inject_errors=False, seed=3)
    assert bill.answer_key == []
    # Clean bill: every line total equals qty * unit price
    for li in bill.line_items:
        assert abs(li.line_total - round(li.quantity * li.unit_price, 2)) < 0.01
