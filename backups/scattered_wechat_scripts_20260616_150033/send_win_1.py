import ctypes
import time

# 定义Windows API常量
VK_LWIN = 0x5B  # 左Windows键
VK_1 = 0x31

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

def send_win_1():
    """发送Win+1快捷键（激活任务栏第一个程序）"""
    print("正在发送Win+1激活任务栏第一个程序...")
    
    # 按下Win键
    press_key(VK_LWIN)
    time.sleep(0.1)
    
    # 按下1
    press_key(VK_1)
    time.sleep(0.1)
    
    # 释放1
    release_key(VK_1)
    time.sleep(0.1)
    
    # 释放Win键
    release_key(VK_LWIN)
    
    print("Win+1发送完成！")

if __name__ == "__main__":
    send_win_1()
    print("请检查是否激活了微信窗口...")