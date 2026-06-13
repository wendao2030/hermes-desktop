
import ctypes
import time

# 定义Windows API常量
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt键
VK_W = 0x57

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

def send_ctrl_alt_w():
    """发送Ctrl+Alt+W快捷键"""
    print("正在发送Ctrl+Alt+W快捷键...")
    
    # 按下Ctrl
    press_key(VK_CONTROL)
    time.sleep(0.1)
    
    # 按下Alt
    press_key(VK_MENU)
    time.sleep(0.1)
    
    # 按下W
    press_key(VK_W)
    time.sleep(0.1)
    
    # 释放W
    release_key(VK_W)
    time.sleep(0.1)
    
    # 释放Alt
    release_key(VK_MENU)
    time.sleep(0.1)
    
    # 释放Ctrl
    release_key(VK_CONTROL)
    
    print("快捷键发送完成！")

if __name__ == "__main__":
    send_ctrl_alt_w()
    print("请检查微信是否弹出...")
