import ctypes
import time
import subprocess
import sys
import os
import pyperclip

print("=== 微信消息发送简化方案 ===")
print("使用最直接的方法发送消息")

# Windows API函数
user32 = ctypes.windll.user32

# 虚拟键码
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_DOWN = 0x28      # 向下箭头
VK_UP = 0x26        # 向上箭头
VK_V = 0x56
VK_A = 0x41
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

def type_direct(text):
    """直接输入文本（英文和数字）"""
    print(f"直接输入: {text}")
    
    for char in text:
        if char.isalpha():
            # 字母
            vk_code = ord(char.upper())
            key_down(vk_code)
            time.sleep(0.02)
            key_up(vk_code)
            time.sleep(0.02)
        elif char.isdigit():
            # 数字
            vk_code = ord(char)
            key_down(vk_code)
            time.sleep(0.02)
            key_up(vk_code)
            time.sleep(0.02)
        elif char == ' ':
            # 空格
            key_down(0x20)
            time.sleep(0.02)
            key_up(0x20)
            time.sleep(0.02)

def press_key(vk_code, delay=0.1):
    """按单个键"""
    key_down(vk_code)
    time.sleep(delay)
    key_up(vk_code)
    time.sleep(delay)

def main():
    print("开始微信消息发送流程...")
    
    # 确保微信在前台
    print("\n1. 确保微信在前台...")
    print("如果微信不在前台，请手动点击微信窗口")
    input("按Enter键继续（确保微信窗口是活动状态）...")
    
    # 2. 激活搜索
    print("\n2. 激活搜索...")
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
        # 回退到拼音
        type_direct("AI shuziren")
        print("✅ 拼音搜索内容输入成功")
    
    time.sleep(3)
    
    # 4. 选择联系人
    print("\n4. 选择联系人...")
    print("尝试不同选择方法：")
    
    # 方法A: 直接回车
    print("方法A: 直接回车")
    press_key(VK_RETURN, delay=0.5)
    time.sleep(2)
    
    print("请观察微信窗口：")
    print("1. 是否进入了聊天界面？")
    print("2. 窗口标题是否显示'AI 数字人'？")
    
    response = input("是否成功进入聊天界面？(y/n): ")
    
    if response.lower() == 'y':
        print("✅ 成功进入聊天界面")
    else:
        print("❌ 未进入聊天界面，尝试方法B")
        
        # 返回搜索
        press_key(VK_ESCAPE)
        time.sleep(1)
        
        # 方法B: 向下箭头+回车
        print("\n方法B: 按↓再回车")
        press_key(VK_DOWN)
        time.sleep(0.5)
        press_key(VK_RETURN)
        time.sleep(2)
        
        response = input("现在是否成功进入聊天界面？(y/n): ")
        if response.lower() != 'y':
            print("❌ 仍然失败，需要手动选择")
            print("请手动使用方向键选择'AI 数字人'，然后按回车")
            input("完成后按Enter继续...")
    
    # 5. 输入测试消息
    print("\n5. 输入测试消息...")
    test_message = "测试消息：这是来自Hermes Agent的自动化测试，请确认是否收到"
    
    if type_with_clipboard(test_message):
        print("✅ 测试消息输入成功")
    else:
        # 回退到英文
        test_message = "Test message: This is an automated test from Hermes Agent, please confirm receipt"
        type_direct(test_message)
        print("✅ 英文测试消息输入成功")
    
    time.sleep(1)
    
    # 6. 发送消息
    print("\n6. 发送消息...")
    press_key(VK_RETURN)
    time.sleep(2)
    
    print("\n=== 操作完成 ===")
    print("✅ 已尝试发送测试消息")
    print(f"目标联系人: {contact_name}")
    print(f"测试消息: {test_message}")
    
    print("\n请检查微信：")
    print("1. 消息是否显示在聊天窗口中？")
    print("2. 是否有发送时间戳？")
    print("3. 对方是否收到？")
    
    # 保存操作记录
    with open("wechat_operation_log.txt", "w", encoding="utf-8") as f:
        f.write(f"操作时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"目标联系人: {contact_name}\n")
        f.write(f"测试消息: {test_message}\n")
        f.write("状态: 已完成发送尝试\n")
    
    print(f"\n操作日志保存到: wechat_operation_log.txt")

if __name__ == "__main__":
    main()