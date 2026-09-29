"""Candorify FastAPI application entrypoint.

Serves the JSON API under /api/* and the static website from ../frontend.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .routers import (
    auth_router,
    bills_router,
    payments_router,
    privacy_router,
    templates_router,
    translate_router,
    upload_router,
)

settings = get_settings()

app = FastAPI(
    title="Candorify API",
    version="0.1.0",
    description="Read your medical bills before you pay. Prototype uses synthetic data only.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin] if settings.frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "translation_offline_only": settings.translation_offline_only,
        "payments_mock_mode": settings.payments_mock_mode,
    }


@app.get("/api/disclaimer")
def disclaimer() -> dict:
    return {
        "text": (
            "Candorify identifies possible billing discrepancies for your review; it "
            "does not verify charges, confirm errors, or guarantee savings. It is not a "
            "substitute for a billing auditor, advocate, or legal or financial advisor. "
            "Nothing is confirmed until the provider or insurance agrees. Acting on "
            "flagged items is your own responsibility. This prototype uses synthetic "
            "bills only and contains no real patient data."
        )
    }


app.include_router(auth_router.router)
app.include_router(bills_router.router)
app.include_router(translate_router.router)
app.include_router(templates_router.router)
app.include_router(payments_router.router)
app.include_router(privacy_router.router)
app.include_router(upload_router.router)

# Serve the static website (mounted last so /api/* wins).
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
_frontend_dir = os.path.abspath(_frontend_dir)
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
