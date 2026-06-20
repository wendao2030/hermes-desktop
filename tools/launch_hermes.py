#!/usr/bin/env python3
"""Robust Hermes Desktop launcher for Windows clients."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path


def _home() -> Path:
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home)
    return Path(__file__).resolve().parents[1]


HERMES_HOME = _home()
LOG_DIR = HERMES_HOME / "logs"
LOG_FILE = LOG_DIR / "launcher.log"
LOCK_FILE = LOG_DIR / "launcher.lock"
URL = "http://127.0.0.1:8765"


def log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def _pythonw() -> Path:
    candidates = [
        HERMES_HOME / "runtime" / "python311" / "pythonw.exe",
        HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "pythonw.exe",
        HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _server_ready(timeout: float = 0.7) -> bool:
    try:
        urllib.request.urlopen(f"{URL}/api/config", timeout=timeout).read()
        return True
    except Exception:
        return False


def _wait_ready(seconds: float = 12.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if _server_ready(timeout=1.0):
            return True
        time.sleep(0.35)
    return False


def _acquire_launcher_lock():
    try:
        import msvcrt

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handle = LOCK_FILE.open("a+b")
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return handle
        except OSError:
            handle.close()
            return None
    except Exception as exc:
        log(f"Launcher lock unavailable: {exc}")
        return object()


def _browser_candidates() -> list[Path]:
    result: list[Path] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if not base:
            continue
        root = Path(base)
        result.extend(
            [
                root / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                root / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
        )
    return result


def _open_app_window() -> bool:
    for browser in _browser_candidates():
        if not browser.exists():
            continue
        try:
            subprocess.Popen(
                [str(browser), f"--app={URL}", "--new-window"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x00000008 if sys.platform == "win32" else 0,
            )
            log(f"Opened app window with {browser}")
            return True
        except Exception as exc:
            log(f"Failed to open app window with {browser}: {exc}")
    return False


def _open_default_browser() -> None:
    try:
        import webbrowser

        webbrowser.open(URL)
        log("Opened default browser fallback")
    except Exception as exc:
        log(f"Failed to open default browser fallback: {exc}")


def main() -> int:
    os.environ["HERMES_HOME"] = str(HERMES_HOME)
    os.environ["HERMES_DISABLE_OPTIONAL_DEP_INSTALL"] = "1"
    os.environ["HERMES_DESKTOP_SERVE_ONLY"] = "1"

    log(f"Launcher started, home={HERMES_HOME}")
    launcher_lock = _acquire_launcher_lock()
    if launcher_lock is None:
        log("Another launcher is starting Hermes; waiting for ready server")
        if not _wait_ready(seconds=15.0):
            log("Existing launcher did not make server ready in time")
            return 2
        if not _open_app_window():
            _open_default_browser()
        return 0

    if not _server_ready():
        server = HERMES_HOME / "desktop-client" / "server.py"
        cwd = HERMES_HOME / "desktop-client"
        pythonw = _pythonw()
        log(f"Starting server: {pythonw} {server} --serve-only")
        try:
            subprocess.Popen(
                [str(pythonw), str(server), "--serve-only"],
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x00000008 if sys.platform == "win32" else 0,
            )
        except Exception as exc:
            log(f"Failed to start server: {exc}")
            return 1

    if not _wait_ready():
        log("Server did not become ready in time")
        return 2

    if not _open_app_window():
        log("Edge/Chrome app window not available; falling back to default browser")
        _open_default_browser()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
