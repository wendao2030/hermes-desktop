"""
修复 cua_backend.py 以支持 Windows
"""

import sys
import os

# 原始文件路径
original_file = r"C:\Users\dtyao\AppData\Local\hermes\hermes-agent\tools\computer_use\cua_backend.py"

# 读取原始文件
with open(original_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改文件开头的描述
old_description = '"Cua-driver backend (macOS only)."'
new_description = '"Cua-driver backend (macOS/Windows/Linux)."'
content = content.replace(old_description, new_description)

# 2. 修改 _is_macos 函数为 _is_supported_platform
old_is_macos = '''def _is_macos() -> bool:
    return sys.platform == "darwin"'''

new_is_supported = '''def _is_supported_platform() -> bool:
    return sys.platform in ["darwin", "win32", "linux"]'''

content = content.replace(old_is_macos, new_is_supported)

# 3. 更新所有 _is_macos() 调用
content = content.replace('_is_macos()', '_is_supported_platform()')

# 4. 修改 _is_arm_mac 函数（可能不需要，但为了完整性）
old_is_arm_mac = '''def _is_arm_mac() -> bool:
    return _is_macos() and platform.machine() == "arm64"'''

new_is_arm_mac = '''def _is_arm_mac() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"'''

content = content.replace(old_is_arm_mac, new_is_arm_mac)

# 5. 修改 is_available 方法中的检查
old_is_available_check = '''    def is_available(self) -> bool:
        if not _is_macos():
            return False
        return cua_driver_binary_available()'''

new_is_available_check = '''    def is_available(self) -> bool:
        if not _is_supported_platform():
            return False
        return cua_driver_binary_available()'''

content = content.replace(old_is_available_check, new_is_available_check)

# 6. 修改其他描述
content = content.replace('macOS-only', 'Cross-platform')
content = content.replace('(macOS', '(Cross-platform')

# 保存修改
with open(original_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("成功修改 cua_backend.py 以支持 Windows/Linux！")
print("现在需要安装 cua-driver (Rust 版本)")