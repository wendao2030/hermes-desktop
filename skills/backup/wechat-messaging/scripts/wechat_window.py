"""Strict WeChat window helpers for Hermes Desktop on Windows.

These helpers intentionally avoid loose title matching. Explorer windows can
contain folder names such as "wechat-messaging", so a real WeChat match must
come from the owning process name.
"""

from __future__ import annotations

import ctypes
import time
from pathlib import Path
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9
SW_SHOW = 5
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_W = 0x57
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

WECHAT_PROCESS_NAMES = {"weixin.exe", "wechat.exe", "wechatappex.exe"}

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
psapi.GetModuleBaseNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.HMODULE,
    wintypes.LPWSTR,
    wintypes.DWORD,
]
psapi.GetModuleBaseNameW.restype = wintypes.DWORD


def _window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def _process_name(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(260)
        if psapi.GetModuleBaseNameW(handle, None, buffer, len(buffer)):
            return buffer.value
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _rect(hwnd: int) -> tuple[int, int, int, int, int, int]:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    return rect.left, rect.top, rect.right, rect.bottom, width, height


def list_wechat_windows() -> list[dict]:
    rows: list[dict] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = _process_name(pid.value)
        if process.lower() not in WECHAT_PROCESS_NAMES:
            return True

        left, top, right, bottom, width, height = _rect(hwnd)
        rows.append(
            {
                "hwnd": int(hwnd),
                "pid": int(pid.value),
                "process": process,
                "class_name": _class_name(hwnd),
                "title": _window_text(hwnd),
                "visible": bool(user32.IsWindowVisible(hwnd)),
                "minimized": bool(user32.IsIconic(hwnd)),
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": width,
                "height": height,
            }
        )
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return rows


def _candidate_score(row: dict) -> tuple[int, int]:
    area = max(0, row["width"]) * max(0, row["height"])
    normal_position = row["left"] > -10000 and row["top"] > -10000
    usable_size = row["width"] >= 300 and row["height"] >= 300
    title = (row.get("title") or "").lower()
    class_name = row.get("class_name") or ""
    score = 0
    score += 100 if row["visible"] and usable_size else 0
    score += 50 if not row["minimized"] else 0
    score += 20 if normal_position else 0
    score += 10 if title in {"weixin", "wechat"} or "wechat" in title else 0
    score += 10 if class_name.startswith("Qt") or class_name == "WeChatMainWndForPC" else 0
    return score, area


def send_wechat_hotkey() -> None:
    for vk in (VK_CONTROL, VK_MENU, VK_W):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.04)
    for vk in (VK_W, VK_MENU, VK_CONTROL):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.04)


def find_wechat_window(wake: bool = True, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        candidates = list_wechat_windows()
        if candidates:
            candidates.sort(key=_candidate_score, reverse=True)
            best = candidates[0]
            if _candidate_score(best)[0] >= 100 or not wake or attempt == retries:
                return best
        if wake and attempt < retries:
            send_wechat_hotkey()
            time.sleep(1.0)
    return None


def restore_and_focus(hwnd: int) -> bool:
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.2)
    user32.ShowWindow(hwnd, SW_SHOW)
    time.sleep(0.2)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    time.sleep(0.1)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    force_foreground(hwnd)
    time.sleep(0.4)
    return bool(user32.IsWindow(hwnd)) and not bool(user32.IsIconic(hwnd))


def force_foreground(hwnd: int) -> bool:
    """Best-effort foreground activation for the WeChat top-level window."""
    user32.BringWindowToTop(hwnd)
    current_thread = kernel32.GetCurrentThreadId()
    window_thread = user32.GetWindowThreadProcessId(hwnd, None)
    if current_thread != window_thread:
        user32.AttachThreadInput(current_thread, window_thread, True)
    try:
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        if current_thread != window_thread:
            user32.AttachThreadInput(current_thread, window_thread, False)
    return user32.GetForegroundWindow() == hwnd


def click_window_point(hwnd: int, rel_x: int, rel_y: int) -> None:
    """Click an absolute screen point derived from a window-relative point."""
    left, top, _right, _bottom, width, height = _rect(hwnd)
    x = left + max(0, min(rel_x, width - 1))
    y = top + max(0, min(rel_y, height - 1))
    force_foreground(hwnd)
    time.sleep(0.15)
    user32.SetCursorPos(x, y)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.2)


def click_wechat_input_box(hwnd: int) -> None:
    """Click the message input area in the current WeChat chat window."""
    info = get_window_info(hwnd)
    # For WeChat 4.x, the message editor is in the lower-right chat panel.
    rel_x = int(info["width"] * 0.68)
    rel_y = max(120, info["height"] - 92)
    click_window_point(hwnd, rel_x, rel_y)


def get_window_info(hwnd: int) -> dict:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    left, top, right, bottom, width, height = _rect(hwnd)
    return {
        "hwnd": int(hwnd),
        "pid": int(pid.value),
        "process": _process_name(pid.value),
        "class_name": _class_name(hwnd),
        "title": _window_text(hwnd),
        "visible": bool(user32.IsWindowVisible(hwnd)),
        "minimized": bool(user32.IsIconic(hwnd)),
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": width,
        "height": height,
    }


def describe_window(row: dict | None) -> str:
    if not row:
        return "not found"
    return (
        f"hwnd={row['hwnd']} pid={row['pid']} process={row['process']} "
        f"class={row['class_name']} title={row['title']!r} "
        f"visible={row['visible']} minimized={row['minimized']} "
        f"size={row['width']}x{row['height']} pos=({row['left']},{row['top']})"
    )


if __name__ == "__main__":
    window = find_wechat_window(wake=True, retries=2)
    print(describe_window(window))
    if window:
        ok = restore_and_focus(window["hwnd"])
        print(f"restore_and_focus={ok}")
