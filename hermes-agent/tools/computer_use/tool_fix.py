"""
临时修复：让 computer_use 在 Windows 上可用
"""

import sys
import os

# 原始文件路径
original_file = r"C:\Users\dtyao\AppData\Local\hermes\hermes-agent\tools\computer_use\tool.py"

# 读取原始文件
with open(original_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 修改 check_computer_use_requirements 函数
# 将 sys.platform != "darwin" 改为 sys.platform not in ["darwin", "win32"]
old_check = '''def check_computer_use_requirements() -> bool:
    """Return True iff computer_use can run on this host.

    Conditions: macOS + cua-driver binary installed (or override via env).
    """
    if sys.platform != "darwin":
        return False
    from tools.computer_use.cua_backend import cua_driver_binary_available
    return cua_driver_binary_available()'''

new_check = '''def check_computer_use_requirements() -> bool:
    """Return True iff computer_use can run on this host.

    Conditions: macOS/Windows + cua-driver binary installed (or override via env).
    """
    if sys.platform not in ["darwin", "win32"]:
        return False
    from tools.computer_use.cua_backend import cua_driver_binary_available
    return cua_driver_binary_available()'''

if old_check in content:
    content = content.replace(old_check, new_check)
    print("成功修改 check_computer_use_requirements 函数")
else:
    print("警告：未找到原函数，可能格式有变化")
    # 尝试另一种方式
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'if sys.platform != "darwin":' in line:
            lines[i] = '    if sys.platform not in ["darwin", "win32"]:'
            content = '\n'.join(lines)
            print(f"在第 {i+1} 行修改成功")
            break

# 保存修改
with open(original_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("修改完成！现在 computer_use 应该支持 Windows 了")