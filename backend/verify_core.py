"""Standalone verification of Candorify core logic using only the stdlib.

This imports the pure-Python modules (generator, check engine, scoring,
translation service offline path, template engine) WITHOUT FastAPI/SQLAlchemy,
so it runs even when third-party packages can't be installed. It proves the
accuracy story and the safety framing.

Run: python3 verify_core.py
"""
from __future__ import annotations

import sys

from app.checks.engine import LineView, run_checks
from app.checks.scoring import AnswerItem, aggregate, score_bill
from app.generator.synthetic import generate_bill
from app.templates_engine.engine import render_template
from app.translation.service import TranslationService


def _lines_from_gen(gen):
    return [
        LineView(id=None, position=gl.position, code=gl.code,
                 code_system=gl.code_system, description=gl.description,
                 quantity=gl.quantity, unit_price=gl.unit_price,
                 line_total=gl.line_total)
        for gl in gen.line_items
    ]


def test_generator_and_flag_language():
    gen = generate_bill(num_line_items=8, inject_errors=True, seed=1)
    assert gen.is_synthetic is True
    assert len(gen.line_items) >= 8
    assert len(gen.answer_key) >= 1
    findings = run_checks(_lines_from_gen(gen), stated_total=gen.stated_total)
    # Every finding must be framed as a potential discrepancy to review.
    for f in findings:
        assert "Potential discrepancy to review" in f.message, f.message
        assert f.severity == "review"
    print(f"  generator: {len(gen.line_items)} lines, "
          f"{len(gen.answer_key)} injected errors, {len(findings)} findings OK")


def test_accuracy_targets(num_bills=200, seed=12345):
    results = []
    for i in range(num_bills):
        gen = generate_bill(num_line_items=8, inject_errors=True,
                            error_rate=0.35, seed=seed + i)
        findings = run_checks(_lines_from_gen(gen), stated_total=gen.stated_total)
        answers = [AnswerItem(kind=a.kind, line_positions=a.line_positions)
                   for a in gen.answer_key]
        results.append(score_bill(findings, answers))
    agg = aggregate(results)
    print(f"  accuracy over {num_bills} bills:")
    print(f"    TP={agg.true_positives} FP={agg.false_positives} FN={agg.false_negatives}")
    print(f"    precision={agg.precision:.4f} recall={agg.recall:.4f} "
          f"false_positive_rate={agg.false_positive_rate:.4f}")
    meets = agg.recall >= 0.95 and agg.false_positive_rate < 0.05
    print(f"    meets target (recall>=0.95, FPR<0.05): {meets}")
    assert meets, "Accuracy target not met"


def test_translation_offline():
    svc = TranslationService()
    r = svc.translate_code("85025", "CPT", "es")
    assert "blood count" in r.plain_english.lower()
    assert r.source in {"offline", "nlm", "none"}
    print(f"  translation 85025 -> EN: '{r.plain_english}'")
    print(f"  translation 85025 -> ES: '{r.translated}' (source={r.source})")
    r2 = svc.translate_code("99213", "CPT", "es")
    assert r2.translated  # some Spanish text returned
    print(f"  translation 99213 -> ES: '{r2.translated}'")


def test_templates():
    t = render_template("request_itemized_bill",
                        {"provider_name": "Testville", "patient_name": "Alex Sample"})
    assert "itemized bill" in t.body.lower()
    assert "Testville" in t.body
    d = render_template("dispute_charge", {
        "provider_name": "Testville", "patient_name": "Alex Sample",
        "items": [{"code": "85025", "description": "CBC", "line_total": 60.0,
                   "note": "appears twice"}],
    })
    assert "85025" in d.body
    assert "not asserting that these are errors" in d.body  # safe framing
    print("  templates: request_itemized_bill + dispute_charge render OK")


def main():
    print("Candorify core verification")
    print("=" * 40)
    try:
        print("[1] Generator + flag language")
        test_generator_and_flag_language()
        print("[2] Accuracy targets")
        test_accuracy_targets()
        print("[3] Translation (offline path)")
        test_translation_offline()
        print("[4] Templates")
        test_templates()
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
    print("=" * 40)
    print("ALL CORE CHECKS PASSED")


if __name__ == "__main__":
    main()
