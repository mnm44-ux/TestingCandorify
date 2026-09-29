"""Pydantic request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    preferred_language: str = "en"
    accept_terms: bool = False  # must be True to register


class UserOut(BaseModel):
    id: int
    email: EmailStr
    preferred_language: str
    tier: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Bills ----
class LineItemIn(BaseModel):
    code: str = ""
    code_system: str = "CPT"
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    line_total: float = 0.0


class LineItemOut(LineItemIn):
    id: int
    position: int

    class Config:
        from_attributes = True


class BillIn(BaseModel):
    provider_name: str = "Synthetic Health System"
    provider_npi: str | None = None
    patient_name: str = "Synthetic Patient"
    service_date: str = ""
    stated_total: float = 0.0
    line_items: list[LineItemIn] = []


class FlagOut(BaseModel):
    id: int
    kind: str
    severity: str
    message: str
    line_item_ids: str
    status: str

    class Config:
        from_attributes = True


class BillOut(BaseModel):
    id: int
    provider_name: str
    provider_npi: str | None
    patient_name: str
    service_date: str
    stated_total: float
    is_synthetic: bool
    line_items: list[LineItemOut]
    flags: list[FlagOut]

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    num_line_items: int = 8
    inject_errors: bool = True
    error_rate: float = 0.35
    seed: int | None = None


class FlagStatusUpdate(BaseModel):
    status: str  # confirmed | dismissed | open


# ---- Translation ----
class TranslateCodeRequest(BaseModel):
    code: str
    code_system: str = "CPT"
    target_language: str = "en"


class TranslateCodeResponse(BaseModel):
    code: str
    code_system: str
    plain_english: str
    translated: str
    target_language: str
    source: str  # nlm | offline | none


# ---- Templates ----
class TemplateRequest(BaseModel):
    template: str  # "request_itemized_bill" | "dispute_charge"
    context: dict = {}
    use_ai: bool = False  # draft with Gemini when available (falls back to template)


class TemplateResponse(BaseModel):
    template: str
    subject: str
    body: str


# ---- PDF upload / review ----
class ParsedLineOut(BaseModel):
    code: str
    code_system: str
    description: str
    quantity: float
    unit_price: float
    line_total: float
    plain_english: str = ""


class UploadParseResponse(BaseModel):
    provider_name: str
    service_date: str = ""
    stated_total: float = 0.0
    line_items: list[ParsedLineOut]
    pii_redaction_counts: dict[str, int] = {}
    notice: str


class ReviewSubmit(BaseModel):
    """User-reviewed/corrected lines to run checks + build the annotated PDF."""
    provider_name: str = "Uploaded Provider"
    service_date: str = ""
    stated_total: float = 0.0
    line_items: list[LineItemIn] = []
    target_language: str = "en"


# ---- Survey (stats only) ----
class SurveySubmit(BaseModel):
    estimated_savings: float = 0.0
    flags_shown: int = 0
    flags_marked_helpful: int = 0
    satisfaction: int = Field(default=0, ge=0, le=5)


# ---- Accuracy scoring ----
class ScoreResponse(BaseModel):
    bills_evaluated: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    false_positive_rate: float
    meets_target: bool
