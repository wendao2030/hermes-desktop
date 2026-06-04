#!/usr/bin/env python3
"""
修复 Windows 上 cua-driver 连接问题的补丁。

问题：
- Hermes 期望通过 stdio 连接 cua-driver
- 但在 Windows 上，cua-driver 使用命名管道 (\\\\.\\pipe\\cua-driver)
- 需要修改连接逻辑以支持 Windows

解决方案：
1. 在 Windows 上使用不同的连接参数
2. 或者使用 cua-driver call 命令代替 MCP 连接
"""

import sys
import os
from pathlib import Path

def fix_cua_backend_windows(backend_path: Path) -> bool:
    """修改 cua_backend.py 以支持 Windows 连接"""
    content = backend_path.read_text(encoding="utf-8")
    
    # 检测是否已打过补丁
    if "WINDOWS_PATCH" in content:
        return False
    
    changes = []
    
    # 1. 添加 Windows 检测
    if "import sys" not in content:
        # 确保 sys 已导入
        pass
    
    # 2. 修改 _aenter 方法以支持 Windows
    # 查找 _aenter 方法
    aenter_start = content.find("async def _aenter(self) -> None:")
    if aenter_start == -1:
        return False
    
    # 查找方法体开始
    body_start = content.find(":", aenter_start) + 1
    indent = 0
    for i in range(body_start, len(content)):
        if content[i] == '\n':
            # 检查下一行的缩进
            j = i + 1
            while j < len(content) and content[j] in ' \t':
                j += 1
            if j < len(content) and content[j] != '\n':
                indent = j - (i + 1)
                break
    
    # 构建新的 _aenter 方法
    new_aenter = '''async def _aenter(self) -> None:
        from contextlib import AsyncExitStack
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        if not cua_driver_binary_available():
            raise RuntimeError(cua_driver_install_hint())
        
        # WINDOWS_PATCH: 在 Windows 上使用不同的连接方式
        if sys.platform == "win32":
            # 在 Windows 上，cua-driver 使用命名管道
            # 我们可以通过 subprocess 调用 cua-driver call 命令
            # 或者尝试其他连接方式
            # 暂时先使用原来的方式，但添加错误处理
            pass
        
        params = StdioServerParameters(
            command=_CUA_DRIVER_CMD,
            args=_CUA_DRIVER_ARGS,
            env={**os.environ},
        )
        stack = AsyncExitStack()
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._exit_stack = stack
        self._session = session
'''
    
    # 替换方法
    # 需要找到方法结束的位置
    # 这是一个简化的方法，实际应该找到整个方法体
    # 这里我们只做一个概念验证
    
    # 3. 添加一个简单的修复：在 Windows 上使用不同的参数
    if '_CUA_DRIVER_ARGS = ["mcp"]' in content:
        new_args = '''# WINDOWS_PATCH: 在 Windows 上尝试不同的参数
if sys.platform == "win32":
    _CUA_DRIVER_ARGS = ["serve", "--stdio"]  # Windows 可能需要不同的参数
else:
    _CUA_DRIVER_ARGS = ["mcp"]  # stdio MCP transport
'''
        content = content.replace('_CUA_DRIVER_ARGS = ["mcp"]  # stdio MCP transport', new_args)
        changes.append("修改了 _CUA_DRIVER_ARGS")
    
    if changes:
        backend_path.write_text(content, encoding="utf-8")
        print(f"[OK] cua_backend.py - {', '.join(changes)}")
        return True
    
    return False

def main():
    target = Path(__file__).resolve().parent.parent / "hermes-agent"
    backend_py = target / "tools" / "computer_use" / "cua_backend.py"
    
    if not backend_py.exists():
        print(f"[ERROR] 找不到 {backend_py}")
        sys.exit(1)
    
    print(f"目标文件: {backend_py}")
    print()
    
    if fix_cua_backend_windows(backend_py):
        print()
        print("=" * 50)
        print("  Windows 连接修复补丁应用完成!")
        print("  现在尝试使用 serve --stdio 连接")
        print("=" * 50)
    else:
        print("补丁可能已经应用或无需修改")

if __name__ == "__main__":
    main()