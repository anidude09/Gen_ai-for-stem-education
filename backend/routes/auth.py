"""
auth.py

This module defines authentication routes for handling user login and logout sessions 
using FastAPI. It manages session creation and termination by storing session details 
(name, email, session ID, start time, and end time) in a local SQLite database (`sessions.db`). 
Each session is uniquely identified by a UUID. 
"""

from fastapi import APIRouter, Form
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import threading
import uuid

# Create a FastAPI router instance for handling authentication routes
router = APIRouter()


# ── Performance: thread-local SQLite connection ────────────────────────────────
# Opening and closing a new sqlite3 connection on every request adds measurable
# latency (OS file open syscall + page-cache warm-up).  A thread-local
# connection is opened once per worker thread and reused for the lifetime of
# that thread, while remaining thread-safe.
_local = threading.local()


def _get_db_conn() -> sqlite3.Connection:
    """Return the per-thread SQLite connection, creating it if needed."""
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
    """
    Initializes the SQLite database on the main thread at startup.
    """
    conn = _get_db_conn()
    _ = conn  # triggers schema creation via _get_db_conn


# Initialize the database on module load
init_db()


class LogoutRequest(BaseModel):
    """
    Request model for logging out a session.
    Expects:
        - session_id (str): The unique identifier of the session to be terminated.
    """
    session_id: str


@router.post("/login")
async def login(name: str = Form(...), email: str = Form(...)):
    """
    Handles user login.
    Creates a new session and stores it in the shared SQLite database.
    """
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
    """
    Handles user logout.
    Records the session end time in the database.
    """
    end_time = datetime.utcnow().isoformat()

    conn = _get_db_conn()
    conn.execute(
        "UPDATE sessions SET end_time = ? WHERE id = ?",
        (end_time, request.session_id),
    )
    conn.commit()

    return {"message": "Session ended", "end_time": end_time}
