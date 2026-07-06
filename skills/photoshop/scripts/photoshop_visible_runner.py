"""Visible Photoshop step runner for demonstration tasks.

Use this helper when the user asks to see Photoshop operate step by step.
It keeps Photoshop visible, brings it forward between steps, and pauses so
the user can observe changes on the canvas.
"""

from __future__ import annotations

import time
from typing import Iterable, Tuple

import pythoncom
import pywintypes
import win32com.client


Step = Tuple[str, str]


def connect_photoshop(retries: int = 30, delay: float = 1.0):
    """Connect to Photoshop and make sure the UI is visible."""
    pythoncom.CoInitialize()
    last_error = None
    for _ in range(retries):
        try:
            ps = win32com.client.Dispatch("Photoshop.Application")
            _com_retry(lambda: setattr(ps, "Visible", True), retries=5, delay=delay)
            _com_retry(lambda: setattr(ps, "DisplayDialogs", 3), retries=5, delay=delay)
            _com_retry(lambda: setattr(ps.Preferences, "RulerUnits", 1), retries=5, delay=delay)
            try:
                ps.BringToFront()
            except Exception:
                pass
            return ps
        except Exception as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to Photoshop: {last_error}")


def _com_retry(action, retries: int = 8, delay: float = 0.8):
    last_error = None
    for _ in range(retries):
        try:
            return action()
        except pywintypes.com_error as exc:
            last_error = exc
            time.sleep(delay)
    raise last_error


def close_open_documents_without_saving(ps):
    """Close stale Photoshop documents without prompting.

    Demo scripts often leave an unsaved document if a previous run failed.
    Closing them here prevents the "Save changes before closing?" modal from
    blocking the next automation run.
    """
    jsx = """
app.displayDialogs = DialogModes.NO;
while (app.documents.length > 0) {
    app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
}
"""
    return _com_retry(lambda: ps.DoJavaScript(jsx, []), retries=8, delay=1.0)


def run_visible_steps(ps, steps: Iterable[Step], delay: float = 1.2):
    """Run JSX snippets one by one with visible pauses.

    Each step is a pair: (step_name, jsx_code). The JSX should be small enough
    to produce one visible change.
    """
    results = []
    for name, jsx in steps:
        try:
            ps.Visible = True
            ps.DisplayDialogs = 3
            try:
                ps.BringToFront()
            except Exception:
                pass
            result = _com_retry(lambda: ps.DoJavaScript(jsx, []), retries=8, delay=1.0)
            results.append({"step": name, "ok": True, "result": str(result)})
            time.sleep(delay)
        except Exception as exc:
            results.append({"step": name, "ok": False, "error": repr(exc)})
            raise
    return results
