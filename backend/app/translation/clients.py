"""Swappable clients for external translation/lookup providers.

Two provider clients are defined behind small interfaces so they can be
swapped or mocked easily:

  NLMCodeClient        -> NLM Clinical Table Search Service (code -> description)
  LibreTranslateClient -> LibreTranslate (free-text language translation)

Both degrade gracefully: on any network error (or when offline mode is on)
they raise ``ProviderUnavailable`` so the service layer can fall back to the
bundled offline dataset.

Docs:
  NLM Clinical Tables: https://clinicaltables.nlm.nih.gov/
  LibreTranslate:      https://libretranslate.com/
"""
from __future__ import annotations

from ..config import get_settings

settings = get_settings()


class ProviderUnavailable(Exception):
    """Raised when an external provider cannot be reached or is disabled."""


# NLM Clinical Tables path per code system (hcpcs covers HCPCS/CPT-like lookups).
_NLM_TABLE = {
    "CPT": "hcpcs",
    "HCPCS": "hcpcs",
    "ICD": "icd10cm",
    "ICD10": "icd10cm",
}


class NLMCodeClient:
    """Look up a billing code's official description from NLM Clinical Tables."""

    def __init__(self, base_url: str | None = None, timeout: float = 6.0):
        self.base_url = (base_url or settings.nlm_base_url).rstrip("/")
        self.timeout = timeout

    def describe(self, code: str, code_system: str = "CPT") -> str:
        if settings.translation_offline_only:
            raise ProviderUnavailable("offline mode enabled")
        import httpx  # lazy import so offline core runs without the dependency
        table = _NLM_TABLE.get(code_system.upper(), "hcpcs")
        url = f"{self.base_url}/{table}/v3/search"
        params = {"terms": code, "sf": "code", "df": "code,short_description"}
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # NLM returns: [total, [codes], null, [[code, description], ...]]
            rows = data[3] if len(data) > 3 and data[3] else []
            for row in rows:
                if str(row[0]).upper() == code.upper() and len(row) > 1:
                    return str(row[1])
            if rows and len(rows[0]) > 1:
                return str(rows[0][1])
            raise ProviderUnavailable(f"no NLM match for {code}")
        except (httpx.HTTPError, ValueError, IndexError, KeyError) as exc:
            raise ProviderUnavailable(str(exc)) from exc


class LibreTranslateClient:
    """Translate free text into a target language via LibreTranslate."""

    def __init__(self, url: str | None = None, api_key: str | None = None, timeout: float = 6.0):
        self.url = url or settings.libretranslate_url
        self.api_key = api_key if api_key is not None else settings.libretranslate_api_key
        self.timeout = timeout

    def translate(self, text: str, target: str, source: str = "en") -> str:
        if settings.translation_offline_only:
            raise ProviderUnavailable("offline mode enabled")
        if target == source:
            return text
        import httpx  # lazy import so offline core runs without the dependency
        payload = {"q": text, "source": source, "target": target, "format": "text"}
        if self.api_key:
            payload["api_key"] = self.api_key
        try:
            resp = httpx.post(self.url, data=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("translatedText")
            if not translated:
                raise ProviderUnavailable("empty translation")
            return str(translated)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ProviderUnavailable(str(exc)) from exc
