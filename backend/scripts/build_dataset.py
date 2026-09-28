"""Generate the labeled synthetic dataset described in the Candorify proposal.

Writes two CSVs into ``data/dataset/``:
  bills.csv       -- every line item of every generated bill
  answer_key.csv  -- the ground-truth injected errors for each bill

This is the "labeled synthetic data set utilized through a spreadsheet" from
the one-pager: an accurate synthetic bill to test on, with injected errors and
an answer key, so false-positive / false-negative rates can be measured.

Run: python -m scripts.build_dataset [num_bills]
"""
from __future__ import annotations

import csv
import os
import sys

from app.generator.synthetic import generate_bill

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "dataset")


def build(num_bills: int = 100, seed: int = 2026) -> tuple[str, str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    bills_path = os.path.abspath(os.path.join(OUT_DIR, "bills.csv"))
    key_path = os.path.abspath(os.path.join(OUT_DIR, "answer_key.csv"))

    with open(bills_path, "w", newline="") as bf, open(key_path, "w", newline="") as kf:
        bw = csv.writer(bf)
        kw = csv.writer(kf)
        bw.writerow(["bill_id", "provider", "service_date", "line_position",
                     "code", "code_system", "description", "quantity",
                     "unit_price", "line_total", "stated_total"])
        kw.writerow(["bill_id", "error_kind", "line_positions", "detail"])

        for bid in range(1, num_bills + 1):
            gen = generate_bill(num_line_items=8, inject_errors=True,
                                error_rate=0.35, seed=seed + bid)
            for li in gen.line_items:
                bw.writerow([bid, gen.provider_name, gen.service_date, li.position,
                             li.code, li.code_system, li.description, li.quantity,
                             li.unit_price, li.line_total, gen.stated_total])
            for a in gen.answer_key:
                kw.writerow([bid, a.kind,
                             " ".join(str(p) for p in a.line_positions), a.detail])

    return bills_path, key_path


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    b, k = build(n)
    print(f"Wrote {b}")
    print(f"Wrote {k}")
