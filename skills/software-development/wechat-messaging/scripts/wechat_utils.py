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
VK_A = 0x41
VK_C = 0x43
VK_BACK = 0x08


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


def send_ctrl_a() -> None:
    _combo(VK_CONTROL, VK_A)


def send_ctrl_c() -> None:
    _combo(VK_CONTROL, VK_C)


def send_enter() -> None:
    _press(VK_RETURN)


def send_tab(count: int = 1) -> None:
    for _ in range(max(1, count)):
        _press(VK_TAB)
        time.sleep(0.08)

def copy_to_clipboard(text: str) -> None:
    """Copy Unicode text to the Windows clipboard.

    Use CF_UNICODETEXT directly. This is more reliable for Chinese contact names
    than simulated typing or clipboard helpers that may fall back to ANSI paths.
    """
    text = str(text or "")
    try:
        import win32clipboard
        import win32con

        for attempt in range(5):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                finally:
                    win32clipboard.CloseClipboard()
                time.sleep(0.2)
                return
            except Exception:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
                if attempt == 4:
                    raise
                time.sleep(0.15)
    except Exception:
        import pyperclip

        pyperclip.copy(text)
        time.sleep(0.2)


def read_clipboard_text() -> str:
    """Read Unicode text from the Windows clipboard for diagnostics."""
    try:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return str(win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT) or "")
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    try:
        import pyperclip

        return str(pyperclip.paste() or "")
    except Exception:
        return ""


def _escaped(text: str) -> str:
    return str(text or "").encode("unicode_escape").decode("ascii")


def clear_search_box() -> None:
    """Clear WeChat search box using the older proven Backspace rhythm."""
    send_ctrl_a()
    time.sleep(0.15)
    for _ in range(20):
        _press(VK_BACK, delay=0.02)
    time.sleep(0.2)


def paste_and_verify_search_text(contact_name: str, attempts: int = 2) -> bool:
    """Paste the contact into WeChat search using the proven clipboard rhythm.

    Older successful runs showed that Chinese contact search is fragile unless
    Ctrl+F, clearing, clipboard paste, and Enter happen in one uninterrupted
    foreground script with enough delay. Do not use typed Chinese or arrow-key
    guessing.
    """
    contact_name = str(contact_name or "")
    for attempt in range(1, max(1, attempts) + 1):
        print("SEARCH_ATTEMPT=" + str(attempt))
        send_ctrl_f()
        time.sleep(1.0)
        clear_search_box()
        copy_to_clipboard(contact_name)
        clipboard_contact = read_clipboard_text()
        print("CONTACT_UNICODE_ESCAPE=" + _escaped(contact_name))
        print("CLIPBOARD_CONTACT_MATCH=" + str(clipboard_contact == contact_name))
        if clipboard_contact != contact_name:
            print("CLIPBOARD_UNICODE_ESCAPE=" + _escaped(clipboard_contact))
            time.sleep(0.3)
            continue
        send_ctrl_v()
        time.sleep(1.5)
        send_ctrl_a()
        time.sleep(0.15)
        send_ctrl_c()
        time.sleep(0.25)
        search_text = read_clipboard_text()
        print("SEARCH_TEXT_UNICODE_ESCAPE=" + _escaped(search_text))
        print("SEARCH_TEXT_MATCH=" + str(search_text == contact_name))
        if search_text != contact_name:
            time.sleep(0.4)
            continue
        print("SEARCH_PASTE_DONE=True")
        return True
    return False


def activate_wechat() -> dict:
    window = find_wechat_window(wake=True, retries=2)
    if not window:
        raise RuntimeError("Real WeChat window was not found")
    hwnd = window["hwnd"]
    restore_and_focus(hwnd)
    time.sleep(0.3)
    return get_window_info(hwnd)


def send_wechat_message(contact_name: str, message: str, *, search_only: bool = False) -> bool:
    window = activate_wechat()
    print("ACTIVE:", describe_window(window))
    hwnd = window["hwnd"]

    if not paste_and_verify_search_text(contact_name):
        print("SEARCH_OK=False")
        return False
    print("SEARCH_OK=True")
    if search_only:
        print("SEARCH_ONLY=True")
        return True
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
