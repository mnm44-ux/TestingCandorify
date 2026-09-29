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
from ..llm import LLMUnavailable, get_llm_client
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
    source: str  # gemini | nlm | offline | none


class TranslationService:
    def __init__(
        self,
        nlm_client: NLMCodeClient | None = None,
        lt_client: LibreTranslateClient | None = None,
        llm_client=None,
    ):
        self.nlm = nlm_client or NLMCodeClient()
        self.lt = lt_client or LibreTranslateClient()
        self.llm = llm_client if llm_client is not None else get_llm_client()

    # ---- Gemini: code -> plain english (+ language) in one call ----
    def _gemini_translate(
        self, code: str, code_system: str, target_language: str
    ) -> tuple[str, str] | None:
        """Return (plain_english, translated) via Gemini, or None if unavailable."""
        lang_name = SUPPORTED_LANGUAGES.get(target_language, "English")
        # If we have an authoritative offline description, give it to the model
        # as grounding so it doesn't invent a meaning for the code.
        meta = offline_lookup(code)
        grounding = (
            f"The official description is: \"{meta['plain']}\". "
            if meta else ""
        )
        prompt = (
            "You are helping a patient understand a line on their medical bill. "
            f"The billing code is {code} ({code_system}). {grounding}"
            "Write ONE short, plain-English sentence a non-medical person can "
            "understand explaining what this charge is for. Be factual and do not "
            "guess if unsure. Then, if the target language is not English, provide "
            "the same sentence translated.\n"
            f"Target language: {lang_name}.\n"
            "Respond in exactly this format (no extra text):\n"
            "ENGLISH: <english sentence>\n"
            "TRANSLATION: <sentence in target language, or same as English if English>"
        )
        try:
            text = self.llm.generate(prompt, temperature=0.2, max_tokens=300)
        except LLMUnavailable:
            return None
        english, translated = self._parse_gemini(text)
        if not english:
            return None
        if target_language == "en" or not translated:
            translated = english
        return english, translated

    @staticmethod
    def _parse_gemini(text: str) -> tuple[str, str]:
        english = translated = ""
        for line in text.splitlines():
            s = line.strip()
            if s.upper().startswith("ENGLISH:"):
                english = s.split(":", 1)[1].strip()
            elif s.upper().startswith("TRANSLATION:"):
                translated = s.split(":", 1)[1].strip()
        # If the model ignored the format, fall back to using the whole text.
        if not english and text.strip():
            english = text.strip().splitlines()[0].strip()
        return english, translated

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

        # Preferred path: Gemini (one call for plain English + translation).
        gemini = self._gemini_translate(code, code_system, target_language)
        if gemini is not None:
            plain, translated = gemini
            return TranslationResult(
                code=code, code_system=code_system, plain_english=plain,
                translated=translated, target_language=target_language,
                source="gemini",
            )

        # Fallback path: offline/NLM description + LibreTranslate/offline language.
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
