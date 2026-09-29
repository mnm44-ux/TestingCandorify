"""Medicare price-comparison service.

Given a line item, resolves a reference Medicare allowed amount (live CMS API
when online, bundled sample dataset otherwise) and compares the charged unit
price to it. Produces a *ratio* and a benchmark note framed for review — never a
verdict. Medicare rates are only a reference point; commercial/self-pay charges
routinely differ.

Resolution order for the reference rate:
  1. Live CMS Physician Fee Schedule (if online)
  2. Bundled offline sample dataset
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import get_settings
from ..data.medicare_rates import medicare_rate as offline_rate
from .client import CMSFeeScheduleClient, RateUnavailable

settings = get_settings()


@dataclass
class BenchmarkResult:
    code: str
    charged_unit_price: float
    medicare_rate: float | None
    ratio: float | None          # charged / medicare_rate
    source: str                  # cms | offline | none
    note: str


class BenchmarkService:
    def __init__(self, cms_client: CMSFeeScheduleClient | None = None):
        self.cms = cms_client or CMSFeeScheduleClient()

    def reference_rate(self, code: str) -> tuple[float | None, str]:
        """Return (rate, source)."""
        try:
            return self.cms.get_rate(code), "cms"
        except RateUnavailable:
            rate = offline_rate(code)
            if rate is not None:
                return rate, "offline"
            return None, "none"

    def compare(self, code: str, charged_unit_price: float) -> BenchmarkResult:
        rate, source = self.reference_rate(code)
        if rate is None or rate <= 0:
            return BenchmarkResult(
                code=code, charged_unit_price=charged_unit_price,
                medicare_rate=rate, ratio=None, source=source,
                note=("No Medicare reference rate is available for this code, so "
                      "no benchmark comparison could be made."),
            )
        ratio = round(charged_unit_price / rate, 2)
        note = (
            f"The charged unit price of ${charged_unit_price:,.2f} is about "
            f"{ratio:g}x the reference Medicare allowed amount of ${rate:,.2f} "
            f"for this code. Medicare rates differ from commercial and self-pay "
            f"prices by design, so this is context for your review — not an error."
        )
        return BenchmarkResult(
            code=code, charged_unit_price=charged_unit_price,
            medicare_rate=rate, ratio=ratio, source=source, note=note,
        )


_service: BenchmarkService | None = None


def get_benchmark_service() -> BenchmarkService:
    global _service
    if _service is None:
        _service = BenchmarkService()
    return _service
