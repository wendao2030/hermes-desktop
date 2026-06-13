import ctypes
import time
import win32gui
import win32con
import win32api

def find_wechat_window():
    """查找微信窗口"""
    print("查找微信窗口...")
    
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if "微信" in window_text:
                windows.append((hwnd, window_text))
        return True
    
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if windows:
        print(f"找到 {len(windows)} 个微信窗口:")
        for hwnd, text in windows:
            print(f"  HWND: {hwnd}, 标题: {text}")
        return windows[0][0]
    else:
        print("未找到微信窗口")
        return None

def activate_window(hwnd):
    """激活窗口"""
    print(f"激活窗口 HWND: {hwnd}")
    
    # 恢复窗口（如果最小化）
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    
    # 置顶窗口
    win32gui.SetForegroundWindow(hwnd)
    
    # 等待窗口激活
    time.sleep(2)
    print("窗口已激活")
    return True

def send_ctrl_f(hwnd):
    """向指定窗口发送Ctrl+F"""
    print("发送Ctrl+F...")
    
    # 发送WM_KEYDOWN消息
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, ord('F'), 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, ord('F'), 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)
    
    print("Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    return True

def send_text_directly(hwnd, text):
    """直接向窗口发送文本"""
    print(f"直接发送文本: {text}")
    
    # 方法1: 使用WM_CHAR消息发送每个字符
    for char in text:
        # 获取字符的虚拟键码
        vk_code = win32api.VkKeyScan(char)
        
        if vk_code != -1:
            # 发送WM_CHAR消息
            win32api.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
            time.sleep(0.05)
    
    print("文本发送完成")
    time.sleep(1)
    return True

def send_enter(hwnd):
    """发送回车键"""
    print("发送回车键...")
    
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.1)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    
    print("回车键已发送")
    time.sleep(1)
    return True

def main():
    print("=== 使用Windows API直接控制微信 ===")
    
    # 1. 查找微信窗口
    hwnd = find_wechat_window()
    if not hwnd:
        print("❌ 未找到微信窗口")
        return
    
    # 2. 激活窗口
    if not activate_window(hwnd):
        print("❌ 窗口激活失败")
        return
    
    # 3. 发送Ctrl+F
    if not send_ctrl_f(hwnd):
        print("❌ Ctrl+F发送失败")
        return
    
    # 4. 输入搜索词
    search_text = "AI 数字人"
    print(f"\n输入搜索词: {search_text}")
    
    # 尝试不同的输入方法
    print("\n尝试方法1: 直接发送字符...")
    if send_text_directly(hwnd, search_text):
        print("✅ 方法1完成")
    else:
        print("❌ 方法1失败")
    
    # 等待搜索结果
    time.sleep(3)
    
    # 5. 选择第一个结果
    print("\n选择第一个搜索结果...")
    if send_enter(hwnd):
        print("✅ 已选择第一个结果")
    
    # 等待聊天界面打开
    time.sleep(2)
    
    # 6. 输入测试消息
    test_message = "这是使用Windows API直接发送的测试消息，请确认是否收到。"
    print(f"\n输入测试消息: {test_message}")
    
    if send_text_directly(hwnd, test_message):
        print("✅ 测试消息已输入")
    
    # 7. 发送消息
    print("\n发送消息...")
    if send_enter(hwnd):
        print("✅ 消息已发送")
    
    print("\n🎉 流程完成！请检查微信是否收到消息。")

if __name__ == "__main__":
    main()