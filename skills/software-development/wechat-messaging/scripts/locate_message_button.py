#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locate WeChat's left-side message button from the current window image.

This avoids asking the model to guess coordinates.  It first looks for the
red unread badge in the left navigation rail, then falls back to the green
message icon, and only then uses a conservative current-layout fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from screenshot_utils import capture_window  # noqa: E402
from wechat_window import (  # noqa: E402
    click_window_point,
    find_wechat_window,
    get_window_info,
    move_cursor_to_client_point,
    restore_and_focus,
)


def _cluster_center(points: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not points:
        return None
    return (
        int(sum(p[0] for p in points) / len(points)),
        int(sum(p[1] for p in points) / len(points)),
    )


def _find_red_badge(image: Image.Image) -> tuple[int, int] | None:
    width, height = image.size
    points: list[tuple[int, int]] = []
    max_x = min(110, width)
    max_y = min(280, height)
    for y in range(80, max_y):
        for x in range(0, max_x):
            r, g, b = image.getpixel((x, y))[:3]
            if r >= 210 and g <= 95 and b <= 95:
                points.append((x, y))
    center = _cluster_center(points)
    if not center or len(points) < 20:
        return None
    # The red badge sits on the upper-right of the message icon.  Click the
    # icon center rather than the badge itself.
    return max(20, center[0] - 18), center[1] + 8


def _find_green_message_icon(image: Image.Image) -> tuple[int, int] | None:
    width, height = image.size
    points: list[tuple[int, int]] = []
    max_x = min(100, width)
    max_y = min(260, height)
    for y in range(90, max_y):
        for x in range(0, max_x):
            r, g, b = image.getpixel((x, y))[:3]
            if r <= 100 and g >= 150 and b <= 140:
                points.append((x, y))
    center = _cluster_center(points)
    if not center or len(points) < 40:
        return None
    return center


def locate_message_button(hwnd: int) -> dict:
    restore_and_focus(hwnd)
    info = get_window_info(hwnd)
    screenshot = capture_window(hwnd, prefix="locate_message_button", draw_cursor=False, draw_grid=False)
    image = Image.open(screenshot).convert("RGB")

    method = "fallback-current-layout"
    point = _find_red_badge(image)
    if point:
        method = "red-unread-badge"
    else:
        point = _find_green_message_icon(image)
        if point:
            method = "green-message-icon"
    if not point:
        # Current WeChat 4.x left navigation layout.  This is window-image
        # relative, then converted to client-relative below.
        point = (55, 170)

    window_x, window_y = point
    client_x = window_x - int(info.get("client_left", info["left"]) - info["left"])
    client_y = window_y - int(info.get("client_top", info["top"]) - info["top"])
    screen_x = info["left"] + window_x
    screen_y = info["top"] + window_y
    return {
        "ok": True,
        "method": method,
        "window_point": {"x": window_x, "y": window_y},
        "client_point": {"x": client_x, "y": client_y},
        "screen_point": {"x": screen_x, "y": screen_y},
        "window": info,
        "screenshot": screenshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate WeChat message button.")
    parser.add_argument("--move", action="store_true", help="Move cursor to the located point.")
    parser.add_argument("--click", action="store_true", help="Click the located point.")
    args = parser.parse_args()

    window = find_wechat_window(wake=True, retries=2)
    if not window:
        print(json.dumps({"ok": False, "error": "WeChat window not found"}, ensure_ascii=False))
        return 2

    result = locate_message_button(window["hwnd"])
    client = result["client_point"]
    if args.click:
        click_window_point(window["hwnd"], client["x"], client["y"])
        result["clicked"] = True
    elif args.move:
        sx, sy = move_cursor_to_client_point(window["hwnd"], client["x"], client["y"])
        result["moved_to"] = {"x": sx, "y": sy}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
