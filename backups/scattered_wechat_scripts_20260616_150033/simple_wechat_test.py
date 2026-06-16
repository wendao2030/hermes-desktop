import ctypes
import time

def simple_wechat_test():
    """最简单的微信测试"""
    print("=== 简单微信测试 ===")
    print("这个测试假设微信窗口已经打开")
    print("如果微信没有打开，请先手动打开微信")
    print("\n3秒后开始测试...")
    time.sleep(3)
    
    # 使用Windows API激活窗口
    user32 = ctypes.windll.user32
    
    # 查找微信窗口
    hwnd = user32.FindWindowW(None, "微信")
    if not hwnd:
        print("❌ 未找到微信窗口，请确保微信已打开")
        return False
    
    print("✅ 找到微信窗口")
    
    # 激活窗口
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    
    print("✅ 微信窗口已激活")
    time.sleep(2)
    
    # 发送Ctrl+F
    print("\n发送Ctrl+F...")
    
    VK_CONTROL = 0x11
    VK_F = 0x46
    
    # 按下Ctrl
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.1)
    
    # 按下F
    user32.keybd_event(VK_F, 0, 0, 0)
    time.sleep(0.1)
    
    # 释放F
    user32.keybd_event(VK_F, 0, 2, 0)
    time.sleep(0.1)
    
    # 释放Ctrl
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    time.sleep(0.1)
    
    print("✅ Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    
    # 输入"TEST"
    print("\n输入'TEST'...")
    
    test_text = "TEST"
    for char in test_text:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        # 按下键
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.05)
        
        # 释放键
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.05)
    
    print(f"✅ '{test_text}' 已输入")
    time.sleep(2)
    
    # 输入"AI 数字人"
    print("\n输入'AI 数字人'...")
    
    search_text = "AI 数字人"
    for char in search_text:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.05)
    
    print(f"✅ '{search_text}' 已输入")
    
    print("\n=== 测试完成 ===")
    print("请立即查看微信搜索框：")
    print("1. 搜索框是否打开？")
    print("2. 框中是否有文字？")
    print("3. 如果有，是什么文字？")
    
    return True

if __name__ == "__main__":
    simple_wechat_test()