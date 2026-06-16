"""
微信自动化 - 简化测试版 v3
目标：先验证 Ctrl+F 是否真的生效
改进：移除最小化/恢复，避免窗口闪烁
"""
import ctypes
from ctypes import wintypes
import time
import pyperclip

VK_CONTROL = 0x11
VK_F = 0x46
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
    """简单激活：不做最小化恢复，避免闪烁"""
    # 只设为前台，不做多余操作
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    # 验证
    active_hwnd = user32.GetForegroundWindow()
    if active_hwnd == hwnd:
        print("✅ 微信已设为前台")
        return True
    else:
        print(f"⚠️  设为前台失败")
        return False

def press_hotkey_simple(vk1, vk2):
    """简化的按键发送"""
    user32.keybd_event(vk1, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk2, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk2, 0, 2, 0)
    time.sleep(0.05)
    user32.keybd_event(vk1, 0, 2, 0)
    time.sleep(0.2)

# ==========================================
# 简化测试：只做 激活 + Ctrl+F
# ==========================================
print("=" * 50)
print("🧪 简化测试：激活 + Ctrl+F")
print("目标：验证搜索框是否真的弹出")
print("=" * 50)

print("\n1️⃣  找到微信窗口...")
hwnd = find_wechat_window()
if not hwnd:
    print("❌ 找不到微信，请手动打开")
    exit(1)
print(f"✅ 找到微信 hwnd={hwnd}")

print("\n2️⃣  设为前台...")
simple_activate(hwnd)
time.sleep(1)

print("\n3️⃣  发送 Ctrl+F...")
print("   请观察：微信顶部是否弹出搜索框？")
press_hotkey_simple(VK_CONTROL, VK_F)
time.sleep(2)

print("\n" + "=" * 50)
print("✅ Ctrl+F 已发送，请观察结果！")
print("=" * 50)
print("\n👀 请告诉我：微信顶部有没有出现搜索框？")
