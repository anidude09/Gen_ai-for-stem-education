"""
activity_log.py

Backend route for recording user activity events into a CSV log file.
Each event is associated with a session ID so that activity can be
traced back to a logged-in user.
"""

from datetime import datetime
from pathlib import Path
import csv
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class ActivityEvent(BaseModel):
    """
    Activity event sent from the frontend.

    Fields:
        - session_id: ID of the authenticated user session.
        - event_type: Short string describing the type of event
          (e.g., "login_success", "detect_full_image", "text_selected").
        - event_data: Optional structured payload with additional details.
        - user_name: Optional user name, if available.
        - user_email: Optional user email, if available.
        - timestamp_utc: Optional client-side timestamp. If omitted, the
          server will use its current UTC time.
    """

    session_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    timestamp_utc: Optional[datetime] = None


_LOG_FIELDNAMES = [
    "timestamp_utc",
    "session_id",
    "user_name",
    "user_email",
    "event_type",
    "event_data_json",
]


# ── Performance: resolve path and create file once at module import ─────────
# Resolving Path(__file__) and checking path.exists() on every request adds
# unnecessary syscall overhead.  We do it once here and cache the result.
_LOG_PATH: Path = Path(__file__).resolve().parent.parent / "activity_log.csv"


def _ensure_log_file(path: Path) -> None:
    """
    Ensure the CSV log file exists and has a header row.
    Called once at module import.
    """

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_LOG_FIELDNAMES)
            writer.writeheader()


# Initialise once at startup
_ensure_log_file(_LOG_PATH)


@router.post("/activity/log", tags=["Activity"])
async def log_activity(event: ActivityEvent) -> dict:
    """
    Append a single activity event to the CSV log.
    Intended to be called from the frontend for important user actions.
    """

    timestamp = event.timestamp_utc or datetime.utcnow()

    row = {
        "timestamp_utc": timestamp.isoformat(),
        "session_id": event.session_id,
        "user_name": event.user_name or "",
        "user_email": event.user_email or "",
        "event_type": event.event_type,
        "event_data_json": json.dumps(event.event_data or {}, ensure_ascii=False),
    }

    with _LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_FIELDNAMES)
        writer.writerow(row)

    return {"status": "ok"}


