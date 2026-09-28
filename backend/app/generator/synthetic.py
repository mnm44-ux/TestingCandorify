"""Synthetic itemized-bill generator with injectable errors + answer key.

Produces realistic-looking itemized bills built from the bundled offline code
set. When ``inject_errors`` is enabled it introduces a controlled mix of:
  - duplicate      : an identical charge line repeated
  - arithmetic     : line_total != quantity * unit_price
  - quantity       : an implausibly high quantity for a service
  - total_mismatch : stated_total != sum(line_totals)

Every injected error is recorded in an answer key so the check engine's
accuracy (precision / recall / false-positive rate) can be measured.

IMPORTANT: All output is SYNTHETIC. No real patient data is ever used.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..data.medical_codes import MEDICAL_CODES, all_codes

PROVIDERS = [
    ("Synthetic Health System", "1234567890"),
    ("Example Regional Medical Center", "1982736450"),
    ("Sample Family Clinic", "1029384756"),
    ("Testville Emergency Physicians", "1122334455"),
]

PATIENTS = ["Alex Sample", "Jordan Doe", "Casey Placeholder", "Riley Example"]


@dataclass
class GenLine:
    position: int
    code: str
    code_system: str
    description: str
    quantity: float
    unit_price: float
    line_total: float


@dataclass
class GenAnswer:
    kind: str              # duplicate | arithmetic | quantity | total_mismatch
    line_positions: list[int]
    detail: str


@dataclass
class GeneratedBill:
    provider_name: str
    provider_npi: str
    patient_name: str
    service_date: str
    stated_total: float
    is_synthetic: bool
    line_items: list[GenLine]
    answer_key: list[GenAnswer] = field(default_factory=list)


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


def generate_bill(
    num_line_items: int = 8,
    inject_errors: bool = True,
    error_rate: float = 0.35,
    seed: int | None = None,
) -> GeneratedBill:
    rng = random.Random(seed)
    num_line_items = max(3, min(num_line_items, 40))

    provider_name, provider_npi = rng.choice(PROVIDERS)
    patient_name = rng.choice(PATIENTS)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    service_date = f"2026-{month:02d}-{day:02d}"

    codes = rng.sample(all_codes(), k=min(num_line_items, len(all_codes())))
    # If more lines requested than unique codes, pad with random reuse.
    while len(codes) < num_line_items:
        codes.append(rng.choice(all_codes()))

    lines: list[GenLine] = []
    for i, code in enumerate(codes):
        meta = MEDICAL_CODES[code]
        unit_price = _round2(rng.uniform(meta["low"], meta["high"]))
        qty = 1.0
        line_total = _round2(qty * unit_price)
        lines.append(
            GenLine(
                position=i,
                code=code,
                code_system=meta["system"],
                description=meta["short"],
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    answers: list[GenAnswer] = []

    if inject_errors and lines:
        num_errors = max(1, round(len(lines) * error_rate))
        error_kinds = ["duplicate", "arithmetic", "quantity"]
        used_positions: set[int] = set()

        for _ in range(num_errors):
            kind = rng.choice(error_kinds)
            candidates = [ln for ln in lines if ln.position not in used_positions]
            if not candidates:
                break
            target = rng.choice(candidates)

            if kind == "duplicate":
                dup = GenLine(
                    position=len(lines),
                    code=target.code,
                    code_system=target.code_system,
                    description=target.description,
                    quantity=target.quantity,
                    unit_price=target.unit_price,
                    line_total=target.line_total,
                )
                lines.append(dup)
                used_positions.add(target.position)
                used_positions.add(dup.position)
                answers.append(
                    GenAnswer(
                        kind="duplicate",
                        line_positions=[target.position, dup.position],
                        detail=f"Line {dup.position} duplicates line {target.position} "
                               f"(code {target.code}).",
                    )
                )
            elif kind == "arithmetic":
                # Break the multiplication: line_total no longer = qty * unit_price
                bad_total = _round2(target.line_total + rng.uniform(20, 150))
                target.line_total = bad_total
                used_positions.add(target.position)
                answers.append(
                    GenAnswer(
                        kind="arithmetic",
                        line_positions=[target.position],
                        detail=f"Line {target.position}: line total {bad_total} does not equal "
                               f"quantity {target.quantity} x unit price {target.unit_price}.",
                    )
                )
            elif kind == "quantity":
                bad_qty = float(rng.randint(5, 20))
                target.quantity = bad_qty
                target.line_total = _round2(bad_qty * target.unit_price)
                used_positions.add(target.position)
                answers.append(
                    GenAnswer(
                        kind="quantity",
                        line_positions=[target.position],
                        detail=f"Line {target.position}: unusually high quantity "
                               f"{bad_qty} for code {target.code}.",
                    )
                )

    subtotal = _round2(sum(ln.line_total for ln in lines))

    # Sometimes inject a stated-total mismatch too.
    stated_total = subtotal
    if inject_errors and rng.random() < 0.4:
        stated_total = _round2(subtotal + rng.uniform(30, 200))
        answers.append(
            GenAnswer(
                kind="total_mismatch",
                line_positions=[],
                detail=f"Stated total {stated_total} does not equal the sum of line "
                       f"totals {subtotal}.",
            )
        )

    return GeneratedBill(
        provider_name=provider_name,
        provider_npi=provider_npi,
        patient_name=patient_name,
        service_date=service_date,
        stated_total=stated_total,
        is_synthetic=True,
        line_items=lines,
        answer_key=answers,
    )
