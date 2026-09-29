"""Template endpoints (dispute letters are a paid feature; requesting an
itemized bill is free)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_optional_user, is_paid
from ..models import User
from ..schemas import TemplateRequest, TemplateResponse
from ..templates_engine import available_templates, render_template

router = APIRouter(prefix="/api/templates", tags=["templates"])

PAID_TEMPLATES = {"dispute_charge"}


@router.get("")
def list_templates() -> list[dict]:
    return available_templates()


@router.post("/render", response_model=TemplateResponse)
def render(
    payload: TemplateRequest,
    user: User | None = Depends(get_optional_user),
) -> TemplateResponse:
    if payload.template in PAID_TEMPLATES and not is_paid(user):
        raise HTTPException(
            status_code=402,
            detail="Drafting dispute letters requires a Candorify paid subscription.",
        )
    try:
        tmpl = render_template(payload.template, payload.context, use_ai=payload.use_ai)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TemplateResponse(template=tmpl.key, subject=tmpl.subject, body=tmpl.body)
