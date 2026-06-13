# -*- coding: utf-8 -*-
"""
粘贴测试消息到微信聊天输入框
"""
import pyperclip
import ctypes
import time

user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_V = 0x56

# 测试消息内容
TEST_MESSAGE = "这是视觉增强模式的测试消息 🎉\n如果能看到这条消息，说明发送流程正常！"

# 复制到剪贴板
pyperclip.copy(TEST_MESSAGE)
print(f"📋 消息已复制到剪贴板:\n{TEST_MESSAGE}")
time.sleep(0.3)

# 发送 Ctrl+V 粘贴
print("\n正在粘贴到聊天输入框...")
user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.1)
user32.keybd_event(VK_V, 0, 0, 0)
time.sleep(0.1)
user32.keybd_event(VK_V, 0, 2, 0)
time.sleep(0.1)
user32.keybd_event(VK_CONTROL, 0, 2, 0)

time.sleep(0.5)
print("✅ 消息粘贴完成！")
print("接下来按回车键发送...")
