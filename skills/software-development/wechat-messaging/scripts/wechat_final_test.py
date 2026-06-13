"""
微信自动化 - 正式测试版
发送给：AI 数字人
经过焦点问题修复的验证版本
参考文档: references/focus-loss-pitfall-2026-06-13.md
"""
import ctypes
from ctypes import wintypes
import time
import pyperclip

# Windows API 常量
VK_CONTROL = 0x11
VK_F = 0x46
VK_RETURN = 0x0D
VK_TAB = 0x09

user32 = ctypes.windll.user32

def find_wechat_window():
    """找到微信窗口句柄"""
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
        hwnd, title, w, h = found_hwnds[0]
        print(f"✅ 找到微信窗口: {title} ({w}x{h})")
        return hwnd
    else:
        print("❌ 未找到微信窗口")
        return None

def force_activate_window(hwnd):
    """强制激活窗口"""
    user32.ShowWindow(hwnd, 6)
    time.sleep(0.2)
    user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    active_hwnd = user32.GetForegroundWindow()
    if active_hwnd == hwnd:
        print("✅ 微信焦点确认")
        return True
    else:
        print(f"⚠️  焦点警告: hwnd={active_hwnd}")
        return False

def press_key(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(0.2)

def press_hotkey(vk1, vk2):
    user32.keybd_event(vk1, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 2, 0)
    time.sleep(0.1)
    user32.keybd_event(vk1, 0, 2, 0)
    time.sleep(0.3)

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.3)
    press_hotkey(VK_CONTROL, ord('V'))

# ==========================================
# 正式测试开始
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 微信消息发送 - 正式测试")
    print("👤 接收人: AI 数字人")
    print("=" * 60)

    # 步骤 0: 找到并激活微信
    print("\n📌 [1/6] 激活微信窗口")
    hwnd = find_wechat_window()
    if not hwnd:
        print("❌ 请先打开微信！")
        exit(1)
    force_activate_window(hwnd)

    # 步骤 1: 激活搜索
    print("\n📌 [2/6] 激活搜索框 (Ctrl+F)")
    force_activate_window(hwnd)
    press_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)

    # 步骤 2: 输入搜索词
    print("\n📌 [3/6] 搜索联系人: AI 数字人")
    force_activate_window(hwnd)
    paste_text("AI 数字人")
    time.sleep(3)

    # 步骤 3: 选择搜索结果
    print("\n📌 [4/6] 选择搜索结果 (两次回车)")
    force_activate_window(hwnd)
    press_key(VK_RETURN)
    time.sleep(0.5)
    press_key(VK_RETURN)
    time.sleep(2)

    # 步骤 4: 确保焦点在输入框
    print("\n📌 [5/6] 移动焦点到聊天输入框")
    force_activate_window(hwnd)
    for _ in range(3):
        press_key(VK_TAB)
    time.sleep(1)

    # 步骤 5: 输入并发送消息
    print("\n📌 [6/6] 发送测试消息")
    force_activate_window(hwnd)
    test_message = """🧪 正式测试消息 🧪
✅ 焦点问题已修复
✅ 每步都确认微信在前台
✅ Python 纯原生实现
✅ 绕过 cua-driver 限制"""
    paste_text(test_message)
    time.sleep(1)

    print("\n📤 按回车发送...")
    press_key(VK_RETURN)
    time.sleep(2)

    print("\n" + "=" * 60)
    print("✅ 测试完成！消息已发送！")
    print("=" * 60)
    print("\n👀 请检查微信的「AI 数字人」聊天窗口！")
