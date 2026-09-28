"""Swappable client for the CMS Medicare Physician Fee Schedule.

Behind a small interface so it can be mocked/swapped like the translation
clients. Degrades gracefully: on any error (or when offline mode is on) it
raises ``RateUnavailable`` so the service falls back to the bundled dataset.

Docs: https://www.cms.gov/medicare/physician-fee-schedule/search
Public data API: https://data.cms.gov/
"""
from __future__ import annotations

from ..config import get_settings

settings = get_settings()


class RateUnavailable(Exception):
    """Raised when a live Medicare rate cannot be retrieved or is disabled."""


class CMSFeeScheduleClient:
    """Fetch a national Medicare allowed amount for a CPT/HCPCS code."""

    def __init__(self, base_url: str | None = None, timeout: float = 6.0):
        self.base_url = (base_url or settings.cms_base_url).rstrip("/")
        self.timeout = timeout

    def get_rate(self, code: str) -> float:
        if settings.benchmark_offline_only:
            raise RateUnavailable("offline mode enabled")
        import httpx  # lazy import so offline core runs without the dependency

        # CMS exposes fee-schedule data via data.cms.gov datasets. The exact
        # dataset id/params are configured via settings so this can be pointed
        # at the current release without code changes.
        url = f"{self.base_url}/data"
        params = {
            settings.cms_code_field: code,
            "size": 1,
        }
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            rows = data if isinstance(data, list) else data.get("data", [])
            if not rows:
                raise RateUnavailable(f"no CMS rate for {code}")
            row = rows[0]
            raw = row.get(settings.cms_rate_field)
            if raw is None:
                raise RateUnavailable(f"rate field missing for {code}")
            return float(raw)
        except RateUnavailable:
            raise
        except Exception as exc:  # httpx / json / value errors
            raise RateUnavailable(str(exc)) from exc
