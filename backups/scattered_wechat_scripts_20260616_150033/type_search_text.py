import ctypes
import time

def type_text(text):
    """模拟键盘输入文本"""
    print(f"正在输入文本: {text}")
    
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
    
    # 输入每个字符
    for char in text:
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
        time.sleep(0.05)  # 短暂延迟
        
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
        time.sleep(0.05)  # 字符间延迟
    
    print(f"文本输入完成: {text}")

def main():
    print("=== 模拟键盘输入 ===")
    
    # 等待一下，确保搜索框有焦点
    time.sleep(1)
    
    # 输入搜索词
    search_text = "AI 数字人"
    type_text(search_text)
    
    print("\n✅ 搜索词输入完成！")
    print("请等待3秒让搜索结果出现...")

if __name__ == "__main__":
    main()