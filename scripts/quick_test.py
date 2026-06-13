import ctypes
import time
import subprocess

def quick_wechat_test():
    """快速测试：激活微信、搜索、输入"""
    print("=== 快速微信输入测试 ===")
    print("注意：请确保微信已经在运行")
    
    # 1. 激活微信窗口
    print("\n1. 激活微信窗口...")
    
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
        "SUCCESS"
    } else {
        "FAIL"
    }
    """
    
    result = subprocess.run(["powershell", "-Command", ps_activate], 
                          capture_output=True, text=True, timeout=5)
    
    if "SUCCESS" in result.stdout:
        print("✅ 微信窗口已激活")
    else:
        print("❌ 微信窗口激活失败")
        return False
    
    # 等待窗口激活
    time.sleep(2)
    
    # 2. 发送Ctrl+F
    print("\n2. 发送Ctrl+F...")
    
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
    
    extra = ctypes.c_ulong(0)
    
    # 发送Ctrl+F
    inputs = []
    
    # Ctrl down
    ctrl_down = Input()
    ctrl_down.type = 1
    ctrl_down.ki = KeyboardInput()
    ctrl_down.ki.wVk = VK_CONTROL
    ctrl_down.ki.wScan = 0
    ctrl_down.ki.dwFlags = 0
    ctrl_down.ki.time = 0
    ctrl_down.ki.dwExtraInfo = ctypes.pointer(extra)
    inputs.append(ctrl_down)
    
    # F down
    f_down = Input()
    f_down.type = 1
    f_down.ki = KeyboardInput()
    f_down.ki.wVk = VK_F
    f_down.ki.wScan = 0
    f_down.ki.dwFlags = 0
    f_down.ki.time = 0
    f_down.ki.dwExtraInfo = ctypes.pointer(extra)
    inputs.append(f_down)
    
    # F up
    f_up = Input()
    f_up.type = 1
    f_up.ki = KeyboardInput()
    f_up.ki.wVk = VK_F
    f_up.ki.wScan = 0
    f_up.ki.dwFlags = 0x0002
    f_up.ki.time = 0
    f_up.ki.dwExtraInfo = ctypes.pointer(extra)
    inputs.append(f_up)
    
    # Ctrl up
    ctrl_up = Input()
    ctrl_up.type = 1
    ctrl_up.ki = KeyboardInput()
    ctrl_up.ki.wVk = VK_CONTROL
    ctrl_up.ki.wScan = 0
    ctrl_up.ki.dwFlags = 0x0002
    ctrl_up.ki.time = 0
    ctrl_up.ki.dwExtraInfo = ctypes.pointer(extra)
    inputs.append(ctrl_up)
    
    # 一次性发送所有输入
    for inp in inputs:
        SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))
        time.sleep(0.1)
    
    print("✅ Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    
    # 3. 输入"TEST"
    print("\n3. 输入'TEST'...")
    
    test_text = "TEST"
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
    
    # 4. 输入"AI 数字人"
    print("\n4. 输入'AI 数字人'...")
    
    search_text = "AI 数字人"
    for char in search_text:
        vk_code = ctypes.windll.user32.VkKeyScanW(ord(char))
        
        press = Input()
        press.type = 1
        press.ki = KeyboardInput()
        press.ki.wVk = vk_code & 0xFF
        press.ki.wScan = 0
        press.ki.dwFlags = 0
        press.ki.time = 0
        press.ki.dwExtraInfo = ctypes.pointer(extra)
        
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
    
    print(f"✅ '{search_text}' 已输入")
    
    print("\n=== 测试完成 ===")
    print("请立即查看微信搜索框：")
    print("1. 是否打开了搜索框？")
    print("2. 搜索框中是否有'TESTAI 数字人'？")
    print("3. 如果没有，请描述你看到的情况。")
    
    return True

if __name__ == "__main__":
    quick_wechat_test()