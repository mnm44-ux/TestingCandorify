"""Translation service: code -> plain English -> target language.

Resolution order for the plain-English description:
  1. Bundled offline dataset (fast, always available, patient-friendly wording)
  2. NLM Clinical Tables (authoritative official description) if online

Resolution order for language translation:
  1. LibreTranslate (full free-text translation) if online
  2. Offline phrase dictionary
  3. Graceful fallback: return English text with a note

The service is a singleton but accepts injected clients for testing.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.medical_codes import lookup as offline_lookup
from .clients import (
    LibreTranslateClient,
    NLMCodeClient,
    ProviderUnavailable,
)
from .languages import SUPPORTED_LANGUAGES, is_supported, offline_translate


@dataclass
class TranslationResult:
    code: str
    code_system: str
    plain_english: str
    translated: str
    target_language: str
    source: str  # nlm | offline | none


class TranslationService:
    def __init__(
        self,
        nlm_client: NLMCodeClient | None = None,
        lt_client: LibreTranslateClient | None = None,
    ):
        self.nlm = nlm_client or NLMCodeClient()
        self.lt = lt_client or LibreTranslateClient()

    # ---- code -> plain english ----
    def describe_code(self, code: str, code_system: str = "CPT") -> tuple[str, str]:
        """Return (plain_english, source)."""
        meta = offline_lookup(code)
        if meta:
            return meta["plain"], "offline"
        try:
            desc = self.nlm.describe(code, code_system)
            return desc, "nlm"
        except ProviderUnavailable:
            return (f"Code {code} ({code_system}). No plain-language description is "
                    f"available offline; look up this code with your provider."), "none"

    # ---- english -> target language ----
    def to_language(self, text: str, target: str) -> str:
        if target == "en" or not target:
            return text
        try:
            return self.lt.translate(text, target=target, source="en")
        except ProviderUnavailable:
            offline = offline_translate(text, target)
            if offline is not None:
                return offline
            label = SUPPORTED_LANGUAGES.get(target, target)
            return f"[{label} translation unavailable offline] {text}"

    def translate_code(
        self, code: str, code_system: str = "CPT", target_language: str = "en"
    ) -> TranslationResult:
        if not is_supported(target_language):
            target_language = "en"
        plain, source = self.describe_code(code, code_system)
        translated = self.to_language(plain, target_language)
        return TranslationResult(
            code=code,
            code_system=code_system,
            plain_english=plain,
            translated=translated,
            target_language=target_language,
            source=source,
        )


_service: TranslationService | None = None


def get_translation_service() -> TranslationService:
    global _service
    if _service is None:
        _service = TranslationService()
    return _service
