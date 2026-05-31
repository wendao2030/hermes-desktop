#!/usr/bin/env python3
"""
应用 Windows 支持补丁到 hermes-agent 源码。

用法:
    python patches/apply_windows_patch.py [hermes-agent目录]

    默认目标: 当前目录下的 hermes-agent/

修改内容:
    tool.py:
        - check_computer_use_requirements(): sys.platform != "darwin"
          → sys.platform not in ["darwin", "win32"]
    
    cua_backend.py:
        - _is_macos() → _is_supported_platform()  [darwin, win32, linux]
        - _is_arm_mac() 改用 sys.platform == "darwin" 直接判断
        - is_available() 调用更新
        - 所有 _is_macos() 调用 → _is_supported_platform()
        - 文档字符串: macOS-only → Cross-platform

幂等性:
    如果补丁已经应用过，脚本会检测到并跳过，不会重复修改。
    用 [PATCH-DTYAO] 标记检测是否已应用。

回滚:
    补丁修改是确定性的。要回滚，用 git checkout 还原这两个文件即可。
"""
import sys
import re
from pathlib import Path


def apply_tool_patch(tool_path: Path) -> bool:
    """修改 tool.py 中的平台检查。"""
    content = tool_path.read_text(encoding="utf-8")

    # 检测是否已打过补丁
    if "[PATCH-DTYAO]" in content or 'not in ["darwin", "win32"]' in content:
        return False

    # 替换 1: 平台判断
    old_guard = 'if sys.platform != "darwin":\n        return False'
    new_guard = 'if sys.platform not in ["darwin", "win32"]:\n        return False  # [PATCH-DTYAO] was: sys.platform != "darwin"'
    if old_guard in content:
        content = content.replace(old_guard, new_guard)

    tool_path.write_text(content, encoding="utf-8")
    return True


def apply_cua_backend_patch(backend_path: Path) -> bool:
    """修改 cua_backend.py 的平台相关代码。"""
    content = backend_path.read_text(encoding="utf-8")

    # 检测是否已打过补丁
    if "_is_supported_platform" in content:
        return False

    changes = 0

    # 1. 模块 docstring
    old = '"Cua-driver backend (macOS only)."'
    new = '"[PATCH-DTYAO] Cua-driver backend (Cross-platform). Original was macOS-only."'
    if old in content:
        content = content.replace(old, new)
        changes += 1

    # 2. _is_macos → _is_supported_platform
    old_func = 'def _is_macos() -> bool:\n    return sys.platform == "darwin"'
    new_func = (
        'def _is_supported_platform() -> bool:\n'
        '    """[PATCH-DTYAO] Original: _is_macos() → sys.platform == "darwin".\n'
        '    Expanded to support Windows and Linux."""\n'
        '    return sys.platform in ["darwin", "win32", "linux"]'
    )
    if old_func in content:
        content = content.replace(old_func, new_func)
        changes += 1

    # 3. _is_arm_mac: 将 _is_macos() 改为 sys.platform == "darwin"
    old_arm = 'def _is_arm_mac() -> bool:\n    return _is_macos() and platform.machine() == "arm64"'
    new_arm = (
        'def _is_arm_mac() -> bool:\n'
        '    return sys.platform == "darwin" and platform.machine() == "arm64"'
    )
    if old_arm in content:
        content = content.replace(old_arm, new_arm)
        changes += 1

    # 4. is_available 中的检查
    old_avail = "if not _is_macos():"
    new_avail = "if not _is_supported_platform():"
    if old_avail in content:
        content = content.replace(old_avail, new_avail)
        changes += 1

    # 5. 所有剩余的 _is_macos() 调用
    if "_is_macos()" in content:
        content = content.replace("_is_macos()", "_is_supported_platform()")
        changes += 1

    # 6. 文档中的 macOS-only → Cross-platform
    if "macOS-only" in content:
        content = content.replace("macOS-only", "Cross-platform")
        changes += 1

    # 7. (macOS → (Cross-platform
    if "(macOS" in content:
        content = content.replace("(macOS", "(Cross-platform")
        changes += 1

    if changes > 0:
        backend_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "hermes-agent"

    tool_py = target / "tools" / "computer_use" / "tool.py"
    backend_py = target / "tools" / "computer_use" / "cua_backend.py"

    if not tool_py.exists():
        print(f"[ERROR] 找不到 {tool_py}")
        sys.exit(1)
    if not backend_py.exists():
        print(f"[ERROR] 找不到 {backend_py}")
        sys.exit(1)

    print(f"目标目录: {target}")
    print()

    applied = False

    if apply_tool_patch(tool_py):
        print("[OK] tool.py — platform check expanded to [darwin, win32]")
        applied = True
    else:
        print("[SKIP] tool.py — patch already applied")

    if apply_cua_backend_patch(backend_py):
        print("[OK] cua_backend.py — _is_macos() -> _is_supported_platform()")
        applied = True
    else:
        print("[SKIP] cua_backend.py — patch already applied")

    if applied:
        print()
        print("=" * 50)
        print("  Windows 补丁应用完成!")
        print("  现在 computer_use 支持 Windows/macOS/Linux")
        print("=" * 50)
    else:
        print()
        print("所有补丁已应用，无需重复操作。")


if __name__ == "__main__":
    main()
