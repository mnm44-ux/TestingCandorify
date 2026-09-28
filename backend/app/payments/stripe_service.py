"""Payment processing via Stripe (test mode) with a local mock fallback.

Design notes / PCI:
  - We NEVER see or store raw card numbers. Card entry happens on Stripe's
    hosted Checkout page (or via Stripe.js Elements on the client). We only
    store Stripe's customer/subscription IDs.
  - In ``payments_mock_mode`` (default, and required in this offline sandbox),
    checkout is simulated locally so the full free->paid upgrade flow works
    end-to-end without network access or real keys. Flip the mode off and set
    the Stripe keys in the environment to use real Stripe test mode.

Setup for real Stripe test mode:
  CANDORIFY_PAYMENTS_MOCK_MODE=false
  CANDORIFY_STRIPE_SECRET_KEY=sk_test_...
  CANDORIFY_STRIPE_PUBLISHABLE_KEY=pk_test_...
  CANDORIFY_STRIPE_PRICE_ID_PAID=price_...
  CANDORIFY_STRIPE_WEBHOOK_SECRET=whsec_...
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from ..config import get_settings

settings = get_settings()


@dataclass
class CheckoutSession:
    id: str
    url: str
    mock: bool


class PaymentError(Exception):
    pass


def _mock_checkout(user_email: str, success_url: str) -> CheckoutSession:
    session_id = "cs_mock_" + uuid.uuid4().hex[:16]
    # Route back through our own confirm endpoint so the mock flow completes.
    url = f"{success_url}?session_id={session_id}&mock=1"
    return CheckoutSession(id=session_id, url=url, mock=True)


def create_checkout_session(
    user_email: str,
    success_url: str,
    cancel_url: str,
    customer_id: str | None = None,
) -> CheckoutSession:
    """Create a Stripe Checkout session for the paid subscription."""
    if settings.payments_mock_mode or not settings.stripe_secret_key:
        return _mock_checkout(user_email, success_url)

    import stripe  # imported lazily so offline installs still work

    stripe.api_key = settings.stripe_secret_key
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": settings.stripe_price_id_paid, "quantity": 1}],
            customer=customer_id,
            customer_email=None if customer_id else user_email,
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
        return CheckoutSession(id=session.id, url=session.url, mock=False)
    except Exception as exc:  # stripe.error.*; keep broad for prototype
        raise PaymentError(str(exc)) from exc


def confirm_session(session_id: str) -> dict:
    """Confirm a completed checkout. Returns customer/subscription references."""
    if session_id.startswith("cs_mock_") or settings.payments_mock_mode:
        return {
            "paid": True,
            "customer_id": "cus_mock_" + uuid.uuid4().hex[:12],
            "subscription_id": "sub_mock_" + uuid.uuid4().hex[:12],
            "mock": True,
        }

    import stripe

    stripe.api_key = settings.stripe_secret_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "paid": session.payment_status == "paid",
            "customer_id": session.customer,
            "subscription_id": session.subscription,
            "mock": False,
        }
    except Exception as exc:
        raise PaymentError(str(exc)) from exc


def publishable_key() -> str:
    return settings.stripe_publishable_key or "pk_test_mock"
