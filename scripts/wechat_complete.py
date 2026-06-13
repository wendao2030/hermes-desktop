import ctypes
import time
import subprocess
import sys

# Windows API常量
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D

# Windows API函数
SendInput = ctypes.windll.user32.SendInput
keybd_event = ctypes.windll.user32.keybd_event

# 结构体定义
class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ki", KeyboardInput),
        ("padding", ctypes.c_ubyte * 8)
    ]

def press_key(vk_code):
    """按下按键"""
    extra = ctypes.c_ulong(0)
    ii_ = Input()
    ii_.type = 1  # KEYBOARD_INPUT
    ii_.ki = KeyboardInput()
    ii_.ki.wVk = vk_code
    ii_.ki.wScan = 0
    ii_.ki.dwFlags = 0  # 按下
    ii_.ki.time = 0
    ii_.ki.dwExtraInfo = ctypes.pointer(extra)
    SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))

def release_key(vk_code):
    """释放按键"""
    extra = ctypes.c_ulong(0)
    ii_ = Input()
    ii_.type = 1  # KEYBOARD_INPUT
    ii_.ki = KeyboardInput()
    ii_.ki.wVk = vk_code
    ii_.ki.wScan = 0
    ii_.ki.dwFlags = 0x0002  # KEYUP
    ii_.ki.time = 0
    ii_.ki.dwExtraInfo = ctypes.pointer(extra)
    SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))

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

def type_text(text):
    """模拟输入文本"""
    print(f"输入文本: {text}")
    
    # 简单方法：使用keybd_event
    for char in text:
        # 对于简单ASCII字符
        vk_code = ord(char.upper())
        keybd_event(vk_code, 0, 0, 0)  # 按下
        time.sleep(0.02)
        keybd_event(vk_code, 0, 2, 0)  # 释放
        time.sleep(0.02)

def main():
    print("=== 微信消息发送完整流程 ===")
    print("目标: 给'AI 数字人'发送测试消息")
    print()
    
    # 步骤1: 激活微信窗口 (Ctrl+Alt+W)
    print("1. 激活微信窗口 (Ctrl+Alt+W)...")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(2)
    
    # 步骤2: 激活搜索 (Ctrl+F)
    print("2. 激活搜索功能 (Ctrl+F)...")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 步骤3: 输入搜索内容
    print("3. 输入搜索内容 'AI 数字人'...")
    type_text("AI 数字人")
    time.sleep(3)
    
    # 步骤4: 选择搜索结果 (回车)
    print("4. 选择搜索结果 (回车)...")
    press_key(VK_RETURN)
    time.sleep(0.1)
    release_key(VK_RETURN)
    time.sleep(2)
    
    # 步骤5: 输入测试消息
    print("5. 输入测试消息...")
    type_text("测试消息：这是通过Python脚本直接发送的完整测试，请确认是否收到")
    time.sleep(1)
    
    # 步骤6: 发送消息 (回车)
    print("6. 发送消息 (回车)...")
    press_key(VK_RETURN)
    time.sleep(0.1)
    release_key(VK_RETURN)
    time.sleep(2)
    
    print()
    print("=== 流程执行完成 ===")
    print("请检查微信聊天记录，确认是否收到消息。")
    print("如果未收到，可能是以下原因：")
    print("1. 微信窗口未获得焦点")
    print("2. 输入法状态问题")
    print("3. 微信界面响应延迟")

if __name__ == "__main__":
    main()