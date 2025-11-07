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
import uuid
import os


# Create a FastAPI router instance for handling authentication routes
router = APIRouter()




DB_PATH = os.environ.get("DB_PATH", "sessions.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        start_time TEXT,
        end_time TEXT
        );
    """)

    return conn


@router.post("/login")
def login(name: str = Form(...), email: str = Form(...)):

    sid = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, name, email, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
            (sid, name, email, datetime.now().isoformat(), None)
        )

    return {"session_id": sid, "status": "ok"}


@router.post("/logout")
def logout(session_id: str = Form(...)):
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ? AND end_time is NULL",
            (datetime.now().isoformat(), session_id)

        )
    return {"status": "ok"}








# def init_db():
#     """
#     Initializes the SQLite database and creates the `sessions` table if it does not already exist.
#     The `sessions` table stores:
#         - id (str): Unique identifier for the session (UUID)
#         - name (str): Name of the user
#         - email (str): Email of the user
#         - start_time (str): ISO formatted string marking when the session started
#         - end_time (str): ISO formatted string marking when the session ended (nullable)
#     """
#     conn = sqlite3.connect("sessions.db")
#     cursor = conn.cursor()
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS sessions (
#             id TEXT PRIMARY KEY,
#             name TEXT,
#             email TEXT,
#             start_time TEXT,
#             end_time TEXT
#         )
#     """)
#     conn.commit()
#     conn.close()
#
#
# # Initialize the database on module load
# init_db()
#
#
# class LogoutRequest(BaseModel):
#     """
#     Request model for logging out a session.
#     Expects:
#         - session_id (str): The unique identifier of the session to be terminated.
#     """
#     session_id: str
#
#
# @router.post("/login")
# async def login(name: str = Form(...), email: str = Form(...)):
#     """
#     Handles user login.
#
#     - Accepts user `name` and `email` as form data.
#     - Generates a unique session ID using UUID.
#     - Captures the session's start time in UTC (ISO format).
#     - Stores the session details in the SQLite database (`sessions` table).
#     - Returns the generated session ID and the session start time.
#
#     This function essentially begins a new user session.
#     """
#     session_id = str(uuid.uuid4())
#     start_time = datetime.utcnow().isoformat()
#
#     conn = sqlite3.connect("sessions.db")
#     cursor = conn.cursor()
#     cursor.execute(
#         "INSERT INTO sessions (id, name, email, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
#         (session_id, name, email, start_time, None),
#     )
#     conn.commit()
#     conn.close()
#
#     return {"session_id": session_id, "start_time": start_time}
#
#
# @router.post("/logout")
# async def logout(request: LogoutRequest):
#     """
#     Handles user logout.
#
#     - Accepts a `LogoutRequest` object containing the session ID.
#     - Records the current UTC time as the session's end time (ISO format).
#     - Updates the corresponding session record in the database by setting its `end_time`.
#     - Returns a confirmation message along with the recorded end time.
#
#     This function effectively ends a user session.
#     """
#     end_time = datetime.utcnow().isoformat()
#
#     conn = sqlite3.connect("sessions.db")
#     cursor = conn.cursor()
#     cursor.execute(
#         "UPDATE sessions SET end_time = ? WHERE id = ?",
#         (end_time, request.session_id),
#     )
#     conn.commit()
#     conn.close()
#
#     return {"message": "Session ended", "end_time": end_time}
