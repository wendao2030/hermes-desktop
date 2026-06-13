"""
键盘输入模拟器（用于微信自动化）
支持：英文逐字输入 + 中文剪贴板粘贴
创建时间：2026年6月11日
验证环境：Windows 10 + 微信 PC 版
"""
import ctypes
import time
import pyperclip

user32 = ctypes.windll.user32

def send_key(vk_code, scan_code=0, is_extended=False):
    """发送单个按键按下"""
    if is_extended:
        user32.keybd_event(vk_code, scan_code, 0x0001, 0)
    else:
        user32.keybd_event(vk_code, scan_code, 0, 0)

def release_key(vk_code, scan_code=0, is_extended=False):
    """释放单个按键"""
    if is_extended:
        user32.keybd_event(vk_code, scan_code, 0x0001 | 0x0002, 0)
    else:
        user32.keybd_event(vk_code, scan_code, 0x0002, 0)

def type_char(char):
    """输入单个英文字符（不支持中文！）"""
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    
    if char == '\n':
        vk = VK_RETURN
    elif char == ' ':
        vk = VK_SPACE
    else:
        vk = ord(char.upper())
    
    send_key(vk)
    time.sleep(0.05)
    release_key(vk)
    time.sleep(0.05)

def type_text_english(text, delay=0.05):
    """逐字输入英文文本（不支持中文）
    中文会乱码或为空，请使用 paste_text() 代替
    """
    print("=== 模拟键盘输入（英文）===")
    print(f"正在输入文本: {text}")
    for char in text:
        type_char(char)
        time.sleep(delay)
    print(f"文本输入完成: {text}")

def paste_text(text):
    """使用剪贴板粘贴方式输入文本（中文首选）
    支持中英文混合、空格、换行
    这是 Windows 上输入中文最可靠的方法
    """
    VK_CONTROL = 0x11
    VK_V = 0x56
    
    # 复制文本到剪贴板
    pyperclip.copy(text)
    print(f"📋 文本已复制到剪贴板: {text}")
    time.sleep(0.5)
    
    # 发送 Ctrl+V 粘贴
    send_key(VK_CONTROL)
    time.sleep(0.1)
    send_key(VK_V)
    time.sleep(0.1)
    release_key(VK_V)
    time.sleep(0.1)
    release_key(VK_CONTROL)
    
    print("✅ Ctrl+V 粘贴完成")
    time.sleep(1)
    return True

def send_enter():
    """发送回车键
    用途：选择搜索结果、发送消息
    """
    VK_RETURN = 0x0D
    print("正在发送回车键...")
    send_key(VK_RETURN)
    time.sleep(0.1)
    release_key(VK_RETURN)
    print("回车键发送完成！")
    return True

def send_tab(times=3):
    """发送 Tab 键（多次）
    用途：移动焦点到聊天输入框（通常需要按3次）
    """
    VK_TAB = 0x09
    print(f"正在发送 {times} 次 Tab 键...")
    for i in range(times):
        send_key(VK_TAB)
        time.sleep(0.1)
        release_key(VK_TAB)
        time.sleep(0.2)
    print(f"{times} 次 Tab 键发送完成！")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法:")
        print("  python keyboard_simulator.py paste '要输入的文本'")
        print("  python keyboard_simulator.py enter")
        print("  python keyboard_simulator.py tab [次数]")
        print("  python keyboard_simulator.py type '英文文本'")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "paste":
        text = sys.argv[2] if len(sys.argv) > 2 else "测试消息"
        paste_text(text)
    elif action == "enter":
        send_enter()
    elif action == "tab":
        times = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        send_tab(times)
    elif action == "type":
        text = sys.argv[2] if len(sys.argv) > 2 else "test"
        type_text_english(text)
    else:
        print(f"未知操作: {action}")
