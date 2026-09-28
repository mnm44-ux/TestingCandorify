"""Scheduled retention sweep.

Deletes any bill whose retention window has passed. Intended to run from cron
or a scheduled task, e.g. daily:

    0 3 * * *  cd /path/to/backend && python -m scripts.retention_sweep

It reuses the same deletion path as the API so behavior is identical.
"""
from __future__ import annotations

import datetime as dt

from app.db import SessionLocal, init_db
from app.models import Bill


def sweep() -> int:
    init_db()
    db = SessionLocal()
    try:
        now = dt.datetime.now(dt.timezone.utc)
        stale = (
            db.query(Bill)
            .filter(Bill.delete_after.isnot(None), Bill.delete_after < now)
            .all()
        )
        count = len(stale)
        for bill in stale:
            db.delete(bill)
        db.commit()
        return count
    finally:
        db.close()


if __name__ == "__main__":
    deleted = sweep()
    print(f"Retention sweep complete: deleted {deleted} expired bill(s).")
