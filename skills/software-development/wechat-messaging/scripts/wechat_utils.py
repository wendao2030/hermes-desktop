"""Reusable WeChat automation helpers.

This module is intentionally small and strict. It never treats Explorer
windows or folders named "wechat-messaging" as WeChat.
"""

from __future__ import annotations

import ctypes
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wechat_window import (
    click_wechat_input_box,
    describe_window,
    find_wechat_window,
    force_foreground,
    get_window_info,
    restore_and_focus,
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_F = 0x46
VK_V = 0x56
VK_TAB = 0x09


def _press(vk: int, delay: float = 0.04) -> None:
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(delay)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(delay)


def _combo(*keys: int) -> None:
    for vk in keys:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.04)
    for vk in reversed(keys):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.04)


def send_ctrl_f() -> None:
    _combo(VK_CONTROL, VK_F)


def send_ctrl_v() -> None:
    _combo(VK_CONTROL, VK_V)


def send_enter() -> None:
    _press(VK_RETURN)


def send_tab(count: int = 1) -> None:
    for _ in range(max(1, count)):
        _press(VK_TAB)
        time.sleep(0.08)

def copy_to_clipboard(text):
    """Copy text to clipboard using pyperclip."""
    import pyperclip
    pyperclip.copy(text)
    time.sleep(0.2)


def activate_wechat() -> dict:
    window = find_wechat_window(wake=True, retries=2)
    if not window:
        raise RuntimeError("Real WeChat window was not found")
    hwnd = window["hwnd"]
    restore_and_focus(hwnd)
    time.sleep(0.3)
    return get_window_info(hwnd)


def send_wechat_message(contact_name: str, message: str) -> bool:
    window = activate_wechat()
    print("ACTIVE:", describe_window(window))
    hwnd = window["hwnd"]

    send_ctrl_f()
    time.sleep(0.5)
    copy_to_clipboard(contact_name)
    send_ctrl_v()
    time.sleep(0.8)
    send_enter()
    time.sleep(0.5)
    send_enter()
    time.sleep(1.2)

    force_foreground(hwnd)
    click_wechat_input_box(hwnd)
    time.sleep(0.4)
    copy_to_clipboard(message)
    send_ctrl_v()
    time.sleep(0.3)
    force_foreground(hwnd)
    send_enter()
    return True


if __name__ == "__main__":
    info = activate_wechat()
    print("ACTIVE:", describe_window(info))
