import ctypes
import time
import subprocess
import sys
import os
import pyperclip

print("=== 微信消息发送终极解决方案 ===")
print("完全绕过cua-driver，使用纯Python Windows API")
print("目标: 向'AI 数字人'发送测试消息")

# Windows API函数
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 虚拟键码
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_DOWN = 0x28      # 向下箭头
VK_UP = 0x26        # 向上箭头
VK_TAB = 0x09       # Tab键
VK_ESCAPE = 0x1B    # Esc键
VK_A = 0x41
VK_V = 0x56
VK_BACK = 0x08      # Backspace键
VK_DELETE = 0x2E    # Delete键

def find_wechat_window():
    """查找微信窗口句柄"""
    print("查找微信窗口...")
    
    def enum_windows_callback(hwnd, windows):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "微信" in title or "WeChat" in title:
                    windows.append((hwnd, title))
        return True
    
    windows = []
    enum_func = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
    user32.EnumWindows(enum_func(enum_windows_callback), ctypes.byref(ctypes.c_int(id(windows))))
    
    return windows

def activate_window(hwnd):
    """激活指定窗口"""
    print(f"激活窗口句柄: {hwnd}")
    
    # 先最小化再恢复，确保窗口在前台
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.5)
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.5)
    
    # 设置前景窗口
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # 模拟Alt键激活
    user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(VK_MENU, 0, 2, 0)  # KEYEVENTF_KEYUP
    time.sleep(0.5)

def send_keys(*keys, delay=0.1):
    """发送按键序列"""
    for key in keys:
        user32.keybd_event(key, 0, 0, 0)
        time.sleep(delay)
        user32.keybd_event(key, 0, 2, 0)
        time.sleep(delay)

def send_hotkey(*keys, delay=0.1):
    """发送组合快捷键"""
    print(f"发送快捷键: {keys}")
    
    # 按下所有修饰键
    for key in keys[:-1]:
        user32.keybd_event(key, 0, 0, 0)
        time.sleep(delay/2)
    
    # 按下主键
    user32.keybd_event(keys[-1], 0, 0, 0)
    time.sleep(delay)
    
    # 释放所有键（逆序）
    for key in reversed(keys):
        user32.keybd_event(key, 0, 2, 0)
        time.sleep(delay/2)
    
    time.sleep(1)

def type_chinese_text(text):
    """输入中文文本（使用剪贴板）"""
    print(f"输入中文文本: {text}")
    
    try:
        # 复制到剪贴板
        pyperclip.copy(text)
        time.sleep(0.5)
        
        # 粘贴
        send_hotkey(VK_CONTROL, VK_V)
        time.sleep(1)
        return True
    except Exception as e:
        print(f"剪贴板失败: {e}")
        return False

def type_english_text(text):
    """输入英文文本"""
    print(f"输入英文文本: {text}")
    
    for char in text:
        if char.isalpha():
            # 字母
            vk_code = ord(char.upper())
            send_keys(vk_code, delay=0.05)
        elif char.isdigit():
            # 数字
            vk_code = ord(char)
            send_keys(vk_code, delay=0.05)
        elif char == ' ':
            # 空格
            send_keys(0x20, delay=0.05)
        else:
            # 其他字符，暂时跳过
            print(f"跳过特殊字符: '{char}'")
            continue

def search_and_select_contact(contact_name):
    """搜索并选择联系人"""
    print(f"\n搜索联系人: {contact_name}")
    
    # 激活搜索
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(2)
    
    # 输入搜索内容
    if any('\u4e00' <= c <= '\u9fff' for c in contact_name):  # 检查是否包含中文
        print("检测到中文，使用剪贴板输入")
        type_chinese_text(contact_name)
    else:
        print("使用英文输入")
        type_english_text(contact_name)
    
    time.sleep(3)
    
    # 尝试选择联系人
    print("\n尝试选择联系人...")
    
    # 方法1: 直接回车（选择第一个结果）
    send_keys(VK_RETURN)
    time.sleep(2)
    
    # 检查是否成功
    windows = find_wechat_window()
    if windows:
        hwnd, title = windows[0]
        print(f"当前窗口标题: {title}")
        
        if contact_name in title:
            print(f"✅ 成功选择联系人: {contact_name}")
            return True
        else:
            print(f"❌ 选择错误，当前窗口: {title}")
            
            # 返回搜索
            send_keys(VK_ESCAPE)
            time.sleep(1)
            
            # 清除搜索
            send_hotkey(VK_CONTROL, VK_A)  # Ctrl+A全选
            time.sleep(0.5)
            send_keys(VK_DELETE)  # 删除
            time.sleep(1)
            
            # 重新输入
            type_chinese_text(contact_name)
            time.sleep(2)
            
            # 方法2: 按向下箭头再回车
            send_keys(VK_DOWN)
            time.sleep(0.5)
            send_keys(VK_RETURN)
            time.sleep(2)
            
            windows = find_wechat_window()
            if windows:
                hwnd, title = windows[0]
                if contact_name in title:
                    print(f"✅ 使用↓成功选择联系人: {contact_name}")
                    return True
    
    return False

def main():
    print("=== 开始微信消息发送 ===")
    
    # 1. 查找微信窗口
    windows = find_wechat_window()
    if not windows:
        print("❌ 未找到微信窗口，尝试激活...")
        
        # 尝试用快捷键激活
        send_hotkey(VK_CONTROL, VK_MENU, VK_W)
        time.sleep(3)
        
        windows = find_wechat_window()
        if not windows:
            print("❌ 仍然未找到微信窗口，请确保微信已打开")
            return
    
    print(f"找到微信窗口: {len(windows)}个")
    for hwnd, title in windows:
        print(f"  - 句柄: {hwnd}, 标题: {title}")
    
    # 2. 激活主窗口（第一个找到的）
    hwnd, title = windows[0]
    activate_window(hwnd)
    print(f"已激活窗口: {title}")
    time.sleep(2)
    
    # 3. 搜索并选择联系人
    contact_name = "AI 数字人"
    if not search_and_select_contact(contact_name):
        print(f"\n❌ 无法自动选择联系人: {contact_name}")
        print("\n请手动执行以下操作：")
        print(f"1. 确保微信窗口在前台")
        print(f"2. 按 Ctrl+F 激活搜索")
        print(f"3. 输入 '{contact_name}'")
        print(f"4. 使用方向键找到正确联系人")
        print(f"5. 按回车键选择")
        print(f"6. 然后告诉我是否成功进入聊天界面")
        return
    
    # 4. 输入测试消息
    print("\n=== 输入测试消息 ===")
    
    # 尝试中文消息
    test_message = "测试消息：这是来自Hermes Agent的自动化测试"
    if type_chinese_text(test_message):
        print("✅ 中文消息输入成功")
    else:
        # 回退到英文
        test_message = "Test message: This is an automated test from Hermes Agent"
        type_english_text(test_message)
        print("✅ 英文消息输入成功")
    
    time.sleep(1)
    
    # 5. 发送消息
    print("\n发送消息...")
    send_keys(VK_RETURN)
    time.sleep(2)
    
    print("\n=== 操作完成 ===")
    print(f"✅ 已尝试向 '{contact_name}' 发送测试消息")
    print("\n请检查：")
    print("1. 微信中是否显示了发送的测试消息？")
    print("2. 消息是否成功发送（有发送时间戳）？")
    print("3. 如果没收到，可能的原因：")
    print("   - 选择了错误的联系人")
    print("   - 消息发送失败")
    print("   - 网络问题")
    
    # 保存日志
    with open("wechat_send_log.txt", "w", encoding="utf-8") as f:
        f.write(f"发送时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"目标联系人: {contact_name}\n")
        f.write(f"测试消息: {test_message}\n")
        f.write("状态: 已尝试发送\n")
    
    print(f"\n日志已保存到: wechat_send_log.txt")

if __name__ == "__main__":
    main()