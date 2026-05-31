#!/usr/bin/env python3
"""Run the Hermes Desktop web server without opening the native window."""

from pathlib import Path
from datetime import datetime
import traceback

import uvicorn


LOG_PATH = Path(__file__).with_name("run_browser_server.log")


def log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
        f.flush()


if __name__ == "__main__":
    try:
        log("importing server.app")
        from server import app, register_browser_bubble_fallbacks

        register_browser_bubble_fallbacks()

        log("starting uvicorn server")
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8765,
            log_level="warning",
            access_log=False,
            log_config=None,
        )
        server = uvicorn.Server(config)
        server.run()
        log("uvicorn stopped")
    except Exception:
        log("uvicorn failed")
        log(traceback.format_exc())
        raise
