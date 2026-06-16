"""
微信自动化 - 步骤2：输入搜索词
前提：搜索框已经通过 Ctrl+F 弹出
"""
import ctypes
from ctypes import wintypes
import time
import pyperclip

VK_CONTROL = 0x11
VK_RETURN = 0x0D

user32 = ctypes.windll.user32

def find_wechat_window():
    found_hwnds = []
    def enum_callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value
        if title and ('微信' in title or 'WeChat' in title):
            if user32.IsWindowVisible(hwnd):
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                if width > 300 and height > 400:
                    found_hwnds.append((hwnd, title, width, height))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    if found_hwnds:
        found_hwnds.sort(key=lambda x: x[2] * x[3], reverse=True)
        return found_hwnds[0][0]
    return None

def simple_activate(hwnd):
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

def paste_text(text):
    """用剪贴板粘贴中文"""
    pyperclip.copy(text)
    time.sleep(0.3)
    # 发送 Ctrl+V
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(ord('V'), 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(ord('V'), 0, 2, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    time.sleep(0.5)

# ==========================================
# 输入搜索词
# ==========================================
print("=" * 50)
print("🧪 步骤2：输入搜索词")
print("目标：在搜索框中输入「AI 数字人」")
print("=" * 50)

hwnd = find_wechat_window()
if hwnd:
    simple_activate(hwnd)
    print(f"\n✅ 微信已设为前台")
else:
    print("❌ 找不到微信")
    exit(1)

print("\n📝 正在输入：AI 数字人")
print("   请观察：搜索框中是否出现文字？")

paste_text("AI 数字人")
time.sleep(2)

print("\n" + "=" * 50)
print("✅ 搜索词已粘贴！")
print("=" * 50)
print("\n👀 请告诉我：搜索框中有没有出现「AI 数字人」？")
