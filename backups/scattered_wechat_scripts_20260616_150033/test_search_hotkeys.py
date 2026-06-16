import ctypes
import time

# 定义Windows API常量
VK_CONTROL = 0x11
VK_F = 0x46
VK_SHIFT = 0x10

# 定义SendInput函数
SendInput = ctypes.windll.user32.SendInput

# C结构体定义
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

def send_ctrl_f():
    """发送Ctrl+F快捷键"""
    print("正在发送Ctrl+F快捷键...")
    
    # 按下Ctrl
    press_key(VK_CONTROL)
    time.sleep(0.1)
    
    # 按下F
    press_key(VK_F)
    time.sleep(0.1)
    
    # 释放F
    release_key(VK_F)
    time.sleep(0.1)
    
    # 释放Ctrl
    release_key(VK_CONTROL)
    
    print("Ctrl+F快捷键发送完成！")

def send_ctrl_shift_f():
    """发送Ctrl+Shift+F快捷键（备用）"""
    print("正在发送Ctrl+Shift+F快捷键...")
    
    # 按下Ctrl
    press_key(VK_CONTROL)
    time.sleep(0.1)
    
    # 按下Shift
    press_key(VK_SHIFT)
    time.sleep(0.1)
    
    # 按下F
    press_key(VK_F)
    time.sleep(0.1)
    
    # 释放F
    release_key(VK_F)
    time.sleep(0.1)
    
    # 释放Shift
    release_key(VK_SHIFT)
    time.sleep(0.1)
    
    # 释放Ctrl
    release_key(VK_CONTROL)
    
    print("Ctrl+Shift+F快捷键发送完成！")

def test_all_search_methods():
    """测试所有可能的搜索快捷键"""
    print("=== 测试微信搜索快捷键 ===")
    
    # 方法1: Ctrl+F
    print("\n1. 尝试Ctrl+F...")
    send_ctrl_f()
    time.sleep(2)
    print("请检查搜索框是否出现...")
    
    # 方法2: Ctrl+F两次
    print("\n2. 尝试Ctrl+F两次...")
    send_ctrl_f()
    time.sleep(0.5)
    send_ctrl_f()
    time.sleep(2)
    print("请检查搜索框是否出现...")
    
    # 方法3: Ctrl+Shift+F
    print("\n3. 尝试Ctrl+Shift+F...")
    send_ctrl_shift_f()
    time.sleep(2)
    print("请检查搜索框是否出现...")

if __name__ == "__main__":
    test_all_search_methods()
    print("\n=== 所有方法测试完成 ===")