"""Upload a real bill PDF, review parsed lines, get an annotated PDF, then wipe.

Privacy model (hybrid):
  - The PDF is parsed LOCALLY (pypdf). The original bytes are never stored and
    never modified.
  - Before any external call, PII is stripped. Only MEDICAL content (codes,
    descriptions, provider, amounts) is sent to Gemini for translation.
  - Parsed data lives on a Bill row marked is_synthetic=False and is DELETED on
    survey submit (finalize) or by the retention sweep — whichever comes first.
  - The generated annotated PDF is built on demand and returned; it is not
    persisted server-side.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..checks import LineView, run_checks
from ..config import get_settings
from ..db import get_db
from ..models import Bill, LineItem, SurveyStat, User
from ..pdf import build_annotated_pdf, extract_text, parse_line_items, strip_pii
from ..pdf.annotate import AnnotatedLine
from ..schemas import ReviewSubmit, SurveySubmit, UploadParseResponse
from ..translation import get_translation_service

router = APIRouter(prefix="/api/upload", tags=["upload"])
settings = get_settings()

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _owned_upload(db: Session, bill_id: int, user: User) -> Bill:
    bill = db.get(Bill, bill_id)
    if not bill or bill.user_id != user.id or bill.is_synthetic:
        raise HTTPException(status_code=404, detail="Upload not found")
    return bill


@router.post("/pdf", response_model=UploadParseResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadParseResponse:
    """Parse a bill PDF locally and return candidate line items for review.

    The original PDF bytes are read in memory, parsed, then discarded — never
    written to disk or persisted.
    """
    if (file.content_type or "") not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large (max 10 MB).")

    try:
        text = extract_text(data)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Could not read this PDF. You can enter the line items manually.",
        )
    finally:
        data = b""  # drop the raw bytes immediately

    parsed = parse_line_items(text)
    pii = strip_pii(text)  # counts only; we don't keep the text

    return UploadParseResponse(
        provider_name=parsed.provider_name,
        service_date="",
        stated_total=0.0,
        line_items=[{
            "code": li.code, "code_system": li.code_system, "description": li.description,
            "quantity": li.quantity, "unit_price": li.unit_price, "line_total": li.line_total,
        } for li in parsed.line_items],
        pii_redaction_counts=pii.counts,
        notice=(
            "We parsed your bill locally and removed personal identifiers. Please "
            "review and correct the lines below before continuing. Only medical "
            "details (codes, descriptions, amounts) will be sent to our AI "
            "translation provider (Google Gemini)."
        ),
    )


@router.post("/review")
def submit_review(
    payload: ReviewSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Persist the user-reviewed lines (ephemeral), run checks, and return the
    bill id + flags. Data is deleted on survey submit."""
    delete_after = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        days=settings.upload_retention_days
    )
    bill = Bill(
        user_id=user.id,
        provider_name=payload.provider_name or "Uploaded Provider",
        patient_name="(personal info removed)",
        service_date=payload.service_date,
        stated_total=payload.stated_total,
        is_synthetic=False,  # real uploaded bill (medical-only, PII stripped)
        delete_after=delete_after,
    )
    for i, li in enumerate(payload.line_items):
        total = li.line_total or round(li.quantity * li.unit_price, 2)
        bill.line_items.append(LineItem(
            position=i, code=li.code, code_system=li.code_system,
            description=li.description, quantity=li.quantity,
            unit_price=li.unit_price, line_total=total,
        ))
    db.add(bill)
    db.commit()
    db.refresh(bill)

    findings = run_checks(
        [LineView(id=li.id, position=li.position, code=li.code,
                  code_system=li.code_system, description=li.description,
                  quantity=li.quantity, unit_price=li.unit_price,
                  line_total=li.line_total) for li in bill.line_items],
        stated_total=bill.stated_total,
    )
    flags = [{"kind": f.kind, "message": f.message, "positions": f.line_positions}
             for f in findings]
    return {"bill_id": bill.id, "flags": flags, "flag_count": len(flags)}


@router.get("/{bill_id}/annotated.pdf")
def download_annotated(
    bill_id: int,
    target_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Generate and return a NEW annotated PDF. The original upload is untouched."""
    bill = _owned_upload(db, bill_id, user)
    svc = get_translation_service()

    ann_lines = []
    for li in bill.line_items:
        tr = svc.translate_code(li.code, li.code_system, target_language)
        ann_lines.append(AnnotatedLine(
            position=li.position, code=li.code, description=li.description,
            plain_english=tr.translated or tr.plain_english,
            quantity=li.quantity, unit_price=li.unit_price, line_total=li.line_total,
        ))

    findings = run_checks(
        [LineView(id=li.id, position=li.position, code=li.code,
                  code_system=li.code_system, description=li.description,
                  quantity=li.quantity, unit_price=li.unit_price,
                  line_total=li.line_total) for li in bill.line_items],
        stated_total=bill.stated_total,
    )
    flags = [{"message": f.message} for f in findings]

    pdf_bytes = build_annotated_pdf(
        provider_name=bill.provider_name, service_date=bill.service_date,
        lines=ann_lines, flags=flags, stated_total=bill.stated_total,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="candorify-review.pdf"'},
    )


@router.post("/{bill_id}/finalize")
def finalize_and_wipe(
    bill_id: int,
    survey: SurveySubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Record STATS-ONLY survey results, then permanently delete the uploaded
    bill and all its medical line items/flags."""
    bill = _owned_upload(db, bill_id, user)

    # Save aggregate stats only — no medical content, no identifiers.
    db.add(SurveyStat(
        user_id=user.id,
        estimated_savings=max(0.0, survey.estimated_savings),
        flags_shown=max(0, survey.flags_shown),
        flags_marked_helpful=max(0, survey.flags_marked_helpful),
        satisfaction=survey.satisfaction,
    ))
    # Wipe the medical data.
    db.delete(bill)  # cascades to line items + flags
    db.commit()
    return {"wiped": True, "bill_id": bill_id}
