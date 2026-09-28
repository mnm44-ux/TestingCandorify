"""Bill endpoints: generate synthetic bills, submit a bill, run checks, review
flags, translate lines (paid), delete (one-tap), and score accuracy.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_optional_user, is_paid, require_paid
from ..checks import LineView, run_checks
from ..checks.scoring import AnswerItem, aggregate, score_bill
from ..config import get_settings
from ..db import get_db
from ..generator import generate_bill
from ..models import AnswerKey, Bill, Flag, FlagStatus, LineItem, User
from ..schemas import (
    BillIn,
    BillOut,
    FlagStatusUpdate,
    GenerateRequest,
    ScoreResponse,
)
from ..translation import get_translation_service

router = APIRouter(prefix="/api/bills", tags=["bills"])
settings = get_settings()


def _persist_generated(db: Session, gen, user: User | None) -> Bill:
    delete_after = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        days=settings.upload_retention_days
    )
    bill = Bill(
        user_id=user.id if user else None,
        provider_name=gen.provider_name,
        provider_npi=gen.provider_npi,
        patient_name=gen.patient_name,
        service_date=gen.service_date,
        stated_total=gen.stated_total,
        is_synthetic=True,
        delete_after=delete_after,
    )
    for gl in gen.line_items:
        bill.line_items.append(
            LineItem(
                position=gl.position, code=gl.code, code_system=gl.code_system,
                description=gl.description, quantity=gl.quantity,
                unit_price=gl.unit_price, line_total=gl.line_total,
            )
        )
    for ak in gen.answer_key:
        bill.answer_keys.append(
            AnswerKey(
                kind=ak.kind,
                line_positions=",".join(str(p) for p in ak.line_positions),
                detail=ak.detail,
            )
        )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def _line_views(bill: Bill) -> list[LineView]:
    return [
        LineView(
            id=li.id, position=li.position, code=li.code, code_system=li.code_system,
            description=li.description, quantity=li.quantity,
            unit_price=li.unit_price, line_total=li.line_total,
        )
        for li in bill.line_items
    ]


def _run_and_store_flags(db: Session, bill: Bill) -> None:
    # Clear previous flags, then recompute.
    for f in list(bill.flags):
        db.delete(f)
    db.flush()
    findings = run_checks(_line_views(bill), stated_total=bill.stated_total)
    for fnd in findings:
        db.add(
            Flag(
                bill_id=bill.id, kind=fnd.kind, severity=fnd.severity,
                message=fnd.message,
                line_item_ids=",".join(str(i) for i in fnd.line_item_ids),
                status=FlagStatus.open.value,
            )
        )
    db.commit()
    db.refresh(bill)


@router.post("/generate", response_model=BillOut)
def generate(
    req: GenerateRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> Bill:
    gen = generate_bill(
        num_line_items=req.num_line_items,
        inject_errors=req.inject_errors,
        error_rate=req.error_rate,
        seed=req.seed,
    )
    bill = _persist_generated(db, gen, user)
    _run_and_store_flags(db, bill)
    return bill


@router.post("", response_model=BillOut)
def submit_bill(
    payload: BillIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> Bill:
    delete_after = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        days=settings.upload_retention_days
    )
    bill = Bill(
        user_id=user.id if user else None,
        provider_name=payload.provider_name, provider_npi=payload.provider_npi,
        patient_name=payload.patient_name, service_date=payload.service_date,
        stated_total=payload.stated_total, is_synthetic=True,
        delete_after=delete_after,
    )
    for i, li in enumerate(payload.line_items):
        computed_total = li.line_total or round(li.quantity * li.unit_price, 2)
        bill.line_items.append(
            LineItem(
                position=i, code=li.code, code_system=li.code_system,
                description=li.description, quantity=li.quantity,
                unit_price=li.unit_price, line_total=computed_total,
            )
        )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    _run_and_store_flags(db, bill)
    return bill


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(bill_id: int, db: Session = Depends(get_db)) -> Bill:
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.post("/{bill_id}/recheck", response_model=BillOut)
def recheck(bill_id: int, db: Session = Depends(get_db)) -> Bill:
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    _run_and_store_flags(db, bill)
    return bill


@router.patch("/flags/{flag_id}")
def update_flag(flag_id: int, upd: FlagStatusUpdate, db: Session = Depends(get_db)) -> dict:
    valid = {s.value for s in FlagStatus}
    if upd.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(valid)}")
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    # We never auto-conclude; the user explicitly confirms or dismisses.
    flag.status = upd.status
    db.commit()
    return {"id": flag.id, "status": flag.status}


@router.get("/{bill_id}/translate")
def translate_bill_lines(
    bill_id: int,
    target_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(require_paid),  # line-by-line translation is a paid feature
) -> dict:
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    svc = get_translation_service()
    out = []
    for li in bill.line_items:
        result = svc.translate_code(li.code, li.code_system, target_language)
        out.append({
            "line_item_id": li.id,
            "position": li.position,
            "code": li.code,
            "plain_english": result.plain_english,
            "translated": result.translated,
            "source": result.source,
        })
    return {"bill_id": bill.id, "target_language": target_language, "lines": out}


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)) -> dict:
    """One-tap deletion: removes the bill and all associated data immediately."""
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    db.delete(bill)
    db.commit()
    return {"deleted": True, "bill_id": bill_id}


@router.post("/score", response_model=ScoreResponse)
def score_accuracy(
    num_bills: int = 50,
    seed: int = 12345,
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Generate a labeled synthetic set and score the check engine against the
    answer keys. Reports precision / recall / false-positive rate."""
    num_bills = max(1, min(num_bills, 500))
    results = []
    for i in range(num_bills):
        gen = generate_bill(num_line_items=8, inject_errors=True,
                            error_rate=0.35, seed=seed + i)
        lines = [
            LineView(id=None, position=gl.position, code=gl.code,
                     code_system=gl.code_system, description=gl.description,
                     quantity=gl.quantity, unit_price=gl.unit_price,
                     line_total=gl.line_total)
            for gl in gen.line_items
        ]
        findings = run_checks(lines, stated_total=gen.stated_total)
        answers = [AnswerItem(kind=a.kind, line_positions=a.line_positions)
                   for a in gen.answer_key]
        results.append(score_bill(findings, answers))

    agg = aggregate(results)
    meets = agg.recall >= 0.95 and agg.false_positive_rate < 0.05
    return ScoreResponse(
        bills_evaluated=num_bills,
        true_positives=agg.true_positives,
        false_positives=agg.false_positives,
        false_negatives=agg.false_negatives,
        precision=round(agg.precision, 4),
        recall=round(agg.recall, 4),
        false_positive_rate=round(agg.false_positive_rate, 4),
        meets_target=meets,
    )
