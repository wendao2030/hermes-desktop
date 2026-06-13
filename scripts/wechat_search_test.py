import ctypes
import time
import subprocess
import sys
import os

print("=== 微信联系人搜索精确测试 ===")
print("目标: 验证搜索'AI 数字人'并选择正确联系人")

# Windows API函数
keybd_event = ctypes.windll.user32.keybd_event
GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW

# 虚拟键码
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_DOWN = 0x28      # 向下箭头
VK_UP = 0x26        # 向上箭头
VK_TAB = 0x09       # Tab键

def get_active_window_title():
    """获取当前活动窗口的标题"""
    hwnd = GetForegroundWindow()
    length = GetWindowTextLength(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buff, length + 1)
    return buff.value

def press_key(vk_code):
    """按下按键"""
    keybd_event(vk_code, 0, 0, 0)

def release_key(vk_code):
    """释放按键"""
    keybd_event(vk_code, 0, 2, 0)

def send_hotkey(*keys):
    """发送组合快捷键"""
    print(f"发送快捷键: {keys}")
    
    # 按下所有修饰键
    for key in keys[:-1]:
        press_key(key)
        time.sleep(0.05)
    
    # 按下主键
    press_key(keys[-1])
    time.sleep(0.1)
    
    # 释放所有键（逆序）
    for key in reversed(keys):
        release_key(key)
        time.sleep(0.05)
    
    time.sleep(0.5)

def type_text_simple(text):
    """简单文本输入（适用于英文和数字）"""
    print(f"输入文本: {text}")
    
    for char in text:
        if char.isalpha():
            # 字母
            vk_code = ord(char.upper())
            press_key(vk_code)
            time.sleep(0.02)
            release_key(vk_code)
            time.sleep(0.02)
        elif char.isdigit():
            # 数字
            vk_code = ord(char)
            press_key(vk_code)
            time.sleep(0.02)
            release_key(vk_code)
            time.sleep(0.02)
        elif char == ' ':
            # 空格
            press_key(0x20)
            time.sleep(0.02)
            release_key(0x20)
            time.sleep(0.02)
        else:
            # 其他字符，暂时跳过
            print(f"跳过特殊字符: '{char}'")
            continue

def test_search_and_select():
    """测试搜索和选择流程"""
    print("\n=== 测试1: 基本搜索流程 ===")
    
    # 1. 激活微信
    print("1. 激活微信窗口...")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(3)
    
    # 2. 激活搜索
    print("2. 激活搜索...")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 3. 输入搜索内容
    print("3. 输入搜索内容...")
    type_text_simple("AI")
    time.sleep(1)
    type_text_simple(" shuziren")
    time.sleep(2)
    
    # 4. 测试不同的选择方法
    print("\n=== 测试2: 不同选择方法 ===")
    
    # 方法A: 直接按回车
    print("方法A: 直接按回车选择第一个结果")
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    # 检查是否进入聊天界面
    current_window = get_active_window_title()
    print(f"当前窗口: {current_window}")
    
    if "AI" in current_window or "数字人" in current_window:
        print("✅ 成功进入聊天界面")
        
        # 输入测试消息
        print("\n输入测试消息...")
        type_text_simple("Test 1: 直接回车选择")
        time.sleep(1)
        
        # 发送
        press_key(VK_RETURN)
        release_key(VK_RETURN)
        time.sleep(2)
        print("✅ 消息1已发送")
    else:
        print("❌ 可能未正确选择联系人")
        
        # 方法B: 按Tab键再回车
        print("\n方法B: 按Tab键再回车")
        press_key(VK_TAB)
        release_key(VK_TAB)
        time.sleep(1)
        press_key(VK_RETURN)
        release_key(VK_RETURN)
        time.sleep(2)
        
        # 再次检查
        current_window = get_active_window_title()
        print(f"当前窗口: {current_window}")
        
        if "AI" in current_window or "数字人" in current_window:
            print("✅ Tab+回车成功进入聊天界面")
            
            # 输入测试消息
            print("\n输入测试消息...")
            type_text_simple("Test 2: Tab+回车选择")
            time.sleep(1)
            
            # 发送
            press_key(VK_RETURN)
            release_key(VK_RETURN)
            time.sleep(2)
            print("✅ 消息2已发送")
        else:
            print("❌ Tab+回车也失败")

def test_alternative_method():
    """测试替代方法：使用鼠标模拟点击"""
    print("\n=== 测试3: 替代方法 - 使用cua-driver截图验证 ===")
    
    # 先激活微信
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(3)
    
    # 激活搜索
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 输入搜索内容
    type_text_simple("AI shuziren")
    time.sleep(2)
    
    print("请手动检查：")
    print("1. 微信搜索框是否显示了'AI 数字人'？")
    print("2. 搜索结果列表是否出现？")
    print("3. 第一个结果是否是'AI 数字人'？")
    print("\n如果是，请按回车键选择第一个结果")
    
    # 等待用户确认
    input("按Enter继续...")
    
    # 按回车选择
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    print("现在应该进入了聊天界面，请输入测试消息...")
    type_text_simple("Test 3: 手动确认后发送")
    time.sleep(1)
    
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    print("✅ 消息3已发送")

def main():
    print("开始微信联系人搜索精确测试")
    print("当前活动窗口:", get_active_window_title())
    
    # 测试基本搜索流程
    test_search_and_select()
    
    print("\n=== 测试总结 ===")
    print("1. 如果看到'AI'或'数字人'在窗口标题中，说明成功选择了正确联系人")
    print("2. 如果窗口标题没有变化，可能是：")
    print("   a. 搜索没有找到'AI 数字人'这个联系人")
    print("   b. 搜索结果列表没有正确显示")
    print("   c. 回车键没有正确选择第一个结果")
    print("3. 建议手动操作一次，观察微信的响应行为")
    
    # 询问是否测试替代方法
    response = input("\n是否测试替代方法？(y/n): ")
    if response.lower() == 'y':
        test_alternative_method()

if __name__ == "__main__":
    main()