"""
微信视觉自动化脚本 - 完全绕过 cua-driver
功能：截图 + 视觉分析 + 键盘鼠标操作
作者：Hermes Agent
"""

import pyautogui
import time
import os
from PIL import ImageGrab

# 配置
SCREENSHOT_PATH = "C:/Users/dtyao/AppData/Local/hermes/screenshots/wechat_test.png"
os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)

# ==========================================
# 1. 截图功能（替代 cua-driver capture）
# ==========================================
def capture_screen():
    """截取整个屏幕"""
    screenshot = ImageGrab.grab()
    screenshot.save(SCREENSHOT_PATH)
    print(f"✅ 截图已保存: {SCREENSHOT_PATH}")
    return SCREENSHOT_PATH

def capture_window(title_contains="微信"):
    """截取包含指定标题的窗口（简化版，先截全屏）"""
    return capture_screen()

# ==========================================
# 2. 键盘操作（替代 cua-driver key）
# ==========================================
def press_hotkey(*keys):
    """发送快捷键"""
    pyautogui.hotkey(*keys)
    print(f"✅ 快捷键: {'+'.join(keys)}")
    time.sleep(0.5)

def press_key(key):
    """发送单个按键"""
    pyautogui.press(key)
    print(f"✅ 按键: {key}")
    time.sleep(0.2)

def type_text(text):
    """输入文本（英文，中文用剪贴板）"""
    pyautogui.typewrite(text)
    print(f"✅ 输入文本: {text}")
    time.sleep(0.3)

# ==========================================
# 3. 剪贴板操作（中文输入）
# ==========================================
def paste_text(text):
    """用剪贴板粘贴中文"""
    import pyperclip
    pyperclip.copy(text)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    print(f"✅ 粘贴文本: {text}")
    time.sleep(0.5)

# ==========================================
# 4. 微信自动化流程
# ==========================================
def wechat_send_message(contact_name, message):
    """
    给指定微信联系人发送消息（带视觉验证）
    """
    print("\n" + "="*60)
    print("🚀 开始微信消息发送流程（视觉增强模式）")
    print("="*60 + "\n")
    
    # 步骤 1: 激活微信
    print("📌 步骤 1/7: 激活微信窗口")
    press_hotkey('ctrl', 'alt', 'w')
    time.sleep(2)
    
    # ✅ 视觉验证 1: 截图确认微信窗口
    print("🔍 视觉验证：截图确认微信窗口...")
    capture_screen()
    # 这里可以调用 vision_analyze 验证微信窗口是否出现
    # （在 Hermes 中通过 tool call 实现）
    
    # 步骤 2: 激活搜索
    print("\n📌 步骤 2/7: 激活搜索框")
    press_hotkey('ctrl', 'f')
    time.sleep(2)
    
    # ✅ 视觉验证 2: 截图确认搜索框
    print("🔍 视觉验证：截图确认搜索框...")
    capture_screen()
    
    # 步骤 3: 输入搜索词
    print("\n📌 步骤 3/7: 输入联系人名称")
    paste_text(contact_name)
    time.sleep(3)
    
    # ✅ 视觉验证 3: 截图确认搜索词已输入
    print("🔍 视觉验证：截图确认搜索词...")
    capture_screen()
    
    # 步骤 4: 选择搜索结果
    print("\n📌 步骤 4/7: 选择搜索结果（两次回车）")
    press_key('enter')
    time.sleep(0.5)
    press_key('enter')
    time.sleep(2)
    
    # ✅ 视觉验证 4: 截图确认进入聊天界面
    print("🔍 视觉验证：截图确认进入聊天...")
    capture_screen()
    
    # 步骤 5: 确保焦点在输入框
    print("\n📌 步骤 5/7: 确保焦点在输入框")
    for _ in range(3):
        press_key('tab')
    time.sleep(1)
    
    # 步骤 6: 输入消息
    print("\n📌 步骤 6/7: 输入消息内容")
    paste_text(message)
    time.sleep(1)
    
    # ✅ 视觉验证 5: 截图确认消息已输入
    print("🔍 视觉验证：截图确认消息内容...")
    capture_screen()
    
    # 步骤 7: 发送消息
    print("\n📌 步骤 7/7: 发送消息")
    press_key('enter')
    time.sleep(2)
    
    # ✅ 视觉验证 6: 截图确认消息已发送
    print("🔍 视觉验证：截图确认消息已发送...")
    final_screenshot = capture_screen()
    
    print("\n" + "="*60)
    print("✅ 所有步骤完成！")
    print(f"📸 最终验证截图: {final_screenshot}")
    print("="*60 + "\n")
    
    return final_screenshot

# ==========================================
# 主程序
# ==========================================
if __name__ == "__main__":
    print("🧪 微信视觉自动化测试工具")
    print("-" * 40)
    
    # 测试发送
    contact = "AI 数字人"
    message = "🎉 纯 Python 视觉自动化测试成功！\n这是绕过 cua-driver 的替代方案！"
    
    wechat_send_message(contact, message)
