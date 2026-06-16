import ctypes
import time
import pyperclip  # 用于剪贴板操作

def send_chinese_to_huang():
    """使用剪贴板方法发送中文消息给黄老师"""
    print("=== 使用剪贴板方法发送中文消息 ===")
    print("这种方法可以正确输入中文汉字")
    print("请确保微信已经运行，3秒后开始...")
    time.sleep(3)
    
    user32 = ctypes.windll.user32
    
    # 常量定义
    VK_CONTROL = 0x11
    VK_F = 0x46
    VK_RETURN = 0x0D
    VK_V = 0x56  # Ctrl+V粘贴
    VK_A = 0x41  # Ctrl+A全选
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
    
    # 3. 清空搜索框
    print("\n3. 清空搜索框...")
    for _ in range(10):
        user32.keybd_event(VK_BACK, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_BACK, 0, 2, 0)
        time.sleep(0.05)
    
    time.sleep(1)
    
    # 4. 使用剪贴板方法输入"黄老师"
    print("\n4. 使用剪贴板输入: 黄老师")
    
    try:
        # 复制"黄老师"到剪贴板
        pyperclip.copy("黄老师")
        print("✅ '黄老师' 已复制到剪贴板")
        time.sleep(0.5)
        
        # 发送Ctrl+V粘贴
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_V, 0, 2, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        
        print("✅ Ctrl+V粘贴完成")
        
    except Exception as e:
        print(f"❌ 剪贴板方法失败: {e}")
        print("尝试使用拼音输入...")
        
        # 备选方案：输入拼音"huang lao shi"
        pinyin = "huang lao shi"
        for char in pinyin:
            if char == ' ':
                user32.keybd_event(0x20, 0, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(0x20, 0, 2, 0)
                time.sleep(0.05)
            else:
                vk_code = user32.VkKeyScanW(ord(char))
                scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
                
                user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
                time.sleep(0.05)
                user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
                time.sleep(0.05)
        
        print("✅ 拼音已输入")
    
    time.sleep(3)  # 等待搜索结果出现
    
    # 5. 选择第一个搜索结果
    print("\n5. 选择搜索结果...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 回车键已发送")
    time.sleep(3)  # 等待进入聊天界面
    
    # 6. 使用剪贴板输入中文消息
    print("\n6. 使用剪贴板输入中文消息...")
    
    test_message = "黄老师您好！这是使用剪贴板方法发送的测试消息，可以正确输入中文汉字。请确认是否收到，谢谢！"
    
    try:
        # 复制消息到剪贴板
        pyperclip.copy(test_message)
        print(f"✅ 消息已复制到剪贴板: {test_message}")
        time.sleep(0.5)
        
        # 发送Ctrl+V粘贴
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_V, 0, 2, 0)
        time.sleep(0.1)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        
        print("✅ 消息已粘贴")
        
    except Exception as e:
        print(f"❌ 剪贴板消息输入失败: {e}")
        return False
    
    time.sleep(1)
    
    # 7. 发送消息
    print("\n7. 发送消息...")
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 消息已发送")
    
    print("\n=== 流程完成 ===")
    print("这次使用了剪贴板方法，应该能正确输入中文汉字！")
    print(f"发送的消息: {test_message}")
    print("\n请检查是否成功发送给了黄老师！")
    
    return True

if __name__ == "__main__":
    send_chinese_to_huang()