"""
尝试启动微信
"""
import subprocess
import time
import os

# 常见的微信安装路径
wechat_paths = [
    r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    r"C:\Program Files\Tencent\WeChat\WeChat.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\WeChat\WeChat.exe"),
]

print("=" * 60)
print("尝试启动微信...")
print("=" * 60)

for path in wechat_paths:
    if os.path.exists(path):
        print(f"\n✅ 找到微信: {path}")
        print("   正在启动...")
        subprocess.Popen(path)
        time.sleep(3)
        print("   ✅ 微信已启动，请等待登录...")
        break
else:
    print("\n❌ 未找到微信安装路径")
    print("   请手动启动微信并登录！")
