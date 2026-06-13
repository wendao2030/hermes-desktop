import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# 查找微信窗口
def find_wechat_window():
    found_windows = []
    
    def enum_callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value
        
        if title and ('微信' in title or 'WeChat' in title):
            # 检查是否是可见窗口
            if user32.IsWindowVisible(hwnd):
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                found_windows.append({
                    'hwnd': hwnd,
                    'title': title,
                    'width': width,
                    'height': height
                })
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    # 筛选：主微信窗口通常比较大，搜一搜窗口比较小
    for win in found_windows:
        print(f"找到窗口: {win['title']} ({win['width']}x{win['height']}) hwnd={win['hwnd']}")
    
    # 优先选择较大的窗口（主界面）
    if found_windows:
        found_windows.sort(key=lambda x: x['width'] * x['height'], reverse=True)
        return found_windows[0]['hwnd']
    
    return None

# 激活窗口
def activate_window(hwnd):
    # 先最小化再恢复，确保窗口被激活
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.2)
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    
    # 设为前台窗口
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # 验证是否激活成功
    active_hwnd = user32.GetForegroundWindow()
    if active_hwnd == hwnd:
        print("✅ 微信主窗口已成功激活！")
        return True
    else:
        print(f"⚠️  激活可能失败，前台窗口 hwnd={active_hwnd}")
        return False

if __name__ == "__main__":
    print("正在查找微信窗口...")
    hwnd = find_wechat_window()
    
    if hwnd:
        print(f"\n找到微信主窗口 hwnd={hwnd}，正在激活...")
        activate_window(hwnd)
    else:
        print("❌ 未找到微信窗口，请先启动微信！")
