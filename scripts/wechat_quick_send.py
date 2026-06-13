import ctypes
import time
import pyperclip

print("=== 微信快速消息发送 ===")
print("简化版，只执行核心步骤")

# Windows API函数
user32 = ctypes.windll.user32

# 虚拟键码
VK_CONTROL = 0x11
VK_MENU = 0x12      # Alt键
VK_W = 0x57
VK_F = 0x46
VK_RETURN = 0x0D
VK_DOWN = 0x28
VK_A = 0x41
VK_V = 0x56
VK_DELETE = 0x2E

def key_down(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)

def key_up(vk_code):
    user32.keybd_event(vk_code, 0, 2, 0)

def send_hotkey(*keys):
    """发送组合快捷键"""
    # 按下所有修饰键
    for key in keys[:-1]:
        key_down(key)
        time.sleep(0.05)
    
    # 按下主键
    key_down(keys[-1])
    time.sleep(0.1)
    
    # 释放所有键（逆序）
    for key in reversed(keys):
        key_up(key)
        time.sleep(0.05)
    
    time.sleep(0.5)

def press_key(vk_code):
    """按单个键"""
    key_down(vk_code)
    time.sleep(0.1)
    key_up(vk_code)
    time.sleep(0.1)

def main():
    print("开始快速发送...")
    
    # 1. 激活微信
    print("1. 激活微信")
    send_hotkey(VK_CONTROL, VK_MENU, VK_W)
    time.sleep(2)
    
    # 2. 激活搜索
    print("2. 激活搜索")
    send_hotkey(VK_CONTROL, VK_F)
    time.sleep(1)
    
    # 3. 清除并输入搜索
    print("3. 输入搜索内容")
    send_hotkey(VK_CONTROL, VK_A)  # 全选
    time.sleep(0.3)
    press_key(VK_DELETE)  # 删除
    time.sleep(0.5)
    
    # 使用剪贴板输入
    try:
        pyperclip.copy("AI 数字人")
        time.sleep(0.3)
        send_hotkey(VK_CONTROL, VK_V)  # 粘贴
        time.sleep(1)
    except:
        print("剪贴板失败，跳过")
    
    time.sleep(2)
    
    # 4. 选择联系人（尝试两种方法）
    print("4. 选择联系人")
    press_key(VK_RETURN)  # 方法1：直接回车
    time.sleep(1.5)
    press_key(VK_DOWN)    # 方法2：向下+回车
    time.sleep(0.5)
    press_key(VK_RETURN)
    time.sleep(2)
    
    # 5. 输入并发送消息
    print("5. 发送消息")
    try:
        pyperclip.copy("快速测试消息 " + time.strftime("%H:%M:%S"))
        time.sleep(0.3)
        send_hotkey(VK_CONTROL, VK_V)  # 粘贴
        time.sleep(0.5)
    except:
        print("消息输入失败")
    
    press_key(VK_RETURN)  # 发送
    time.sleep(1)
    
    print("\n✅ 快速发送完成")
    print("请检查微信是否收到消息")

if __name__ == "__main__":
    main()