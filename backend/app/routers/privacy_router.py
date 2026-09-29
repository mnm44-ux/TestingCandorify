"""Privacy endpoints: run retention sweep, delete all of a user's data."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import Bill, User

router = APIRouter(prefix="/api/privacy", tags=["privacy"])
settings = get_settings()


@router.get("/policy")
def policy() -> dict:
    return {
        "retention_days": settings.upload_retention_days,
        "summary": (
            "When you upload a bill, Candorify parses it and removes personal "
            "identifiers (name, address, sex, birthdate, phone, email, SSN, MRN, "
            "account number) on a best-effort basis. Only medical content (codes, "
            "descriptions, provider name, amounts) is sent to our AI provider "
            "(Google Gemini) for translation. Your original file is never modified. "
            "Uploaded data is minimized, encrypted in transit in production, and "
            "permanently deleted after you finish your review (or automatically "
            "after the retention window). We keep only non-identifying performance "
            "statistics — never your bill contents or personal information — and we "
            "never sell or share your data. Candorify is not a HIPAA-covered entity."
        ),
    }


@router.post("/sweep")
def retention_sweep(db: Session = Depends(get_db)) -> dict:
    """Delete any bill past its retention window. Safe to call repeatedly
    (e.g. from a scheduled job)."""
    now = dt.datetime.now(dt.timezone.utc)
    stale = db.query(Bill).filter(Bill.delete_after.isnot(None), Bill.delete_after < now).all()
    count = len(stale)
    for bill in stale:
        db.delete(bill)
    db.commit()
    return {"deleted": count}


@router.delete("/me")
def delete_my_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """One-tap deletion of the user's account and all associated bills/flags."""
    db.delete(user)  # cascades to subscription, bills, line items, flags, answer keys
    db.commit()
    return {"deleted": True}
