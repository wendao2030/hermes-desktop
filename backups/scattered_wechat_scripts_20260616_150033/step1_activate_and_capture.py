"""
微信视觉自动化 - 步骤1：激活微信 + 截图
"""
import pyautogui
import time
from PIL import ImageGrab
import os

# 截图保存路径
SCREENSHOT_DIR = "C:/Users/dtyao/AppData/Local/hermes/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

print("=" * 50)
print("🧪 微信视觉验证测试 - 步骤1：激活 + 截图")
print("=" * 50)

# 1. 激活微信
print("\n1️⃣  发送 Ctrl+Alt+W 激活微信...")
pyautogui.hotkey('ctrl', 'alt', 'w')
time.sleep(2)

# 2. 截图
print("\n2️⃣  截取屏幕...")
screenshot_path = os.path.join(SCREENSHOT_DIR, "wechat_activation_test.png")
screenshot = ImageGrab.grab()
screenshot.save(screenshot_path)

print(f"\n✅ 截图已保存: {screenshot_path}")
print("\n" + "=" * 50)
print("📋 下一步: 调用 vision_analyze 分析这张截图")
print("=" * 50)

# 返回截图路径给 Hermes
print(f"\nSCREENSHOT_PATH={screenshot_path}")
