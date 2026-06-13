import ctypes
import time

def send_correct_message_to_huang():
    """给黄老师发送正确的测试信息（包含空格）"""
    print("=== 给黄老师发送正确的测试信息 ===")
    print("请确保微信已经运行，3秒后开始...")
    time.sleep(3)
    
    user32 = ctypes.windll.user32
    
    # 常量定义
    VK_CONTROL = 0x11
    VK_F = 0x46
    VK_RETURN = 0x0D
    VK_SPACE = 0x20  # 空格键
    
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
    print("\n2. 发送Ctrl+F搜索黄老师...")
    
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_F, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_F, 0, 2, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    
    print("✅ Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    
    # 3. 先清空搜索框（按Backspace多次）
    print("\n3. 清空搜索框...")
    VK_BACK = 0x08
    for _ in range(20):  # 多按几次确保清空
        user32.keybd_event(VK_BACK, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_BACK, 0, 2, 0)
        time.sleep(0.05)
    
    time.sleep(1)
    
    # 4. 输入搜索词 "黄老师"（带正确的中文）
    print("\n4. 输入搜索词: 黄老师")
    
    search_text = "黄老师"
    
    for char in search_text:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.05)
    
    print(f"✅ '{search_text}' 已输入")
    time.sleep(3)  # 等待搜索结果出现
    
    # 5. 选择第一个搜索结果
    print("\n5. 选择搜索结果（黄老师）...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 回车键已发送")
    time.sleep(3)  # 等待进入聊天界面
    
    # 6. 输入正确的测试消息（包含空格）
    print("\n6. 输入正确的测试消息给黄老师...")
    
    # 正确的消息，包含空格
    test_message = "黄老师您好！这是来自 Hermes Agent 的自动化测试消息，用于验证微信消息发送功能。请确认是否收到，谢谢！"
    print(f"消息内容: {test_message}")
    
    for char in test_message:
        if char == ' ':  # 处理空格
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
    
    print(f"✅ 消息已输入（包含空格）")
    time.sleep(1)
    
    # 7. 发送消息
    print("\n7. 发送消息...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 消息已发送")
    
    print("\n=== 流程完成 ===")
    print("请检查是否成功发送给黄老师：")
    print(f"'{test_message}'")
    print("\n注意：这次消息中包含了正确的空格：'Hermes Agent'")
    
    return True

if __name__ == "__main__":
    send_correct_message_to_huang()