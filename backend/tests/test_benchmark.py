"""Tests for the Medicare price-comparison (benchmark) feature."""
from __future__ import annotations

from app.benchmark.service import BenchmarkService
from app.checks.engine import LineView, check_benchmark, run_checks


def _lv(pos, code, unit, qty=1.0):
    return LineView(id=pos, position=pos, code=code, code_system="CPT",
                    description="x", quantity=qty, unit_price=unit,
                    line_total=round(unit * qty, 2))


def test_offline_rate_lookup():
    svc = BenchmarkService()
    r = svc.compare("85025", 55.0)  # Medicare ref ~11.0
    assert r.source == "offline"
    assert r.medicare_rate == 11.0
    assert r.ratio == round(55.0 / 11.0, 2)
    assert "not an error" in r.note.lower() or "review" in r.note.lower()


def test_unknown_code_no_rate():
    svc = BenchmarkService()
    r = svc.compare("00000", 100.0)
    assert r.medicare_rate is None
    assert r.ratio is None
    assert r.source == "none"


def test_benchmark_finding_only_above_threshold():
    svc = BenchmarkService()
    # 85025 ref ~11.0; 11 * 5 = 55 threshold. 60 -> flagged, 30 -> not.
    high = check_benchmark([_lv(0, "85025", 60.0)], svc)
    low = check_benchmark([_lv(0, "85025", 30.0)], svc)
    assert len(high) == 1 and high[0].kind == "benchmark"
    assert "Potential discrepancy to review" in high[0].message
    assert low == []


def test_run_checks_without_service_has_no_benchmark():
    findings = run_checks([_lv(0, "85025", 500.0)])
    assert all(f.kind != "benchmark" for f in findings)


def test_run_checks_with_service_includes_benchmark():
    svc = BenchmarkService()
    findings = run_checks([_lv(0, "85025", 500.0)], benchmark_service=svc)
    assert any(f.kind == "benchmark" for f in findings)
