import ctypes
import time
import pyperclip


def press_key(user32, vk, delay=0.08):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(delay)
    user32.keybd_event(vk, 0, 2, 0)
    time.sleep(delay)


def hotkey(user32, *keys):
    for vk in keys:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
    for vk in reversed(keys):
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.05)


def paste_text(user32, text):
    VK_CONTROL = 0x11
    VK_V = 0x56
    pyperclip.copy(text)
    time.sleep(0.5)
    hotkey(user32, VK_CONTROL, VK_V)
    time.sleep(1)


def main():
    print("=== 给姐姐发送微信测试信息 ===")
    user32 = ctypes.windll.user32

    VK_CONTROL = 0x11
    VK_F = 0x46
    VK_RETURN = 0x0D
    VK_BACK = 0x08

    contact = "姐姐"
    message = "姐姐您好！这是Hermes Agent发送的微信自动化测试消息，请确认是否收到。"

    print("1. 激活微信窗口...")
    hwnd = user32.FindWindowW(None, "微信")
    if not hwnd:
        print("ERROR: 未找到微信窗口")
        return 1
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(2)
    print("OK: 微信窗口已激活")

    print("2. 打开搜索框 Ctrl+F...")
    hotkey(user32, VK_CONTROL, VK_F)
    time.sleep(2)

    print("3. 清空搜索框...")
    # 先全选再退格，避免残留；再多按几次退格兜底
    hotkey(user32, VK_CONTROL, 0x41)  # Ctrl+A
    press_key(user32, VK_BACK)
    for _ in range(8):
        press_key(user32, VK_BACK, 0.04)
    time.sleep(0.5)

    print(f"4. 粘贴联系人名称: {contact}")
    paste_text(user32, contact)
    time.sleep(3)

    print("5. 回车选择第一个搜索结果...")
    press_key(user32, VK_RETURN)
    time.sleep(3)

    print(f"6. 粘贴消息: {message}")
    paste_text(user32, message)
    time.sleep(1)

    print("7. 回车发送消息...")
    press_key(user32, VK_RETURN)
    time.sleep(1)

    print("DONE: 已执行发送流程，请检查是否发给了姐姐。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
