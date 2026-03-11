"""activity_log.py - Buffers and writes user activity events to CSV."""

from datetime import datetime
from pathlib import Path
import csv
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class ActivityEvent(BaseModel):
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


_LOG_PATH: Path = Path(__file__).resolve().parent.parent / "activity_log.csv"


def _ensure_log_file(path: Path) -> None:

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_LOG_FIELDNAMES)
            writer.writeheader()


_ensure_log_file(_LOG_PATH)


# Buffered CSV writer — flushes every 5s or every 10 events
import threading
import atexit

_LOG_BUFFER: list[dict] = []
_LOG_LOCK = threading.Lock()
_FLUSH_INTERVAL = 5.0      # seconds
_FLUSH_THRESHOLD = 10       # flush when N events are buffered


def _flush_log_buffer() -> None:
    with _LOG_LOCK:
        if not _LOG_BUFFER:
            return
        rows = list(_LOG_BUFFER)
        _LOG_BUFFER.clear()

    with _LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_FIELDNAMES)
        for row in rows:
            writer.writerow(row)


def _periodic_flush():
    _flush_log_buffer()
    _timer = threading.Timer(_FLUSH_INTERVAL, _periodic_flush)
    _timer.daemon = True
    _timer.start()



_periodic_flush()


atexit.register(_flush_log_buffer)


@router.post("/activity/log", tags=["Activity"])
async def log_activity(event: ActivityEvent) -> dict:

    timestamp = event.timestamp_utc or datetime.utcnow()

    row = {
        "timestamp_utc": timestamp.isoformat(),
        "session_id": event.session_id,
        "user_name": event.user_name or "",
        "user_email": event.user_email or "",
        "event_type": event.event_type,
        "event_data_json": json.dumps(event.event_data or {}, ensure_ascii=False),
    }

    with _LOG_LOCK:
        _LOG_BUFFER.append(row)
        should_flush = len(_LOG_BUFFER) >= _FLUSH_THRESHOLD

    if should_flush:
        _flush_log_buffer()

    return {"status": "ok"}

