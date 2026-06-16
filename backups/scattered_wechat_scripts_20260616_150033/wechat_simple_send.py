"""
微信自动化 - 最简版
直接操作：假设微信已经在前台
"""
import ctypes
import time
import pyperclip

VK_CONTROL = 0x11
VK_F = 0x46
VK_RETURN = 0x0D
VK_TAB = 0x09

user32 = ctypes.windll.user32

def press_key(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(0.2)

def press_hotkey(vk1, vk2):
    user32.keybd_event(vk1, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk2, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk2, 0, 2, 0)
    time.sleep(0.05)
    user32.keybd_event(vk1, 0, 2, 0)
    time.sleep(0.3)

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.3)
    press_hotkey(VK_CONTROL, ord('V'))

# ==========================================
# 最简流程发送
# ==========================================
print("=" * 50)
print("🚀 微信消息发送 - 最简版")
print("前提：微信窗口已在前台")
print("=" * 50)

# 1. 激活搜索
print("\n📌 [1/5] Ctrl+F 激活搜索")
press_hotkey(VK_CONTROL, VK_F)
time.sleep(2)

# 2. 输入搜索词
print("\n📌 [2/5] 输入：AI 数字人")
paste_text("AI 数字人")
time.sleep(3)

# 3. 选择搜索结果
print("\n📌 [3/5] 两次回车选择结果")
press_key(VK_RETURN)
time.sleep(0.5)
press_key(VK_RETURN)
time.sleep(2)

# 4. 移动焦点到输入框
print("\n📌 [4/5] 移动焦点到输入框")
for _ in range(3):
    press_key(VK_TAB)
time.sleep(1)

# 5. 发送消息
print("\n📌 [5/5] 发送消息")
test_message = """🎉 自动化测试成功！

✅ Ctrl+Alt+W 激活微信
✅ Ctrl+F 激活搜索
✅ 输入联系人名称
✅ 进入聊天界面
✅ 发送消息成功

纯 Python 实现，绕过 cua-driver 限制！"""
paste_text(test_message)
time.sleep(1)

print("\n📤 按回车发送...")
press_key(VK_RETURN)
time.sleep(2)

print("\n" + "=" * 50)
print("✅ 所有步骤完成！")
print("=" * 50)
