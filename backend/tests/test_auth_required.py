"""Verify that using the tools requires an account (login-gated endpoints).

Everyone — free or paid — must be authenticated to generate/submit bills,
look up codes, or render letter templates. These tests use FastAPI's TestClient
against an in-memory SQLite DB. They run in CI where dependencies are installed.
"""
from __future__ import annotations

import pytest

# Skip cleanly if the web stack isn't installed (e.g. the offline sandbox).
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register(client, email="user@example.com", password="password123"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# ---- guests are blocked ----
def test_guest_cannot_generate_bill(client):
    assert client.post("/api/bills/generate", json={"num_line_items": 5}).status_code == 401


def test_guest_cannot_lookup_code(client):
    r = client.post("/api/translate/code", json={"code": "85025", "code_system": "CPT"})
    assert r.status_code == 401


def test_guest_cannot_render_template(client):
    r = client.post("/api/templates/render",
                    json={"template": "request_itemized_bill", "context": {}})
    assert r.status_code == 401


# ---- public endpoints stay open ----
def test_public_endpoints_open(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/translate/languages").status_code == 200
    assert client.get("/api/disclaimer").status_code == 200


# ---- authenticated users can use the tools ----
def test_authenticated_user_can_generate_and_owns_bill(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/bills/generate", json={"num_line_items": 6}, headers=headers)
    assert r.status_code == 200, r.text
    bill_id = r.json()["id"]

    # A different user must NOT be able to read the first user's bill.
    other = _register(client, email="other@example.com")
    r2 = client.get(f"/api/bills/{bill_id}", headers={"Authorization": f"Bearer {other}"})
    assert r2.status_code == 404

    # The owner can read it.
    r3 = client.get(f"/api/bills/{bill_id}", headers=headers)
    assert r3.status_code == 200


def test_free_user_blocked_from_paid_but_allowed_free(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    # Free feature (request itemized bill) works for any logged-in user.
    r = client.post("/api/templates/render",
                    json={"template": "request_itemized_bill", "context": {}},
                    headers=headers)
    assert r.status_code == 200
    # Paid feature (dispute letter) is blocked for a free user.
    r2 = client.post("/api/templates/render",
                     json={"template": "dispute_charge", "context": {}},
                     headers=headers)
    assert r2.status_code == 402
