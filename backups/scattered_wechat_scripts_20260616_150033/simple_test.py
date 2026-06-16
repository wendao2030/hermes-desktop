import ctypes
import time

def simple_keyboard_simulation():
    """最简单的键盘模拟测试"""
    print("=== 微信输入测试 - 手动验证版 ===")
    print("\n请确保：")
    print("1. 微信窗口已打开")
    print("2. 微信窗口是当前活动窗口")
    print("3. 你已经手动按了Ctrl+F打开了搜索框")
    print("\n准备好后按回车键开始测试...")
    input()
    
    # 定义SendInput
    SendInput = ctypes.windll.user32.SendInput
    
    # 定义结构体
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
    
    # 测试1: 输入"TEST"
    print("\n测试1: 输入'TEST'")
    print("请观察搜索框中是否出现了'TEST'...")
    
    test_text = "TEST"
    for char in test_text:
        # 获取虚拟键码
        vk_code = ctypes.windll.user32.VkKeyScanW(ord(char))
        
        # 按下
        extra = ctypes.c_ulong(0)
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
    
    print("✅ 'TEST' 已发送")
    time.sleep(2)
    
    # 询问结果
    result = input("\n搜索框中是否出现了'TEST'？(y/n): ")
    
    if result.lower() == 'y':
        print("✅ 键盘模拟成功！")
        print("\n现在测试中文输入...")
        
        # 测试2: 输入"AI 数字人"
        print("\n测试2: 输入'AI 数字人'")
        
        # 先删除之前的TEST
        print("删除之前的文本...")
        VK_BACK = 0x08
        for _ in range(4):  # 删除4个字符
            extra = ctypes.c_ulong(0)
            press = Input()
            press.type = 1
            press.ki = KeyboardInput()
            press.ki.wVk = VK_BACK
            press.ki.wScan = 0
            press.ki.dwFlags = 0
            press.ki.time = 0
            press.ki.dwExtraInfo = ctypes.pointer(extra)
            
            release = Input()
            release.type = 1
            release.ki = KeyboardInput()
            release.ki.wVk = VK_BACK
            release.ki.wScan = 0
            release.ki.dwFlags = 0x0002
            release.ki.time = 0
            release.ki.dwExtraInfo = ctypes.pointer(extra)
            
            SendInput(1, ctypes.pointer(press), ctypes.sizeof(press))
            time.sleep(0.1)
            SendInput(1, ctypes.pointer(release), ctypes.sizeof(release))
            time.sleep(0.1)
        
        time.sleep(1)
        
        # 输入"AI 数字人"
        chinese_text = "AI 数字人"
        print(f"输入: {chinese_text}")
        
        for char in chinese_text:
            vk_code = ctypes.windll.user32.VkKeyScanW(ord(char))
            
            extra = ctypes.c_ulong(0)
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
        
        print(f"✅ '{chinese_text}' 已发送")
        time.sleep(2)
        
        print("\n🎉 测试完成！")
        print("请手动按回车键选择第一个搜索结果，然后继续测试消息发送。")
        
    else:
        print("❌ 键盘模拟失败")
        print("可能的原因：")
        print("1. 微信窗口没有获得焦点")
        print("2. 搜索框没有打开")
        print("3. Windows权限问题")

if __name__ == "__main__":
    simple_keyboard_simulation()