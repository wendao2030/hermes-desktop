import ctypes
import time
import pyperclip  # 用于复制文本到剪贴板

def activate_wechat():
    """激活微信窗口"""
    print("1. 激活微信窗口...")
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "微信")
    
    if hwnd:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        time.sleep(2)
        print("✅ 微信窗口已激活")
        return True
    else:
        print("❌ 未找到微信窗口")
        return False

def send_ctrl_f():
    """发送Ctrl+F搜索快捷键"""
    print("\n2. 发送Ctrl+F搜索...")
    
    VK_CONTROL = 0x11
    VK_F = 0x46
    
    # 定义SendInput结构
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
    
    SendInput = ctypes.windll.user32.SendInput
    
    # 按下Ctrl
    extra = ctypes.c_ulong(0)
    ctrl_down = Input()
    ctrl_down.type = 1
    ctrl_down.ki = KeyboardInput()
    ctrl_down.ki.wVk = VK_CONTROL
    ctrl_down.ki.wScan = 0
    ctrl_down.ki.dwFlags = 0
    ctrl_down.ki.time = 0
    ctrl_down.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 按下F
    f_down = Input()
    f_down.type = 1
    f_down.ki = KeyboardInput()
    f_down.ki.wVk = VK_F
    f_down.ki.wScan = 0
    f_down.ki.dwFlags = 0
    f_down.ki.time = 0
    f_down.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 释放F
    f_up = Input()
    f_up.type = 1
    f_up.ki = KeyboardInput()
    f_up.ki.wVk = VK_F
    f_up.ki.wScan = 0
    f_up.ki.dwFlags = 0x0002
    f_up.ki.time = 0
    f_up.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 释放Ctrl
    ctrl_up = Input()
    ctrl_up.type = 1
    ctrl_up.ki = KeyboardInput()
    ctrl_up.ki.wVk = VK_CONTROL
    ctrl_up.ki.wScan = 0
    ctrl_up.ki.dwFlags = 0x0002
    ctrl_up.ki.time = 0
    ctrl_up.ki.dwExtraInfo = ctypes.pointer(extra)
    
    # 发送按键序列
    SendInput(1, ctypes.pointer(ctrl_down), ctypes.sizeof(ctrl_down))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(f_down), ctypes.sizeof(f_down))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(f_up), ctypes.sizeof(f_up))
    time.sleep(0.1)
    SendInput(1, ctypes.pointer(ctrl_up), ctypes.sizeof(ctrl_up))
    
    print("✅ Ctrl+F已发送")
    time.sleep(2)  # 等待搜索框出现
    return True

def type_with_clipboard(text):
    """使用剪贴板粘贴方式输入文本"""
    print(f"\n3. 输入文本: {text}")
    
    try:
        # 复制文本到剪贴板
        pyperclip.copy(text)
        print(f"✅ 文本已复制到剪贴板: {text}")
        time.sleep(0.5)
        
        # 发送Ctrl+V粘贴
        VK_CONTROL = 0x11
        VK_V = 0x56
        
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
        
        SendInput = ctypes.windll.user32.SendInput
        
        # 按下Ctrl
        extra = ctypes.c_ulong(0)
        ctrl_down = Input()
        ctrl_down.type = 1
        ctrl_down.ki = KeyboardInput()
        ctrl_down.ki.wVk = VK_CONTROL
        ctrl_down.ki.wScan = 0
        ctrl_down.ki.dwFlags = 0
        ctrl_down.ki.time = 0
        ctrl_down.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 按下V
        v_down = Input()
        v_down.type = 1
        v_down.ki = KeyboardInput()
        v_down.ki.wVk = VK_V
        v_down.ki.wScan = 0
        v_down.ki.dwFlags = 0
        v_down.ki.time = 0
        v_down.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 释放V
        v_up = Input()
        v_up.type = 1
        v_up.ki = KeyboardInput()
        v_up.ki.wVk = VK_V
        v_up.ki.wScan = 0
        v_up.ki.dwFlags = 0x0002
        v_up.ki.time = 0
        v_up.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 释放Ctrl
        ctrl_up = Input()
        ctrl_up.type = 1
        ctrl_up.ki = KeyboardInput()
        ctrl_up.ki.wVk = VK_CONTROL
        ctrl_up.ki.wScan = 0
        ctrl_up.ki.dwFlags = 0x0002
        ctrl_up.ki.time = 0
        ctrl_up.ki.dwExtraInfo = ctypes.pointer(extra)
        
        # 发送Ctrl+V
        SendInput(1, ctypes.pointer(ctrl_down), ctypes.sizeof(ctrl_down))
        time.sleep(0.1)
        SendInput(1, ctypes.pointer(v_down), ctypes.sizeof(v_down))
        time.sleep(0.1)
        SendInput(1, ctypes.pointer(v_up), ctypes.sizeof(v_up))
        time.sleep(0.1)
        SendInput(1, ctypes.pointer(ctrl_up), ctypes.sizeof(ctrl_up))
        
        print("✅ Ctrl+V粘贴完成")
        time.sleep(1)  # 等待粘贴完成
        return True
        
    except Exception as e:
        print(f"❌ 剪贴板粘贴失败: {e}")
        return False

def main():
    print("=== 微信搜索输入测试 ===")
    
    # 1. 激活微信
    if not activate_wechat():
        return
    
    # 2. 发送Ctrl+F搜索
    if not send_ctrl_f():
        return
    
    # 3. 输入搜索词
    search_text = "AI 数字人"
    if type_with_clipboard(search_text):
        print(f"\n🎉 成功输入搜索词: {search_text}")
        print("请等待3秒查看搜索结果...")
        time.sleep(3)
        
        # 4. 选择第一个结果
        print("\n4. 选择第一个搜索结果...")
        VK_RETURN = 0x0D
        
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
        
        SendInput = ctypes.windll.user32.SendInput
        
        # 发送回车键
        extra = ctypes.c_ulong(0)
        enter_down = Input()
        enter_down.type = 1
        enter_down.ki = KeyboardInput()
        enter_down.ki.wVk = VK_RETURN
        enter_down.ki.wScan = 0
        enter_down.ki.dwFlags = 0
        enter_down.ki.time = 0
        enter_down.ki.dwExtraInfo = ctypes.pointer(extra)
        
        enter_up = Input()
        enter_up.type = 1
        enter_up.ki = KeyboardInput()
        enter_up.ki.wVk = VK_RETURN
        enter_up.ki.wScan = 0
        enter_up.ki.dwFlags = 0x0002
        enter_up.ki.time = 0
        enter_up.ki.dwExtraInfo = ctypes.pointer(extra)
        
        SendInput(1, ctypes.pointer(enter_down), ctypes.sizeof(enter_down))
        time.sleep(0.1)
        SendInput(1, ctypes.pointer(enter_up), ctypes.sizeof(enter_up))
        
        print("✅ 回车键已发送，选择第一个结果")
        time.sleep(2)
        
        # 5. 输入测试消息
        print("\n5. 输入测试消息...")
        test_message = "这是来自Hermes Agent的测试消息，使用剪贴板粘贴，请确认是否收到。"
        if type_with_clipboard(test_message):
            print(f"✅ 测试消息已输入: {test_message}")
            
            # 发送消息
            SendInput(1, ctypes.pointer(enter_down), ctypes.sizeof(enter_down))
            time.sleep(0.1)
            SendInput(1, ctypes.pointer(enter_up), ctypes.sizeof(enter_up))
            
            print("✅ 消息已发送！")
            print("\n🎉 完整流程完成！请检查微信是否收到消息。")
        else:
            print("❌ 测试消息输入失败")
    else:
        print("❌ 搜索词输入失败")

if __name__ == "__main__":
    main()