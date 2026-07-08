#!/usr/bin/env python3
"""Robust Hermes Desktop launcher for Windows clients."""

from __future__ import annotations

import os
import shutil
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
SERVER_STDOUT_LOG = LOG_DIR / "server-launch.stdout.log"
SERVER_STDERR_LOG = LOG_DIR / "server-launch.stderr.log"
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
        HERMES_HOME / "runtime" / "python311" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


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


def _log_recent_file(path: Path, *, lines: int = 40) -> None:
    try:
        if not path.exists():
            log(f"{path.name} does not exist")
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        tail = text.splitlines()[-lines:]
        if tail:
            log(f"Recent {path.name}:")
            for line in tail:
                log(f"  {line}")
    except Exception as exc:
        log(f"Failed to read {path.name}: {exc}")


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
    os.environ["HERMES_DISABLE_LAZY_INSTALLS"] = "1"
    runtime_python = HERMES_HOME / "runtime" / "python311" / "python.exe"
    os.environ["HERMES_RUNTIME_PYTHON"] = str(runtime_python)
    os.environ["HERMES_PYTHON"] = str(runtime_python)
    os.environ["HERMES_DESKTOP_SERVE_ONLY"] = "1"
    # Auto-detect Chromium browser (Edge > Chrome > Chromium) for Playwright
    _browser = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")
    if not _browser:
        for _d in filter(bool, [os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")]):
            _c = os.path.join(_d, "Microsoft", "Edge", "Application", "msedge.exe")
            if os.path.isfile(_c): _browser = _c; break
    if _browser:
        os.environ.setdefault("PUPPETEER_EXECUTABLE_PATH", _browser)

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
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            stdout_file = SERVER_STDOUT_LOG.open("a", encoding="utf-8", errors="replace")
            stderr_file = SERVER_STDERR_LOG.open("a", encoding="utf-8", errors="replace")
            stdout_file.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] server start\n")
            stderr_file.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] server start\n")
            stdout_file.flush()
            stderr_file.flush()
            subprocess.Popen(
                [str(pythonw), str(server), "--serve-only"],
                cwd=str(cwd),
                stdout=stdout_file,
                stderr=stderr_file,
                creationflags=0x00000008 if sys.platform == "win32" else 0,
            )
        except Exception as exc:
            log(f"Failed to start server: {exc}")
            return 1

    if not _wait_ready(seconds=45.0):
        log("Server did not become ready in time")
        _log_recent_file(SERVER_STDOUT_LOG)
        _log_recent_file(SERVER_STDERR_LOG)
        return 2

    if not _open_app_window():
        log("Edge/Chrome app window not available; falling back to default browser")
        _open_default_browser()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
