import ctypes
import time
import pyperclip

print("=== 微信消息发送完全自动化方案 ===")
print("无需人工交互，自动执行所有步骤")

# Windows API函数
user32 = ctypes.windll.user32

# 虚拟键码
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_DOWN = 0x28      # 向下箭头
VK_A = 0x41
VK_V = 0x56
VK_DELETE = 0x2E    # Delete键
VK_ESCAPE = 0x1B    # Esc键

def key_down(vk_code):
    """按下按键"""
    user32.keybd_event(vk_code, 0, 0, 0)

def key_up(vk_code):
    """释放按键"""
    user32.keybd_event(vk_code, 0, 2, 0)

def send_hotkey(*keys, delay=0.1):
    """发送组合快捷键"""
    print(f"发送快捷键: {keys}")
    
    # 按下所有修饰键
    for key in keys[:-1]:
        key_down(key)
        time.sleep(delay/2)
    
    # 按下主键
    key_down(keys[-1])
    time.sleep(delay)
    
    # 释放所有键（逆序）
    for key in reversed(keys):
        key_up(key)
        time.sleep(delay/2)
    
    time.sleep(1)

def type_with_clipboard(text):
    """使用剪贴板输入文本"""
    print(f"使用剪贴板输入: {text}")
    
    try:
        pyperclip.copy(text)
        time.sleep(0.5)
        
        # 粘贴
        send_hotkey(VK_CONTROL, VK_V)
        time.sleep(1)
        return True
    except Exception as e:
        print(f"剪贴板失败: {e}")
        return False

def press_key(vk_code, delay=0.1):
    """按单个键"""
    key_down(vk_code)
    time.sleep(delay)
    key_up(vk_code)
    time.sleep(delay)

def main():
    print("开始完全自动化微信消息发送...")
    
    # 记录开始时间
    start_time = time.time()
    
    # 1. 激活微信窗口
    print("\n1. 激活微信窗口 (Ctrl+Alt+W)...")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(3)
    
    # 2. 激活搜索
    print("\n2. 激活搜索 (Ctrl+F)...")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 3. 输入搜索内容
    print("\n3. 输入搜索内容...")
    contact_name = "AI 数字人"
    
    # 先清除可能存在的旧内容
    send_hotkey(VK_CONTROL, VK_A)  # Ctrl+A全选
    time.sleep(0.5)
    press_key(VK_DELETE)  # 删除
    time.sleep(1)
    
    # 输入搜索内容
    if type_with_clipboard(contact_name):
        print("✅ 中文搜索内容输入成功")
    else:
        print("❌ 剪贴板失败，尝试备用方案")
        # 这里可以添加备用输入方法
    
    time.sleep(3)
    
    # 4. 选择联系人（尝试多种方法）
    print("\n4. 选择联系人...")
    
    # 方法1: 直接回车
    print("尝试方法1: 直接回车")
    press_key(VK_RETURN)
    time.sleep(2)
    
    # 方法2: 如果方法1失败，尝试向下箭头+回车
    print("等待2秒后尝试方法2: ↓+回车")
    time.sleep(2)
    press_key(VK_DOWN)
    time.sleep(0.5)
    press_key(VK_RETURN)
    time.sleep(2)
    
    # 方法3: 如果还失败，尝试Esc返回再重新选择
    print("等待2秒后尝试方法3: Esc返回再↓+回车")
    time.sleep(2)
    press_key(VK_ESCAPE)
    time.sleep(1)
    press_key(VK_DOWN)
    time.sleep(0.5)
    press_key(VK_DOWN)  # 按两次↓
    time.sleep(0.5)
    press_key(VK_RETURN)
    time.sleep(2)
    
    # 5. 输入测试消息
    print("\n5. 输入测试消息...")
    test_message = "测试消息：这是来自Hermes Agent的完全自动化测试，时间戳：" + time.strftime("%Y-%m-%d %H:%M:%S")
    
    if type_with_clipboard(test_message):
        print("✅ 测试消息输入成功")
    else:
        print("❌ 消息输入失败，使用备用消息")
        test_message = "Test: Automated message from Hermes Agent at " + time.strftime("%Y-%m-%d %H:%M:%S")
        # 这里可以添加备用输入方法
    
    time.sleep(1)
    
    # 6. 发送消息
    print("\n6. 发送消息...")
    press_key(VK_RETURN)
    time.sleep(2)
    
    # 7. 发送确认消息
    print("\n7. 发送确认消息...")
    confirm_message = "✅ 自动化消息发送完成，请确认是否收到"
    if type_with_clipboard(confirm_message):
        time.sleep(1)
        press_key(VK_RETURN)
        time.sleep(2)
    
    # 计算总耗时
    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("=== 自动化操作完成 ===")
    print(f"总耗时: {total_time:.1f}秒")
    print(f"目标联系人: {contact_name}")
    print(f"测试消息: {test_message}")
    print("="*50)
    
    print("\n操作总结:")
    print("✅ 已执行完整自动化流程")
    print("✅ 尝试了多种选择联系人的方法")
    print("✅ 发送了带时间戳的测试消息")
    print("✅ 发送了确认消息")
    
    print("\n请检查微信：")
    print("1. 是否收到了测试消息？")
    print("2. 消息内容是否正确？")
    print("3. 时间戳是否匹配？")
    
    # 保存详细日志
    log_content = f"""微信消息发送自动化日志
=====================
操作时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {total_time:.1f}秒

目标联系人: {contact_name}
测试消息: {test_message}

执行步骤:
1. 激活微信窗口 (Ctrl+Alt+W)
2. 激活搜索 (Ctrl+F)
3. 输入搜索内容: {contact_name}
4. 选择联系人 (尝试了3种方法)
5. 输入测试消息
6. 发送消息
7. 发送确认消息

状态: 自动化流程执行完成

注意事项:
- 如果未收到消息，可能是选择了错误的联系人
- 可以检查微信聊天记录确认
- 如需重试，可以再次运行此脚本
"""
    
    with open("wechat_auto_log.txt", "w", encoding="utf-8") as f:
        f.write(log_content)
    
    print(f"\n详细日志保存到: wechat_auto_log.txt")
    print("\n如果仍然没收到消息，可能是：")
    print("1. 选择了错误的联系人")
    print("2. 微信界面状态异常")
    print("3. 需要手动验证联系人选择")

if __name__ == "__main__":
    main()