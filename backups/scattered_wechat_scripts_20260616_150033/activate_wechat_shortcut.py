"""
用微信全局快捷键激活：Ctrl+Alt+W
"""
import ctypes
import time

VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_W = ord('W')

user32 = ctypes.windll.user32

print("=" * 50)
print("用全局快捷键激活微信: Ctrl+Alt+W")
print("=" * 50)

# 发送 Ctrl+Alt+W
print("\n📡 发送 Ctrl+Alt+W...")
user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_MENU, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_W, 0, 0, 0)
time.sleep(0.1)
user32.keybd_event(VK_W, 0, 2, 0)
time.sleep(0.05)
user32.keybd_event(VK_MENU, 0, 2, 0)
time.sleep(0.05)
user32.keybd_event(VK_CONTROL, 0, 2, 0)
time.sleep(1)

print("\n✅ 快捷键已发送！")
print("👀 微信窗口应该弹出来了，请确认！")
