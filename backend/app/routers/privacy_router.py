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
            "Candorify uses synthetic bills only in this prototype and never stores "
            "real patient data. Uploads are minimized, encrypted in transit in "
            "production, auto-deleted after the retention window, and can be removed "
            "instantly with one-tap deletion. We never sell or share your data."
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
