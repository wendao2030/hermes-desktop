import ctypes
import time

# 定义Windows API常量
VK_MENU = 0x12  # Alt键
VK_TAB = 0x09

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

def send_alt_tab():
    """发送Alt+Tab快捷键来切换窗口"""
    print("正在发送Alt+Tab切换窗口...")
    
    # 按下Alt
    press_key(VK_MENU)
    time.sleep(0.1)
    
    # 按下Tab
    press_key(VK_TAB)
    time.sleep(0.5)  # 稍长一点时间，让Alt+Tab界面出现
    
    # 释放Tab
    release_key(VK_TAB)
    time.sleep(0.1)
    
    # 释放Alt（这会切换到选中的窗口）
    release_key(VK_MENU)
    
    print("Alt+Tab切换完成！")

if __name__ == "__main__":
    send_alt_tab()
    print("请检查是否切换到微信窗口...")