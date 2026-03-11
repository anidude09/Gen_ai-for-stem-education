"""auth.py - Login/logout routes with SQLite session storage."""

from fastapi import APIRouter, Form
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import threading
import uuid


router = APIRouter()


# Thread-local SQLite connection for performance
_local = threading.local()


def _get_db_conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect("sessions.db", check_same_thread=False)
        # Ensure the schema exists on first use in this thread
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                start_time TEXT,
                end_time TEXT
            )
        """)
        _local.conn.commit()
    return _local.conn


def init_db():
    _get_db_conn()


init_db()


class LogoutRequest(BaseModel):
    session_id: str


@router.post("/login")
async def login(name: str = Form(...), email: str = Form(...)):
    session_id = str(uuid.uuid4())
    start_time = datetime.utcnow().isoformat()

    conn = _get_db_conn()
    conn.execute(
        "INSERT INTO sessions (id, name, email, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
        (session_id, name, email, start_time, None),
    )
    conn.commit()

    return {"session_id": session_id, "start_time": start_time}


@router.post("/logout")
async def logout(request: LogoutRequest):
    end_time = datetime.utcnow().isoformat()

    conn = _get_db_conn()
    conn.execute(
        "UPDATE sessions SET end_time = ? WHERE id = ?",
        (end_time, request.session_id),
    )
    conn.commit()

    return {"message": "Session ended", "end_time": end_time}
