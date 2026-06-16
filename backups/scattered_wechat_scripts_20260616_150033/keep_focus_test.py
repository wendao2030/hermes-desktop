import ctypes
import time
import subprocess
import os

def keep_focus_and_input():
    """保持微信焦点并输入"""
    print("=== 保持焦点输入测试 ===")
    
    # 1. 先找到并激活微信窗口
    print("\n1. 激活微信窗口...")
    
    # 使用PowerShell激活微信窗口
    ps_activate = """
    Add-Type @'
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern IntPtr FindWindow(string className, string windowName);
    }
    '@
    
    $hwnd = [Win32]::FindWindow($null, "微信")
    if ($hwnd -ne [IntPtr]::Zero) {
        [Win32]::ShowWindow($hwnd, 9)
        [Win32]::SetForegroundWindow($hwnd)
        "微信窗口已激活"
    } else {
        "未找到微信窗口"
    }
    """
    
    result = subprocess.run(["powershell", "-Command", ps_activate], 
                          capture_output=True, text=True, timeout=5)
    
    if "微信窗口已激活" in result.stdout:
        print("✅ 微信窗口已激活")
    else:
        print("❌ 微信窗口激活失败")
        print(f"错误: {result.stdout}")
        return False
    
    # 等待窗口完全激活
    time.sleep(2)
    
    # 2. 发送Ctrl+F（在微信窗口激活状态下）
    print("\n2. 发送Ctrl+F...")
    
    # 使用SendInput发送快捷键（此时微信窗口应该还有焦点）
    SendInput = ctypes.windll.user32.SendInput
    
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
            ("ki", KeyboardInput)
        ]
    
    VK_CONTROL = 0x11
    VK_F = 0x46
    
    # 发送Ctrl+F
    extra = ctypes.c_ulong(0)
    
    # Ctrl down
    ctrl_down = Input()
    ctrl_down.type = 1
    ctrl_down.ki = KeyboardInput()
    ctrl_down.ki.wVk = VK_CONTROL
    ctrl_down.ki.wScan = 0
    ctrl_down.ki.dwFlags = 0
    ctrl_down.ki.time = 0
    ctrl_down.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # F down
    f_down = Input()
    f_down.type = 1
    f_down.ki = KeyboardInput()
    f_down.ki.wVk = VK_F
    f_down.ki.wScan = 0
    f_down.ki.dwFlags = 0
    f_down.ki.time = 0
    f_down.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # F up
    f_up = Input()
    f_up.type = 1
    f_up.ki = KeyboardInput()
    f_up.ki.wVk = VK_F
    f_up.ki.wScan = 0
    f_up.ki.dwFlags = 0x0002
    f_up.ki.time = 0
    f_up.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # Ctrl up
    ctrl_up = Input()
    ctrl_up.type = 1
    ctrl_up.ki = KeyboardInput()
    ctrl_up.ki.wVk = VK_CONTROL
    ctrl_up.ki.wScan = 0
    ctrl_up.ki.dwFlags = 0x0002
    ctrl_up.ki.time = 0
    ctrl_up.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 执行按键序列
    SendInput(1, ctypes.pointer(ctrl_down), ctypes.sizeof(ctrl_down))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(f_down), ctypes.sizeof(f_down))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(f_up), ctypes.sizeof(f_up))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(ctrl_up), ctypes.sizeof(ctrl_up))
    
    print("✅ Ctrl+F已发送")
    
    # 等待搜索框出现
    time.sleep(2)
    
    # 3. 立即输入文本（在焦点丢失前）
    print("\n3. 立即输入文本...")
    
    # 输入"TEST"进行测试
    test_text = "TEST"
    print(f"输入: {test_text}")
    
    for char in test_text:
        vk_code = ctypes.windll.user32.VkKeyScanW(ord(char))
        
        # 按下
        press = Input()
        press.type = 1
        press.ki = KeyboardInput()
        press.ki.wVk = vk_code & 0xFF
        press.ki.wScan = 0
        press.ki.dwFlags = 0
        press.ki.time = 0
        press.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 释放
        release = Input()
        release.type = 1
        release.ki = KeyboardInput()
        release.ki.wVk = vk_code & 0xFF
        release.ki.wScan = 0
        release.ki.dwFlags = 0x0002
        release.ki.time = 0
        release.ki.dwExtraInfo = ctypes.pointer(extra)
        
        SendInput(1, ctypes.pointer(press), ctypes.sizeof(press))
        time.sleep(0.05)
        SendInput(1, ctypes.pointer(release), ctypes.sizeof(release))
        time.sleep(0.05)
    
    print(f"✅ '{test_text}' 已输入")
    
    # 等待一下让你观察
    time.sleep(3)
    
    print("\n=== 测试完成 ===")
    print("请立即查看微信搜索框中是否出现了'TEST'？")
    
    return True

def main():
    print("说明：这个脚本会一次性完成所有操作，避免焦点丢失。")
    print("请确保微信已经在运行，然后按回车键开始...")
    input()
    
    if keep_focus_and_input():
        print("\n✅ 脚本执行完成")
        print("\n请回答：")
        print("1. 微信搜索框中是否出现了'TEST'？")
        print("2. 如果没有，搜索框是否打开了？")
    else:
        print("\n❌ 脚本执行失败")

if __name__ == "__main__":
    main()