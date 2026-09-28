"""Translation endpoints (code -> plain English -> language)."""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas import TranslateCodeRequest, TranslateCodeResponse
from ..translation import get_translation_service
from ..translation.languages import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api/translate", tags=["translation"])


@router.get("/languages")
def languages() -> dict:
    return SUPPORTED_LANGUAGES


@router.post("/code", response_model=TranslateCodeResponse)
def translate_code(payload: TranslateCodeRequest) -> TranslateCodeResponse:
    svc = get_translation_service()
    result = svc.translate_code(
        code=payload.code,
        code_system=payload.code_system,
        target_language=payload.target_language,
    )
    return TranslateCodeResponse(
        code=result.code,
        code_system=result.code_system,
        plain_english=result.plain_english,
        translated=result.translated,
        target_language=result.target_language,
        source=result.source,
    )
