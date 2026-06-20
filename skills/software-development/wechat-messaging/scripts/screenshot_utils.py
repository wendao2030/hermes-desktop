#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Screenshot helpers for the WeChat skill.

Normal Windows screenshots do not include the mouse cursor.  When a model
needs to reason about where the pointer is, capture with draw_cursor=True so
the saved image contains an explicit red crosshair and coordinate label.
"""

from __future__ import annotations

import os
import time
import uuid

import win32con
import win32gui
import win32ui
from PIL import Image, ImageDraw

from auto_reply_config import TEMP_SCREENSHOT_DIR
from wechat_window import get_cursor_pos


def ensure_temp_dir() -> None:
    os.makedirs(TEMP_SCREENSHOT_DIR, exist_ok=True)


def _draw_grid(draw: ImageDraw.ImageDraw, width: int, height: int, step: int = 50) -> None:
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=(220, 220, 220), width=1)
        draw.text((x + 3, 3), str(x), fill=(120, 120, 120))
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=(220, 220, 220), width=1)
        draw.text((3, y + 3), str(y), fill=(120, 120, 120))


def _draw_cursor_marker(
    image: Image.Image,
    window_left: int,
    window_top: int,
    *,
    label: str = "cursor",
) -> None:
    cursor_x, cursor_y = get_cursor_pos()
    rel_x = cursor_x - window_left
    rel_y = cursor_y - window_top
    if rel_x < 0 or rel_y < 0 or rel_x >= image.width or rel_y >= image.height:
        return

    draw = ImageDraw.Draw(image)
    r = 10
    draw.ellipse((rel_x - r, rel_y - r, rel_x + r, rel_y + r), outline=(255, 0, 0), width=3)
    draw.line((rel_x - 16, rel_y, rel_x + 16, rel_y), fill=(255, 0, 0), width=3)
    draw.line((rel_x, rel_y - 16, rel_x, rel_y + 16), fill=(255, 0, 0), width=3)
    text = f"{label}: window({rel_x},{rel_y}) screen({cursor_x},{cursor_y})"
    box_w = min(image.width - 4, max(260, len(text) * 7))
    y = max(2, rel_y - 34)
    x = min(max(2, rel_x + 14), max(2, image.width - box_w - 4))
    draw.rectangle((x, y, x + box_w, y + 24), fill=(255, 255, 230), outline=(255, 0, 0), width=1)
    draw.text((x + 6, y + 5), text, fill=(180, 0, 0))


def capture_window(hwnd: int, prefix: str = "wechat", *, draw_cursor: bool = False, draw_grid: bool = False) -> str:
    """Capture a window to the skill temp folder.

    Args:
        hwnd: Window handle.
        prefix: File name prefix.
        draw_cursor: Overlay the current cursor as a red crosshair.
        draw_grid: Overlay 50px coordinate grid lines.

    Returns:
        Absolute path to the saved PNG file.
    """
    ensure_temp_dir()

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid window size: {width}x{height}")

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        image = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr,
            "raw",
            "BGRX",
            0,
            1,
        )
        if draw_grid:
            _draw_grid(ImageDraw.Draw(image), image.width, image.height)
        if draw_cursor:
            _draw_cursor_marker(image, left, top)

        filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(TEMP_SCREENSHOT_DIR, filename)
        image.save(filepath)
        return filepath
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def cleanup_temp_screenshots() -> int:
    if not os.path.exists(TEMP_SCREENSHOT_DIR):
        return 0

    count = 0
    for filename in os.listdir(TEMP_SCREENSHOT_DIR):
        if not filename.lower().endswith(".png"):
            continue
        filepath = os.path.join(TEMP_SCREENSHOT_DIR, filename)
        try:
            os.remove(filepath)
            count += 1
        except OSError:
            pass
    return count
