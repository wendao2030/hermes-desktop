"""
枚举所有窗口，看看微信在哪
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

print("=" * 70)
print("正在枚举所有可见窗口...")
print("=" * 70)

count = 0
def enum_callback(hwnd, lParam):
    global count
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd) + 1
        if length > 1:
            buffer = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buffer, length)
            title = buffer.value
            if title.strip():
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                print(f"[{count:3d}] hwnd={hwnd:<8d} size={width:4d}x{height:<4d} 标题: {title[:50]}")
                count += 1
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

print("\n" + "=" * 70)
print(f"共找到 {count} 个可见窗口")
print("=" * 70)
print("\n👀 请找找看，微信窗口的标题是什么？")
