"""
微信视觉自动化 - 完整发送流程
直接用 ctypes 调用 Windows API（避免 pyautogui 的 numpy 问题）
"""
import ctypes
import time
import pyperclip

# Windows API 常量
VK_CONTROL = 0x11
VK_F = 0x46
VK_RETURN = 0x0D
VK_TAB = 0x09

user32 = ctypes.windll.user32

def press_key(vk_code):
    """按下并释放一个键"""
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(0.2)

def press_hotkey(vk1, vk2):
    """按下组合键"""
    user32.keybd_event(vk1, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk2, 0, 2, 0)
    time.sleep(0.1)
    user32.keybd_event(vk1, 0, 2, 0)
    time.sleep(0.3)

def paste_text(text):
    """用剪贴板粘贴中文"""
    pyperclip.copy(text)
    time.sleep(0.3)
    press_hotkey(VK_CONTROL, ord('V'))

print("=" * 60)
print("🚀 微信消息发送 - 完整流程")
print("=" * 60)

# 步骤 2: 激活搜索
print("\n📌 步骤 2/6: 激活搜索框 (Ctrl+F)")
press_hotkey(VK_CONTROL, VK_F)
time.sleep(2)

# 步骤 3: 输入搜索词
print("\n📌 步骤 3/6: 输入联系人名称 (AI 数字人)")
paste_text("AI 数字人")
time.sleep(3)

# 步骤 4: 选择搜索结果
print("\n📌 步骤 4/6: 选择搜索结果 (两次回车)")
press_key(VK_RETURN)
time.sleep(0.5)
press_key(VK_RETURN)
time.sleep(2)

# 步骤 5: 确保焦点在输入框
print("\n📌 步骤 5/6: 移动焦点到输入框 (按3次Tab)")
for _ in range(3):
    press_key(VK_TAB)
time.sleep(1)

# 步骤 6: 输入并发送消息
print("\n📌 步骤 6/6: 输入并发送消息")
message = "🎉 Python 视觉自动化测试成功！\n这是绕过 cua-driver 的纯 Python 方案！"
paste_text(message)
time.sleep(1)

print("\n📤 按回车发送消息...")
press_key(VK_RETURN)
time.sleep(2)

print("\n" + "=" * 60)
print("✅ 所有发送步骤已完成！")
print("=" * 60)
print("\n👀 请检查微信的「AI 数字人」聊天窗口，看看是否收到消息！")
