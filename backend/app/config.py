"""Application configuration.

All secrets/keys are read from the environment. Sensible offline-friendly
defaults are provided so the prototype runs end-to-end without any external
services or credentials.
"""
from __future__ import annotations

import os
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # stdlib-only fallback (e.g. offline core verification)
    _HAS_PYDANTIC_SETTINGS = False

    class SettingsConfigDict(dict):  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    class BaseSettings:  # type: ignore[no-redef]
        """Minimal env-backed settings shim used only when pydantic-settings is
        unavailable. Reads CANDORIFY_<UPPER_FIELD> from the environment and
        coerces to the annotated type; otherwise uses the class default."""

        model_config: dict = {}

        def __init__(self, **overrides):
            prefix = self.model_config.get("env_prefix", "")
            for name, typ in type(self).__annotations__.items():
                if name in overrides:
                    value = overrides[name]
                else:
                    env_val = os.environ.get(prefix + name.upper())
                    default = getattr(type(self), name, None)
                    value = self._coerce(env_val, typ, default) if env_val is not None else default
                setattr(self, name, value)

        @staticmethod
        def _coerce(raw, typ, default):
            try:
                if typ is bool or isinstance(default, bool):
                    return str(raw).strip().lower() in {"1", "true", "yes", "on"}
                if typ is int or isinstance(default, int):
                    return int(raw)
                if typ is float or isinstance(default, float):
                    return float(raw)
            except (ValueError, TypeError):
                return default
            return raw


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CANDORIFY_", env_file=".env", extra="ignore")

    # Core
    app_name: str = "Candorify"
    environment: str = "development"
    secret_key: str = "dev-insecure-change-me"  # override in production
    database_url: str = "sqlite:///./candorify.db"

    # Auth
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Privacy / retention
    upload_retention_days: int = 30  # auto-delete uploads after this window

    # Translation providers
    nlm_base_url: str = "https://clinicaltables.nlm.nih.gov/api"
    libretranslate_url: str = "https://libretranslate.com/translate"
    libretranslate_api_key: str = ""  # optional
    # When True, never make network calls; use bundled offline dataset only.
    # Defaults to True so the prototype works in sandboxed/offline environments.
    translation_offline_only: bool = True

    # Payments (Stripe test mode)
    stripe_secret_key: str = ""       # sk_test_...
    stripe_publishable_key: str = ""  # pk_test_...
    stripe_webhook_secret: str = ""   # whsec_...
    stripe_price_id_paid: str = ""    # price_... for the paid tier
    # When True, payments are simulated locally (no real Stripe call needed).
    payments_mock_mode: bool = True

    frontend_origin: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
