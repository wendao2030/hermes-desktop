"""
微信自动化 - 焦点修复版
核心改进：每步操作前强制激活微信窗口
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
                # 主窗口通常比较大，排除小的弹窗
                if width > 300 and height > 400:
                    found_hwnds.append((hwnd, title, width, height))
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    if found_hwnds:
        # 按窗口大小排序，取最大的（主窗口）
        found_hwnds.sort(key=lambda x: x[2] * x[3], reverse=True)
        hwnd, title, w, h = found_hwnds[0]
        print(f"✅ 找到微信窗口: {title} ({w}x{h}) hwnd={hwnd}")
        return hwnd
    else:
        print("❌ 未找到微信窗口")
        return None

def force_activate_window(hwnd):
    """强制激活窗口（确保焦点在微信）"""
    # 1. 先最小化
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.2)
    # 2. 再恢复
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    # 3. 设为前台窗口
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # 验证是否真的激活
    active_hwnd = user32.GetForegroundWindow()
    if active_hwnd == hwnd:
        print("✅ 微信窗口已成功激活（焦点确认）")
        return True
    else:
        print(f"⚠️  警告：前台窗口不是微信 (hwnd={active_hwnd})")
        return False

def press_key(vk_code):
    """按下并释放一个键"""
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(0.2)

def press_hotkey(vk1, vk2):
    """按下组合键"""
    user32.keybd_event(vk1, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 2, 0)
    time.sleep(0.1)
    user32.keybd_event(vk1, 0, 2, 0)
    time.sleep(0.3)

def paste_text(text):
    """用剪贴板粘贴中文"""
    pyperclip.copy(text)
    time.sleep(0.3)
    press_hotkey(VK_CONTROL, ord('V'))

# ==========================================
# 主程序
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 微信消息发送 - 焦点修复版")
    print("核心改进：每步前强制激活微信窗口")
    print("=" * 60)

    # 步骤 0: 找到并激活微信
    print("\n📌 步骤 0/6: 找到并强制激活微信窗口")
    hwnd = find_wechat_window()
    if not hwnd:
        print("❌ 请先手动打开微信！")
        exit(1)

    force_activate_window(hwnd)

    # 步骤 1: 激活搜索
    print("\n📌 步骤 1/6: 激活搜索框 (Ctrl+F)")
    force_activate_window(hwnd)  # 再次确保焦点
    press_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)

    # 步骤 2: 输入搜索词
    print("\n📌 步骤 2/6: 输入联系人名称 (AI 数字人)")
    force_activate_window(hwnd)  # 再次确保焦点
    paste_text("AI 数字人")
    time.sleep(3)

    # 步骤 3: 选择搜索结果
    print("\n📌 步骤 3/6: 选择搜索结果 (两次回车)")
    force_activate_window(hwnd)  # 再次确保焦点
    press_key(VK_RETURN)
    time.sleep(0.5)
    press_key(VK_RETURN)
    time.sleep(2)

    # 步骤 4: 确保焦点在输入框
    print("\n📌 步骤 4/6: 移动焦点到输入框 (按3次Tab)")
    force_activate_window(hwnd)  # 再次确保焦点
    for _ in range(3):
        press_key(VK_TAB)
    time.sleep(1)

    # 步骤 5: 输入并发送消息
    print("\n📌 步骤 5/6: 输入并发送消息")
    force_activate_window(hwnd)  # 再次确保焦点
    message = "🎉 焦点修复版测试成功！\n这次确保了每步都在微信窗口操作！"
    paste_text(message)
    time.sleep(1)

    print("\n📤 按回车发送消息...")
    press_key(VK_RETURN)
    time.sleep(2)

    print("\n" + "=" * 60)
    print("✅ 所有发送步骤已完成！")
    print("=" * 60)
    print("\n👀 请检查微信的「AI 数字人」聊天窗口！")
