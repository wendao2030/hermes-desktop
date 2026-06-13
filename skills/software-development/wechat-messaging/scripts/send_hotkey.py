"""
微信快捷键激活脚本
当cua-driver的Ctrl+Alt+W快捷键发送失败时使用此脚本
直接通过Windows API发送快捷键，绕过cua-driver缺陷
"""

import ctypes
import time
import sys

# 定义Windows API常量
VK_CONTROL = 0x11      # Ctrl键
VK_MENU = 0x12         # Alt键
VK_W = 0x57            # W键

# 定义SendInput函数
SendInput = ctypes.windll.user32.SendInput

# C结构体定义
class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),          # 虚拟键码
        ("wScan", ctypes.c_ushort),        # 硬件扫描码
        ("dwFlags", ctypes.c_ulong),       # 按键标志
        ("time", ctypes.c_ulong),          # 时间戳
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))  # 额外信息
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),          # 输入类型 (1=键盘)
        ("ki", KeyboardInput),             # 键盘输入结构
        ("padding", ctypes.c_ubyte * 8)    # 填充字节
    ]

def press_key(vk_code):
    """按下按键"""
    extra = ctypes.c_ulong(0)
    ii_ = Input()
    ii_.type = 1  # KEYBOARD_INPUT
    ii_.ki = KeyboardInput()
    ii_.ki.wVk = vk_code
    ii_.ki.wScan = 0
    ii_.ki.dwFlags = 0  # 按下标志
    ii_.ki.time = 0
    ii_.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 发送按键按下事件
    ctypes.windll.user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))

def release_key(vk_code):
    """释放按键"""
    extra = ctypes.c_ulong(0)
    ii_ = Input()
    ii_.type = 1  # KEYBOARD_INPUT
    ii_.ki = KeyboardInput()
    ii_.ki.wVk = vk_code
    ii_.ki.wScan = 0
    ii_.ki.dwFlags = 0x0002  # KEYUP标志
    ii_.ki.time = 0
    ii_.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 发送按键释放事件
    ctypes.windll.user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))

def send_ctrl_alt_w():
    """发送Ctrl+Alt+W快捷键到系统级"""
    print("[INFO] 正在通过Windows API发送Ctrl+Alt+W快捷键...")
    
    try:
        # 按下Ctrl键
        press_key(VK_CONTROL)
        time.sleep(0.05)  # 短暂延迟确保按键顺序
        
        # 按下Alt键
        press_key(VK_MENU)
        time.sleep(0.05)
        
        # 按下W键
        press_key(VK_W)
        time.sleep(0.1)   # 保持按键按下状态
        
        # 释放W键
        release_key(VK_W)
        time.sleep(0.05)
        
        # 释放Alt键
        release_key(VK_MENU)
        time.sleep(0.05)
        
        # 释放Ctrl键
        release_key(VK_CONTROL)
        
        print("[SUCCESS] Ctrl+Alt+W快捷键发送完成！")
        print("[NOTE] 请检查微信窗口是否弹出")
        return True
        
    except Exception as e:
        print(f"[ERROR] 发送快捷键失败: {e}")
        return False

def check_wechat_process():
    """检查微信进程状态"""
    import subprocess
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq WeChatAppEx.exe', '/NH'],
            capture_output=True, text=True, shell=True
        )
        if 'WeChatAppEx.exe' in result.stdout:
            print("[INFO] 微信进程正在运行")
            return True
        else:
            print("[WARNING] 未找到微信进程")
            return False
    except Exception as e:
        print(f"[ERROR] 检查进程失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("微信快捷键激活工具")
    print("=" * 50)
    
    # 检查微信进程
    if not check_wechat_process():
        print("[WARNING] 微信可能未运行，快捷键可能无效")
    
    # 发送快捷键
    success = send_ctrl_alt_w()
    
    # 等待用户验证
    if success:
        print("\n[ACTION REQUIRED] 请确认：")
        print("1. 微信窗口是否弹出？")
        print("2. 如果未弹出，请尝试手动按Ctrl+Alt+W")
        print("3. 如果手动有效但脚本无效，可能是权限问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())