"""Google Gemini client (optional AI provider).

A small, swappable client used for two things in Candorify:
  1. Translating a billing-code description into plain English + a target language
  2. Drafting/polishing the request-itemized-bill and dispute letters

Design principles (consistent with the translation/benchmark clients):
  - **Key-gated:** does nothing unless ``llm_api_key`` is set and ``llm_enabled``
    is True. The key is read from the environment, never hard-coded.
  - **Graceful:** any error (no key, disabled, network, bad response) raises
    ``LLMUnavailable`` so callers fall back to the existing offline/template path.
  - **Lazy import** of httpx so the offline core runs without the dependency.

Free key (no credit card): https://aistudio.google.com/app/apikey
API docs: https://ai.google.dev/api/generate-content
"""
from __future__ import annotations

from ..config import get_settings

settings = get_settings()


class LLMUnavailable(Exception):
    """Raised when the LLM provider is disabled, unconfigured, or unreachable."""


class GeminiClient:
    """Minimal REST client for the Gemini generateContent endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 15.0,
    ):
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(settings.llm_enabled and self.api_key)

    def generate(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        """Send a single-prompt request and return the model's text.

        Raises ``LLMUnavailable`` on any problem so the caller can fall back.
        """
        if not self.enabled:
            raise LLMUnavailable("Gemini is disabled or no API key is configured")

        import httpx  # lazy import so the offline core runs without the dependency

        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        try:
            resp = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                # Could be a safety block or empty response.
                raise LLMUnavailable("Gemini returned no candidates")
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if not text:
                raise LLMUnavailable("Gemini returned empty text")
            return text
        except LLMUnavailable:
            raise
        except Exception as exc:  # httpx / json / key errors
            raise LLMUnavailable(str(exc)) from exc


_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
