import ctypes
import time

# 定义Windows API常量
VK_TAB = 0x09
VK_RETURN = 0x0D

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

def send_tab():
    """发送Tab键"""
    print("正在发送Tab键导航...")
    
    # 按下Tab
    press_key(VK_TAB)
    time.sleep(0.1)
    
    # 释放Tab
    release_key(VK_TAB)
    
    print("Tab键发送完成！")

def send_enter():
    """发送回车键"""
    print("正在发送回车键选择...")
    
    # 按下回车
    press_key(VK_RETURN)
    time.sleep(0.1)
    
    # 释放回车
    release_key(VK_RETURN)
    
    print("回车键发送完成！")

def select_first_result():
    """选择第一个搜索结果"""
    print("=== 选择第一个搜索结果 ===")
    
    # 方法1: 直接按回车（如果搜索框焦点正确，回车会选择第一个结果）
    print("\n1. 尝试直接按回车选择第一个结果...")
    send_enter()
    time.sleep(2)
    
    # 方法2: 按Tab然后回车
    print("\n2. 尝试按Tab导航然后回车...")
    send_tab()
    time.sleep(0.5)
    send_enter()
    time.sleep(2)
    
    # 方法3: 按两次Tab然后回车
    print("\n3. 尝试按两次Tab导航然后回车...")
    send_tab()
    time.sleep(0.2)
    send_tab()
    time.sleep(0.2)
    send_enter()
    time.sleep(2)

if __name__ == "__main__":
    select_first_result()
    print("\n=== 选择完成 ===")