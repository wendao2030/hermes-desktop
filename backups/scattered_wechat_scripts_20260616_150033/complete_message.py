import ctypes
import time

def complete_wechat_message():
    """完成微信消息发送"""
    print("=== 完成微信消息发送 ===")
    
    user32 = ctypes.windll.user32
    
    # 1. 先按回车键选择第一个搜索结果
    print("\n1. 按回车键选择第一个搜索结果...")
    
    VK_RETURN = 0x0D
    
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 回车键已发送")
    
    # 等待进入聊天界面
    time.sleep(3)
    
    # 2. 输入测试消息
    print("\n2. 输入测试消息...")
    
    # 先输入英文测试
    test_message_en = "TEST MESSAGE FROM HERMES"
    print(f"输入英文测试: {test_message_en}")
    
    for char in test_message_en:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.03)
    
    print(f"✅ '{test_message_en}' 已输入")
    time.sleep(1)
    
    # 发送消息
    print("\n3. 发送消息...")
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 消息已发送")
    time.sleep(2)
    
    # 4. 输入中文消息
    print("\n4. 输入中文测试消息...")
    
    # 先删除之前的英文
    VK_BACK = 0x08
    for _ in range(len(test_message_en)):
        user32.keybd_event(VK_BACK, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_BACK, 0, 2, 0)
        time.sleep(0.05)
    
    time.sleep(1)
    
    # 输入中文消息
    test_message_cn = "这是来自Hermes Agent的测试消息，请确认是否收到。"
    print(f"输入中文消息: {test_message_cn}")
    
    for char in test_message_cn:
        vk_code = user32.VkKeyScanW(ord(char))
        scan_code = user32.MapVirtualKeyW(vk_code & 0xFF, 0)
        
        user32.keybd_event(vk_code & 0xFF, scan_code, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk_code & 0xFF, scan_code, 2, 0)
        time.sleep(0.05)
    
    print(f"✅ '{test_message_cn}' 已输入")
    time.sleep(1)
    
    # 发送中文消息
    print("\n5. 发送中文消息...")
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_RETURN, 0, 2, 0)
    
    print("✅ 中文消息已发送")
    
    print("\n=== 完成 ===")
    print("请检查微信中是否收到了两条测试消息：")
    print("1. 英文: 'TEST MESSAGE FROM HERMES'")
    print("2. 中文: '这是来自Hermes Agent的测试消息，请确认是否收到。'")
    
    return True

if __name__ == "__main__":
    complete_wechat_message()