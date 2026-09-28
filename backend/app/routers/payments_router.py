"""Payment endpoints: start checkout, confirm, and Stripe webhook."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import Subscription, Tier, User
from ..payments import PaymentError, confirm_session, create_checkout_session, publishable_key

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()


@router.get("/config")
def payment_config() -> dict:
    return {
        "publishable_key": publishable_key(),
        "mock_mode": settings.payments_mock_mode,
        "paid_features": [
            "Line-by-line plain-English translation of every charge",
            "Translation into other languages",
            "Comparison against public Medicare rates (coming soon)",
            "Draft dispute letters / templates",
        ],
    }


@router.post("/checkout")
def start_checkout(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    base = str(request.base_url).rstrip("/")
    success_url = f"{base}/api/payments/confirm"
    cancel_url = f"{base}/#pricing"
    customer_id = user.subscription.stripe_customer_id if user.subscription else None
    try:
        session = create_checkout_session(
            user_email=user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_id=customer_id,
        )
    except PaymentError as exc:
        raise HTTPException(status_code=502, detail=f"Payment provider error: {exc}") from exc
    return {"checkout_url": session.url, "session_id": session.id, "mock": session.mock}


def _activate_paid(db: Session, user: User, customer_id: str | None, sub_id: str | None) -> None:
    if user.subscription is None:
        user.subscription = Subscription(user_id=user.id)
    user.subscription.tier = Tier.paid.value
    user.subscription.active = True
    user.subscription.stripe_customer_id = customer_id
    user.subscription.stripe_subscription_id = sub_id
    db.commit()


@router.get("/confirm")
def confirm(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Confirm a completed checkout and upgrade the user to the paid tier."""
    try:
        info = confirm_session(session_id)
    except PaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not info.get("paid"):
        raise HTTPException(status_code=402, detail="Payment not completed")
    _activate_paid(db, user, info.get("customer_id"), info.get("subscription_id"))
    return {"upgraded": True, "tier": Tier.paid.value, "mock": info.get("mock", False)}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Stripe webhook receiver (real mode). In mock mode this is a no-op stub."""
    if settings.payments_mock_mode or not settings.stripe_webhook_secret:
        return {"received": True, "mock": True}

    import stripe

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                _activate_paid(db, user, session.get("customer"), session.get("subscription"))
    return {"received": True}
