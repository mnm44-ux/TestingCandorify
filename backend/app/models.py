"""SQLAlchemy ORM models for Candorify.

Data model overview:
  User            -- an account (patient)
  Subscription    -- tier (free/paid) + Stripe references
  Bill            -- an itemized bill (synthetic in the prototype)
  LineItem        -- a single charge line on a bill
  Flag            -- a "potential discrepancy to review" found by the check engine
  AnswerKey       -- ground-truth injected errors (for accuracy scoring only)
"""
from __future__ import annotations

import datetime as dt
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Tier(str, Enum):
    free = "free"
    paid = "paid"


class FlagStatus(str, Enum):
    open = "open"          # awaiting user review
    confirmed = "confirmed"  # user chose to confirm (still not "verified" by us)
    dismissed = "dismissed"  # user dismissed


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    # Records that the user accepted the Terms (incl. Gemini/Google disclosure).
    terms_accepted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    subscription: Mapped["Subscription"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    bills: Mapped[list["Bill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    tier: Mapped[str] = mapped_column(String(16), default=Tier.free.value)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="subscription")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(255), default="Synthetic Health System")
    provider_npi: Mapped[str | None] = mapped_column(String(16), nullable=True)
    patient_name: Mapped[str] = mapped_column(String(255), default="Synthetic Patient")
    service_date: Mapped[str] = mapped_column(String(32), default="")
    stated_total: Mapped[float] = mapped_column(Float, default=0.0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)
    # Uploads auto-delete after retention window; computed at creation time.
    delete_after: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="bills")
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", order_by="LineItem.position"
    )
    flags: Mapped[list["Flag"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )
    answer_keys: Mapped[list["AnswerKey"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    code: Mapped[str] = mapped_column(String(16), default="")
    code_system: Mapped[str] = mapped_column(String(16), default="CPT")  # CPT/HCPCS/NDC/ICD
    description: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)

    bill: Mapped["Bill"] = relationship(back_populates="line_items")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    # One of: duplicate, arithmetic, quantity, total_mismatch
    kind: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16), default="review")
    # Always framed as a potential discrepancy to review.
    message: Mapped[str] = mapped_column(Text)
    line_item_ids: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    status: Mapped[str] = mapped_column(String(16), default=FlagStatus.open.value)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    bill: Mapped["Bill"] = relationship(back_populates="flags")


class AnswerKey(Base):
    """Ground-truth record of an injected error. Used ONLY for accuracy scoring."""

    __tablename__ = "answer_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    kind: Mapped[str] = mapped_column(String(32))  # duplicate/arithmetic/quantity/total_mismatch
    line_positions: Mapped[str] = mapped_column(Text, default="")  # comma-separated positions
    detail: Mapped[str] = mapped_column(Text, default="")

    bill: Mapped["Bill"] = relationship(back_populates="answer_keys")



class SurveyStat(Base):
    """Post-review survey — PERFORMANCE STATS ONLY.

    Deliberately stores NO medical content and NO personal identifiers: no
    codes, no bill text, no names. Only aggregate performance metrics so the
    team can measure impact. Not linked to any bill; user_id is nullable and
    kept only so a user can't spam multiple entries per review if desired.
    """

    __tablename__ = "survey_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    estimated_savings: Mapped[float] = mapped_column(Float, default=0.0)
    flags_shown: Mapped[int] = mapped_column(Integer, default=0)
    flags_marked_helpful: Mapped[int] = mapped_column(Integer, default=0)
    satisfaction: Mapped[int] = mapped_column(Integer, default=0)  # 1..5
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)
