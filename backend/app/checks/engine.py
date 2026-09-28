"""Check engine.

Analyzes a bill's line items and produces *potential discrepancies to review*.
The engine NEVER concludes that an error exists — every finding is phrased as
something for the user to confirm or dismiss.

Detectors:
  - duplicate      : two lines with same code, unit price, and quantity
  - arithmetic     : line_total != round(quantity * unit_price)
  - quantity       : quantity above a per-service plausibility threshold
  - total_mismatch : stated_total != sum(line_totals)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# Services where more than 1 unit is rarely legitimate on a single bill line.
# Conservative thresholds keep the false-positive rate low.
QUANTITY_THRESHOLDS: dict[str, float] = {
    "99213": 1, "99214": 1, "99284": 1, "99285": 1,  # visits
    "71046": 1, "74177": 1, "70450": 1, "72148": 1,  # imaging
    "93000": 1, "80053": 1, "85025": 1, "80048": 1,  # labs/panels
    "81001": 1,
}
DEFAULT_QUANTITY_THRESHOLD = 4.0
MONEY_TOLERANCE = 0.01


@dataclass
class LineView:
    """Minimal view of a line item the engine needs."""
    id: int | None
    position: int
    code: str
    code_system: str
    description: str
    quantity: float
    unit_price: float
    line_total: float


@dataclass
class Finding:
    kind: str          # duplicate | arithmetic | quantity | total_mismatch
    severity: str      # always "review"
    message: str
    line_positions: list[int]
    line_item_ids: list[int]


def _money_eq(a: float, b: float) -> bool:
    return abs(a - b) <= MONEY_TOLERANCE


def check_arithmetic(lines: list[LineView]) -> list[Finding]:
    findings = []
    for ln in lines:
        expected = round(ln.quantity * ln.unit_price, 2)
        if not _money_eq(expected, ln.line_total):
            findings.append(
                Finding(
                    kind="arithmetic",
                    severity="review",
                    message=(
                        f"Potential discrepancy to review: on line {ln.position + 1} "
                        f"({ln.code} — {ln.description}), the listed line total of "
                        f"${ln.line_total:,.2f} does not match quantity "
                        f"{ln.quantity:g} × unit price ${ln.unit_price:,.2f} "
                        f"(= ${expected:,.2f}). You may want to ask the provider to explain."
                    ),
                    line_positions=[ln.position],
                    line_item_ids=[ln.id] if ln.id is not None else [],
                )
            )
    return findings


def check_duplicates(lines: list[LineView]) -> list[Finding]:
    groups: dict[tuple, list[LineView]] = defaultdict(list)
    for ln in lines:
        key = (ln.code.upper(), round(ln.unit_price, 2), round(ln.quantity, 2))
        groups[key].append(ln)

    findings = []
    for key, group in groups.items():
        if len(group) > 1:
            positions = [g.position for g in group]
            ids = [g.id for g in group if g.id is not None]
            findings.append(
                Finding(
                    kind="duplicate",
                    severity="review",
                    message=(
                        f"Potential discrepancy to review: the charge for {group[0].code} "
                        f"({group[0].description}) at ${group[0].unit_price:,.2f} appears "
                        f"{len(group)} times (lines "
                        f"{', '.join(str(p + 1) for p in positions)}). "
                        f"This could be a duplicate — consider confirming it was performed "
                        f"more than once."
                    ),
                    line_positions=positions,
                    line_item_ids=ids,
                )
            )
    return findings


def check_quantities(lines: list[LineView]) -> list[Finding]:
    findings = []
    for ln in lines:
        threshold = QUANTITY_THRESHOLDS.get(ln.code.upper(), DEFAULT_QUANTITY_THRESHOLD)
        if ln.quantity > threshold:
            findings.append(
                Finding(
                    kind="quantity",
                    severity="review",
                    message=(
                        f"Potential discrepancy to review: line {ln.position + 1} "
                        f"({ln.code} — {ln.description}) lists a quantity of "
                        f"{ln.quantity:g}, which is higher than typically expected "
                        f"for this service. You may want to confirm this quantity."
                    ),
                    line_positions=[ln.position],
                    line_item_ids=[ln.id] if ln.id is not None else [],
                )
            )
    return findings


def check_total(lines: list[LineView], stated_total: float) -> list[Finding]:
    subtotal = round(sum(ln.line_total for ln in lines), 2)
    if stated_total and not _money_eq(subtotal, stated_total):
        return [
            Finding(
                kind="total_mismatch",
                severity="review",
                message=(
                    f"Potential discrepancy to review: the bill's stated total of "
                    f"${stated_total:,.2f} does not match the sum of the line items "
                    f"(${subtotal:,.2f}). You may want to ask for a corrected statement."
                ),
                line_positions=[],
                line_item_ids=[],
            )
        ]
    return []


def run_checks(lines: list[LineView], stated_total: float = 0.0) -> list[Finding]:
    """Run all detectors and return the combined list of findings."""
    findings: list[Finding] = []
    findings += check_duplicates(lines)
    findings += check_arithmetic(lines)
    findings += check_quantities(lines)
    findings += check_total(lines, stated_total)
    return findings
