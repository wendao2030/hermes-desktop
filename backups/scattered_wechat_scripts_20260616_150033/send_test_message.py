import ctypes
import time

def type_message():
    """输入测试消息"""
    print("=== 输入测试消息 ===")
    
    # 消息内容
    message = "这是来自Hermes Agent的测试消息，使用Python脚本激活微信和搜索，请确认是否收到。"
    
    # 加载Windows API
    user32 = ctypes.windll.user32
    
    # 定义SendInput函数
    SendInput = user32.SendInput
    
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
    
    print(f"正在输入消息: {message}")
    
    # 输入每个字符
    for char in message:
        # 获取虚拟键码
        vk_code = user32.VkKeyScanW(ord(char))
        
        # 按下键
        extra = ctypes.c_ulong(0)
        ii_press = Input()
        ii_press.type = 1  # KEYBOARD_INPUT
        ii_press.ki = KeyboardInput()
        ii_press.ki.wVk = vk_code & 0xFF
        ii_press.ki.wScan = 0
        ii_press.ki.dwFlags = 0  # 按下
        ii_press.ki.time = 0
        ii_press.ki.dwExtraInfo = ctypes.pointer(extra)
        
        SendInput(1, ctypes.pointer(ii_press), ctypes.sizeof(ii_press))
        time.sleep(0.03)  # 短暂延迟
        
        # 释放键
        ii_release = Input()
        ii_release.type = 1  # KEYBOARD_INPUT
        ii_release.ki = KeyboardInput()
        ii_release.ki.wVk = vk_code & 0xFF
        ii_release.ki.wScan = 0
        ii_release.ki.dwFlags = 0x0002  # KEYUP
        ii_release.ki.time = 0
        ii_release.ki.dwExtraInfo = ctypes.pointer(extra)
        
        SendInput(1, ctypes.pointer(ii_release), ctypes.sizeof(ii_release))
        time.sleep(0.03)  # 字符间延迟
    
    print(f"✅ 消息输入完成: {message}")
    
    # 等待一下
    time.sleep(1)
    
    # 发送回车键发送消息
    print("\n正在发送回车键发送消息...")
    
    VK_RETURN = 0x0D
    
    # 按下回车键
    extra = ctypes.c_ulong(0)
    ii_press = Input()
    ii_press.type = 1  # KEYBOARD_INPUT
    ii_press.ki = KeyboardInput()
    ii_press.ki.wVk = VK_RETURN
    ii_press.ki.wScan = 0
    ii_press.ki.dwFlags = 0  # 按下
    ii_press.ki.time = 0
    ii_press.ki.dwExtraInfo = ctypes.pointer(extra)
    
    SendInput(1, ctypes.pointer(ii_press), ctypes.sizeof(ii_press))
    time.sleep(0.1)
    
    # 释放回车键
    ii_release = Input()
    ii_release.type = 1  # KEYBOARD_INPUT
    ii_release.ki = KeyboardInput()
    ii_release.ki.wVk = VK_RETURN
    ii_release.ki.wScan = 0
    ii_release.ki.dwFlags = 0x0002  # KEYUP
    ii_release.ki.time = 0
    ii_release.ki.dwExtraInfo = ctypes.pointer(extra)
    
    SendInput(1, ctypes.pointer(ii_release), ctypes.sizeof(ii_release))
    
    print("✅ 回车键发送完成！")
    print("\n🎉 消息发送流程完成！")

def main():
    type_message()

if __name__ == "__main__":
    main()