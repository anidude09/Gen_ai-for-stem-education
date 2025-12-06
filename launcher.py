"""
launcher.py

Standalone launcher for the Gen_ai-for-stem-education project.

Goals:
- Provide a minimal Windows-friendly entry point that can later be packaged
  into a single EXE (e.g., with PyInstaller).
- Start the FastAPI backend (uvicorn) in the background.
- Perform basic health checks:
  - Required Python packages import successfully.
  - Basic internet connectivity is available.
- Show a small popup window with a status message and a "green dot" if
  everything looks good (otherwise, show a yellow/red dot and a short note).

Run directly from the project root:
    python launcher.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from typing import List, Tuple

import tkinter as tk
from tkinter import ttk


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8001
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# Packages we consider essential for the app to run.
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "numpy",
    "cv2",        # opencv-python
    "easyocr",
    "groq",
    "PIL",        # pillow
    "requests",
]


@dataclass
class CheckResult:
    ok: bool
    details: List[str]


def _check_imports() -> CheckResult:
    """Try importing the main required packages."""
    missing: List[str] = []
    errors: List[str] = []

    for name in REQUIRED_PACKAGES:
        try:
            __import__(name)
        except Exception as exc:  # pragma: no cover - best effort
            missing.append(name)
            errors.append(f"{name}: {exc}")

    if not missing:
        return CheckResult(ok=True, details=["All required Python packages imported successfully."])

    lines = ["Missing or failed imports:"] + errors
    return CheckResult(ok=False, details=lines)


def _check_internet(timeout: float = 3.0) -> CheckResult:
    """Check that we can reach the internet (simple HTTP GET)."""
    try:
        import requests  # type: ignore

        resp = requests.get("https://www.google.com", timeout=timeout)
        if resp.ok:
            return CheckResult(ok=True, details=["Internet connectivity OK."])
        return CheckResult(ok=False, details=[f"Internet check returned HTTP {resp.status_code}."])
    except Exception as exc:  # pragma: no cover - best effort
        return CheckResult(ok=False, details=[f"Internet check failed: {exc}"])


def _start_backend_in_thread():
    """
    Start the FastAPI backend (uvicorn) in a daemon thread.

    We run uvicorn programmatically and adjust sys.path so that importing
    backend.app works regardless of the current working directory. This
    helps when packaging into a single EXE.
    """

    def _run():
        try:
            import uvicorn  # type: ignore

            project_root = os.path.abspath(os.path.dirname(__file__))
            backend_dir = os.path.join(project_root, "backend")

            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            # Import the FastAPI app
            import app as backend_app  # type: ignore

            uvicorn.run(
                backend_app.app,
                host=BACKEND_HOST,
                port=BACKEND_PORT,
                log_level="info",
            )
        except Exception as exc:  # pragma: no cover - best effort
            # In a GUI context we can't easily surface logs; print to stderr.
            print(f"[launcher] Backend failed to start: {exc}", file=sys.stderr)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _open_frontend_in_browser(delay: float = 2.0):
    """
    Open the frontend in the default browser after a short delay.
    This assumes the React app is ultimately served via the backend.
    """

    def _run():
        time.sleep(delay)
        try:
            webbrowser.open(BACKEND_URL)
        except Exception:
            # Non-critical; ignore.
            pass

    threading.Thread(target=_run, daemon=True).start()


class StatusWindow(tk.Tk):
    """
    Simple Tkinter window that shows:
    - A colored dot (green/yellow/red).
    - A status message describing the current checks.
    """

    def __init__(self):
        super().__init__()

        self.title("Gen AI for STEM - Launcher")
        self.resizable(False, False)

        # Small, centered window.
        self.geometry("420x180")

        self.status_var = tk.StringVar(value="Running checks...")

        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Row with colored dot + main label
        row = ttk.Frame(container)
        row.pack(anchor="w", pady=(0, 8))

        self.dot_canvas = tk.Canvas(row, width=24, height=24, highlightthickness=0)
        self.dot_canvas.pack(side="left", padx=(0, 8))
        self._dot_id = self.dot_canvas.create_oval(4, 4, 20, 20, fill="yellow", outline="")

        label = ttk.Label(row, textvariable=self.status_var, font=("Segoe UI", 10, "bold"))
        label.pack(side="left")

        # Details box
        self.details_text = tk.Text(
            container,
            width=52,
            height=5,
            wrap="word",
        )
        self.details_text.pack(fill="both", expand=True)
        self.details_text.configure(state="disabled")

        # Button row
        btn_row = ttk.Frame(container)
        btn_row.pack(fill="x", pady=(8, 0))

        self.refresh_button = ttk.Button(btn_row, text="Re-run checks", command=self.run_checks)
        self.refresh_button.pack(side="left")

        close_button = ttk.Button(btn_row, text="Close", command=self.destroy)
        close_button.pack(side="right")

        # Run checks after the window is displayed
        self.after(200, self.run_checks)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _set_dot_color(self, color: str):
        self.dot_canvas.itemconfig(self._dot_id, fill=color)

    def _set_details(self, lines: List[str]):
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, "\n".join(lines))
        self.details_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Check orchestration
    # ------------------------------------------------------------------
    def run_checks(self):
        """Run import + internet checks in a worker thread and update the UI."""
        self.refresh_button.configure(state="disabled")
        self._set_dot_color("yellow")
        self.status_var.set("Running checks...")
        self._set_details(["Running dependency and internet checks..."])

        def _worker():
            imports = _check_imports()
            internet = _check_internet()

            ok = imports.ok and internet.ok
            if ok:
                status = "All systems OK."
                color = "green"
            else:
                status = "Issues detected. See details below."
                color = "red"

            details: List[str] = []
            details.extend(imports.details)
            details.append("")
            details.extend(internet.details)

            # Back to main thread to update UI
            def _update():
                self._set_dot_color(color)
                self.status_var.set(status)
                self._set_details(details)
                self.refresh_button.configure(state="normal")

            self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()


def main():
    # Start backend + open browser in the background
    _start_backend_in_thread()
    _open_frontend_in_browser(delay=3.0)

    # Show status window
    app = StatusWindow()
    app.mainloop()


if __name__ == "__main__":
    main()


