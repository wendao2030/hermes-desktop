import ctypes
import time
import subprocess
import sys
import os

print("=== 微信消息发送深度调试 ===")
print("目标: 找出消息未发送成功的原因")
print()

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
VK_SHIFT = 0x10

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

def type_text_advanced(text):
    """使用剪贴板输入复杂文本（中文等）"""
    print(f"使用剪贴板输入文本: {text}")
    
    # 将文本复制到剪贴板
    import pyperclip
    try:
        pyperclip.copy(text)
        print("文本已复制到剪贴板")
        
        # 按Ctrl+V粘贴
        send_hotkey(VK_CONTROL, 0x56)  # Ctrl+V
        time.sleep(1)
        return True
    except Exception as e:
        print(f"剪贴板方法失败: {e}")
        return False

def check_wechat_process():
    """检查微信进程状态"""
    print("检查微信进程...")
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq WeChatAppEx.exe'],
            capture_output=True,
            text=True,
            encoding='gbk'
        )
        print(result.stdout)
        return "WeChatAppEx.exe" in result.stdout
    except:
        print("无法检查进程状态")
        return False

def main():
    print("=== 开始深度调试 ===")
    
    # 检查当前活动窗口
    print(f"当前活动窗口: {get_active_window_title()}")
    
    # 检查微信进程
    if not check_wechat_process():
        print("警告: 未检测到微信进程，请确保微信已运行")
        return
    
    print("\n=== 执行完整流程 ===")
    
    # 步骤1: 激活微信窗口
    print("\n1. 激活微信窗口 (Ctrl+Alt+W)...")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(3)
    print(f"激活后窗口: {get_active_window_title()}")
    
    # 检查是否成功激活微信
    current_window = get_active_window_title()
    if "微信" not in current_window and "WeChat" not in current_window:
        print("警告: 微信窗口可能未获得焦点")
        print("尝试Alt+Tab切换到微信...")
        send_hotkey(VK_MENU, VK_RETURN)  # Alt+Enter作为替代
        time.sleep(2)
    
    # 步骤2: 激活搜索
    print("\n2. 激活搜索功能 (Ctrl+F)...")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 步骤3: 输入搜索内容
    print("\n3. 输入搜索内容...")
    print("方法A: 直接输入 'AI 数字人'")
    type_text_simple("AI shuziren")  # 先用拼音测试
    time.sleep(2)
    
    # 步骤4: 选择搜索结果
    print("\n4. 选择搜索结果 (回车)...")
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    # 步骤5: 输入测试消息
    print("\n5. 输入测试消息...")
    print("方法A: 简单英文测试")
    type_text_simple("Test message from Hermes Agent")
    time.sleep(1)
    
    # 步骤6: 发送消息
    print("\n6. 发送消息 (回车)...")
    press_key(VK_RETURN)
    release_key(VK_RETURN)
    time.sleep(2)
    
    print("\n=== 调试完成 ===")
    print("总结:")
    print("1. 如果看到'微信'或'WeChat'在窗口标题中，说明窗口激活成功")
    print("2. 如果输入的是英文，说明键盘输入基本正常")
    print("3. 如果仍然没收到消息，可能是:")
    print("   a. 微信界面未正确响应快捷键")
    print("   b. 输入法状态问题（中文/英文切换）")
    print("   c. 微信版本兼容性问题")
    print("   d. 消息发送但被微信拦截")
    
    print("\n建议:")
    print("1. 请手动检查微信窗口是否在前台")
    print("2. 请检查输入法是否为英文状态")
    print("3. 可以尝试手动发送一条消息，看看是否正常")

if __name__ == "__main__":
    main()