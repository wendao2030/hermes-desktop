import ctypes
import time

def send_to_huang_correctly():
    """正确搜索'黄老师'并发送消息"""
    print("=== 正确搜索'黄老师'并发送消息 ===")
    print("请确保微信已经运行，3秒后开始...")
    time.sleep(3)
    
    user32 = ctypes.windll.user32
    
    # 常量定义
    VK_CONTROL = 0x11
    VK_F = 0x46
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    VK_BACK = 0x08
    
    # 1. 查找并激活微信窗口
    print("\n1. 激活微信窗口...")
    hwnd = user32.FindWindowW(None, "微信")
    
    if not hwnd:
        print("❌ 未找到微信窗口")
        return False
    
    print("✅ 找到微信窗口")
    
    # 激活窗口
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(2)
    print("✅ 微信窗口已激活")
    
    # 2. 发送Ctrl+F搜索
    print("\n2. 发送Ctrl+F打开搜索框...")
    
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_F, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_F, 0, 2, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    
    print("✅ Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    
    # 3. 清空搜索框（如果之前有内容）
    print("\n3. 清空搜索框...")
    for _ in range(15):  # 按多次Backspace确保清空
        user32.keybd_event(VK_BACK, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_BACK, 0, 2, 0)
        time.sleep(0.05)
    
    time.sleep(1)
    
    # 4. 输入搜索词 "黄老师"
    print("\n4. 输入搜索词: 黄老师")
    
    search_text = "黄老师"
    print(f"正在输入: {search_text}")
    
    for char in search_text:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.1)  # 稍慢一点确保输入
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.1)
    
    print(f"✅ '{search_text}' 已输入")
    time.sleep(3)  # 等待搜索结果出现
    
    # 5. 选择第一个搜索结果（应该是黄老师）
    print("\n5. 选择搜索结果（黄老师）...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 回车键已发送，选择黄老师")
    time.sleep(3)  # 等待进入聊天界面
    
    # 6. 输入测试消息
    print("\n6. 输入测试消息...")
    
    test_message = "黄老师您好！这是来自Hermes Agent的测试消息，请确认是否收到。"
    print(f"消息内容: {test_message}")
    
    for char in test_message:
        if char == ' ':
            user32.keybd_event(VK_SPACE, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_SPACE, 0, 2, 0)
            time.sleep(0.05)
        else:
            vk_code = user32.VkKeyScanW(ord(char))
            scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
            
            user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
            time.sleep(0.05)
    
    print(f"✅ 消息已输入")
    time.sleep(1)
    
    # 7. 发送消息
    print("\n7. 发送消息...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 消息已发送")
    
    print("\n=== 流程完成 ===")
    print("总结：")
    print("1. 搜索了: '黄老师'")
    print("2. 发送了消息: '黄老师您好！这是来自Hermes Agent的测试消息，请确认是否收到。'")
    print("\n请检查微信是否成功发送给了黄老师！")
    
    return True

if __name__ == "__main__":
    send_to_huang_correctly()