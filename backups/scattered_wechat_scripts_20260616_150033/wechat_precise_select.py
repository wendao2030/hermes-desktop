import ctypes
import time
import subprocess
import sys
import os

print("=== 微信精确选择联系人测试 ===")
print("问题分析: 搜索'AI 数字人'后，第一个结果可能不是目标联系人")
print("解决方案: 使用方向键精确选择")

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
VK_ESCAPE = 0x1B    # Esc键

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

def clear_search():
    """清除搜索内容"""
    print("清除搜索内容...")
    # 按Esc键取消搜索
    press_key(VK_ESCAPE)
    release_key(VK_ESCAPE)
    time.sleep(1)
    
    # 或者按Ctrl+A全选然后删除
    send_hotkey(VK_CONTROL, 0x41)  # Ctrl+A
    time.sleep(0.5)
    press_key(0x2E)  # Delete键
    release_key(0x2E)
    time.sleep(1)

def test_precise_selection():
    """测试精确选择联系人"""
    print("\n=== 策略: 使用方向键精确选择 ===")
    
    # 1. 激活微信
    print("1. 激活微信窗口...")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(3)
    
    # 2. 激活搜索
    print("2. 激活搜索...")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 3. 输入精确搜索内容
    print("3. 输入精确搜索内容...")
    # 先清除可能存在的旧内容
    clear_search()
    
    # 输入"A"（最小化匹配）
    type_text_simple("A")
    time.sleep(2)
    
    print("\n4. 使用方向键浏览搜索结果...")
    print("假设'AI 数字人'在搜索结果中，但可能不是第一个")
    
    # 方法A: 按一次向下箭头，然后回车
    print("\n方法A: 按一次↓，选择第二个结果")
    press_key(VK_DOWN)
    release_key(VK_DOWN)
    time.sleep(1)
    
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    current_window = get_active_window_title()
    print(f"当前窗口: {current_window}")
    
    if "AI" in current_window or "数字人" in current_window:
        print("✅ 成功选择'AI 数字人'")
        return True
    else:
        print(f"❌ 选择错误: {current_window}")
        
        # 返回搜索界面
        print("\n返回搜索界面重新尝试...")
        press_key(VK_ESCAPE)
        release_key(VK_ESCAPE)
        time.sleep(2)
        
        # 清除搜索
        clear_search()
        
        # 重新搜索
        type_text_simple("AI shuziren")
        time.sleep(2)
        
        # 方法B: 尝试不同的方向键组合
        print("\n方法B: 尝试不同方向键位置")
        
        # 尝试按两次向下箭头（选择第三个结果）
        for i in range(2):
            press_key(VK_DOWN)
            release_key(VK_DOWN)
            time.sleep(0.5)
        
        press_key(VK_RETURN)
        release_key(VK_RETURN)
        time.sleep(2)
        
        current_window = get_active_window_title()
        print(f"当前窗口: {current_window}")
        
        if "AI" in current_window or "数字人" in current_window:
            print("✅ 成功选择'AI 数字人'")
            return True
    
    return False

def send_test_message():
    """发送测试消息"""
    print("\n=== 发送测试消息 ===")
    
    # 输入消息
    print("输入测试消息...")
    type_text_simple("Hello AI Digital Person! This is a test from Hermes Agent.")
    time.sleep(1)
    
    # 发送
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    print("✅ 测试消息已发送")

def manual_verification_mode():
    """手动验证模式"""
    print("\n=== 手动验证模式 ===")
    print("由于自动化选择困难，建议手动操作验证：")
    print("\n请手动执行以下步骤：")
    print("1. 按 Ctrl+Alt+W 激活微信窗口")
    print("2. 按 Ctrl+F 激活搜索")
    print("3. 输入 'AI 数字人'")
    print("4. 观察搜索结果列表")
    print("5. 使用方向键找到 'AI 数字人'")
    print("6. 按回车键选择")
    print("7. 输入测试消息并发送")
    
    print("\n问题诊断：")
    print("1. 搜索'AI 数字人'后，第一个结果是什么？")
    print("2. 'AI 数字人'在第几个位置？")
    print("3. 窗口标题是否显示正确联系人？")

def main():
    print("开始微信精确选择联系人测试")
    print("当前活动窗口:", get_active_window_title())
    
    # 尝试自动精确选择
    success = test_precise_selection()
    
    if success:
        print("\n✅ 成功选择了正确联系人！")
        send_test_message()
    else:
        print("\n❌ 自动选择失败，需要手动验证")
        manual_verification_mode()
        
        # 询问是否继续尝试
        print("\n是否根据手动验证结果调整脚本？")
        print("请告诉我：")
        print("1. 搜索'AI 数字人'后，第一个结果是什么？")
        print("2. 'AI 数字人'在第几个位置（1,2,3,...）？")
        print("3. 窗口标题显示什么？")

if __name__ == "__main__":
    main()