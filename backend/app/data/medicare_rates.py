"""Bundled sample Medicare rate dataset (national, non-facility, illustrative).

These are approximate, publicly-known ballpark Medicare allowed amounts (USD)
for common CPT/HCPCS codes, used as an OFFLINE benchmark so the price-comparison
feature works without network access. In production the live CMS Physician Fee
Schedule API (https://www.cms.gov/medicare/physician-fee-schedule/search)
provides authoritative, locality-adjusted rates; this table is only a fallback.

Values are intentionally rounded and approximate. They are a *reference point*
for review — not a statement of what a charge "should" be. Medicare rates differ
from commercial/self-pay rates by design.
"""
from __future__ import annotations

# code -> approximate national Medicare allowed amount (USD)
MEDICARE_RATES: dict[str, float] = {
    "99213": 92.0,
    "99214": 131.0,
    "99284": 175.0,
    "99285": 258.0,
    "80053": 14.5,
    "85025": 11.0,
    "80048": 11.5,
    "81001": 4.5,
    "71046": 30.0,
    "74177": 275.0,
    "70450": 130.0,
    "72148": 225.0,
    "36415": 3.0,
    "12001": 130.0,
    "93000": 17.0,
    "96372": 26.0,
    "J1885": 1.5,
    "J2405": 2.0,
    "A9150": 6.0,
    "Q9967": 3.0,
}


def medicare_rate(code: str) -> float | None:
    return MEDICARE_RATES.get(code.strip().upper())
