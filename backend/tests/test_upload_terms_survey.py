"""Upload flow, terms acceptance, and survey/wipe (FastAPI TestClient; CI only)."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Bill, SurveyStat  # noqa: E402


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()


def _token(client, email="u@example.com"):
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "password123", "accept_terms": True})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def test_registration_requires_terms(ctx):
    client, _ = ctx
    r = client.post("/api/auth/register",
                    json={"email": "no@example.com", "password": "password123", "accept_terms": False})
    assert r.status_code == 400
    assert "Terms" in r.json()["detail"]


def test_review_creates_real_bill_then_finalize_wipes(ctx):
    client, Session = ctx
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Submit reviewed lines (as if parsed from a PDF).
    payload = {
        "provider_name": "Example Medical Center",
        "service_date": "2026-05-14",
        "stated_total": 105.0,
        "line_items": [
            {"code": "85025", "code_system": "CPT", "description": "CBC",
             "quantity": 1, "unit_price": 60.0, "line_total": 60.0},
            {"code": "85025", "code_system": "CPT", "description": "CBC",
             "quantity": 1, "unit_price": 60.0, "line_total": 60.0},  # duplicate
        ],
    }
    r = client.post("/api/upload/review", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    bill_id = r.json()["bill_id"]
    assert r.json()["flag_count"] >= 1  # duplicate should be flagged

    # Bill exists and is a real (non-synthetic) upload.
    db = Session()
    assert db.get(Bill, bill_id) is not None
    assert db.get(Bill, bill_id).is_synthetic is False
    db.close()

    # Finalize with survey -> wipes the bill, keeps only stats.
    survey = {"estimated_savings": 60.0, "flags_shown": 1,
              "flags_marked_helpful": 1, "satisfaction": 5}
    r2 = client.post(f"/api/upload/{bill_id}/finalize", json=survey, headers=headers)
    assert r2.status_code == 200 and r2.json()["wiped"] is True

    db = Session()
    assert db.get(Bill, bill_id) is None            # medical data gone
    stats = db.query(SurveyStat).all()
    assert len(stats) == 1                            # stats kept
    assert stats[0].estimated_savings == 60.0
    db.close()


def test_upload_endpoints_require_login(ctx):
    client, _ = ctx
    assert client.post("/api/upload/review", json={"line_items": []}).status_code == 401
    assert client.post("/api/upload/1/finalize", json={}).status_code == 401
