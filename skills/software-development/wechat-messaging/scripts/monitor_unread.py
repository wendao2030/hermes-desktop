#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Official unread-message monitor evidence entrypoint for WeChat.

This script does not invent replies and does not OCR contact names.  It only
performs deterministic local actions and returns evidence for Hermes to inspect:
window status, message-button location, unread-badge state, double-click cycles,
and screenshot paths.  Contact recognition must be based on the screenshots
returned by this script, not on guessed coordinates or old chat history.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from locate_message_button import locate_message_button  # noqa: E402
from screenshot_utils import capture_window, cleanup_temp_screenshots  # noqa: E402
from wechat_window import (  # noqa: E402
    click_client_point,
    describe_window,
    find_wechat_window,
    force_foreground,
    get_window_info,
    restore_and_focus,
)


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _double_click_client(hwnd: int, client_x: int, client_y: int) -> None:
    click_client_point(hwnd, client_x, client_y)
    time.sleep(0.12)
    click_client_point(hwnd, client_x, client_y)


def _cycle_once(hwnd: int, client: dict, index: int) -> dict:
    client_x = int(client["x"])
    client_y = int(client["y"])
    force_foreground(hwnd)
    _double_click_client(hwnd, client_x, client_y)
    time.sleep(0.8)
    screenshot = capture_window(
        hwnd,
        prefix=f"monitor_unread_cycle_{index}",
        draw_cursor=True,
        draw_grid=True,
    )
    return {
        "cycle": index,
        "action": "double_click_message_button",
        "client_point": {"x": client_x, "y": client_y},
        "screenshot": screenshot,
        "instruction": (
            "Inspect the chat-person list immediately to the right of the "
            "message button. If the target contact appears there with an "
            "unread badge, click that list item before inspecting the right "
            "chat panel."
        ),
    }


def inspect_unread(max_cycles: int = 1, clean_first: bool = False) -> dict:
    if clean_first:
        cleanup_temp_screenshots()

    result: dict = {
        "ok": False,
        "action": "monitor_unread_inspect",
        "max_cycles": max_cycles,
        "cycles": [],
        "errors": [],
    }

    window = find_wechat_window(wake=True, retries=2)
    if not window:
        result["error"] = "WeChat window not found"
        result["advice"] = "Ask the user to open and log in to WeChat."
        return result

    hwnd = int(window["hwnd"])
    result["initial_window"] = window
    restored = restore_and_focus(hwnd)
    after = get_window_info(hwnd)
    result["restore_ok"] = bool(restored)
    result["window_after_restore"] = after
    result["window_summary"] = describe_window(after)
    if not restored:
        result["error"] = "WeChat window could not be foregrounded"
        return result

    location = locate_message_button(hwnd)
    result["message_button"] = location
    method = location.get("method")
    result["has_unread_badge"] = method == "red-unread-badge"

    if not result["has_unread_badge"]:
        result["ok"] = True
        result["status"] = "no_unread_badge_detected"
        result["instruction"] = (
            "The message button did not show a red unread badge in the locator "
            "screenshot. Do not claim a target contact has new messages."
        )
        return result

    client = location["client_point"]
    cycles = max(1, int(max_cycles))
    for index in range(1, cycles + 1):
        result["cycles"].append(_cycle_once(hwnd, client, index))

    # Re-locate after cycling so the caller can tell whether unread badges remain.
    final_location = locate_message_button(hwnd)
    result["final_message_button"] = final_location
    result["final_has_unread_badge"] = final_location.get("method") == "red-unread-badge"
    result["ok"] = True
    result["status"] = "cycled_unread_contacts"
    result["next_step"] = (
        "Use the cycle screenshots to identify contacts in the chat-person list. "
        "If the target contact was selected, inspect the chat panel, compare with "
        "chat_history.py, then send via message_sender.py. If unread remains, run "
        "this script again or increase --max-cycles."
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and cycle WeChat unread-message contacts.")
    parser.add_argument("--max-cycles", type=int, default=1, help="Number of message-button double-click cycles to perform.")
    parser.add_argument("--clean-first", action="store_true", help="Clean old temp screenshots before running.")
    args = parser.parse_args()

    result = inspect_unread(max_cycles=args.max_cycles, clean_first=args.clean_first)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
