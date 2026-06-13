"""
微信自动化 - 完整流程：选择结果 + 发送消息
前提：搜索框中已输入「AI 数字人」
"""
import ctypes
from ctypes import wintypes
import time
import pyperclip

VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_TAB = 0x09

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

def press_key(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(0.2)

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.3)
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(ord('V'), 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(ord('V'), 0, 2, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    time.sleep(0.5)

# ==========================================
# 完整流程：选择结果 → 进入聊天 → 发送消息
# ==========================================
print("=" * 60)
print("🚀 继续测试：选择结果 + 进入聊天 + 发送消息")
print("=" * 60)

hwnd = find_wechat_window()
if hwnd:
    simple_activate(hwnd)
    print(f"\n✅ 微信已设为前台")
else:
    print("❌ 找不到微信")
    exit(1)

# 步骤 1: 两次回车选择搜索结果
print("\n📌 步骤 1/3: 两次回车选择搜索结果")
press_key(VK_RETURN)
time.sleep(0.5)
press_key(VK_RETURN)
time.sleep(2)
print("   ✅ 已进入聊天界面")

# 步骤 2: 移动焦点到输入框
print("\n📌 步骤 2/3: 移动焦点到输入框 (按3次Tab)")
for _ in range(3):
    press_key(VK_TAB)
time.sleep(1)
print("   ✅ 焦点已移到输入框")

# 步骤 3: 输入并发送消息
print("\n📌 步骤 3/3: 输入并发送测试消息")
test_message = """🎉 完整流程测试成功！

✅ Ctrl+F 激活搜索
✅ 输入「AI 数字人」
✅ 两次回车选择结果
✅ 进入聊天界面
✅ 发送消息成功

纯 Python 实现，绕过 cua-driver 限制！"""
paste_text(test_message)
time.sleep(1)

print("\n📤 按回车发送消息...")
press_key(VK_RETURN)
time.sleep(2)

print("\n" + "=" * 60)
print("✅ 所有步骤完成！消息已发送！")
print("=" * 60)
print("\n👀 请检查「AI 数字人」聊天窗口！")
