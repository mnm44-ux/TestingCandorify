"""Tests for the check engine and accuracy scoring (pure logic, no web deps)."""
from __future__ import annotations

from app.checks.engine import LineView, run_checks
from app.checks.scoring import AnswerItem, aggregate, score_bill
from app.generator.synthetic import generate_bill


def _lv(pos, code, qty, unit, total, system="CPT", desc="x"):
    return LineView(id=pos, position=pos, code=code, code_system=system,
                    description=desc, quantity=qty, unit_price=unit, line_total=total)


def test_detects_duplicate():
    lines = [_lv(0, "85025", 1, 60.0, 60.0), _lv(1, "85025", 1, 60.0, 60.0)]
    findings = run_checks(lines)
    kinds = {f.kind for f in findings}
    assert "duplicate" in kinds


def test_detects_arithmetic():
    lines = [_lv(0, "80053", 1, 50.0, 75.0)]  # 1 * 50 != 75
    findings = run_checks(lines)
    assert any(f.kind == "arithmetic" for f in findings)


def test_detects_quantity():
    lines = [_lv(0, "99284", 8, 500.0, 4000.0)]  # ER visit qty 8 is implausible
    findings = run_checks(lines)
    assert any(f.kind == "quantity" for f in findings)


def test_detects_total_mismatch():
    lines = [_lv(0, "80053", 1, 50.0, 50.0)]
    findings = run_checks(lines, stated_total=999.0)
    assert any(f.kind == "total_mismatch" for f in findings)


def test_no_false_positive_on_clean_bill():
    lines = [_lv(0, "80053", 1, 50.0, 50.0), _lv(1, "85025", 1, 40.0, 40.0)]
    findings = run_checks(lines, stated_total=90.0)
    assert findings == []


def test_flag_language_is_never_conclusive():
    lines = [_lv(0, "85025", 1, 60.0, 60.0), _lv(1, "85025", 1, 60.0, 60.0)]
    for f in run_checks(lines):
        assert "Potential discrepancy to review" in f.message
        assert "confirmed error" not in f.message.lower()
        assert f.severity == "review"


def test_accuracy_meets_target_over_synthetic_set():
    results = []
    for i in range(150):
        gen = generate_bill(num_line_items=8, inject_errors=True, error_rate=0.35, seed=i)
        lines = [
            LineView(id=None, position=g.position, code=g.code, code_system=g.code_system,
                     description=g.description, quantity=g.quantity,
                     unit_price=g.unit_price, line_total=g.line_total)
            for g in gen.line_items
        ]
        findings = run_checks(lines, stated_total=gen.stated_total)
        answers = [AnswerItem(kind=a.kind, line_positions=a.line_positions) for a in gen.answer_key]
        results.append(score_bill(findings, answers))
    agg = aggregate(results)
    assert agg.recall >= 0.95
    assert agg.false_positive_rate < 0.05
