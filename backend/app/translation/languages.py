"""Supported target languages + a small offline phrase dictionary.

The offline dictionary lets language translation work without any network
access (the sandbox is offline). In production, LibreTranslate provides full
free-text translation; this dictionary is only a graceful fallback so the
prototype never fails to render something useful.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "zh": "Chinese (Simplified)",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "pt": "Portuguese",
    "ru": "Russian",
}

# Whole-phrase translations for the plain-English descriptions we generate.
# Keyed by (language, english_phrase). Only a representative subset is filled
# in for the offline fallback; unknown phrases fall back to English text
# prefixed with the language note.
OFFLINE_PHRASES: dict[str, dict[str, str]] = {
    "es": {
        "Standard office visit with your doctor (established patient)":
            "Consulta médica estándar con su doctor (paciente establecido)",
        "Complete blood count (checks red/white cells and platelets)":
            "Hemograma completo (revisa glóbulos rojos/blancos y plaquetas)",
        "Chest X-ray, two views": "Radiografía de tórax, dos vistas",
        "Drawing blood from a vein for testing":
            "Extracción de sangre de una vena para análisis",
        "Emergency room visit, high complexity":
            "Visita a la sala de emergencias, alta complejidad",
        "Ondansetron (Zofran) injection — anti-nausea medication":
            "Inyección de ondansetrón (Zofran) — medicamento contra las náuseas",
    },
    "fr": {
        "Standard office visit with your doctor (established patient)":
            "Consultation médicale standard avec votre médecin (patient établi)",
        "Chest X-ray, two views": "Radiographie thoracique, deux vues",
        "Drawing blood from a vein for testing":
            "Prélèvement de sang dans une veine pour analyse",
    },
}


def is_supported(lang: str) -> bool:
    return lang in SUPPORTED_LANGUAGES


def offline_translate(text: str, target: str) -> str | None:
    if target == "en":
        return text
    table = OFFLINE_PHRASES.get(target)
    if table and text in table:
        return table[text]
    return None
