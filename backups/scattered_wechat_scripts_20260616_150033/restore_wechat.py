"""
先激活微信窗口（处理最小化情况）
"""
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

def find_and_restore_wechat():
    """找到微信并恢复窗口（如果最小化）"""
    found_hwnds = []
    def enum_callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value
        if title and ('微信' in title or 'WeChat' in title):
            # 包括最小化的窗口
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            # 主窗口要么可见（大），要么最小化（小但有标题）
            if width > 100 and height > 100:
                found_hwnds.append((hwnd, title, width, height, user32.IsWindowVisible(hwnd)))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    if found_hwnds:
        found_hwnds.sort(key=lambda x: x[2] * x[3], reverse=True)
        hwnd, title, w, h, visible = found_hwnds[0]
        print(f"✅ 找到微信: {title} ({w}x{h}) visible={visible}")
        
        # 恢复窗口（如果最小化）
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.5)
        
        # 设为前台
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        
        print("✅ 微信已恢复并设为前台")
        return hwnd
    else:
        print("❌ 找不到微信窗口")
        return None

# 执行
find_and_restore_wechat()
