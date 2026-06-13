import ctypes
import time
import subprocess

def activate_and_search():
    """激活微信窗口并立即执行搜索"""
    print("=== 激活微信并执行搜索 ===")
    
    # 1. 激活微信窗口
    print("\n1. 激活微信窗口...")
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "微信")
    
    if not hwnd:
        print("❌ 未找到微信窗口")
        return False
    
    print("✅ 找到微信窗口")
    
    # 激活窗口
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
    user32.SetForegroundWindow(hwnd)
    
    # 等待窗口完全激活
    time.sleep(2)
    print("✅ 微信窗口已激活")
    
    # 2. 发送Ctrl+F快捷键
    print("\n2. 发送Ctrl+F快捷键...")
    
    # 使用Windows API发送Ctrl+F
    VK_CONTROL = 0x11
    VK_F = 0x46
    
    def press_key(vk_code):
        extra = ctypes.c_ulong(0)
        ii_ = ctypes.Structure()
        ii_.type = 1
        ii_.ki = ctypes.Structure()
        ii_.ki.wVk = vk_code
        ii_.ki.wScan = 0
        ii_.ki.dwFlags = 0
        ii_.ki.time = 0
        ii_.ki.dwExtraInfo = ctypes.pointer(extra)
        user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))
    
    def release_key(vk_code):
        extra = ctypes.c_ulong(0)
        ii_ = ctypes.Structure()
        ii_.type = 1
        ii_.ki = ctypes.Structure()
        ii_.ki.wVk = vk_code
        ii_.ki.wScan = 0
        ii_.ki.dwFlags = 0x0002  # KEYUP
        ii_.ki.time = 0
        ii_.ki.dwExtraInfo = ctypes.pointer(extra)
        user32.SendInput(1, ctypes.pointer(ii_), ctypes.sizeof(ii_))
    
    # 按下Ctrl+F
    press_key(VK_CONTROL)
    time.sleep(0.1)
    press_key(VK_F)
    time.sleep(0.1)
    release_key(VK_F)
    time.sleep(0.1)
    release_key(VK_CONTROL)
    
    print("✅ Ctrl+F快捷键已发送")
    
    # 等待搜索框出现
    time.sleep(2)
    print("✅ 等待搜索框出现完成")
    
    # 3. 输入搜索词
    print("\n3. 准备输入搜索词...")
    print("请在搜索框中输入: AI 数字人")
    
    return True

def main():
    if activate_and_search():
        print("\n🎉 激活和搜索准备完成！")
        print("现在可以在搜索框中输入'AI 数字人'了")
    else:
        print("\n❌ 操作失败")

if __name__ == "__main__":
    main()